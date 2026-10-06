// ================= Estado global =================
let token = localStorage.getItem("ec_token") || null;
let usuarioAtual = JSON.parse(localStorage.getItem("ec_usuario") || "null");

let estacoes = [];
let selecionada = null;
let filtroAtual = "todos";
let localizacaoUsuario = null; // { lat, lng }
let pagamentosAtivos = true;
let reservaExpiraMinutos = 15;
let velocidadeMediaKmh = 35;

let mapa = null;
let marcadores = [];
let marcadorUsuario = null;

// ================= Utilidades =================
function dinheiro(valor) {
    return "R$ " + Number(valor).toFixed(2).replace(".", ",");
}

function mostrarToast(mensagem, duracaoMs = 3200) {
    const toast = document.getElementById("toast");
    toast.textContent = mensagem;
    toast.classList.remove("oculto");
    clearTimeout(mostrarToast._timer);
    mostrarToast._timer = setTimeout(() => toast.classList.add("oculto"), duracaoMs);
}

async function api(caminho, opcoes = {}) {
    const cabecalhos = { "Content-Type": "application/json", ...(opcoes.headers || {}) };
    if (token) cabecalhos["Authorization"] = "Bearer " + token;

    const resposta = await fetch(caminho, { ...opcoes, headers: cabecalhos });
    const dados = await resposta.json().catch(() => ({}));

    if (!resposta.ok) {
        const erro = new Error(dados.detail || "Ocorreu um erro na requisição");
        erro.status = resposta.status;
        throw erro;
    }
    return dados;
}

function tratarSessaoExpirada(erro) {
    if (erro.status !== 401) return false;

    encerrarSessao();
    const erroEl = document.getElementById("erro-auth");
    erroEl.textContent = "Sua sessão expirou. Entre novamente.";
    erroEl.classList.remove("oculto");
    return true;
}

// ================= Autenticação =================
let tokenRedefinirSenha = null;

function mudarAbaAuth(aba) {
    document.getElementById("aba-login").classList.toggle("ativa", aba === "login");
    document.getElementById("aba-cadastro").classList.toggle("ativa", aba === "cadastro");
    document.getElementById("form-login").classList.toggle("oculto", aba !== "login");
    document.getElementById("form-cadastro").classList.toggle("oculto", aba !== "cadastro");
    document.getElementById("form-esqueci-senha").classList.add("oculto");
    document.getElementById("form-redefinir-senha").classList.add("oculto");
    document.getElementById("link-esqueci-senha").classList.remove("oculto");
    document.getElementById("erro-auth").classList.add("oculto");
    document.getElementById("sucesso-auth").classList.add("oculto");
}

function mostrarEsqueciSenha() {
    document.querySelectorAll(".abas-auth .aba").forEach((b) => b.classList.remove("ativa"));
    document.getElementById("form-login").classList.add("oculto");
    document.getElementById("form-cadastro").classList.add("oculto");
    document.getElementById("form-redefinir-senha").classList.add("oculto");
    document.getElementById("link-esqueci-senha").classList.add("oculto");
    document.getElementById("form-esqueci-senha").classList.remove("oculto");
    document.getElementById("erro-auth").classList.add("oculto");
    document.getElementById("sucesso-auth").classList.add("oculto");
}

function mostrarRedefinirSenha(token) {
    tokenRedefinirSenha = token;
    document.querySelectorAll(".abas-auth .aba").forEach((b) => b.classList.remove("ativa"));
    document.getElementById("form-login").classList.add("oculto");
    document.getElementById("form-cadastro").classList.add("oculto");
    document.getElementById("form-esqueci-senha").classList.add("oculto");
    document.getElementById("link-esqueci-senha").classList.add("oculto");
    document.getElementById("form-redefinir-senha").classList.remove("oculto");
}

function salvarSessao(dados) {
    token = dados.access_token;
    usuarioAtual = dados.usuario;
    localStorage.setItem("ec_token", token);
    localStorage.setItem("ec_usuario", JSON.stringify(usuarioAtual));
}

function encerrarSessao() {
    token = null;
    usuarioAtual = null;
    localStorage.removeItem("ec_token");
    localStorage.removeItem("ec_usuario");
    pararAtualizacaoLocalizacao();
    document.getElementById("app").classList.add("oculto");
    document.getElementById("tela-auth").classList.remove("oculto");
}

