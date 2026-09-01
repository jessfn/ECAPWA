"""Smoke test end-to-end del MVP — ECA-020.

Recorre el flujo real que describe el ticket: alta de técnico → login →
bootstrap → jornada → actividad + evidencia → aparece en la consulta
admin. Usa la fixture `app_con_bd_real` (`tests/conftest.py`): se **salta**
si no hay `TEST_DATABASE_URL` alcanzable — en este entorno de desarrollo
sin PostgreSQL local se salta; en el servidor/CI con BD real, corre de
verdad. Es justo lo que el ticket pide: "debe pasar en CI local antes del
piloto" y "correr `test_smoke` contra el entorno de piloto".

Usa la propia capa de servicios para el alta (como haría `crear_admin.py`
o el panel), nunca contraseñas elegidas a mano: `crear_usuario` genera una
temporal aleatoria, que es la que se usa para el login de la prueba.
"""
from __future__ import annotations

import io
import uuid as uuid_lib
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def cliente(app_con_bd_real) -> TestClient:
    return TestClient(app_con_bd_real)


def _crear_tecnico_y_credenciales():
    """Alta de un técnico de prueba directamente por la capa de servicio,
    igual que haría `scripts/crear_admin.py` — nunca una contraseña elegida
    por la prueba."""
    from app.core.db import SessionLocal
    from app.services import usuarios_service

    db = SessionLocal()
    try:
        correo = f"smoke.{uuid_lib.uuid4().hex[:10]}@ejemplo-pruebas.org"
        usuario, contrasena_temporal = usuarios_service.crear_usuario(
            db,
            nombre="Smoke",
            apellido_paterno="Test",
            apellido_materno=None,
            correo=correo,
            telefono=None,
            curp=None,
            claves_rol=["TECNICO"],
            actor=None,
        )
        return correo, contrasena_temporal
    finally:
        db.close()


def test_flujo_completo_mvp(cliente: TestClient) -> None:
    correo, contrasena = _crear_tecnico_y_credenciales()

    # 1. Login
    respuesta = cliente.post("/auth/login", json={"correo": correo, "contrasena": contrasena})
    assert respuesta.status_code == 200, respuesta.text
    tokens = respuesta.json()
    cabeceras = {"Authorization": f"Bearer {tokens['access_token']}"}

    # 2. Bootstrap (subconjunto offline: catálogos + ECA del técnico)
    respuesta = cliente.get("/sync/bootstrap", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    bootstrap = respuesta.json()
    tipos = bootstrap["catalogos"]["tipos_actividad"]
    modalidades = bootstrap["catalogos"]["modalidades"]
    assert tipos and modalidades, "El bootstrap debe traer catálogos ya sembrados."

    # Tipo que no exige ECA ni evidencia — evita depender de datos de
    # geografía/ECA que este entorno de prueba no tiene por qué tener.
    tipo = next(t for t in tipos if not t["requiere_eca"] and not t["requiere_evidencia"])
    modalidad_id = modalidades[0]["id"]

    # 3. Jornada
    jornada_uuid = str(uuid_lib.uuid4())
    respuesta = cliente.post(
        "/jornadas",
        json={"uuid": jornada_uuid, "inicio_en": datetime.now(timezone.utc).isoformat()},
        headers=cabeceras,
    )
    assert respuesta.status_code == 201, respuesta.text

    # 4. Actividad
    actividad_uuid = str(uuid_lib.uuid4())
    respuesta = cliente.post(
        "/actividades",
        json={
            "uuid": actividad_uuid,
            "jornada_uuid": jornada_uuid,
            "modalidad_id": modalidad_id,
            "tipo_actividad_id": tipo["id"],
            "descripcion": "Actividad de smoke test end-to-end (ECA-020).",
            "fecha_hora": datetime.now(timezone.utc).isoformat(),
        },
        headers=cabeceras,
    )
    assert respuesta.status_code == 201, respuesta.text
    actividad = respuesta.json()

    # 5. Evidencia (imagen mínima válida)
    imagen = _jpeg_minimo()
    respuesta = cliente.post(
        f"/actividades/{actividad_uuid}/evidencias",
        data={"uuid": str(uuid_lib.uuid4()), "orden": "1"},
        files={"archivo": ("foto.jpg", io.BytesIO(imagen), "image/jpeg")},
        headers=cabeceras,
    )
    assert respuesta.status_code == 201, respuesta.text

    # 6. La actividad aparece en el propio historial del técnico
    respuesta = cliente.get("/actividades/me", headers=cabeceras)
    assert respuesta.status_code == 200
    uuids_propias = {a["uuid"] for a in respuesta.json()["resultados"]}
    assert actividad_uuid in uuids_propias

    # 7. Reenviar el mismo push no duplica (idempotencia — ECA-017)
    respuesta = cliente.post(
        "/sync/push",
        json={
            "dispositivo_uuid": str(uuid_lib.uuid4()),
            "jornadas": [],
            "actividades": [
                {
                    "uuid": actividad_uuid,
                    "jornada_uuid": jornada_uuid,
                    "modalidad_id": modalidad_id,
                    "tipo_actividad_id": tipo["id"],
                    "descripcion": "reintento",
                    "fecha_hora": datetime.now(timezone.utc).isoformat(),
                }
            ],
        },
        headers=cabeceras,
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["resultados"][0]["resultado"] == "DUPLICADO"


def _jpeg_minimo() -> bytes:
    # JPEG 1x1 blanco válido — suficiente para probar el flujo de subida
    # sin depender de un archivo de prueba externo.
    return bytes.fromhex(
        "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f14"
        "1d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffdb0043010909090c0b0c180d"
        "0d1832211c213232323232323232323232323232323232323232323232323232323232323232323232323232323232323232"
        "3232323232ffc00011080001000103012200021101031101ffc4001f0000010501010101010100000000000000000102030405"
        "060708090a0bffc400b5100002010303020403050504040000017d01020300041105122131410613516107227114328191a1"
        "08233042b1c115524d1f0246272728090a161718191a25262728292a3435363738393a434445464748494a535455565758595a"
        "636465666768696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9ba"
        "c2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffda000c03010002110311003f00"
        "f7fa28a2803fffd9"
    )
