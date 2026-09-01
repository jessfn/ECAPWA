"""Pruebas de gestión de usuarios (CRUD, roles, import CSV) — ECA-004.

Mismo enfoque que `test_auth.py`: sin PostgreSQL real, sustituyendo
`app.repositories.usuarios`/`app.repositories.rbac` por repositorios en
memoria vía monkeypatch.

Criterios de aceptación cubiertos aquí:
- El import valida por fila y no crea nada si el lote se cancela.
- Toda alta/baja/cambio de rol queda en `auditoria_eventos` sin CURP completa
  ni contraseñas (`app/core/audit.py::sanear_datos_auditoria`).
"""
from __future__ import annotations

import itertools

import pytest

from app.core.audit import sanear_datos_auditoria
from app.core.security import validar_fortaleza_contrasena
from app.models.rbac import Rol, UsuarioRol
from app.models.usuario import Usuario
from app.services import importacion_usuarios_service, usuarios_service

_contador_ids = itertools.count(1)


class DBFalsa:
    def add(self, _obj) -> None:
        pass

    def flush(self) -> None:
        pass

    def commit(self) -> None:
        pass

    def refresh(self, _obj) -> None:
        pass


class RepoUsuariosEnMemoria:
    def __init__(self) -> None:
        self.por_correo: dict[str, Usuario] = {}
        self.tokens_revocados: list[tuple[int, str]] = []

    def obtener_por_correo(self, _db, correo: str) -> Usuario | None:
        return self.por_correo.get(correo)

    def crear_usuario(self, _db, usuario: Usuario) -> Usuario:
        usuario.id = next(_contador_ids)
        self.por_correo[usuario.correo] = usuario
        return usuario

    def revocar_todos_los_tokens_de(self, _db, usuario_id: int, *, motivo: str) -> None:
        self.tokens_revocados.append((usuario_id, motivo))


class RepoRbacEnMemoria:
    def __init__(self, claves_rol: set[str] = frozenset({"ADMIN", "TECNICO"})) -> None:
        self.roles = {clave: Rol(id=next(_contador_ids), clave=clave, nombre=clave) for clave in claves_rol}
        self.asignaciones: dict[int, list[str]] = {}

    def obtener_rol_por_clave(self, _db, clave: str) -> Rol | None:
        return self.roles.get(clave)

    def asignar_rol(self, _db, *, usuario_id: int, rol_id: int, asignado_por) -> None:
        clave = next(c for c, r in self.roles.items() if r.id == rol_id)
        self.asignaciones.setdefault(usuario_id, []).append(clave)

    def asignaciones_activas_de(self, _db, usuario_id: int) -> list:
        class _Asignacion:
            def __init__(self, rol: Rol) -> None:
                self.rol = rol

        return [_Asignacion(self.roles[c]) for c in self.asignaciones.get(usuario_id, [])]

    def reemplazar_roles(self, _db, *, usuario_id: int, claves_rol_nuevas: set[str], asignado_por) -> None:
        for clave in claves_rol_nuevas:
            if clave not in self.roles:
                raise ValueError(f"Rol desconocido o inactivo: {clave}")
        self.asignaciones[usuario_id] = list(claves_rol_nuevas)


@pytest.fixture
def repos(monkeypatch: pytest.MonkeyPatch) -> tuple[RepoUsuariosEnMemoria, RepoRbacEnMemoria]:
    repo_u = RepoUsuariosEnMemoria()
    repo_r = RepoRbacEnMemoria()

    for nombre in ("obtener_por_correo", "crear_usuario", "revocar_todos_los_tokens_de"):
        monkeypatch.setattr(usuarios_service.repo_usuarios, nombre, getattr(repo_u, nombre))
        monkeypatch.setattr(importacion_usuarios_service.repo_usuarios, nombre, getattr(repo_u, nombre))
    for nombre in ("obtener_rol_por_clave", "asignar_rol", "asignaciones_activas_de", "reemplazar_roles"):
        monkeypatch.setattr(usuarios_service.repo_rbac, nombre, getattr(repo_r, nombre))
        monkeypatch.setattr(importacion_usuarios_service.repo_rbac, nombre, getattr(repo_r, nombre))

    return repo_u, repo_r