async function iniciarApp() {
    document.getElementById("tela-auth").classList.add("oculto");
    document.getElementById("app").classList.remove("oculto");

    try {
        // Recarrega os dados do usuário do servidor: a sessão salva no celular pode estar
        // desatualizada (ex.: usuário virou admin depois do último login).
        usuarioAtual = await api("/api/auth/me");
        localStorage.setItem("ec_usuario", JSON.stringify(usuarioAtual));
    } catch (e) {
        if (tratarSessaoExpirada(e)) return;
        console.error(e);
    }
    document.getElementById("nav-admin").classList.toggle("oculto", !usuarioAtual?.is_admin);

    try {
        const config = await api("/api/config");
        pagamentosAtivos = config.pagamentosAtivos;
        reservaExpiraMinutos = config.reservaExpiraMinutos ?? reservaExpiraMinutos;
        velocidadeMediaKmh = config.velocidadeMediaKmh ?? velocidadeMediaKmh;

        if (config.googleMapsApiKey) {
            await carregarGoogleMaps(config.googleMapsApiKey);
        } else {
            document.getElementById("mapa").classList.add("oculto");
            const aviso = document.getElementById("aviso-mapa");
            aviso.textContent = "Mapa desativado: configure GOOGLE_MAPS_API_KEY no arquivo .env do servidor.";
            aviso.classList.remove("oculto");
        }
    } catch (e) {
        console.error(e);
    }

    obterLocalizacao(true);
    await carregarEstacoes();
    registrarServiceWorker();
    configurarInstalacaoApp();
    verificarRetornoPagamento();
    verificarRetornoParceiro();
    verificarCarregamentosAtivos();
    iniciarAtualizacaoLocalizacao();
}

document.getElementById("form-login").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const erroEl = document.getElementById("erro-auth");
    erroEl.classList.add("oculto");

    try {
        const dados = await api("/api/auth/login", {
            method: "POST",
            body: JSON.stringify({
                email: document.getElementById("login-email").value,
                senha: document.getElementById("login-senha").value,
            }),
        });
        salvarSessao(dados);
        iniciarApp();
    } catch (e) {
        erroEl.textContent = e.message;
        erroEl.classList.remove("oculto");
    }
});

document.getElementById("form-cadastro").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const erroEl = document.getElementById("erro-auth");
    erroEl.classList.add("oculto");

    try {
        const dados = await api("/api/auth/registrar", {
            method: "POST",
            body: JSON.stringify({
                nome: document.getElementById("cad-nome").value,
                email: document.getElementById("cad-email").value,
                telefone: document.getElementById("cad-telefone").value || null,
                senha: document.getElementById("cad-senha").value,
            }),
        });
        salvarSessao(dados);
        iniciarApp();
    } catch (e) {
        erroEl.textContent = e.message;
        erroEl.classList.remove("oculto");
    }
});

document.getElementById("btn-sair").addEventListener("click", encerrarSessao);

document.getElementById("link-esqueci-senha").addEventListener("click", (evento) => {
    evento.preventDefault();
    mostrarEsqueciSenha();
});

document.getElementById("link-voltar-login").addEventListener("click", (evento) => {
    evento.preventDefault();
    mudarAbaAuth("login");
});

document.getElementById("form-esqueci-senha").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const erroEl = document.getElementById("erro-auth");
    const sucessoEl = document.getElementById("sucesso-auth");
    erroEl.classList.add("oculto");
    sucessoEl.classList.add("oculto");

    try {
        const resposta = await api("/api/auth/esqueci-senha", {
            method: "POST",
            body: JSON.stringify({ email: document.getElementById("esqueci-email").value }),
        });
        sucessoEl.textContent = resposta.mensagem;
        sucessoEl.classList.remove("oculto");
    } catch (e) {
        erroEl.textContent = e.message;
        erroEl.classList.remove("oculto");
    }
});

document.getElementById("form-redefinir-senha").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const erroEl = document.getElementById("erro-auth");
    erroEl.classList.add("oculto");

    try {
        const resposta = await api("/api/auth/redefinir-senha", {
            method: "POST",
            body: JSON.stringify({
                token: tokenRedefinirSenha,
                nova_senha: document.getElementById("redefinir-senha").value,
            }),
        });
        window.history.replaceState({}, document.title, window.location.pathname);
        mudarAbaAuth("login");
        const sucessoEl = document.getElementById("sucesso-auth");
        sucessoEl.textContent = resposta.mensagem;
        sucessoEl.classList.remove("oculto");
    } catch (e) {
        erroEl.textContent = e.message;
        erroEl.classList.remove("oculto");
    }
});

{
    const parametrosAuth = new URLSearchParams(window.location.search);
    const tokenUrl = parametrosAuth.get("redefinir_senha");
    if (tokenUrl) mostrarRedefinirSenha(tokenUrl);
}

// ================= Navegação por abas =================
document.querySelectorAll(".nav-item").forEach((botao) => {
    botao.addEventListener("click", () => {
        document.querySelectorAll(".nav-item").forEach((b) => b.classList.remove("ativo"));
        document.querySelectorAll(".tab").forEach((t) => t.classList.remove("ativa"));

        botao.classList.add("ativo");
        document.getElementById("tab-" + botao.dataset.tab).classList.add("ativa");

        if (botao.dataset.tab === "historico") carregarHistorico();
        if (botao.dataset.tab === "perfil") carregarPerfil();
        if (botao.dataset.tab === "admin") carregarAdmin();
    });
});

