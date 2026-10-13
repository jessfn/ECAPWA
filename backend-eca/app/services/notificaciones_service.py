"""Lógica de notificaciones (admin -> técnicos) — publicación, programación,
vigencia, bandeja del técnico y medios.

Reglas de tiempo (pedido explícito): el panel y la PWA capturan y muestran
horario de la Ciudad de México; en la base todo es UTC. Una fecha que llegue
SIN zona se interpreta como CDMX.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import shutil
import time
import uuid as uuid_lib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import Session, selectinload

from app.core.audit import registrar_evento
from app.core.settings import get_settings
from app.core.storage import get_storage
from app.models.notificacion import Notificacion, NotificacionAdjunto, NotificacionLectura
from app.models.rbac import Rol, UsuarioRol
from app.models.usuario import Usuario

CDMX = ZoneInfo("America/Mexico_City")
CANAL_NOTIFICACIONES = "notificaciones_cambiaron"

MAX_IMAGEN = 25 * 1024 * 1024
MAX_VIDEO = 200 * 1024 * 1024
TAMANO_PARTE_MAX = 8 * 1024 * 1024
VIGENCIA_FIRMA_S = 7 * 24 * 3600


class NotificacionError(Exception):
    """Error de regla de negocio -> 422 / 404 en el router."""


class NoEncontradaError(NotificacionError):
    pass


# --------------------------------------------------------------------- tiempo
def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


def normalizar_fecha(valor: datetime | None) -> datetime | None:
    """Fecha sin zona = hora de CDMX; con zona se respeta. Devuelve UTC."""
    if valor is None:
        return None
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=CDMX)
    return valor.astimezone(timezone.utc)


# ------------------------------------------------------------- firma de medios
def _firmar(adjunto_uuid: str, exp: int) -> str:
    clave = get_settings().SECRET_KEY.encode()
    return hmac.new(clave, f"notif-media:{adjunto_uuid}:{exp}".encode(), hashlib.sha256).hexdigest()[:40]


def url_medio(adjunto_uuid: uuid_lib.UUID) -> str:
    exp = int(time.time()) + VIGENCIA_FIRMA_S
    return f"/notificaciones/medios/{adjunto_uuid}?exp={exp}&sig={_firmar(str(adjunto_uuid), exp)}"


def firma_valida(adjunto_uuid: str, exp: int, sig: str) -> bool:
    if exp < time.time():
        return False
    return hmac.compare_digest(_firmar(adjunto_uuid, exp), sig)


# ------------------------------------------------------------------ validación
def _url_valida(url: str | None) -> str | None:
    if url is None:
        return None
    url = url.strip()
    if not url:
        return None
    # Solo https:// o rutas internas de la app: nada de javascript:, data:, etc.
    if url.startswith("https://") or (url.startswith("/") and not url.startswith("//")):
        return url
    raise NotificacionError("La URL debe empezar con https:// o ser una ruta interna (/ruta).")


def _limpio(texto: str | None) -> str | None:
    if texto is None:
        return None
    texto = texto.strip()
    return texto or None


def _es_tecnico_activo(db: Session, usuario_id: int) -> bool:
    consulta = (
        select(Usuario.id)
        .join(UsuarioRol, UsuarioRol.usuario_id == Usuario.id)
        .join(Rol, Rol.id == UsuarioRol.rol_id)
        .where(
            Usuario.id == usuario_id,
            Usuario.estado == "ACTIVO",
            UsuarioRol.activo.is_(True),
            Rol.clave == "TECNICO",
        )
    )
    return db.execute(consulta).first() is not None


def contar_tecnicos_activos(db: Session) -> int:
    return db.execute(
        select(func.count(func.distinct(Usuario.id)))
        .join(UsuarioRol, UsuarioRol.usuario_id == Usuario.id)
        .join(Rol, Rol.id == UsuarioRol.rol_id)
        .where(Usuario.estado == "ACTIVO", UsuarioRol.activo.is_(True), Rol.clave == "TECNICO")
    ).scalar_one()


def buscar_destinatarios(db: Session, texto: str | None, limite: int = 15) -> list[Usuario]:
    consulta = (
        select(Usuario)
        .join(UsuarioRol, UsuarioRol.usuario_id == Usuario.id)
        .join(Rol, Rol.id == UsuarioRol.rol_id)
        .where(Usuario.estado == "ACTIVO", UsuarioRol.activo.is_(True), Rol.clave == "TECNICO")
    )
    if texto and texto.strip():
        patron = f"%{texto.strip()}%"
        nombre = Usuario.nombre + " " + Usuario.apellido_paterno + " " + func.coalesce(Usuario.apellido_materno, "")
        consulta = consulta.where(
            or_(nombre.ilike(patron), Usuario.correo.ilike(patron), Usuario.curp.ilike(patron))
        )
    consulta = consulta.order_by(func.lower(Usuario.apellido_paterno), func.lower(Usuario.nombre)).limit(limite)
    return list(db.execute(consulta).scalars())


def nombre_completo(u: Usuario | None) -> str | None:
    if u is None:
        return None
    return " ".join(p for p in (u.nombre, u.apellido_paterno, u.apellido_materno) if p)


# ----------------------------------------------------------- crear / publicar
def _avisar_cambio(db: Session, notif: Notificacion) -> None:
    """NOTIFY transaccional: los workers avisan por WebSocket a los técnicos
    conectados. El payload solo lleva a quién avisar, nunca el contenido."""
    payload = json.dumps({"destino": notif.destino, "usuario_id": notif.usuario_destino_id})
    db.execute(text("SELECT pg_notify(:c, :p)"), {"c": CANAL_NOTIFICACIONES, "p": payload})


def _publicar(db: Session, notif: Notificacion) -> None:
    notif.estado = "PUBLICADA"
    notif.publicada_en = ahora_utc()
    notif.destinatarios_total = contar_tecnicos_activos(db) if notif.destino == "TODOS" else 1
    _avisar_cambio(db, notif)


def crear(db: Session, *, actor: Usuario, datos) -> Notificacion:
    titulo = _limpio(datos.titulo)
    if not titulo:
        raise NotificacionError("El título es obligatorio.")

    if datos.destino == "USUARIO":
        if datos.usuario_destino_id is None or not _es_tecnico_activo(db, datos.usuario_destino_id):
            raise NotificacionError("El destinatario debe ser un técnico activo.")
        usuario_destino_id = datos.usuario_destino_id
    else:
        usuario_destino_id = None

    ahora = ahora_utc()
    programada = normalizar_fecha(datos.programada_para)
    expira = normalizar_fecha(datos.expira_en)
    if programada is not None and programada <= ahora + timedelta(seconds=30):
        programada = None  # "para ya": se publica de inmediato
    if expira is not None:
        inicio = programada or ahora
        if expira <= inicio:
            raise NotificacionError("La fecha de vencimiento debe ser posterior a la de publicación.")

    adjuntos: list[NotificacionAdjunto] = []
    for orden, adj_uuid in enumerate(datos.adjuntos):
        adj = db.execute(
            select(NotificacionAdjunto).where(
                NotificacionAdjunto.uuid == adj_uuid,
                NotificacionAdjunto.notificacion_id.is_(None),
                NotificacionAdjunto.subido_por == actor.id,
            )
        ).scalar_one_or_none()
        if adj is None:
            raise NotificacionError("Alguno de los archivos adjuntos no existe o ya se usó.")
        adj.orden = orden
        adjuntos.append(adj)

    notif = Notificacion(
        titulo=titulo,
        subtitulo=_limpio(datos.subtitulo),
        descripcion=_limpio(datos.descripcion),
        url=_url_valida(datos.url),
        url_texto=_limpio(datos.url_texto),
        tipo=datos.tipo,
        destino=datos.destino,
        usuario_destino_id=usuario_destino_id,
        estado="PROGRAMADA",
        programada_para=programada,
        expira_en=expira,
        creado_por=actor.id,
    )
    notif.adjuntos = adjuntos
    db.add(notif)
    db.flush()
    if programada is None:
        _publicar(db, notif)
    registrar_evento(
        db,
        accion="NOTIFICACION_CREADA",
        modulo="notificaciones",
        actor_usuario_id=actor.id,
        entidad_tipo="notificacion",
        entidad_id=notif.id,
        entidad_uuid=notif.uuid,
        descripcion=f"{'Programó' if programada else 'Envió'} la notificación «{titulo}» ({notif.destino}).",
    )
    db.commit()
    db.refresh(notif)
    return notif


def publicar_programadas(db: Session) -> list[Notificacion]:
    """Publica las notificaciones PROGRAMADAS cuya hora ya llegó. `SKIP LOCKED`
    evita que los 4 workers publiquen la misma dos veces."""
    pendientes = list(
        db.execute(
            select(Notificacion)
            .where(
                Notificacion.estado == "PROGRAMADA",
                Notificacion.programada_para.is_not(None),
                Notificacion.programada_para <= ahora_utc(),
            )
            .with_for_update(skip_locked=True)
        ).scalars()
    )
    publicadas = []
    for notif in pendientes:
        if notif.expira_en is not None and notif.expira_en <= ahora_utc():
            notif.estado = "RETIRADA"
            notif.retirada_en = ahora_utc()
            continue
        _publicar(db, notif)
        publicadas.append(notif)
    db.commit()
    return publicadas


def retirar(db: Session, *, actor: Usuario, notif_uuid: uuid_lib.UUID) -> Notificacion:
    notif = obtener_por_uuid(db, notif_uuid)
    if notif.estado == "RETIRADA":
        return notif
    notif.estado = "RETIRADA"
    notif.retirada_en = ahora_utc()
    _avisar_cambio(db, notif)
    registrar_evento(
        db,
        accion="NOTIFICACION_RETIRADA",
        modulo="notificaciones",
        actor_usuario_id=actor.id,
        entidad_tipo="notificacion",
        entidad_id=notif.id,
        entidad_uuid=notif.uuid,
        descripcion=f"Retiró la notificación «{notif.titulo}».",
    )
    db.commit()
    return notif


def obtener_por_id(db: Session, notif_id: int) -> Notificacion | None:
    return db.execute(
        select(Notificacion).options(selectinload(Notificacion.adjuntos)).where(Notificacion.id == notif_id)
    ).scalar_one_or_none()


def obtener_por_uuid(db: Session, notif_uuid: uuid_lib.UUID) -> Notificacion:
    notif = db.execute(
        select(Notificacion).options(selectinload(Notificacion.adjuntos)).where(Notificacion.uuid == notif_uuid)
    ).scalar_one_or_none()
    if notif is None:
        raise NoEncontradaError("Notificación no encontrada.")
    return notif


# ------------------------------------------------------------------- historial
def listar_admin(db: Session, *, estado: str | None, texto: str | None, limite: int = 200) -> list[Notificacion]:
    consulta = select(Notificacion).options(selectinload(Notificacion.adjuntos))
    if estado:
        consulta = consulta.where(Notificacion.estado == estado)
    if texto and texto.strip():
        consulta = consulta.where(Notificacion.titulo.ilike(f"%{texto.strip()}%"))
    consulta = consulta.order_by(Notificacion.creado_en.desc()).limit(limite)
    return list(db.execute(consulta).scalars())


def lecturas_por_notificacion(db: Session, ids: list[int]) -> dict[int, int]:
    if not ids:
        return {}
    filas = db.execute(
        select(NotificacionLectura.notificacion_id, func.count())
        .where(NotificacionLectura.notificacion_id.in_(ids))
        .group_by(NotificacionLectura.notificacion_id)
    ).all()
    return {i: n for i, n in filas}


def esta_vigente(n: Notificacion, ahora: datetime | None = None) -> bool:
    ahora = ahora or ahora_utc()
    return n.estado == "PUBLICADA" and (n.expira_en is None or n.expira_en > ahora)


# --------------------------------------------------------- bandeja del técnico
def _condicion_visible(usuario_id: int, ahora: datetime):
    return and_(
        Notificacion.estado == "PUBLICADA",
        or_(Notificacion.expira_en.is_(None), Notificacion.expira_en > ahora),
        or_(
            Notificacion.destino == "TODOS",
            and_(Notificacion.destino == "USUARIO", Notificacion.usuario_destino_id == usuario_id),
        ),
    )


def bandeja(
    db: Session, *, usuario: Usuario, limite: int = 50, desde: datetime | None = None
) -> tuple[list[tuple[Notificacion, bool]], int]:
    """(lista de (notificación, leída), total de no leídas). Solo técnicos."""
    if not _es_tecnico_activo(db, usuario.id):
        return [], 0
    ahora = ahora_utc()
    visible = _condicion_visible(usuario.id, ahora)
    # Un técnico dado de alta DESPUÉS del envío a "todos" no la recibe.
    visible = and_(visible, Notificacion.publicada_en >= _alta_efectiva(db, usuario))

    consulta = (
        select(Notificacion, NotificacionLectura.id.is_not(None))
        .options(selectinload(Notificacion.adjuntos))
        .outerjoin(
            NotificacionLectura,
            and_(NotificacionLectura.notificacion_id == Notificacion.id, NotificacionLectura.usuario_id == usuario.id),
        )
        .where(visible)
    )
    if desde is not None:
        consulta = consulta.where(Notificacion.publicada_en > normalizar_fecha(desde))
    consulta = consulta.order_by(Notificacion.publicada_en.desc()).limit(limite)
    filas = [(n, bool(leida)) for n, leida in db.execute(consulta).all()]

    no_leidas = db.execute(
        select(func.count())
        .select_from(Notificacion)
        .outerjoin(
            NotificacionLectura,
            and_(NotificacionLectura.notificacion_id == Notificacion.id, NotificacionLectura.usuario_id == usuario.id),
        )
        .where(visible, NotificacionLectura.id.is_(None))
    ).scalar_one()
    return filas, no_leidas


def _alta_efectiva(db: Session, usuario: Usuario) -> datetime:
    return usuario.creado_en


def marcar_leida(db: Session, *, usuario: Usuario, notif_uuid: uuid_lib.UUID) -> None:
    notif = db.execute(select(Notificacion).where(Notificacion.uuid == notif_uuid)).scalar_one_or_none()
    if notif is None or not db.execute(
        select(Notificacion.id).where(Notificacion.id == notif.id, _condicion_visible(usuario.id, ahora_utc()))
    ).first():
        raise NoEncontradaError("Notificación no encontrada.")
    db.execute(
        text(
            "INSERT INTO notificaciones_lecturas (notificacion_id, usuario_id) VALUES (:n, :u) "
            "ON CONFLICT (notificacion_id, usuario_id) DO NOTHING"
        ),
        {"n": notif.id, "u": usuario.id},
    )
    db.commit()


def marcar_todas_leidas(db: Session, *, usuario: Usuario) -> int:
    ahora = ahora_utc()
    resultado = db.execute(
        text(
            "INSERT INTO notificaciones_lecturas (notificacion_id, usuario_id) "
            "SELECT n.id, :u FROM notificaciones n WHERE n.estado = 'PUBLICADA' "
            "AND (n.expira_en IS NULL OR n.expira_en > :ahora) "
            "AND (n.destino = 'TODOS' OR n.usuario_destino_id = :u) "
            "ON CONFLICT (notificacion_id, usuario_id) DO NOTHING"
        ),
        {"u": usuario.id, "ahora": ahora},
    )
    db.commit()
    return resultado.rowcount or 0


# ------------------------------------------------------------------- medios
def _directorio_subidas() -> Path:
    base = Path(get_settings().STORAGE_DIR) / "notificaciones" / "_subidas"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _tipo_por_bytes(cabecera: bytes) -> tuple[str, str] | None:
    """(tipo, mime) por firma real del archivo (no por lo que diga el cliente)."""
    if cabecera.startswith(b"\xff\xd8\xff"):
        return "IMAGEN", "image/jpeg"
    if cabecera.startswith(b"\x89PNG\r\n\x1a\n"):
        return "IMAGEN", "image/png"
    if cabecera[:4] == b"RIFF" and cabecera[8:12] == b"WEBP":
        return "IMAGEN", "image/webp"
    if cabecera[:6] in (b"GIF87a", b"GIF89a"):
        return "IMAGEN", "image/gif"
    if cabecera[4:8] == b"ftyp":
        marca = cabecera[8:12]
        if marca in (b"heic", b"heix", b"mif1", b"msf1", b"hevc"):
            return "IMAGEN", "image/heic"
        if marca == b"qt  ":
            return "VIDEO", "video/quicktime"
        return "VIDEO", "video/mp4"
    if cabecera.startswith(b"\x1a\x45\xdf\xa3"):
        return "VIDEO", "video/webm"
    return None


def iniciar_subida(*, actor: Usuario, nombre: str, tamano: int, total_partes: int) -> uuid_lib.UUID:
    if tamano > MAX_VIDEO:
        raise NotificacionError("El archivo supera el máximo permitido (200 MB).")
    sid = uuid_lib.uuid4()
    carpeta = _directorio_subidas() / str(sid)
    carpeta.mkdir(parents=True)
    (carpeta / "meta.json").write_text(
        json.dumps({"usuario_id": actor.id, "nombre": nombre, "tamano": tamano, "partes": total_partes})
    )
    return sid


def _carpeta_subida(actor: Usuario, subida_id: uuid_lib.UUID) -> tuple[Path, dict]:
    carpeta = _directorio_subidas() / str(subida_id)
    meta_ruta = carpeta / "meta.json"
    if not meta_ruta.exists():
        raise NoEncontradaError("Subida no encontrada.")
    meta = json.loads(meta_ruta.read_text())
    if meta["usuario_id"] != actor.id:
        raise NoEncontradaError("Subida no encontrada.")
    return carpeta, meta


def ruta_parte(actor: Usuario, subida_id: uuid_lib.UUID, numero: int) -> Path:
    carpeta, meta = _carpeta_subida(actor, subida_id)
    if not 0 <= numero < meta["partes"]:
        raise NotificacionError("Número de parte inválido.")
    return carpeta / f"parte_{numero:04d}"


def finalizar_subida(db: Session, *, actor: Usuario, subida_id: uuid_lib.UUID) -> NotificacionAdjunto:
    carpeta, meta = _carpeta_subida(actor, subida_id)
    partes = [carpeta / f"parte_{i:04d}" for i in range(meta["partes"])]
    if not all(p.exists() for p in partes):
        raise NotificacionError("Faltan partes del archivo; reintenta la subida.")
    total = sum(p.stat().st_size for p in partes)
    if total != meta["tamano"]:
        raise NotificacionError("El archivo llegó incompleto; reintenta la subida.")

    with partes[0].open("rb") as f:
        cabecera = f.read(32)
    detectado = _tipo_por_bytes(cabecera)
    if detectado is None:
        shutil.rmtree(carpeta, ignore_errors=True)
        raise NotificacionError("Formato no permitido: solo imágenes (JPG, PNG, WEBP, GIF, HEIC) y videos (MP4, MOV, WEBM).")
    tipo, mime = detectado
    if tipo == "IMAGEN" and total > MAX_IMAGEN:
        shutil.rmtree(carpeta, ignore_errors=True)
        raise NotificacionError("La imagen supera el máximo permitido (25 MB).")

    adj_uuid = uuid_lib.uuid4()
    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif",
           "image/heic": "heic", "video/mp4": "mp4", "video/quicktime": "mov", "video/webm": "webm"}[mime]
    clave = f"notificaciones/{adj_uuid}.{ext}"
    destino = get_storage().ruta(clave)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("wb") as salida:
        for p in partes:
            with p.open("rb") as f:
                shutil.copyfileobj(f, salida, 1024 * 1024)
    shutil.rmtree(carpeta, ignore_errors=True)

    adj = NotificacionAdjunto(
        uuid=adj_uuid,
        tipo=tipo,
        mime=mime,
        nombre_original=meta["nombre"][:255],
        storage_clave=clave,
        tamano_bytes=total,
        subido_por=actor.id,
    )
    db.add(adj)
    db.commit()
    db.refresh(adj)
    return adj


def adjunto_por_uuid(db: Session, adj_uuid: uuid_lib.UUID) -> NotificacionAdjunto:
    adj = db.execute(select(NotificacionAdjunto).where(NotificacionAdjunto.uuid == adj_uuid)).scalar_one_or_none()
    if adj is None:
        raise NoEncontradaError("Archivo no encontrado.")
    return adj
