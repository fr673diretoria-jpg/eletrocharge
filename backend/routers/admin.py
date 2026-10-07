from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, ocpp_server, schemas, security
from ..database import get_db
from .contato import CHAVE_EMAIL_FALE_CONOSCO, obter_email_fale_conosco

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _estacao_para_saida(estacao: models.Estacao) -> schemas.EstacaoOut:
    saida = schemas.EstacaoOut.model_validate(estacao)
    saida.ocpp_conectado = bool(estacao.ocpp_identity) and estacao.ocpp_identity in ocpp_server.conexoes_ativas
    return saida


def _validar_ocpp_identity_unica(
    ocpp_identity: str, db: Session, ignorar_estacao_id: int | None = None
) -> None:
    query = db.query(models.Estacao).filter(models.Estacao.ocpp_identity == ocpp_identity)
    if ignorar_estacao_id is not None:
        query = query.filter(models.Estacao.id != ignorar_estacao_id)
    if query.first():
        raise HTTPException(status_code=400, detail="Já existe uma estação com essa identidade OCPP")


@router.get("/estacoes", response_model=list[schemas.EstacaoOut])
def listar_estacoes(
    admin: models.Usuario = Depends(security.exigir_admin),
    db: Session = Depends(get_db),
):
    return [_estacao_para_saida(e) for e in db.query(models.Estacao).all()]


@router.post("/estacoes", response_model=schemas.EstacaoOut, status_code=201)
def criar_estacao(
    dados: schemas.EstacaoCreate,
    admin: models.Usuario = Depends(security.exigir_admin),
    db: Session = Depends(get_db),
):
    if dados.ocpp_identity:
        _validar_ocpp_identity_unica(dados.ocpp_identity, db)

    estacao = models.Estacao(**dados.model_dump(), vagas_livres=dados.vagas_total)
    db.add(estacao)
    db.commit()
    db.refresh(estacao)
    return _estacao_para_saida(estacao)


@router.put("/estacoes/{estacao_id}", response_model=schemas.EstacaoOut)
def atualizar_estacao(
    estacao_id: int,
    dados: schemas.EstacaoUpdate,
    admin: models.Usuario = Depends(security.exigir_admin),
    db: Session = Depends(get_db),
):
    estacao = db.query(models.Estacao).filter(models.Estacao.id == estacao_id).first()
    if not estacao:
        raise HTTPException(status_code=404, detail="Estação não encontrada")

    if dados.ocpp_identity:
        _validar_ocpp_identity_unica(dados.ocpp_identity, db, ignorar_estacao_id=estacao_id)

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(estacao, campo, valor)

    db.commit()
    db.refresh(estacao)
    return _estacao_para_saida(estacao)


@router.delete("/estacoes/{estacao_id}")
def remover_estacao(
    estacao_id: int,
    admin: models.Usuario = Depends(security.exigir_admin),
    db: Session = Depends(get_db),
):
    estacao = db.query(models.Estacao).filter(models.Estacao.id == estacao_id).first()
    if not estacao:
        raise HTTPException(status_code=404, detail="Estação não encontrada")

    db.delete(estacao)
    db.commit()
    return {"ok": True}


@router.get("/pagamentos", response_model=list[schemas.PagamentoAdminOut])
def listar_pagamentos(
    admin: models.Usuario = Depends(security.exigir_admin),
    db: Session = Depends(get_db),
):
    pagamentos = db.query(models.Pagamento).order_by(models.Pagamento.criado_em.desc()).all()

    resultado = []
    for p in pagamentos:
        saida = schemas.PagamentoAdminOut.model_validate(p)
        saida.usuario_nome = p.usuario.nome if p.usuario else None
        saida.usuario_email = p.usuario.email if p.usuario else None
        saida.estacao_nome = p.estacao.nome if p.estacao else None
        saida.parceiro_nome = p.parceiro.nome if p.parceiro else None
        resultado.append(saida)

    return resultado


@router.get("/config-contato", response_model=schemas.EmailContatoConfig)
def obter_config_contato(
    admin: models.Usuario = Depends(security.exigir_admin),
    db: Session = Depends(get_db),
):
    return {"email": obter_email_fale_conosco(db)}


@router.put("/config-contato", response_model=schemas.EmailContatoConfig)
def atualizar_config_contato(
    dados: schemas.EmailContatoConfig,
    admin: models.Usuario = Depends(security.exigir_admin),
    db: Session = Depends(get_db),
):
    registro = db.query(models.Configuracao).filter(models.Configuracao.chave == CHAVE_EMAIL_FALE_CONOSCO).first()
    if registro:
        registro.valor = dados.email
    else:
        db.add(models.Configuracao(chave=CHAVE_EMAIL_FALE_CONOSCO, valor=dados.email))
    db.commit()
    return {"email": dados.email}


@router.get("/resumo")
def resumo(
    admin: models.Usuario = Depends(security.exigir_admin),
    db: Session = Depends(get_db),
):
    aprovados = db.query(models.Pagamento).filter(models.Pagamento.status == "aprovado").all()

    faturamento_total = sum(p.valor for p in aprovados)
    comissao_total = sum(p.comissao_valor or 0 for p in aprovados)

    return {
        "faturamento_total": round(faturamento_total, 2),
        "comissao_total": round(comissao_total, 2),
        "repasse_parceiros": round(faturamento_total - comissao_total, 2),
        "transacoes_aprovadas": len(aprovados),
        "usuarios_unicos": len({p.usuario_id for p in aprovados}),
    }