// ================= Filtros =================
document.querySelectorAll(".filtro").forEach((botao) => {
    botao.addEventListener("click", () => {
        document.querySelectorAll(".filtro").forEach((b) => b.classList.remove("ativo"));
        botao.classList.add("ativo");
        filtroAtual = botao.dataset.filtro;
        carregarEstacoes();
    });
});

// ================= GPS =================
function obterLocalizacao(silencioso = false) {
    if (!navigator.geolocation) {
        if (!silencioso) mostrarToast("Seu navegador não suporta geolocalização.");
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (posicao) => {
            localizacaoUsuario = {
                lat: posicao.coords.latitude,
                lng: posicao.coords.longitude,
            };
            atualizarMarcadorUsuario(true);
            carregarEstacoes();
            if (!silencioso) mostrarToast("Localização atualizada.");
        },
        (erro) => {
            if (!silencioso) {
                mostrarToast(
                    "Não foi possível obter sua localização. Em celulares, é necessário HTTPS."
                );
            }
        },
        { enableHighAccuracy: true, timeout: 8000 }
    );
}

document.getElementById("btn-gps").addEventListener("click", () => obterLocalizacao(false));

// Mantém a localização do usuário sempre atualizada no mapa, sem recentralizar a cada leitura.
let watchIdLocalizacao = null;

function iniciarAtualizacaoLocalizacao() {
    if (watchIdLocalizacao !== null || !navigator.geolocation) return;

    watchIdLocalizacao = navigator.geolocation.watchPosition(
        (posicao) => {
            localizacaoUsuario = {
                lat: posicao.coords.latitude,
                lng: posicao.coords.longitude,
            };
            atualizarMarcadorUsuario(false);
        },
        () => {},
        { enableHighAccuracy: true, maximumAge: 10000, timeout: 20000 }
    );
}

function pararAtualizacaoLocalizacao() {
    if (watchIdLocalizacao !== null) {
        navigator.geolocation.clearWatch(watchIdLocalizacao);
        watchIdLocalizacao = null;
    }
}

// ================= Google Maps =================
function carregarGoogleMaps(chave) {
    return new Promise((resolve, reject) => {
        if (window.google && window.google.maps) return resolve();

        window.__iniciarMapaGoogle = () => resolve();
        const script = document.createElement("script");
        script.src =
            "https://maps.googleapis.com/maps/api/js?key=" +
            encodeURIComponent(chave) +
            "&callback=__iniciarMapaGoogle";
        script.async = true;
        script.defer = true;
        script.onerror = () => reject(new Error("Falha ao carregar Google Maps"));
        document.head.appendChild(script);
    }).then(() => {
        const centro = localizacaoUsuario || { lat: -24.9578, lng: -53.4595 };
        mapa = new google.maps.Map(document.getElementById("mapa"), {
            center: centro,
            zoom: 13,
            disableDefaultUI: true,
            zoomControl: true,
        });
    });
}

function iconeMarcador(cor) {
    const svg =
        '<svg xmlns="http://www.w3.org/2000/svg" width="34" height="34">' +
        '<circle cx="17" cy="17" r="15" fill="' + cor + '" stroke="white" stroke-width="3"/>' +
        '<text x="17" y="23" font-size="16" text-anchor="middle" fill="white">⚡</text>' +
        "</svg>";
    return {
        url: "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(svg),
        scaledSize: new google.maps.Size(34, 34),
    };
}

function iconeUsuario() {
    const svg =
        '<svg xmlns="http://www.w3.org/2000/svg" width="34" height="34">' +
        '<circle cx="17" cy="17" r="15" fill="#1a73e8" stroke="white" stroke-width="3"/>' +
        '<circle cx="17" cy="13" r="4.5" fill="white"/>' +
        '<path d="M8 26c0-6 4.5-9.5 9-9.5s9 3.5 9 9.5" fill="white"/>' +
        "</svg>";
    return {
        url: "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(svg),
        scaledSize: new google.maps.Size(34, 34),
    };
}

function atualizarMarcadorUsuario(centralizar = true) {
    if (!mapa || !localizacaoUsuario) return;

    if (centralizar) mapa.setCenter(localizacaoUsuario);

    if (marcadorUsuario) {
        marcadorUsuario.setPosition(localizacaoUsuario);
    } else {
        marcadorUsuario = new google.maps.Marker({
            position: localizacaoUsuario,
            map: mapa,
            title: "Você está aqui",
            zIndex: google.maps.Marker.MAX_ZINDEX + 1,
            icon: iconeUsuario(),
        });
    }
}

