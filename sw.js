/* Service worker приложения «Карта подарков».
 * Стратегия: stale-while-revalidate — отдаём из кэша сразу и параллельно
 * обновляем кэш из сети. Если в кэше нет — идём в сеть; если и сеть недоступна,
 * для навигационных запросов отдаём сохранённый index.html.
 */

const CACHE = 'gift-v13';

const PRECACHE = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icon-180.png',
  './icon-192.png',
  './icon-512.png',
];

const FALLBACK = './index.html';

// --- установка: складываем оболочку в кэш --------------------------------
// Каждый файл добавляем отдельно: отсутствие одного не ломает установку.
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) =>
        Promise.all(PRECACHE.map((url) => cache.add(url).catch(() => undefined)))
      )
      .then(() => self.skipWaiting())
  );
});

// --- активация: чистим старые кэши и забираем клиентов -------------------
self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))
      );
      await self.clients.claim();
    })()
  );
});

// --- запросы --------------------------------------------------------------
self.addEventListener('fetch', (event) => {
  const request = event.request;

  // Только GET и только свой origin.
  if (request.method !== 'GET') return;
  // Range-запросы видео не кэшируем: иначе в кэш попадёт часть файла.
  if (request.headers.get('range')) return;

  let url;
  try {
    url = new URL(request.url);
  } catch (error) {
    return;
  }
  if (url.origin !== self.location.origin) return;

  // Навигацию отдаём сначала из сети: так новая версия дизайна видна сразу.
  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request));
    return;
  }

  event.respondWith(staleWhileRevalidate(request));
});

async function networkFirst(request) {
  const cache = await caches.open(CACHE);
  try {
    const response = await fetch(request);
    if (response && response.ok) {
      cache.put(request, response.clone()).catch(() => undefined);
    }
    return response;
  } catch (error) {
    const cached =
      (await cache.match(request, { ignoreSearch: true })) ||
      (await cache.match(FALLBACK)) ||
      (await cache.match('./'));
    if (cached) return cached;
    throw error;
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE);

  // ignoreSearch: страница с ?dev=1 или ?date=... тоже находит кэш.
  const cached = await cache.match(request, { ignoreSearch: true });

  // Параллельно тянем свежую версию из сети и обновляем кэш.
  const network = fetch(request).then((response) => {
    if (response && response.ok) {
      cache.put(request, response.clone()).catch(() => undefined);
    }
    return response;
  });

  if (cached) {
    // Ошибку сети гасим: пользователь уже получил ответ из кэша.
    network.catch(() => undefined);
    return cached;
  }

  try {
    return await network;
  } catch (error) {
    // Сети нет и в кэше пусто: для навигации отдаём оболочку.
    if (request.mode === 'navigate') {
      const fallback =
        (await cache.match(FALLBACK)) || (await cache.match('./'));
      if (fallback) return fallback;
    }
    throw error;
  }
}
