"""Router `/parametros-config` — ECA-014.

Lectura, cualquier autenticado: son parámetros operativos no sensibles
(umbrales, reglas) que el propio cliente (PWA/panel) necesita leer para
comportarse según lo que el admin configuró, sin desplegar código. La
edición queda fuera de alcance de este ticket (no hay pantalla admin
todavía para tocar `parametros_config`).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.usuario import Usuario
from app.repositories import parametros_config as repo_config
from app.schemas.parametro_config import ParametroPublico

router = APIRouter(prefix="/parametros-config", tags=["parametros-config"])


@router.get("/{clave}", response_model=ParametroPublico)
def obtener_parametro(
    clave: str,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
) -> ParametroPublico:
    parametro = repo_config.obtener(db, clave)
    if parametro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Parámetro desconocido: {clave}")
    return ParametroPublico(clave=parametro.clave, valor=parametro.valor)