function renderizarMarcadores() {
    if (!mapa) return;

    marcadores.forEach((m) => m.setMap(null));
    marcadores = [];

    const cores = { livre: "#168a55", ocupado: "#d48718", offline: "#6b7680" };

    estacoes.forEach((estacao) => {
        const marcador = new google.maps.Marker({
            position: { lat: estacao.latitude, lng: estacao.longitude },
            map: mapa,
            title: estacao.nome,
            icon: iconeMarcador(cores[estacao.status] || "#168a55"),
        });

        marcador.addListener("click", () => {
            const card = document.getElementById("card-" + estacao.id);
            if (card) {
                card.scrollIntoView({ behavior: "smooth", block: "center" });
                card.classList.add("destacado");
                setTimeout(() => card.classList.remove("destacado"), 1500);
            }
        });

        marcadores.push(marcador);
    });
}

// ================= Estações =================
async function carregarEstacoes() {
    let caminho = "/api/estacoes?filtro=" + filtroAtual;
    if (localizacaoUsuario) {
        caminho += "&lat=" + localizacaoUsuario.lat + "&lng=" + localizacaoUsuario.lng;
    }

    estacoes = await api(caminho);
    renderizarLista();
    renderizarMarcadores();
}

function renderizarLista() {
    const lista = document.getElementById("lista");

    const rotulos = {
        livre: "🟢 Disponível",
        ocupado: "🟠 Ocupado",
        offline: "⚫ Indisponível",
    };

    lista.innerHTML = estacoes
        .map(
            (e) => `
        <div class="card" id="card-${e.id}">
            <div class="card-top">
                <div>
                    <strong>${e.nome}</strong>
                    <div class="card-info">
                        ${e.distancia_km != null ? e.distancia_km.toFixed(1).replace(".", ",") + " km • " : ""}
                        ${e.conector} • ${e.potencia_kw} kW
                    </div>
                    <div class="card-info">${e.endereco}</div>
                </div>
                <div class="card-preco">${dinheiro(e.preco_kwh)}/kWh</div>
            </div>

            <div class="card-acoes">
                <span class="badge ${e.status}">
                    ${e.status === "livre" ? rotulos.livre + " (" + e.vagas_livres + ")" : rotulos[e.status]}
                </span>
                <button class="botao" onclick="navegarAteEstacao(${e.latitude}, ${e.longitude})">🧭 Navegar</button>
                ${e.vagas_livres > 0
                    ? `<button class="botao primario" onclick="reservar(${e.id})">Reservar / carregar</button>`
                    : ""}
            </div>
        </div>
    `
        )
        .join("") || `<p class="aviso">Nenhuma estação encontrada para este filtro.</p>`;
}

function navegarAteEstacao(lat, lng) {
    window.open(`https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`, "_blank");
}

function navegarEstacaoSelecionada() {
    if (!selecionada) return;
    navegarAteEstacao(selecionada.latitude, selecionada.longitude);
}

// ================= Pagamento =================
function reservar(id) {
    selecionada = estacoes.find((e) => e.id === id);
    if (!selecionada) return;

    if (!pagamentosAtivos) {
        mostrarToast("Pagamentos ainda não configurados pelo administrador (MP_ACCESS_TOKEN).");
        return;
    }

    document.getElementById("estacao-pagamento").textContent =
        selecionada.nome + " — " + dinheiro(selecionada.preco_kwh) + "/kWh";
    document.getElementById("resultado-pagamento").classList.add("oculto");
    atualizarAvisoTempoReserva();
    document.getElementById("painel-pagamento").classList.remove("oculto");
}

function atualizarAvisoTempoReserva() {
    const avisoEl = document.getElementById("aviso-tempo-reserva");
    if (!selecionada || selecionada.distancia_km == null || !velocidadeMediaKmh) {
        avisoEl.classList.add("oculto");
        return;
    }

    const tempoEstimadoMin = Math.round((selecionada.distancia_km / velocidadeMediaKmh) * 60);
    if (tempoEstimadoMin > reservaExpiraMinutos) {
        const distanciaTexto = selecionada.distancia_km.toFixed(1).replace(".", ",");
        avisoEl.textContent =
            `⚠️ Você está a ${distanciaTexto} km (~${tempoEstimadoMin} min de chegada). ` +
            `Sua reserva no carregador expira ${reservaExpiraMinutos} min após o pagamento aprovado — ` +
            "ela pode expirar antes de você chegar.";
        avisoEl.classList.remove("oculto");
    } else {
        avisoEl.classList.add("oculto");
    }
}

function fecharPainelPagamento() {
    document.getElementById("painel-pagamento").classList.add("oculto");
}

