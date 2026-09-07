"""Acceso a datos de `Rol`/`Permiso`/`UsuarioRol` — ECA-004."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rbac import Permiso, Rol, UsuarioPermiso, UsuarioRol


def listar_roles_activos(db: Session) -> list[Rol]:
    return list(db.execute(select(Rol).where(Rol.activo.is_(True)).order_by(Rol.clave)).scalars())


def listar_permisos_activos(db: Session) -> list[Permiso]:
    return list(
        db.execute(select(Permiso).where(Permiso.activo.is_(True)).order_by(Permiso.clave)).scalars()
    )


def obtener_rol_por_clave(db: Session, clave: str) -> Rol | None:
    return db.execute(select(Rol).where(Rol.clave == clave, Rol.activo.is_(True))).scalar_one_or_none()


def permisos_efectivos_de(db: Session, usuario_id: int) -> set[str]:
    """Unión de los permisos de todos los roles activos del usuario CON los
    otorgados directamente a esa persona (`usuarios_permisos`, ECA-021) —
    el rol `USUARIO` no trae ningún permiso propio, así que sin la segunda
    mitad de esta unión no podría hacer nada."""
    from app.models.rbac import RolPermiso

    por_rol = db.execute(
        select(Permiso.clave)
        .join(RolPermiso, RolPermiso.permiso_id == Permiso.id)
        .join(UsuarioRol, UsuarioRol.rol_id == RolPermiso.rol_id)
        .where(
            UsuarioRol.usuario_id == usuario_id,
            UsuarioRol.activo.is_(True),
            Permiso.activo.is_(True),
        )
    ).scalars()
    return set(por_rol) | permisos_directos_de(db, usuario_id)


def permisos_directos_de(db: Session, usuario_id: int) -> set[str]:
    filas = db.execute(
        select(Permiso.clave)
        .join(UsuarioPermiso, UsuarioPermiso.permiso_id == Permiso.id)
        .where(UsuarioPermiso.usuario_id == usuario_id, Permiso.activo.is_(True))
    ).scalars()
    return set(filas)


def reemplazar_permisos_directos(
    db: Session, *, usuario_id: int, claves_nuevas: set[str], otorgado_por: int | None
) -> set[str]:
    """Deja otorgados a `usuario_id` EXACTAMENTE los permisos de
    `claves_nuevas` (reemplazo total, no incremental) — mismo criterio que
    `reemplazar_roles`."""
    permisos_por_clave = {p.clave: p for p in listar_permisos_activos(db)}
    desconocidas = claves_nuevas - set(permisos_por_clave)
    if desconocidas:
        raise ValueError(f"Permiso(s) desconocido(s): {sorted(desconocidas)}")

    actuales = list(
        db.execute(select(UsuarioPermiso).where(UsuarioPermiso.usuario_id == usuario_id)).scalars()
    )
    id_a_clave = {p.id: clave for clave, p in permisos_por_clave.items()}
    claves_actuales = {id_a_clave[up.permiso_id] for up in actuales if up.permiso_id in id_a_clave}

    for up in actuales:
        if id_a_clave.get(up.permiso_id) not in claves_nuevas:
            db.delete(up)

    for clave in claves_nuevas - claves_actuales:
        db.add(
            UsuarioPermiso(
                usuario_id=usuario_id, permiso_id=permisos_por_clave[clave].id, otorgado_por=otorgado_por
            )
        )

    db.flush()
    return claves_nuevas


def asignaciones_activas_de(db: Session, usuario_id: int) -> list[UsuarioRol]:
    return list(
        db.execute(
            select(UsuarioRol).where(UsuarioRol.usuario_id == usuario_id, UsuarioRol.activo.is_(True))
        ).scalars()
    )


def asignar_rol(db: Session, *, usuario_id: int, rol_id: int, asignado_por: int | None) -> UsuarioRol:
    asignacion = UsuarioRol(usuario_id=usuario_id, rol_id=rol_id, asignado_por=asignado_por)
    db.add(asignacion)
    db.flush()
    return asignacion


def revocar_asignacion(db: Session, asignacion: UsuarioRol) -> None:
    asignacion.activo = False
    asignacion.vigente_hasta = datetime.now(timezone.utc)
    db.add(asignacion)


def reemplazar_roles(
    db: Session, *, usuario_id: int, claves_rol_nuevas: set[str], asignado_por: int | None
) -> list[UsuarioRol]:
    """Deja activas exactamente las asignaciones de `claves_rol_nuevas`: revoca
    (baja lógica, conserva historial) las que sobran y crea las que faltan."""
    activas = asignaciones_activas_de(db, usuario_id)
    claves_activas = {a.rol.clave for a in activas}

    for asignacion in activas:
        if asignacion.rol.clave not in claves_rol_nuevas:
            revocar_asignacion(db, asignacion)

    nuevas: list[UsuarioRol] = []
    for clave in claves_rol_nuevas - claves_activas:
        rol = obtener_rol_por_clave(db, clave)
        if rol is None:
            raise ValueError(f"Rol desconocido o inactivo: {clave}")
        nuevas.append(asignar_rol(db, usuario_id=usuario_id, rol_id=rol.id, asignado_por=asignado_por))

    db.flush()
    return asignaciones_activas_de(db, usuario_id)
