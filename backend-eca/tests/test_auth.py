"""Pruebas de autenticación — ECA-003.

Mismo enfoque que `test_health.py`/`test_db.py` (ECA-002): la lógica de
negocio (`auth_service`) se prueba sin PostgreSQL real, sustituyendo
`app.repositories.usuarios` por un repositorio en memoria vía monkeypatch —
evita depender de tipos específicos de Postgres (`CITEXT`, `gen_random_uuid`)
que una BD de prueba distinta (SQLite) no entendería. Los modelos ORM
(`Usuario`, `TokenRefresco`) se instancian igual, solo que nunca tocan una
sesión real: aquí actúan como simples contenedores de datos.

Criterios de aceptación del ticket ECA-003:
- Ninguna ruta devuelve o acepta contraseña en claro.
- El JWT tiene `exp`.
- Logout invalida el refresh.
- Un usuario en BAJA no puede autenticarse.
"""
from __future__ import annotations

import itertools
import uuid as uuid_lib
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.security import (
    ContrasenaDebilError,
    TokenInvalidoError,
    crear_access_token,
    decodificar_access_token,
    hash_contrasena,
    validar_fortaleza_contrasena,
    verificar_contrasena,
)
from app.models.token_refresco import TokenRefresco
from app.models.usuario import Usuario
from app.services import auth_service

CORREO = "tecnico@ejemplo.org"
CONTRASENA = "Correcta123"

_contador_ids = itertools.count(1)


class RepositorioEnMemoria:
    """Sustituto en memoria de `app.repositories.usuarios`, con la misma forma."""

    def __init__(self) -> None:
        self.usuarios_por_id: dict[int, Usuario] = {}
        self.usuarios_por_correo: dict[str, Usuario] = {}
        self.tokens_por_jti: dict[uuid_lib.UUID, TokenRefresco] = {}

    def agregar_usuario(self, usuario: Usuario) -> Usuario:
        usuario.id = next(_contador_ids)
        self.usuarios_por_id[usuario.id] = usuario
        self.usuarios_por_correo[usuario.correo] = usuario
        return usuario

    # --- misma firma que app.repositories.usuarios ---

    def obtener_por_correo(self, _db, correo: str) -> Usuario | None:
        return self.usuarios_por_correo.get(correo)

    def obtener_por_id(self, _db, usuario_id: int) -> Usuario | None:
        return self.usuarios_por_id.get(usuario_id)

    def crear_token_refresco(self, _db, *, usuario_id, jti, hash_token, expira_en, **kw) -> TokenRefresco:
        token = TokenRefresco(
            id=next(_contador_ids),
            usuario_id=usuario_id,
            jti=jti,
            hash_token=hash_token,
            expira_en=expira_en,
            emitido_en=datetime.now(timezone.utc),
        )
        self.tokens_por_jti[jti] = token
        return token

    def obtener_token_refresco_por_jti(self, _db, jti) -> TokenRefresco | None:
        return self.tokens_por_jti.get(jti)

    def revocar_token_refresco(self, _db, token: TokenRefresco, *, motivo: str) -> None:
        token.revocado_en = datetime.now(timezone.utc)
        token.motivo_revocacion = motivo

    def revocar_todos_los_tokens_de(self, _db, usuario_id: int, *, motivo: str) -> None:
        for token in self.tokens_por_jti.values():
            if token.usuario_id == usuario_id and token.revocado_en is None:
                self.revocar_token_refresco(_db, token, motivo=motivo)


class DBFalsa:
    def add(self, _obj) -> None:
        pass

    def commit(self) -> None:
        pass


@pytest.fixture
def repo_memoria(monkeypatch: pytest.MonkeyPatch) -> RepositorioEnMemoria:
    repo = RepositorioEnMemoria()
    for nombre in (
        "obtener_por_correo",
        "obtener_por_id",
        "crear_token_refresco",
        "obtener_token_refresco_por_jti",
        "revocar_token_refresco",
        "revocar_todos_los_tokens_de",
    ):
        monkeypatch.setattr(auth_service.repo, nombre, getattr(repo, nombre))
    return repo


