"""Configurações da aplicação, carregadas de variáveis de ambiente (.env)."""
import os

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "chave-insegura-troque-no-env")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# URL de conexão do banco (SQLAlchemy). Padrão: SQLite local. Para Postgres (ex.: Supabase),
# defina DATABASE_URL no .env, ex.: postgresql://postgres:SENHA@db.xxxxxxxx.supabase.co:5432/postgres
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./eletrocharge.db")

# Mercado Pago - Access Token da conta "master" da plataforma (usado quando a estação não tem parceiro).
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")

# Credenciais do app registrado como Marketplace no Mercado Pago (necessárias para conectar parceiros via OAuth).
MP_CLIENT_ID = os.getenv("MP_CLIENT_ID", "")
MP_CLIENT_SECRET = os.getenv("MP_CLIENT_SECRET", "")

# Comissão padrão (%) retida pela plataforma em pagamentos de estações com parceiro conectado.
COMISSAO_PADRAO_PERCENTUAL = float(os.getenv("COMISSAO_PADRAO_PERCENTUAL", "15"))

# E-mails (separados por vírgula) que recebem acesso ao painel administrativo automaticamente no login.
ADMIN_EMAILS = [
    e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()
]

# Distância (em metros) que o motorista precisa se afastar da estação, após o pagamento aprovado,
# para o app liberar a vaga automaticamente via GPS.
DISTANCIA_LIBERACAO_VAGA_METROS = float(os.getenv("DISTANCIA_LIBERACAO_VAGA_METROS", "300"))

# Google Maps JavaScript API - chave restrita por referrer no Google Cloud Console.
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# URL pública da aplicação (usada nos back_urls e no webhook do Mercado Pago).
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")
