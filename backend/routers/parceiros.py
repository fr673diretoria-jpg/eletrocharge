from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .. import config, mp_oauth, models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/api/admin/parceiros", tags=["parceiros"])


def _para_saida(parceiro: models.Parceiro) -> schemas.ParceiroOut:
    saida = schemas.ParceiroOut.model_validate(parceiro)
    saida.conectado = bool(parceiro.mp_access_token)
    return saida


@router.get("", response_model=list[schemas.ParceiroOut])
def listar_parceiros(
    admin: models.Usuario = Depends(security.exigir_admin),
    db: Session = Depends(get_db),
):
    return [_para_saida(p) for p in db.query(models.Parceiro).all()]


@router.post("", response_model=schemas.ParceiroOut, status_code=201)
def criar_parceiro(
    dados: schemas.ParceiroCreate,
    admin: models.Usuario = Depends(security.exigir_admin),
    db: Session = Depends(get_db),
):
    parceiro = models.Parceiro(**dados.model_dump())
    db.add(parceiro)
    db.commit()
    db.refresh(parceiro)
    return _para_saida(parceiro)


@router.post("/{parceiro_id}/estacoes/{estacao_id}")
def vincular_estacao(
    parceiro_id: int,
    estacao_id: int,
    admin: models.Usuario = Depends(security.exigir_admin),
    db: Session = Depends(get_db),
):
    estacao = db.query(models.Estacao).filter(models.Estacao.id == estacao_id).first()
    parceiro = db.query(models.Parceiro).filter(models.Parceiro.id == parceiro_id).first()
    if not estacao or not parceiro:
        raise HTTPException(status_code=404, detail="Estação ou parceiro não encontrado")

    estacao.parceiro_id = parceiro.id
    db.commit()
    return {"ok": True}


@router.get("/{parceiro_id}/conectar")
def link_conexao(
    parceiro_id: int,
    admin: models.Usuario = Depends(security.exigir_admin),
    db: Session = Depends(get_db),
):
    if not config.MP_CLIENT_ID or not config.MP_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Defina MP_CLIENT_ID e MP_CLIENT_SECRET no .env (registre o app como Marketplace no Mercado Pago)",
        )

    parceiro = db.query(models.Parceiro).filter(models.Parceiro.id == parceiro_id).first()
    if not parceiro:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado")

    return {"url_autorizacao": mp_oauth.url_de_autorizacao(parceiro.id)}


@router.get("/oauth/callback")
def oauth_callback(code: str, state: str, db: Session = Depends(get_db)):
    """Mercado Pago redireciona o parceiro para cá após ele autorizar a conexão da conta."""
    parceiro = db.query(models.Parceiro).filter(models.Parceiro.id == int(state)).first()
    if not parceiro:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado")

    try:
        dados_token = mp_oauth.trocar_code_por_token(code)
    except Exception:
        raise HTTPException(status_code=502, detail="Falha ao conectar a conta do Mercado Pago")

    mp_oauth.salvar_token_no_parceiro(parceiro, dados_token, db)
    return RedirectResponse(url=f"{config.APP_BASE_URL}/?parceiro_conectado=1")
