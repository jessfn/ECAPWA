# Fuente del catálogo de municipios — PENDIENTE

**Estado: sin definir.** No se cargó ningún municipio real todavía.

## Por qué

El ticket ECA-006 pide sembrar ~2,469 municipios, pero también advierte
explícitamente en su sección "Riesgos":

> Fuente INEGI desactualizada o con claves cambiadas → acordar con Jesús la
> fuente exacta (año del catálogo). Documentar la fuente en
> `data/inegi/FUENTE.md`.

No tengo forma de verificar ~2,469 claves y nombres de municipio de memoria
con la confianza necesaria para un catálogo que va a ser la base de datos
oficial de ECA, ámbitos de técnico y asignaciones — un error aquí (un
municipio con clave equivocada, un nombre mal escrito, un municipio de
creación reciente faltante) sería silencioso y difícil de detectar después.
Los 32 estados sí se sembraron directamente en `0006_seed_estados.py`: es
un catálogo estable, público y de muy bajo riesgo de error (sin cambios
desde 1974, y solo 32 filas — un caso muy distinto a los municipios).

## Qué falta (decisión de Jesús)

1. Confirmar la **fuente oficial exacta** del catálogo de municipios y su
   **año/versión** (p. ej. "Catálogo Único de Claves de Áreas Geoestadísticas
   Estatales, Municipales y Localidades" del INEGI, marco geoestadístico
   vigente a la fecha de la carga).
2. Entregar el archivo (CSV/XLSX del propio INEGI, o el que ya use
   Sembrando Vida si su catálogo de municipios está actualizado y viene de
   fuente verificable) con al menos: `clave_inegi` (5 dígitos: 2 de estado +
   3 de municipio), `nombre`, `estado_clave_inegi` (o el nombre del estado).
3. Colocar ese archivo como `data/inegi/municipios.csv` (columnas:
   `clave_inegi,nombre,estado_clave_inegi`) en este mismo directorio.
4. Correr `python -m scripts.cargar_municipios data/inegi/municipios.csv`
   (ver ese script — hace upsert por `clave_inegi`, es seguro correrlo más
   de una vez).

## Mientras tanto

`GET /geo/municipios?estado_id=` funciona correctamente pero devuelve una
lista vacía para todos los estados hasta que se cargue el catálogo real.
Los tests de ECA-006 cubren la lógica (filtro, búsqueda, permisos) con
municipios de prueba, no con el catálogo real.
