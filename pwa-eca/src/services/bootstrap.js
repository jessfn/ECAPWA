// pwa-eca — bootstrap y pull offline de catálogos/ECA (ECA-018).
//
// `GET /sync/bootstrap` (primer login) y `GET /sync/pull` (periódico)
// entregan el subconjunto relevante del técnico — nunca las ~5 000 ECA
// completas (`03` §6.8). Se guarda en IndexedDB (`catalogos`, `ecas`,
// `meta`) para que `SelectorEca` y "Nueva actividad" funcionen 100 %
// offline con esos datos.
import { api } from './api'
import { abrirBD } from './db'

async function guardarLocal(data) {
  const db = await abrirBD()
  const tx = db.transaction(['catalogos', 'ecas', 'meta'], 'readwrite')

  await tx.objectStore('catalogos').put({ clave: 'modalidades', items: data.catalogos.modalidades })
  await tx.objectStore('catalogos').put({ clave: 'tipos_actividad', items: data.catalogos.tipos_actividad })
  await tx.objectStore('catalogos').put({ clave: 'temas', items: data.catalogos.temas })
  await tx.objectStore('catalogos').put({ clave: 'subtemas', items: data.catalogos.subtemas })
  await tx
    .objectStore('catalogos')
    .put({ clave: 'sistemas_productivos', items: data.catalogos.sistemas_productivos })
  await tx.objectStore('catalogos').put({ clave: 'geo', valor: data.geo })
  await tx.objectStore('catalogos').put({ clave: 'ambito', valor: data.ambito })
  await tx.objectStore('catalogos').put({ clave: 'config', valor: data.config })

  await tx.objectStore('ecas').clear()
  for (const eca of data.ecas) {
    await tx.objectStore('ecas').put({ id: eca.eca_id, ...eca })
  }

  await tx.objectStore('meta').put({ clave: 'bootstrap', generado_en: data.generado_en, aviso: data.aviso || null })

  await tx.done
}

export async function ejecutarBootstrap() {
  const { data } = await api.get('/sync/bootstrap')
  await guardarLocal(data)
  return data
}

export async function ejecutarPull() {
  const db = await abrirBD()
  const meta = await db.get('meta', 'bootstrap')
  const params = meta?.generado_en ? { desde: meta.generado_en } : {}
  const { data } = await api.get('/sync/pull', { params })
  await guardarLocal(data)
  return data
}

export async function leerCatalogosLocal() {
  const db = await abrirBD()
  const [modalidades, tiposActividad, temas, subtemas, sistemasProductivos] = await Promise.all([
    db.get('catalogos', 'modalidades'),
    db.get('catalogos', 'tipos_actividad'),
    db.get('catalogos', 'temas'),
    db.get('catalogos', 'subtemas'),
    db.get('catalogos', 'sistemas_productivos'),
  ])
  return {
    modalidades: modalidades?.items || [],
    tiposActividad: tiposActividad?.items || [],
    temas: temas?.items || [],
    subtemas: subtemas?.items || [],
    sistemasProductivos: sistemasProductivos?.items || [],
  }
}

export async function leerEcasLocal() {
  const db = await abrirBD()
  return db.getAll('ecas')
}

export async function leerMetaBootstrap() {
  const db = await abrirBD()
  return db.get('meta', 'bootstrap')
}
