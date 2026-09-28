"""
EletroCharge - protótipo de localizador de carregadores elétricos
Backend simples em Python/FastAPI.

Instalação:
    pip install fastapi uvicorn

Executar:
    uvicorn eletrocharge:app --reload

Depois abra:
    http://127.0.0.1:8000
"""

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="EletroCharge", version="1.0")

ESTACOES = [
    {
        "id": 1,
        "nome": "Shopping Cascavel",
        "distancia_km": 2.1,
        "preco_kwh": 1.89,
        "livres": 3,
        "total": 4,
        "potencia_kw": 60,
        "conector": "CCS2",
        "rapido": True,
        "status": "livre",
    },
    {
        "id": 2,
        "nome": "Posto Paraná",
        "distancia_km": 4.7,
        "preco_kwh": 1.69,
        "livres": 2,
        "total": 3,
        "potencia_kw": 50,
        "conector": "CCS2",
        "rapido": True,
        "status": "livre",
    },
    {
        "id": 3,
        "nome": "Supermercado Central",
        "distancia_km": 6.3,
        "preco_kwh": 1.49,
        "livres": 0,
        "total": 4,
        "potencia_kw": 22,
        "conector": "Tipo 2",
        "rapido": False,
        "status": "ocupado",
    },
    {
        "id": 4,
        "nome": "EletroPark Norte",
        "distancia_km": 8.8,
        "preco_kwh": 1.99,
        "livres": 0,
        "total": 2,
        "potencia_kw": 120,
        "conector": "CCS2",
        "rapido": True,
        "status": "offline",
    },
]


class Pagamento(BaseModel):
    estacao_id: int
    metodo: str = "Pix"
    valor: float


@app.get("/api/estacoes")
def listar_estacoes(
    filtro: str = Query("todos", enum=["todos", "livre", "rapido", "ccs"])
):
    resultado = ESTACOES

    if filtro == "livre":
        resultado = [e for e in resultado if e["livres"] > 0]
    elif filtro == "rapido":
        resultado = [e for e in resultado if e["rapido"]]
    elif filtro == "ccs":
        resultado = [e for e in resultado if e["conector"] == "CCS2"]

    return {"estacoes": resultado}


@app.get("/api/estacoes/{estacao_id}")
def detalhes_estacao(estacao_id: int):
    for estacao in ESTACOES:
        if estacao["id"] == estacao_id:
            return estacao

    return {"erro": "Estação não encontrada"}


@app.post("/api/pagamento")
def pagamento(dados: Pagamento):
    estacao = next(
        (e for e in ESTACOES if e["id"] == dados.estacao_id),
        None,
    )

    if not estacao:
        return {"sucesso": False, "mensagem": "Estação não encontrada"}

    if estacao["livres"] <= 0:
        return {"sucesso": False, "mensagem": "Não há carregador disponível"}

    if dados.metodo not in ("Pix", "Cartão"):
        return {"sucesso": False, "mensagem": "Método de pagamento inválido"}

    return {
        "sucesso": True,
        "mensagem": (
            f"Pagamento simulado com {dados.metodo}. "
            f"Valor: R$ {dados.valor:.2f}"
        ),
        "estacao": estacao["nome"],
    }


HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EletroCharge</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f2f5f7;
    color: #172027;
}
.container {
    max-width: 900px;
    margin: auto;
    padding: 20px;
}
header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 15px;
    flex-wrap: wrap;
}
h1 { margin: 0; }
.sub { color: #65727a; }
button {
    border: 0;
    border-radius: 10px;
    padding: 11px 15px;
    cursor: pointer;
    background: white;
    border: 1px solid #d5dde2;
}
button.active, button.primary {
    background: #197a4b;
    color: white;
}
.filtros {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 18px 0;
}
.mapa {
    height: 300px;
    border-radius: 18px;
    background:
        linear-gradient(25deg, transparent 47%, #fff 48%, #fff 53%, transparent 54%),
        linear-gradient(145deg, transparent 45%, #fff 46%, #fff 51%, transparent 52%),
        #dfe6e3;
    position: relative;
    overflow: hidden;
    border: 1px solid #ccd5d1;
}
.mapa h3 {
    position: absolute;
    left: 15px;
    top: 8px;
    background: white;
    padding: 9px 12px;
    border-radius: 10px;
}
.pin {
    position: absolute;
    border-radius: 50%;
    padding: 10px;
    background: #168a55;
    color: white;
    font-weight: bold;
    cursor: pointer;
}
.pin:nth-of-type(2) { left: 20%; top: 50%; }
.pin:nth-of-type(3) { left: 60%; top: 25%; }
.pin:nth-of-type(4) { right: 15%; top: 60%; background: #d48718; }
.pin:nth-of-type(5) { left: 45%; bottom: 15%; background: #777; }

.lista {
    display: grid;
    gap: 12px;
    margin-top: 18px;
}
.card {
    background: white;
    border: 1px solid #d8e0e4;
    border-radius: 16px;
    padding: 16px;
}
.top {
    display: flex;
    justify-content: space-between;
    gap: 15px;
}
.preco {
    font-size: 20px;
    font-weight: bold;
}
.info {
    color: #68757c;
    font-size: 14px;
    margin-top: 5px;
}
.acoes {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    margin-top: 12px;
    flex-wrap: wrap;
}
.pagamento {
    display: none;
    margin-top: 18px;
}
input, select {
    width: 100%;
    padding: 12px;
    border: 1px solid #ccd5da;
    border-radius: 9px;
    margin: 6px 0 12px;
}
@media (max-width: 600px) {
    .top { flex-direction: column; }
    .mapa { height: 250px; }
}
</style>
</head>

<body>
<div class="container">

<header>
    <div>
        <h1>⚡ EletroCharge</h1>
        <div class="sub">Localize, reserve e pague seu carregamento</div>
    </div>
    <button onclick="minhaLocalizacao()">⌖ Minha localização</button>
</header>

<div class="filtros">
    <button class="active" onclick="filtrar('todos', this)">Todos</button>
    <button onclick="filtrar('livre', this)">Disponíveis</button>
    <button onclick="filtrar('rapido', this)">Rápidos</button>
    <button onclick="filtrar('ccs', this)">CCS2</button>
</div>

<div class="mapa">
    <h3>📍 Cascavel - PR</h3>
    <div class="pin" style="left:20%;top:50%" onclick="selecionar(1)">⚡</div>
    <div class="pin" style="left:60%;top:25%" onclick="selecionar(2)">⚡</div>
    <div class="pin" style="right:15%;top:60%;background:#d48718" onclick="selecionar(3)">⚡</div>
    <div class="pin" style="left:45%;bottom:15%;background:#777" onclick="selecionar(4)">⚡</div>
</div>

<div id="lista" class="lista"></div>

<div id="pagamento" class="card pagamento">
    <h2>💳 Pagamento</h2>
    <p id="estacaoPagamento"></p>

    <label>Valor</label>
    <input id="valor" type="number" value="20" min="1" step="0.01">

    <label>Método</label>
    <select id="metodo">
        <option>Pix</option>
        <option>Cartão</option>
    </select>

    <button class="primary" onclick="pagar()">Confirmar pagamento</button>
    <p id="resultado"></p>
</div>

</div>

<script>
let estacoes = [];
let selecionada = null;

function dinheiro(valor) {
    return "R$ " + Number(valor).toFixed(2).replace(".", ",");
}

async function carregar(filtro = "todos") {
    const resposta = await fetch("/api/estacoes?filtro=" + filtro);
    const dados = await resposta.json();
    estacoes = dados.estacoes;

    const lista = document.getElementById("lista");

    lista.innerHTML = estacoes.map(e => `
        <div class="card">
            <div class="top">
                <div>
                    <strong>${e.nome}</strong>
                    <div class="info">
                        ${e.distancia_km.toFixed(1).replace(".", ",")} km
                        • ${e.conector}
                        • ${e.potencia_kw} kW
                    </div>
                </div>

                <div class="preco">
                    ${dinheiro(e.preco_kwh)}/kWh
                </div>
            </div>

            <div class="acoes">
                <div>
                    ${e.status === "livre"
                        ? "🟢 " + e.livres + " vagas livres"
                        : e.status === "ocupado"
                        ? "🟠 Ocupado"
                        : "⚫ Indisponível"}
                </div>

                <div>
                    <button onclick="selecionar(${e.id})">Detalhes</button>
                    ${e.livres > 0
                        ? `<button class="primary" onclick="reservar(${e.id})">Reservar / carregar</button>`
                        : ""}
                </div>
            </div>
        </div>
    `).join("");
}

function filtrar(filtro, botao) {
    document.querySelectorAll(".filtros button")
        .forEach(b => b.classList.remove("active"));

    botao.classList.add("active");
    carregar(filtro);
}

function selecionar(id) {
    const e = estacoes.find(x => x.id === id);
    if (!e) return;

    alert(
        e.nome +
        "\\nDistância: " + e.distancia_km + " km" +
        "\\nPreço: " + dinheiro(e.preco_kwh) + "/kWh" +
        "\\nPotência: " + e.potencia_kw + " kW" +
        "\\nConector: " + e.conector
    );
}

function reservar(id) {
    selecionada = estacoes.find(x => x.id === id);
    if (!selecionada) return;

    document.getElementById("pagamento").style.display = "block";
    document.getElementById("estacaoPagamento").textContent =
        "Estação: " + selecionada.nome +
        " — " + dinheiro(selecionada.preco_kwh) + "/kWh";

    document.getElementById("pagamento")
        .scrollIntoView({behavior: "smooth"});
}

async function pagar() {
    if (!selecionada) return;

    const valor = Number(document.getElementById("valor").value);
    const metodo = document.getElementById("metodo").value;

    const resposta = await fetch("/api/pagamento", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            estacao_id: selecionada.id,
            metodo: metodo,
            valor: valor
        })
    });

    const dados = await resposta.json();

    document.getElementById("resultado").textContent =
        dados.mensagem;
}

function minhaLocalizacao() {
    alert(
        "Nesta versão de demonstração, a localização é aproximada.\\n\\n" +
        "Na versão comercial podemos integrar GPS + Google Maps/Mapbox."
    );
}

carregar();
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def inicio():
    return HTML


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