async function confirmarPagamento() {
    if (!selecionada) return;

    const valor = Number(document.getElementById("valor-pagamento").value);
    const metodo = document.getElementById("metodo-pagamento").value;
    const resultadoEl = document.getElementById("resultado-pagamento");
    const botao = document.getElementById("btn-confirmar-pagamento");

    resultadoEl.classList.add("oculto");

    if (!localizacaoUsuario) {
        obterLocalizacao(true);
        resultadoEl.textContent = "Ative a localização para reservar uma estação próxima.";
        resultadoEl.classList.remove("oculto");
        return;
    }

    botao.disabled = true;
    botao.textContent = "Gerando cobrança...";

    try {
        const pagamento = await api("/api/pagamentos", {
            method: "POST",
            body: JSON.stringify({
                estacao_id: selecionada.id,
                valor,
                metodo,
                lat: localizacaoUsuario.lat,
                lng: localizacaoUsuario.lng,
            }),
        });

        if (pagamento.checkout_url) {
            window.location.href = pagamento.checkout_url;
        } else {
            throw new Error("Não foi possível iniciar o checkout.");
        }
    } catch (e) {
        resultadoEl.textContent = e.message;
        resultadoEl.classList.remove("oculto");
    } finally {
        botao.disabled = false;
        botao.textContent = "Ir para pagamento seguro";
    }
}

function verificarRetornoPagamento() {
    const parametros = new URLSearchParams(window.location.search);
    const status = parametros.get("pagamento");
    const pagamentoId = parametros.get("pagamento_id");
    if (!status) return;

    const mensagens = {
        sucesso: "✅ Pagamento aprovado! Bom carregamento.",
        falha: "❌ Pagamento não aprovado.",
        pendente: "⏳ Pagamento pendente de confirmação.",
    };
    mostrarToast(mensagens[status] || "Retorno de pagamento recebido.");

    window.history.replaceState({}, document.title, window.location.pathname);

    if (status === "sucesso" && pagamentoId) {
        mostrarConectorReservado(pagamentoId);
    }
}

async function mostrarConectorReservado(pagamentoId, tentativas = 5) {
    try {
        const pagamento = await api(`/api/pagamentos/${pagamentoId}`);
        if (pagamento.ocpp_connector_id) {
            mostrarToast(`🔌 Use o conector nº ${pagamento.ocpp_connector_id} nesta estação.`, 6000);
            return;
        }
    } catch (e) {
        // ignora, tenta de novo abaixo
    }
    if (tentativas > 0) {
        setTimeout(() => mostrarConectorReservado(pagamentoId, tentativas - 1), 2000);
    }
}

// ================= Histórico =================
async function carregarHistorico() {
    const lista = document.getElementById("lista-historico");
    lista.innerHTML = "<p>Carregando...</p>";

    try {
        const pagamentos = await api("/api/pagamentos/meus");

        lista.innerHTML =
            pagamentos
                .map(
                    (p) => `
            <div class="item-historico">
                <div>
                    <strong>${dinheiro(p.valor)}</strong>
                    <div class="card-info">${new Date(p.criado_em).toLocaleString("pt-BR")} • ${p.metodo}</div>
                    ${p.status === "aprovado" && p.ocpp_connector_id ? `<div class="card-info">🔌 Conector nº ${p.ocpp_connector_id}</div>` : ""}
                </div>
                ${p.status === "aprovado"
                    ? `<button class="botao" onclick="finalizarManualmente(${p.id})">Finalizar carregamento</button>`
                    : `<span class="status-pill ${p.status}">${p.status}</span>`}
            </div>
        `
                )
                .join("") || "<p>Nenhum pagamento realizado ainda.</p>";
    } catch (e) {
        lista.innerHTML = `<p class="erro-auth">${e.message}</p>`;
    }
}

// ================= Liberação automática de vaga via GPS =================
let watchIdCarregamento = null;
let pagamentosEmAndamento = [];

async function verificarCarregamentosAtivos() {
    try {
        const pagamentos = await api("/api/pagamentos/meus");
        pagamentosEmAndamento = pagamentos.filter((p) => p.status === "aprovado");
    } catch (e) {
        pagamentosEmAndamento = [];
    }

    if (pagamentosEmAndamento.length > 0) {
        iniciarMonitoramentoGps();
    } else {
        pararMonitoramentoGps();
    }
}

function iniciarMonitoramentoGps() {
    if (watchIdCarregamento !== null || !navigator.geolocation) return;

    watchIdCarregamento = navigator.geolocation.watchPosition(
        async (posicao) => {
            const lat = posicao.coords.latitude;
            const lng = posicao.coords.longitude;

            for (const pagamento of [...pagamentosEmAndamento]) {
                try {
                    const resultado = await tentarFinalizar(pagamento.id, lat, lng);
                    if (resultado.liberado) {
                        pagamentosEmAndamento = pagamentosEmAndamento.filter((p) => p.id !== pagamento.id);
                    }
                } catch (e) {
                    // Ignora falha pontual; tenta de novo na próxima leitura do GPS.
                }
            }

            if (pagamentosEmAndamento.length === 0) pararMonitoramentoGps();
        },
        () => {},
        { enableHighAccuracy: true, maximumAge: 15000, timeout: 20000 }
    );
}

function pararMonitoramentoGps() {
    if (watchIdCarregamento !== null) {
        navigator.geolocation.clearWatch(watchIdCarregamento);
        watchIdCarregamento = null;
    }
}

