# EletroCharge — sistema completo

Evolução profissional do protótipo `eletrocharge.py`: backend modular em FastAPI, frontend mobile-first (PWA),
cadastro/login de usuários, geolocalização real com Google Maps e pagamento real via Mercado Pago.

## Estrutura

```
backend/            # API FastAPI (auth, estações, pagamentos, config)
frontend/           # HTML/CSS/JS servidos como PWA (mobile-first)
requirements.txt
.env.example
```

## 1. Instalação

```powershell
pip install -r requirements.txt
copy .env.example .env
```

## 2. Configurar o `.env`

- `SECRET_KEY`: gere uma string aleatória (ex.: `python -c "import secrets;print(secrets.token_hex(32))"`).
- `GOOGLE_MAPS_API_KEY`: crie no [Google Cloud Console](https://console.cloud.google.com/google/maps-apis),
  habilite "Maps JavaScript API" e restrinja a chave por referrer HTTP.
- `MP_ACCESS_TOKEN`: obtenha em [Mercado Pago Developers](https://www.mercadopago.com.br/developers/panel) →
  Suas integrações → Credenciais (use as de **teste** primeiro, depois as de **produção**).
- `APP_BASE_URL`: URL pública do servidor (necessária para o Mercado Pago redirecionar o usuário e enviar o webhook).

## 3. Executar

Em desenvolvimento (recarrega o servidor a cada alteração de código):

```powershell
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Para uso com **várias pessoas/celulares ao mesmo tempo**, rode sem `--reload` (evita quedas de conexão
quando o processo reinicia):

```powershell
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Acesse `http://127.0.0.1:8000` no navegador.

## 4. Rodar no celular para múltiplos usuários

O backend já está pronto para isso: `--host 0.0.0.0` aceita conexões de outros dispositivos, o CORS é aberto,
a autenticação é por token (cada pessoa loga com sua própria conta) e o SQLite roda em modo **WAL**, que permite
várias leituras/escritas simultâneas sem travar.

**A) Mesma rede Wi-Fi (mais simples, sem custo)**

1. Descubra o IP local do computador: `ipconfig` (procure "Endereço IPv4", ex.: `192.168.1.9`).
2. Garanta que a porta 8000 está liberada no Firewall do Windows (regra de entrada). Se não tiver uma regra,
   crie pelo Painel de Controle → Firewall do Windows Defender → Configurações avançadas → Regra de Entrada.
3. Cada celular, conectado à **mesma rede Wi-Fi**, acessa `http://192.168.1.9:8000` (troque pelo IP real) e
   cria sua própria conta.
4. **Limitação**: nessa forma (HTTP simples, sem certificado), o GPS do navegador pode não funcionar em alguns
   celulares, pois geolocalização exige contexto seguro (HTTPS). Se o app pedir localização e falhar, use a
   opção B abaixo.

**B) Acesso por internet com HTTPS (necessário para GPS funcionar em qualquer celular/rede, e para o webhook
do Mercado Pago em produção)**

- Opção rápida para testes: [ngrok](https://ngrok.com/) → `ngrok http 8000`. Gera uma URL HTTPS pública;
  compartilhe-a com todos os usuários. Atualize `APP_BASE_URL` no `.env` para essa URL e reinicie o servidor.
- Opção estável (URL fixa, recomendada quando o grupo de usuários é o mesmo por mais tempo):
  [Tailscale Funnel](https://tailscale.com/kb/1223/funnel) ou um domínio próprio com HTTPS (Caddy/Let's Encrypt)
  apontando para o servidor.
- Sempre que trocar a URL pública, atualize também a restrição de referenciador HTTP da chave do
  `GOOGLE_MAPS_API_KEY` no Google Cloud Console para incluir a nova URL.

**C) Escalando além do SQLite**

Para um número grande de usuários simultâneos em produção, migre de SQLite para PostgreSQL (troque apenas
`SQLALCHEMY_DATABASE_URL` em `backend/database.py`) e rode atrás de um proxy reverso (Nginx/Caddy) com HTTPS.

## 5. Instalar como app (PWA)

Pelo Chrome no celular, use "Adicionar à tela inicial" para instalar o EletroCharge como aplicativo.

## 5. Pagamentos reais

O botão "Reservar / carregar" cria uma cobrança real (Checkout Pro) no Mercado Pago e redireciona o usuário
para a página oficial de pagamento (Pix, cartão ou boleto). A confirmação chega via webhook
(`/api/pagamentos/webhook`), que revalida o pagamento diretamente na API do Mercado Pago antes de atualizar
o status no banco — por isso, em produção, `APP_BASE_URL` precisa ser acessível publicamente.
