import io

import qrcode
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from .. import config

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
def obter_config():
    """Configuração pública consumida pelo frontend (nenhum segredo é exposto aqui)."""
    return {
        "googleMapsApiKey": config.GOOGLE_MAPS_API_KEY,
        "pagamentosAtivos": bool(config.MP_ACCESS_TOKEN),
    }


@router.get("/qrcode")
def gerar_qrcode(url: str = Query(min_length=1, max_length=500)):
    """Gera um QR code (PNG) apontando para a URL informada — usado na página /instalar.html
    para o motorista escanear com a câmera do celular em vez de digitar o endereço."""
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL inválida")

    imagem = qrcode.make(url, box_size=10, border=2)
    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="image/png")