async function tentarFinalizar(pagamentoId, lat, lng) {
    const resultado = await api(`/api/pagamentos/${pagamentoId}/finalizar`, {
        method: "POST",
        body: JSON.stringify({ lat, lng }),
    });

    if (resultado.liberado) {
        mostrarToast("🔓 " + resultado.mensagem);
        if (document.getElementById("tab-historico").classList.contains("ativa")) carregarHistorico();
        carregarEstacoes();
    }
    return resultado;
}

function finalizarManualmente(pagamentoId) {
    if (!navigator.geolocation) {
        mostrarToast("Seu navegador não suporta geolocalização.");
        return;
    }

    navigator.geolocation.getCurrentPosition(
        async (posicao) => {
            try {
                const r = await tentarFinalizar(pagamentoId, posicao.coords.latitude, posicao.coords.longitude);
                if (!r.liberado) mostrarToast("ℹ️ " + r.mensagem);
            } catch (e) {
                mostrarToast(e.message);
            }
        },
        () => mostrarToast("Não foi possível obter sua localização agora."),
        { enableHighAccuracy: true, timeout: 8000 }
    );
}

// ================= Perfil =================
async function carregarPerfil() {
    const el = document.getElementById("dados-perfil");
    try {
        const usuario = await api("/api/auth/me");
        el.innerHTML = `
            <p><strong>Nome:</strong> ${usuario.nome}</p>
            <p><strong>E-mail:</strong> ${usuario.email}</p>
            <p><strong>Telefone:</strong> ${usuario.telefone || "não informado"}</p>
        `;
    } catch (e) {
        if (tratarSessaoExpirada(e)) return;
        el.innerHTML = `<p class="erro-auth">${e.message}</p>`;
    }
}

// ================= PWA =================
function registrarServiceWorker() {
    if ("serviceWorker" in navigator) {
        navigator.serviceWorker.register("/service-worker.js").catch(() => {});
    }
}

let promptDeInstalacao = null;

function estaInstalado() {
    return (
        window.matchMedia("(display-mode: standalone)").matches ||
        window.navigator.standalone === true
    );
}

function botoesInstalar() {
    return [document.getElementById("btn-instalar"), document.getElementById("link-instalar")];
}

function mostrarBotoesInstalar() {
    botoesInstalar().forEach((el) => el.classList.remove("oculto"));
}

function esconderBotoesInstalar() {
    botoesInstalar().forEach((el) => el.classList.add("oculto"));
}

window.addEventListener("beforeinstallprompt", (evento) => {
    evento.preventDefault();
    promptDeInstalacao = evento;
    if (!estaInstalado()) mostrarBotoesInstalar();
});

window.addEventListener("appinstalled", () => {
    promptDeInstalacao = null;
    esconderBotoesInstalar();
    document.getElementById("banner-instalar-ios").classList.add("oculto");
    mostrarToast("✅ EletroCharge instalado com sucesso!");
});

function configurarInstalacaoApp() {
    if (estaInstalado()) return;

    const ehIOS = /iphone|ipad|ipod/.test(navigator.userAgent.toLowerCase());
    if (ehIOS) mostrarBotoesInstalar();
}

async function instalarApp() {
    if (promptDeInstalacao) {
        promptDeInstalacao.prompt();
        const escolha = await promptDeInstalacao.userChoice;
        if (escolha.outcome === "accepted") esconderBotoesInstalar();
        promptDeInstalacao = null;
        return;
    }

    // iOS (Safari) não tem instalação automática: mostra o passo a passo manual.
    const estaLogado = !document.getElementById("app").classList.contains("oculto");
    if (estaLogado) {
        document.getElementById("banner-instalar-ios").classList.remove("oculto");
    } else {
        mostrarToast('📲 Toque em Compartilhar (⬆️) e depois em "Adicionar à Tela de Início".', 5000);
    }
}

document.getElementById("btn-instalar").addEventListener("click", instalarApp);
document.getElementById("link-instalar").addEventListener("click", (evento) => {
    evento.preventDefault();
    instalarApp();
});

// ================= Admin (parceiros, comissão, transações) =================
function verificarRetornoParceiro() {
    const parametros = new URLSearchParams(window.location.search);
    if (parametros.get("parceiro_conectado")) {
        mostrarToast("✅ Parceiro conectado ao Mercado Pago com sucesso!");
        window.history.replaceState({}, document.title, window.location.pathname);
    }
}

async function carregarAdmin() {
    if (!usuarioAtual?.is_admin) return;
    await Promise.all([carregarResumoAdmin(), carregarEstacoesAdmin(), carregarParceiros(), carregarTransacoesAdmin()]);
}