@pytest.fixture
def actor(repos) -> Usuario:
    repo_u, repo_r = repos
    admin = Usuario(
        nombre="Ada", apellido_paterno="Admin", correo="admin@ejemplo.org", contrasena_hash="x"
    )
    return repo_u.crear_usuario(None, admin)


DB = DBFalsa()


# --- usuarios_service --------------------------------------------------


def test_crear_usuario_ok(repos, actor: Usuario) -> None:
    repo_u, repo_r = repos
    usuario, contrasena_temporal = usuarios_service.crear_usuario(
        DB,
        nombre="Beto",
        apellido_paterno="Técnico",
        apellido_materno=None,
        correo="beto@ejemplo.org",
        telefono=None,
        curp=None,
        claves_rol=["TECNICO"],
        actor=actor,
    )
    assert usuario.correo == "beto@ejemplo.org"
    assert usuario.requiere_cambio_contrasena is True
    validar_fortaleza_contrasena(contrasena_temporal)  # no lanza
    assert repo_r.asignaciones[usuario.id] == ["TECNICO"]


def test_crear_usuario_correo_duplicado_rechazado(repos, actor: Usuario) -> None:
    repo_u, _ = repos
    repo_u.por_correo["ya@ejemplo.org"] = Usuario(
        nombre="X", apellido_paterno="Y", correo="ya@ejemplo.org", contrasena_hash="x"
    )
    with pytest.raises(usuarios_service.CorreoDuplicadoError):
        usuarios_service.crear_usuario(
            DB,
            nombre="Beto",
            apellido_paterno="Técnico",
            apellido_materno=None,
            correo="ya@ejemplo.org",
            telefono=None,
            curp=None,
            claves_rol=[],
            actor=actor,
        )


def test_crear_usuario_rol_desconocido_rechazado(repos, actor: Usuario) -> None:
    with pytest.raises(usuarios_service.RolDesconocidoError):
        usuarios_service.crear_usuario(
            DB,
            nombre="Beto",
            apellido_paterno="Técnico",
            apellido_materno=None,
            correo="beto@ejemplo.org",
            telefono=None,
            curp=None,
            claves_rol=["FANTASMA"],
            actor=actor,
        )


def test_cambiar_estado_a_baja_revoca_tokens(repos, actor: Usuario) -> None:
    repo_u, _ = repos
    usuario, _ = usuarios_service.crear_usuario(
        DB,
        nombre="Beto",
        apellido_paterno="Técnico",
        apellido_materno=None,
        correo="beto@ejemplo.org",
        telefono=None,
        curp=None,
        claves_rol=[],
        actor=actor,
    )
    usuarios_service.cambiar_estado(DB, usuario=usuario, estado_nuevo="BAJA", actor=actor)
    assert (usuario.id, "BAJA_USUARIO") in repo_u.tokens_revocados
    assert usuario.estado == "BAJA"


def test_asignar_roles_rol_desconocido_rechazado(repos, actor: Usuario) -> None:
    usuario, _ = usuarios_service.crear_usuario(
        DB,
        nombre="Beto",
        apellido_paterno="Técnico",
        apellido_materno=None,
        correo="beto@ejemplo.org",
        telefono=None,
        curp=None,
        claves_rol=[],
        actor=actor,
    )
    with pytest.raises(usuarios_service.RolDesconocidoError):
        usuarios_service.asignar_roles(DB, usuario=usuario, claves_rol=["FANTASMA"], actor=actor)


