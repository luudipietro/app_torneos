/** Mini envoltorio de IndexedDB: lo justo para la cola, las copias locales y los conflictos. */
const DB_NAME = 'torneos-offline'
export const STORES = { outbox: 'outbox', snapshots: 'snapshots', conflicts: 'conflicts' } as const
type Store = (typeof STORES)[keyof typeof STORES]

let dbPromise: Promise<IDBDatabase> | null = null

export function openDb(): Promise<IDBDatabase> {
  dbPromise ??= new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1)
    req.onupgradeneeded = () => {
      const db = req.result
      db.createObjectStore(STORES.outbox, { keyPath: 'seq', autoIncrement: true })
      db.createObjectStore(STORES.snapshots, { keyPath: 'matchId' })
      db.createObjectStore(STORES.conflicts, { keyPath: 'id', autoIncrement: true })
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => { dbPromise = null; reject(req.error) }
  })
  return dbPromise
}

/** Cierra y olvida la conexión (los tests la usan para empezar de cero). */
export async function resetDb() {
  if (dbPromise) (await dbPromise).close()
  dbPromise = null
}

async function run<T>(store: Store, mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, mode)
    const req = fn(tx.objectStore(store))
    tx.oncomplete = () => resolve(req.result)
    tx.onerror = () => reject(tx.error)
    tx.onabort = () => reject(tx.error)
  })
}

export const idb = {
  all: <T>(store: Store) => run<T[]>(store, 'readonly', (s) => s.getAll()),
  get: <T>(store: Store, key: IDBValidKey) => run<T | undefined>(store, 'readonly', (s) => s.get(key)),
  put: (store: Store, value: unknown) => run(store, 'readwrite', (s) => s.put(value)),
  add: (store: Store, value: unknown) => run(store, 'readwrite', (s) => s.add(value)),
  del: (store: Store, key: IDBValidKey) => run(store, 'readwrite', (s) => s.delete(key)),
  clear: (store: Store) => run(store, 'readwrite', (s) => s.clear()),
}