async function carregarResumoAdmin() {
    const el = document.getElementById("resumo-admin");
    try {
        const r = await api("/api/admin/resumo");
        el.innerHTML = `
            <div class="resumo-item"><span class="rotulo">Faturamento aprovado</span><span class="valor">${dinheiro(r.faturamento_total)}</span></div>
            <div class="resumo-item"><span class="rotulo">Comissão da plataforma</span><span class="valor">${dinheiro(r.comissao_total)}</span></div>
            <div class="resumo-item"><span class="rotulo">Repasse aos parceiros</span><span class="valor">${dinheiro(r.repasse_parceiros)}</span></div>
            <div class="resumo-item"><span class="rotulo">Usuários únicos</span><span class="valor">${r.usuarios_unicos}</span></div>
        `;
    } catch (e) {
        el.innerHTML = `<p class="erro-auth">${e.message}</p>`;
    }
}

let parceirosCache = [];
let estacoesAdminCache = [];

async function carregarEstacoesAdmin() {
    const lista = document.getElementById("lista-estacoes-admin");
    try {
        estacoesAdminCache = await api("/api/admin/estacoes");

        lista.innerHTML =
            estacoesAdminCache
                .map(
                    (e) => `
            <div class="card">
                <div class="card-top">
                    <div>
                        <strong>${e.nome}</strong>
                        <div class="card-info">${e.endereco}</div>
                        <div class="card-info">${e.conector} • ${e.potencia_kw} kW • ${dinheiro(e.preco_kwh)}/kWh</div>
                        ${e.ocpp_identity
                            ? `<div class="card-info">OCPP: ${e.ocpp_identity} • ${e.ocpp_conectado ? "🟢 conectado" : "⚪ desconectado"}</div>`
                            : ""}
                    </div>
                    <span class="badge ${e.status}">${e.status}</span>
                </div>
                <div class="card-acoes">
                    <span class="card-info">${e.vagas_livres}/${e.vagas_total} vagas livres</span>
                    <div>
                        <button class="botao" onclick="editarEstacao(${e.id})">Editar</button>
                        <button class="botao perigo" onclick="removerEstacao(${e.id})">Remover</button>
                    </div>
                </div>
            </div>
        `
                )
                .join("") || "<p>Nenhuma estação cadastrada ainda.</p>";

        preencherSelectEstacoes();
    } catch (e) {
        lista.innerHTML = `<p class="erro-auth">${e.message}</p>`;
    }
}

function usarLocalizacaoNaEstacao() {
    if (!navigator.geolocation) {
        mostrarToast("Seu navegador não suporta geolocalização.");
        return;
    }
    navigator.geolocation.getCurrentPosition(
        (posicao) => {
            document.getElementById("estacao-latitude").value = posicao.coords.latitude;
            document.getElementById("estacao-longitude").value = posicao.coords.longitude;
            mostrarToast("Localização preenchida.");
        },
        () => mostrarToast("Não foi possível obter sua localização agora."),
        { enableHighAccuracy: true, timeout: 8000 }
    );
}

function editarEstacao(id) {
    const e = estacoesAdminCache.find((x) => x.id === id);
    if (!e) return;

    document.getElementById("estacao-nome").value = e.nome;
    document.getElementById("estacao-endereco").value = e.endereco;
    document.getElementById("estacao-latitude").value = e.latitude;
    document.getElementById("estacao-longitude").value = e.longitude;
    document.getElementById("estacao-preco").value = e.preco_kwh;
    document.getElementById("estacao-potencia").value = e.potencia_kw;
    document.getElementById("estacao-conector").value = e.conector;
    document.getElementById("estacao-rapido").checked = e.rapido;
    document.getElementById("estacao-vagas").value = e.vagas_total;
    document.getElementById("estacao-status").value = e.status;
    document.getElementById("estacao-ocpp").value = e.ocpp_identity || "";

    document.getElementById("form-estacao").dataset.editandoId = id;
    document.getElementById("btn-salvar-estacao").textContent = "Salvar alterações";
    document.getElementById("btn-cancelar-edicao-estacao").classList.remove("oculto");
    document.getElementById("form-estacao").scrollIntoView({ behavior: "smooth" });
}

function cancelarEdicaoEstacao() {
    const form = document.getElementById("form-estacao");
    form.reset();
    delete form.dataset.editandoId;
    document.getElementById("btn-salvar-estacao").textContent = "Cadastrar estação";
    document.getElementById("btn-cancelar-edicao-estacao").classList.add("oculto");
}

async function removerEstacao(id) {
    if (!confirm("Remover esta estação? Essa ação não pode ser desfeita.")) return;
    try {
        await api(`/api/admin/estacoes/${id}`, { method: "DELETE" });
        mostrarToast("Estação removida.");
        carregarEstacoesAdmin();
    } catch (e) {
        mostrarToast(e.message);
    }
}