@pytest.fixture
def usuario_activo(repo_memoria: RepositorioEnMemoria) -> Usuario:
    usuario = Usuario(
        uuid=uuid_lib.uuid4(),
        nombre="Ana",
        apellido_paterno="Pérez",
        correo=CORREO,
        contrasena_hash=hash_contrasena(CONTRASENA),
        estado="ACTIVO",
        requiere_cambio_contrasena=False,
    )
    return repo_memoria.agregar_usuario(usuario)


DB = DBFalsa()


@pytest.fixture(autouse=True)
def _entorno(env_valido: None) -> None:
    """`crear_access_token`/`decodificar_access_token` necesitan `SECRET_KEY`
    (vía `get_settings()`) en todas las pruebas de este módulo."""


# --- Unitarias: hash / JWT / fortaleza de contraseña -----------------------


def test_hash_contrasena_verifica_correctamente() -> None:
    hash_ = hash_contrasena(CONTRASENA)
    assert hash_ != CONTRASENA
    assert verificar_contrasena(CONTRASENA, hash_)
    assert not verificar_contrasena("otra-cosa", hash_)


def test_jwt_incluye_exp_y_expira() -> None:
    token, expira_en = crear_access_token(usuario_id=1)
    payload = jwt.decode(token, options={"verify_signature": False})
    assert "exp" in payload
    assert expira_en > datetime.now(timezone.utc)
    assert decodificar_access_token(token) == 1


def test_jwt_expirado_es_invalido() -> None:
    from app.core import security

    settings = security.get_settings()
    ahora = datetime.now(timezone.utc)
    payload = {"sub": "1", "iat": ahora - timedelta(minutes=20), "exp": ahora - timedelta(minutes=5)}
    token_vencido = jwt.encode(payload, settings.SECRET_KEY, algorithm=security.ALGORITMO_JWT)

    with pytest.raises(TokenInvalidoError):
        decodificar_access_token(token_vencido)


@pytest.mark.parametrize("contrasena", ["corto1", "sinnumeros", "12345678901", ""])
def test_contrasena_debil_rechazada(contrasena: str) -> None:
    with pytest.raises(ContrasenaDebilError):
        validar_fortaleza_contrasena(contrasena)


def test_contrasena_fuerte_aceptada() -> None:
    validar_fortaleza_contrasena("Correcta123")  # no lanza


# --- Servicio: login / refresh / logout / estado del usuario ---------------


def test_login_correcto_emite_par_de_tokens(usuario_activo: Usuario) -> None:
    access_token, refresh_token, expira_en = auth_service.login(DB, correo=CORREO, contrasena=CONTRASENA)
    assert access_token
    assert refresh_token
    assert expira_en > datetime.now(timezone.utc)
    assert decodificar_access_token(access_token) == usuario_activo.id


def test_login_contrasena_incorrecta_rechazado(usuario_activo: Usuario) -> None:
    with pytest.raises(auth_service.CredencialesInvalidasError):
        auth_service.login(DB, correo=CORREO, contrasena="incorrecta")


def test_login_correo_inexistente_rechazado(repo_memoria: RepositorioEnMemoria) -> None:
    with pytest.raises(auth_service.CredencialesInvalidasError):
        auth_service.login(DB, correo="no-existe@ejemplo.org", contrasena=CONTRASENA)


@pytest.mark.parametrize("estado", ["SUSPENDIDO", "BAJA"])
def test_login_usuario_no_activo_rechazado(usuario_activo: Usuario, estado: str) -> None:
    usuario_activo.estado = estado
    with pytest.raises(auth_service.UsuarioNoAutorizadoError):
        auth_service.login(DB, correo=CORREO, contrasena=CONTRASENA)


def test_refresh_rota_el_token_y_el_anterior_deja_de_servir(usuario_activo: Usuario) -> None:
    _, refresh_1, _ = auth_service.login(DB, correo=CORREO, contrasena=CONTRASENA)

    _, refresh_2, _ = auth_service.refrescar(DB, refresh_token=refresh_1)
    assert refresh_2 != refresh_1

    with pytest.raises(auth_service.RefreshTokenInvalidoError):
        auth_service.refrescar(DB, refresh_token=refresh_1)