def test_a_publico_con_roles_asignados_no_revienta(repos, actor: Usuario) -> None:
    """Regresión: `Usuario.roles` es la relación ORM (objetos `UsuarioRol`),
    no la lista de claves que expone `UsuarioPublico.roles: list[str]`. Un
    `Usuario` con al menos un rol ya asignado en la relación (como ocurre con
    cualquier usuario real tras iniciar sesión) reventaba `GET /auth/me` con
    un 500 porque `model_validate(usuario, from_attributes=True)` intentaba
    leer `usuario.roles` directo del ORM antes de que `a_publico` pudiera
    sustituirlo por la lista de claves correcta."""
    import uuid as uuid_lib

    repo_u, repo_r = repos
    usuario = Usuario(
        nombre="Jess",
        apellido_paterno="Admin",
        correo="jess@ejemplo.org",
        contrasena_hash="x",
        uuid=uuid_lib.uuid4(),
        estado="ACTIVO",
        requiere_cambio_contrasena=False,
    )
    repo_u.crear_usuario(None, usuario)
    rol = repo_r.roles["ADMIN"]
    usuario.roles.append(UsuarioRol(usuario_id=usuario.id, rol_id=rol.id, rol=rol))
    repo_r.asignaciones[usuario.id] = ["ADMIN"]

    publico = usuarios_service.a_publico(DB, usuario)

    assert publico.roles == ["ADMIN"]


def test_generar_contrasena_temporal_cumple_politica() -> None:
    for _ in range(20):
        validar_fortaleza_contrasena(usuarios_service.generar_contrasena_temporal())  # no lanza


# --- importacion_usuarios_service ---------------------------------------

CSV_VALIDO = (
    "nombre,apellido_paterno,apellido_materno,correo,curp,rol\n"
    "Ana,Pérez,López,ana@ejemplo.org,,TECNICO\n"
    "Beto,Gómez,,beto@ejemplo.org,,TECNICO\n"
)

CSV_CON_ERROR = (
    "nombre,apellido_paterno,apellido_materno,correo,curp,rol\n"
    "Ana,Pérez,López,ana@ejemplo.org,,TECNICO\n"
    "Beto,Gómez,,ana@ejemplo.org,,TECNICO\n"  # correo duplicado dentro del CSV
)

CSV_ROL_INEXISTENTE = (
    "nombre,apellido_paterno,apellido_materno,correo,curp,rol\n" "Ana,Pérez,López,ana@ejemplo.org,,FANTASMA\n"
)


def test_importar_usuarios_todo_valido_crea_todo(repos, actor: Usuario) -> None:
    repo_u, _ = repos
    resultado = importacion_usuarios_service.importar_usuarios(DB, contenido_csv=CSV_VALIDO, actor=actor)
    assert resultado.creados == 2
    assert resultado.con_error == 0
    assert "ana@ejemplo.org" in repo_u.por_correo
    assert "beto@ejemplo.org" in repo_u.por_correo
    for fila in resultado.detalle:
        assert fila.resultado == "creado"
        assert fila.contrasena_temporal


def test_importar_usuarios_con_error_no_crea_nada(repos, actor: Usuario) -> None:
    repo_u, _ = repos
    resultado = importacion_usuarios_service.importar_usuarios(DB, contenido_csv=CSV_CON_ERROR, actor=actor)
    assert resultado.creados == 0
    assert resultado.con_error >= 1
    assert "ana@ejemplo.org" not in repo_u.por_correo  # nada creado: el lote se cancela completo


def test_importar_usuarios_rol_inexistente_no_crea_nada(repos, actor: Usuario) -> None:
    repo_u, _ = repos
    resultado = importacion_usuarios_service.importar_usuarios(
        DB, contenido_csv=CSV_ROL_INEXISTENTE, actor=actor
    )
    assert resultado.creados == 0
    assert "ana@ejemplo.org" not in repo_u.por_correo


def test_importar_usuarios_columnas_faltantes_rechazado(repos, actor: Usuario) -> None:
    with pytest.raises(ValueError):
        importacion_usuarios_service.importar_usuarios(
            DB, contenido_csv="nombre,correo\nAna,ana@ejemplo.org\n", actor=actor
        )


# --- auditoría: nunca contraseñas ni CURP completo ----------------------


def test_sanear_datos_auditoria_excluye_campos_sensibles() -> None:
    saneado = sanear_datos_auditoria(
        {
            "correo": "ana@ejemplo.org",
            "contrasena": "secreta123",
            "contrasena_hash": "$argon2id$...",
            "curp": "PEXA900101HDFRXX01",
            "estado": "ACTIVO",
        }
    )
    assert saneado == {"correo": "ana@ejemplo.org", "estado": "ACTIVO"}


def test_sanear_datos_auditoria_none_pasa_none() -> None:
    assert sanear_datos_auditoria(None) is None
