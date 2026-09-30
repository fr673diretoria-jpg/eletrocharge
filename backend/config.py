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

# Distância máxima (em metros) para permitir reservar/pagar por uma estação.
DISTANCIA_MAXIMA_PAGAMENTO_METROS = float(os.getenv("DISTANCIA_MAXIMA_PAGAMENTO_METROS", "200"))

# Tempo máximo (em minutos) para uma estação OCPP iniciar a transação após o pagamento aprovado.
RESERVA_EXPIRA_MINUTOS = int(os.getenv("RESERVA_EXPIRA_MINUTOS", "15"))

# Velocidade média assumida (km/h) para estimar o tempo de chegada até a estação antes do
# pagamento, e avisar o motorista se a reserva pode expirar antes dele chegar.
VELOCIDADE_MEDIA_KMH = float(os.getenv("VELOCIDADE_MEDIA_KMH", "35"))

# Google Maps JavaScript API - chave restrita por referrer no Google Cloud Console.
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# URL pública da aplicação (usada nos back_urls e no webhook do Mercado Pago).
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")

# Tempo de validade (em minutos) do link de redefinição de senha enviado por e-mail.
RESET_SENHA_EXPIRA_MINUTOS = int(os.getenv("RESET_SENHA_EXPIRA_MINUTOS", "30"))

# SMTP usado para enviar o e-mail de "esqueci minha senha". Se SMTP_HOST não for definido,
# o link é apenas registrado no log do servidor (útil em desenvolvimento local).
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "EletroCharge <nao-responda@eletrocharge.com>")

# Resend (https://resend.com) - envia e-mail via API HTTPS. Preferido em produção porque
# provedores de hospedagem (ex.: Render) costumam bloquear conexões SMTP de saída.
# Se definido, tem prioridade sobre SMTP_HOST acima.
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
