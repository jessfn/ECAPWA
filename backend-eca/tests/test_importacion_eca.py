"""Pruebas de importación masiva de ECA — ECA-007.

Sin PostgreSQL real: `app.repositories.ecas`/`app.repositories.geo` se
sustituyen por repositorios en memoria vía monkeypatch (mismo patrón que
`test_usuarios.py`).

Criterios de aceptación cubiertos:
- Parser acepta CSV y XLSX.
- Archivo sin columna identificador estable → se rechaza entero, sin
  insertar ni deduplicar por nombre/municipio (DP-2).
- Detecta `clave_fuente` duplicada en el archivo, municipio inexistente,
  campos requeridos vacíos.
- Upsert por `clave_fuente` actualiza sin duplicar; confirmar dos veces el
  mismo lote es idempotente.
"""
from __future__ import annotations

import io
import itertools
import uuid as uuid_lib

import pytest
from openpyxl import Workbook

from app.models.eca import Eca
from app.models.geo import Estado, Municipio
from app.models.lote_importacion import LoteImportacion
from app.models.usuario import Usuario
from app.services import importacion_eca_service as svc

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


class RepoEcasEnMemoria:
    def __init__(self) -> None:
        self.lotes: dict[uuid_lib.UUID, LoteImportacion] = {}
        self.ecas_por_clave_fuente: dict[str, Eca] = {}

    def crear_lote(self, _db, lote: LoteImportacion) -> LoteImportacion:
        lote.id = next(_contador_ids)
        lote.uuid = uuid_lib.uuid4()
        self.lotes[lote.uuid] = lote
        return lote

    def obtener_lote_por_uuid(self, _db, lote_uuid) -> LoteImportacion | None:
        return self.lotes.get(lote_uuid)

    def obtener_por_clave_fuente(self, _db, clave_fuente: str) -> Eca | None:
        return self.ecas_por_clave_fuente.get(clave_fuente)

    def crear_eca(self, _db, eca: Eca) -> Eca:
        eca.id = next(_contador_ids)
        self.ecas_por_clave_fuente[eca.clave_fuente] = eca
        return eca


@pytest.fixture
def geo_semilla() -> tuple[dict[str, Estado], dict[str, Municipio]]:
    estado = Estado(id=1, clave_inegi="09", nombre="Ciudad de México", abreviatura="CMX")
    municipio = Municipio(id=1, estado_id=1, clave_inegi="09002", nombre="Azcapotzalco")
    return {"09": estado}, {"09002": municipio}


@pytest.fixture
def repos(monkeypatch: pytest.MonkeyPatch, geo_semilla):
    estados_por_clave, municipios_por_clave = geo_semilla
    repo_e = RepoEcasEnMemoria()

    monkeypatch.setattr(svc.repo_ecas, "crear_lote", repo_e.crear_lote)
    monkeypatch.setattr(svc.repo_ecas, "obtener_lote_por_uuid", repo_e.obtener_lote_por_uuid)
    monkeypatch.setattr(svc.repo_ecas, "obtener_por_clave_fuente", repo_e.obtener_por_clave_fuente)
    monkeypatch.setattr(svc.repo_ecas, "crear_eca", repo_e.crear_eca)
    monkeypatch.setattr(svc.repo_geo, "listar_estados", lambda _db: list(estados_por_clave.values()))
    monkeypatch.setattr(
        svc.repo_geo, "listar_todos_municipios", lambda _db: list(municipios_por_clave.values())
    )
    return repo_e


@pytest.fixture
def actor() -> Usuario:
    return Usuario(id=1, nombre="Ada", apellido_paterno="Admin", correo="a@b.com", contrasena_hash="x")


DB = DBFalsa()

CSV_10_OK = "clave_fuente,nombre,estado_clave_inegi,municipio_clave_inegi\n" + "".join(
    f"ECA-{i:03d},Escuela {i},09,09002\n" for i in range(1, 11)
)

CSV_5_ERRORES = (
    "clave_fuente,nombre,estado_clave_inegi,municipio_clave_inegi\n"
    "ECA-100,Escuela 100,09,09002\n"
    "ECA-100,Escuela duplicada,09,09002\n"  # clave_fuente duplicada en archivo
    ",Sin identificador,09,09002\n"  # identificador vacío
    "ECA-101,,09,09002\n"  # nombre vacío
    "ECA-102,Escuela municipio malo,09,99999\n"  # municipio inexistente
    "ECA-103,Escuela estado malo,88,09002\n"  # estado inexistente
)

CSV_SIN_IDENTIFICADOR = "nombre,estado_clave_inegi,municipio_clave_inegi\nEscuela X,09,09002\n"


# --- iniciar_importacion (parseo + validación, nada se escribe todavía) --


def test_parser_acepta_csv(repos, actor: Usuario) -> None:
    lote = svc.iniciar_importacion(
        DB, contenido=CSV_10_OK.encode(), nombre_archivo="ecas.csv", columna_identificador=None, actor=actor
    )
    assert lote.estado == "VALIDADO"
    assert lote.filas_validas == 10
    assert lote.filas_con_error == 0


