import { idb, STORES } from './idb'

/** Al cerrar sesión: borra lo guardado del torneo (copias de partidos, respuestas cacheadas). La cola de pendientes no se toca. */
export async function clearPrivateData() {
  try { await idb.clear(STORES.snapshots) } catch { /* sin IndexedDB */ }
  try { await caches.delete('api-cache') } catch { /* sin Cache API */ }
}
