"""Modelos SQLAlchemy del backend ECA.

Importar aquí cada modelo nuevo es necesario para que quede registrado en
``Base.metadata`` (usado por `alembic --autogenerate` y por los tests que
crean el esquema en memoria).
"""
from app.models.actividad import Actividad
from app.models.ambito import AmbitoTecnico
from app.models.asignacion_eca import AsignacionTecnicoEca
from app.models.auditoria import AuditoriaEvento
from app.models.catalogos import Modalidad, SistemaProductivo, Subtema, Tema, TipoActividad
from app.models.dispositivo import Dispositivo
from app.models.eca import Eca
from app.models.evidencia import ActividadEvidencia
from app.models.geo import Estado, Municipio
from app.models.jornada import Jornada
from app.models.lote_importacion import LoteImportacion
from app.models.parametro_config import ParametroConfig
from app.models.rbac import Permiso, Rol, RolPermiso, UsuarioRol
from app.models.solicitud_acceso import SolicitudAcceso
from app.models.token_refresco import TokenRefresco
from app.models.usuario import Usuario

__all__ = [
    "Usuario",
    "TokenRefresco",
    "Rol",
    "Permiso",
    "RolPermiso",
    "UsuarioRol",
    "AuditoriaEvento",
    "Estado",
    "Municipio",
    "Eca",
    "LoteImportacion",
    "AmbitoTecnico",
    "AsignacionTecnicoEca",
    "ParametroConfig",
    "Modalidad",
    "TipoActividad",
    "Tema",
    "Subtema",
    "SistemaProductivo",
    "Jornada",
    "Actividad",
    "ActividadEvidencia",
    "Dispositivo",
    "SolicitudAcceso",
]
