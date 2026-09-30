const CACHE_NOME = "eletrocharge-v7";
const ARQUIVOS_APP_SHELL = [
    "/",
    "/css/style.css",
    "/js/app.js",
    "/manifest.json",
    "/icons/icon.svg",
    "/icons/icon-192.png",
    "/icons/icon-512.png",
    "/icons/icon-maskable.png",
];

self.addEventListener("install", (evento) => {
    evento.waitUntil(
        caches.open(CACHE_NOME).then((cache) => cache.addAll(ARQUIVOS_APP_SHELL))
    );
    self.skipWaiting();
});

self.addEventListener("activate", (evento) => {
    evento.waitUntil(
        caches.keys().then((chaves) =>
            Promise.all(
                chaves
                    .filter((chave) => chave !== CACHE_NOME)
                    .map((chave) => caches.delete(chave))
            )
        )
    );
    self.clients.claim();
});

self.addEventListener("fetch", (evento) => {
    const url = new URL(evento.request.url);

    // Nunca cachear chamadas de API: dados de estações e pagamento são sempre atuais.
    if (url.pathname.startsWith("/api/")) {
        return;
    }

    evento.respondWith(
        caches.match(evento.request).then((resposta) => {
            return (
                resposta ||
                fetch(evento.request).catch(() => caches.match("/"))
            );
        })
    );
});
