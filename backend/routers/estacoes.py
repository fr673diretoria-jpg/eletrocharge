from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..carregamento import expirar_reservas_ocpp
from ..database import get_db
from ..geo import calcular_distancia_km

router = APIRouter(prefix="/api/estacoes", tags=["estações"])


@router.get("", response_model=List[schemas.EstacaoOut])
async def listar_estacoes(
    filtro: str = Query("todos", enum=["todos", "livre", "rapido", "ccs"]),
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    db: Session = Depends(get_db),
):
    await expirar_reservas_ocpp(db)
    query = db.query(models.Estacao)

    if filtro == "livre":
        query = query.filter(models.Estacao.vagas_livres > 0)
    elif filtro == "rapido":
        query = query.filter(models.Estacao.rapido.is_(True))
    elif filtro == "ccs":
        query = query.filter(models.Estacao.conector == "CCS2")

    resultado = []
    for estacao in query.all():
        saida = schemas.EstacaoOut.model_validate(estacao)
        saida.ocpp_identity = None  # detalhe interno de integração, não é do interesse do motorista
        if lat is not None and lng is not None:
            saida.distancia_km = round(
                calcular_distancia_km(lat, lng, estacao.latitude, estacao.longitude), 1
            )
        resultado.append(saida)

    if lat is not None and lng is not None:
        resultado.sort(key=lambda x: x.distancia_km if x.distancia_km is not None else 9e9)

    return resultado


@router.get("/{estacao_id}", response_model=schemas.EstacaoOut)
def detalhes_estacao(estacao_id: int, db: Session = Depends(get_db)):
    estacao = db.query(models.Estacao).filter(models.Estacao.id == estacao_id).first()
    if not estacao:
        raise HTTPException(status_code=404, detail="Estação não encontrada")
    saida = schemas.EstacaoOut.model_validate(estacao)
    saida.ocpp_identity = None
    return saida