document.getElementById("form-estacao").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const form = evento.target;
    const idEditando = form.dataset.editandoId;

    const corpo = {
        nome: document.getElementById("estacao-nome").value,
        endereco: document.getElementById("estacao-endereco").value,
        latitude: Number(document.getElementById("estacao-latitude").value),
        longitude: Number(document.getElementById("estacao-longitude").value),
        preco_kwh: Number(document.getElementById("estacao-preco").value),
        potencia_kw: Number(document.getElementById("estacao-potencia").value),
        conector: document.getElementById("estacao-conector").value,
        rapido: document.getElementById("estacao-rapido").checked,
        vagas_total: Number(document.getElementById("estacao-vagas").value),
        status: document.getElementById("estacao-status").value,
        ocpp_identity: document.getElementById("estacao-ocpp").value || null,
    };

    try {
        if (idEditando) {
            await api(`/api/admin/estacoes/${idEditando}`, { method: "PUT", body: JSON.stringify(corpo) });
            mostrarToast("Estação atualizada!");
        } else {
            await api("/api/admin/estacoes", { method: "POST", body: JSON.stringify(corpo) });
            mostrarToast("Estação cadastrada!");
        }
        cancelarEdicaoEstacao();
        carregarEstacoesAdmin();
        carregarEstacoes();
    } catch (e) {
        mostrarToast(e.message);
    }
});

async function carregarParceiros() {
    const lista = document.getElementById("lista-parceiros");
    try {
        parceirosCache = await api("/api/admin/parceiros");

        lista.innerHTML =
            parceirosCache
                .map(
                    (p) => `
            <div class="item-historico">
                <div>
                    <strong>${p.nome}</strong>
                    <div class="card-info">${p.email} • comissão: ${p.comissao_percentual != null ? p.comissao_percentual + "%" : "padrão do sistema"}</div>
                </div>
                ${p.conectado
                    ? `<span class="status-pill aprovado">Conectado</span>`
                    : `<button class="botao primario" onclick="conectarParceiro(${p.id})">Conectar Mercado Pago</button>`}
            </div>
        `
                )
                .join("") || "<p>Nenhum parceiro cadastrado ainda.</p>";

        preencherSelectParceiros();
    } catch (e) {
        lista.innerHTML = `<p class="erro-auth">${e.message}</p>`;
    }
}

async function conectarParceiro(id) {
    try {
        const r = await api(`/api/admin/parceiros/${id}/conectar`);
        window.open(r.url_autorizacao, "_blank");
    } catch (e) {
        mostrarToast(e.message);
    }
}

function preencherSelectParceiros() {
    const select = document.getElementById("vincular-parceiro");
    select.innerHTML = parceirosCache
        .map((p) => `<option value="${p.id}">${p.nome}</option>`)
        .join("");
}

function preencherSelectEstacoes() {
    const select = document.getElementById("vincular-estacao");
    select.innerHTML = estacoesAdminCache
        .map((e) => `<option value="${e.id}">${e.nome}</option>`)
        .join("");
}

document.getElementById("form-parceiro").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    try {
        const comissao = document.getElementById("parceiro-comissao").value;
        await api("/api/admin/parceiros", {
            method: "POST",
            body: JSON.stringify({
                nome: document.getElementById("parceiro-nome").value,
                email: document.getElementById("parceiro-email").value,
                comissao_percentual: comissao ? Number(comissao) : null,
            }),
        });
        evento.target.reset();
        mostrarToast("Parceiro cadastrado!");
        carregarParceiros();
    } catch (e) {
        mostrarToast(e.message);
    }
});

document.getElementById("form-vincular").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const estacaoId = document.getElementById("vincular-estacao").value;
    const parceiroId = document.getElementById("vincular-parceiro").value;

    try {
        await api(`/api/admin/parceiros/${parceiroId}/estacoes/${estacaoId}`, { method: "POST" });
        mostrarToast("Estação vinculada ao parceiro!");
    } catch (e) {
        mostrarToast(e.message);
    }
});

async function carregarTransacoesAdmin() {
    const lista = document.getElementById("lista-transacoes-admin");
    try {
        const pagamentos = await api("/api/admin/pagamentos");

        lista.innerHTML =
            pagamentos
                .map(
                    (p) => `
            <div class="item-historico">
                <div>
                    <strong>${dinheiro(p.valor)}</strong>
                    <div class="card-info">
                        ${p.usuario_nome || "?"} • ${p.estacao_nome || "?"}
                        ${p.parceiro_nome ? " • parceiro: " + p.parceiro_nome : ""}
                    </div>
                    <div class="card-info">
                        ${new Date(p.criado_em).toLocaleString("pt-BR")}
                        ${p.comissao_valor != null ? " • comissão: " + dinheiro(p.comissao_valor) : ""}
                    </div>
                </div>
                <span class="status-pill ${p.status}">${p.status}</span>
            </div>
        `
                )
                .join("") || "<p>Nenhuma transação ainda.</p>";
    } catch (e) {
        lista.innerHTML = `<p class="erro-auth">${e.message}</p>`;
    }
}

// ================= Boot =================
configurarInstalacaoApp(); // roda já na tela de login, não só depois de autenticar

if (token && usuarioAtual && !tokenRedefinirSenha) {
    iniciarApp();
}
