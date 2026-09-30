from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import models
from .database import Base, SessionLocal, engine
from .routers import admin, auth, estacoes, pagamentos, parceiros, publico
from . import ocpp_server

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

Base.metadata.create_all(bind=engine)


def _migrar_colunas_novas():
    """Adiciona colunas criadas após a primeira versão do banco (SQLite não altera tabelas existentes
    automaticamente com create_all)."""
    if engine.dialect.name == "postgresql":
        # Postgres suporta ADD COLUMN IF NOT EXISTS nativamente, então não precisa checar antes.
        with engine.connect() as conexao:
            conexao.exec_driver_sql("ALTER TABLE pagamentos ADD COLUMN IF NOT EXISTS ocpp_connector_id INTEGER")
            conexao.commit()
        return
    if engine.dialect.name != "sqlite":
        return
    with engine.connect() as conexao:
        colunas_usuarios = {l[1] for l in conexao.exec_driver_sql("PRAGMA table_info(usuarios)")}
        if "is_admin" not in colunas_usuarios:
            conexao.exec_driver_sql("ALTER TABLE usuarios ADD COLUMN is_admin BOOLEAN DEFAULT 0")

        colunas_estacoes = {l[1] for l in conexao.exec_driver_sql("PRAGMA table_info(estacoes)")}
        if "parceiro_id" not in colunas_estacoes:
            conexao.exec_driver_sql("ALTER TABLE estacoes ADD COLUMN parceiro_id INTEGER")
        if "ocpp_identity" not in colunas_estacoes:
            conexao.exec_driver_sql("ALTER TABLE estacoes ADD COLUMN ocpp_identity TEXT")

        colunas_pagamentos = {l[1] for l in conexao.exec_driver_sql("PRAGMA table_info(pagamentos)")}
        if "comissao_valor" not in colunas_pagamentos:
            conexao.exec_driver_sql("ALTER TABLE pagamentos ADD COLUMN comissao_valor FLOAT")
        if "parceiro_id" not in colunas_pagamentos:
            conexao.exec_driver_sql("ALTER TABLE pagamentos ADD COLUMN parceiro_id INTEGER")
        if "ocpp_id_tag" not in colunas_pagamentos:
            conexao.exec_driver_sql("ALTER TABLE pagamentos ADD COLUMN ocpp_id_tag TEXT")
        if "ocpp_transaction_id" not in colunas_pagamentos:
            conexao.exec_driver_sql("ALTER TABLE pagamentos ADD COLUMN ocpp_transaction_id INTEGER")
        if "ocpp_connector_id" not in colunas_pagamentos:
            conexao.exec_driver_sql("ALTER TABLE pagamentos ADD COLUMN ocpp_connector_id INTEGER")

        conexao.commit()


_migrar_colunas_novas()

app = FastAPI(title="EletroCharge", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(estacoes.router)
app.include_router(pagamentos.router)
app.include_router(publico.router)
app.include_router(parceiros.router)
app.include_router(admin.router)
app.include_router(ocpp_server.router)


ESTACOES_SEED = [
    dict(
        nome="Shopping Cascavel", endereco="Av. Brasil, 5000 - Centro, Cascavel - PR",
        latitude=-24.9578, longitude=-53.4595, preco_kwh=1.89, potencia_kw=60,
        conector="CCS2", rapido=True, vagas_livres=3, vagas_total=4, status="livre",
    ),
    dict(
        nome="Posto Paraná", endereco="Av. Tancredo Neves, 1200 - Coqueiral, Cascavel - PR",
        latitude=-24.9445, longitude=-53.4712, preco_kwh=1.69, potencia_kw=50,
        conector="CCS2", rapido=True, vagas_livres=2, vagas_total=3, status="livre",
    ),
    dict(
        nome="Supermercado Central", endereco="R. Paraná, 3400 - Centro, Cascavel - PR",
        latitude=-24.9601, longitude=-53.4488, preco_kwh=1.49, potencia_kw=22,
        conector="Tipo 2", rapido=False, vagas_livres=0, vagas_total=4, status="ocupado",
    ),
    dict(
        nome="EletroPark Norte", endereco="R. Recife, 800 - São Cristóvão, Cascavel - PR",
        latitude=-24.9312, longitude=-53.4550, preco_kwh=1.99, potencia_kw=120,
        conector="CCS2", rapido=True, vagas_livres=0, vagas_total=2, status="offline",
    ),
]


@app.on_event("startup")
def semear_estacoes():
    db = SessionLocal()
    try:
        if db.query(models.Estacao).count() == 0:
            for dados in ESTACOES_SEED:
                db.add(models.Estacao(**dados))
            db.commit()
    finally:
        db.close()


# Serve o frontend (index.html, css, js, manifest, service worker) como fallback.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