def test_refresh_desconocido_rechazado(repo_memoria: RepositorioEnMemoria) -> None:
    with pytest.raises(auth_service.RefreshTokenInvalidoError):
        auth_service.refrescar(DB, refresh_token=f"{uuid_lib.uuid4()}.no-existe")


def test_refresh_expirado_rechazado(usuario_activo: Usuario, repo_memoria: RepositorioEnMemoria) -> None:
    _, refresh_token, _ = auth_service.login(DB, correo=CORREO, contrasena=CONTRASENA)

    jti = next(iter(repo_memoria.tokens_por_jti))
    repo_memoria.tokens_por_jti[jti].expira_en = datetime.now(timezone.utc) - timedelta(days=1)

    with pytest.raises(auth_service.RefreshTokenInvalidoError):
        auth_service.refrescar(DB, refresh_token=refresh_token)


def test_logout_revoca_el_refresh(usuario_activo: Usuario) -> None:
    _, refresh_token, _ = auth_service.login(DB, correo=CORREO, contrasena=CONTRASENA)

    auth_service.logout(DB, refresh_token=refresh_token)

    with pytest.raises(auth_service.RefreshTokenInvalidoError):
        auth_service.refrescar(DB, refresh_token=refresh_token)


def test_logout_con_token_desconocido_no_lanza(repo_memoria: RepositorioEnMemoria) -> None:
    auth_service.logout(DB, refresh_token="no-existe.tampoco")  # no debe lanzar


def test_cambiar_contrasena_revoca_sesiones_existentes(usuario_activo: Usuario) -> None:
    _, refresh_token, _ = auth_service.login(DB, correo=CORREO, contrasena=CONTRASENA)

    auth_service.cambiar_contrasena(
        DB, usuario=usuario_activo, contrasena_actual=CONTRASENA, contrasena_nueva="OtraBuena456"
    )

    with pytest.raises(auth_service.RefreshTokenInvalidoError):
        auth_service.refrescar(DB, refresh_token=refresh_token)
    assert verificar_contrasena("OtraBuena456", usuario_activo.contrasena_hash)


def test_cambiar_contrasena_actual_incorrecta_rechazado(usuario_activo: Usuario) -> None:
    with pytest.raises(auth_service.CredencialesInvalidasError):
        auth_service.cambiar_contrasena(
            DB, usuario=usuario_activo, contrasena_actual="mala", contrasena_nueva="OtraBuena456"
        )


def test_cambiar_contrasena_debil_rechazada(usuario_activo: Usuario) -> None:
    with pytest.raises(ContrasenaDebilError):
        auth_service.cambiar_contrasena(
            DB, usuario=usuario_activo, contrasena_actual=CONTRASENA, contrasena_nueva="debil"
        )


# --- HTTP: forma de la API, sin contraseñas en claro ------------------------


@pytest.fixture
def cliente(env_valido: None) -> TestClient:
    from app.main import crear_app

    return TestClient(crear_app())


def test_login_http_no_expone_contrasena_en_respuesta(env_valido: None) -> None:
    """No asume que haya (o no haya) una BD real alcanzable con estas
    credenciales de prueba: solo confirma que, gane quien gane, la
    contraseña enviada nunca aparece reflejada en la respuesta. Con
    `raise_server_exceptions=False` un 500 real (p. ej. sin BD) se devuelve
    como respuesta en vez de propagar la excepción al test."""
    from app.main import crear_app

    cliente_tolerante = TestClient(crear_app(), raise_server_exceptions=False)
    respuesta = cliente_tolerante.post(
        "/auth/login", json={"correo": "nadie@ejemplo.org", "contrasena": "lo-que-sea"}
    )
    assert respuesta.status_code in (401, 500, 503)
    assert "lo-que-sea" not in respuesta.text


def test_me_sin_token_es_401(cliente: TestClient) -> None:
    respuesta = cliente.get("/auth/me")
    assert respuesta.status_code == 401


def test_me_con_token_invalido_es_401(cliente: TestClient) -> None:
    respuesta = cliente.get("/auth/me", headers={"Authorization": "Bearer token-invalido"})
    assert respuesta.status_code == 401