def test_parser_acepta_xlsx(repos, actor: Usuario) -> None:
    libro = Workbook()
    hoja = libro.active
    hoja.append(["clave_fuente", "nombre", "estado_clave_inegi", "municipio_clave_inegi"])
    hoja.append(["ECA-200", "Escuela XLSX", "09", "09002"])
    buffer = io.BytesIO()
    libro.save(buffer)

    lote = svc.iniciar_importacion(
        DB, contenido=buffer.getvalue(), nombre_archivo="ecas.xlsx", columna_identificador=None, actor=actor
    )
    assert lote.filas_validas == 1
    assert lote.resumen["filas_validas_datos"][0]["clave_fuente"] == "ECA-200"


def test_deteccion_de_errores_por_fila(repos, actor: Usuario) -> None:
    lote = svc.iniciar_importacion(
        DB, contenido=CSV_5_ERRORES.encode(), nombre_archivo="ecas.csv", columna_identificador=None, actor=actor
    )
    assert lote.filas_validas == 1  # solo la primera fila es válida
    assert lote.filas_con_error == 5
    mensajes = [e["mensaje"] for e in lote.resumen["errores"]]
    assert any("duplicado" in m.lower() for m in mensajes)
    assert any("Identificador vacío" in m for m in mensajes)
    assert any("Nombre requerido" in m for m in mensajes)
    assert any("Municipio desconocido" in m for m in mensajes)
    assert any("Estado desconocido" in m for m in mensajes)


def test_sin_identificador_estable_no_crea_lote(repos, actor: Usuario) -> None:
    with pytest.raises(svc.SinIdentificadorEstableError):
        svc.iniciar_importacion(
            DB,
            contenido=CSV_SIN_IDENTIFICADOR.encode(),
            nombre_archivo="ecas.csv",
            columna_identificador=None,
            actor=actor,
        )
    assert repos.lotes == {}  # nada se creó


def test_columna_identificador_explicita_pero_ausente_tambien_falla(repos, actor: Usuario) -> None:
    with pytest.raises(svc.SinIdentificadorEstableError):
        svc.iniciar_importacion(
            DB,
            contenido=CSV_SIN_IDENTIFICADOR.encode(),
            nombre_archivo="ecas.csv",
            columna_identificador="columna_que_no_existe",
            actor=actor,
        )


# --- confirmar_importacion (upsert real) ----------------------------------


def test_confirmar_crea_ecas_nuevas(repos, actor: Usuario) -> None:
    lote = svc.iniciar_importacion(
        DB, contenido=CSV_10_OK.encode(), nombre_archivo="ecas.csv", columna_identificador=None, actor=actor
    )
    lote_confirmado, creadas, actualizadas = svc.confirmar_importacion(DB, lote_uuid=lote.uuid, actor=actor)

    assert creadas == 10
    assert actualizadas == 0
    assert lote_confirmado.estado == "CONFIRMADO"
    assert len(repos.ecas_por_clave_fuente) == 10


def test_reimportar_mismo_archivo_actualiza_sin_duplicar(repos, actor: Usuario) -> None:
    lote1 = svc.iniciar_importacion(
        DB, contenido=CSV_10_OK.encode(), nombre_archivo="ecas.csv", columna_identificador=None, actor=actor
    )
    svc.confirmar_importacion(DB, lote_uuid=lote1.uuid, actor=actor)

    lote2 = svc.iniciar_importacion(
        DB, contenido=CSV_10_OK.encode(), nombre_archivo="ecas.csv", columna_identificador=None, actor=actor
    )
    _lote2_confirmado, creadas2, actualizadas2 = svc.confirmar_importacion(
        DB, lote_uuid=lote2.uuid, actor=actor
    )

    assert creadas2 == 0
    assert actualizadas2 == 10  # las mismas 10 claves_fuente, no duplicadas
    assert len(repos.ecas_por_clave_fuente) == 10


def test_confirmar_dos_veces_el_mismo_lote_es_idempotente(repos, actor: Usuario) -> None:
    lote = svc.iniciar_importacion(
        DB, contenido=CSV_10_OK.encode(), nombre_archivo="ecas.csv", columna_identificador=None, actor=actor
    )
    svc.confirmar_importacion(DB, lote_uuid=lote.uuid, actor=actor)
    assert len(repos.ecas_por_clave_fuente) == 10

    # Confirmar de nuevo el mismo lote no debe volver a insertar/actualizar.
    _lote_otra_vez, creadas2, actualizadas2 = svc.confirmar_importacion(DB, lote_uuid=lote.uuid, actor=actor)

    assert len(repos.ecas_por_clave_fuente) == 10
    assert creadas2 == 10  # devuelve el resumen guardado la primera vez, no vuelve a contar


def test_confirmar_lote_inexistente_lanza(repos, actor: Usuario) -> None:
    with pytest.raises(svc.LoteNoEncontradoError):
        svc.confirmar_importacion(DB, lote_uuid=uuid_lib.uuid4(), actor=actor)
