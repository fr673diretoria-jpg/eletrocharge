from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    telefone = Column(String, nullable=True)
    senha_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    criado_em = Column(DateTime, default=datetime.utcnow)

    pagamentos = relationship("Pagamento", back_populates="usuario")


class Parceiro(Base):
    """Dono de estação (recebe o valor da recarga via split de pagamento do Mercado Pago)."""

    __tablename__ = "parceiros"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=False)
    telefone = Column(String, nullable=True)
    comissao_percentual = Column(Float, nullable=True)  # se nulo, usa o padrão global (config)

    mp_user_id = Column(String, nullable=True)
    mp_access_token = Column(String, nullable=True)
    mp_refresh_token = Column(String, nullable=True)
    mp_token_expira_em = Column(DateTime, nullable=True)

    criado_em = Column(DateTime, default=datetime.utcnow)

    estacoes = relationship("Estacao", back_populates="parceiro")


class Estacao(Base):
    __tablename__ = "estacoes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    endereco = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    preco_kwh = Column(Float, nullable=False)
    potencia_kw = Column(Integer, nullable=False)
    conector = Column(String, nullable=False)
    rapido = Column(Boolean, default=False)
    vagas_livres = Column(Integer, default=0)
    vagas_total = Column(Integer, default=1)
    status = Column(String, default="livre")  # livre, ocupado, offline
    parceiro_id = Column(Integer, ForeignKey("parceiros.id"), nullable=True)
    ocpp_identity = Column(String, nullable=True)  # ID do carregador físico (OCPP charge point id)

    parceiro = relationship("Parceiro", back_populates="estacoes")
    pagamentos = relationship("Pagamento", back_populates="estacao")
    conectores = relationship("Conector", back_populates="estacao")


class Conector(Base):
    """Um conector físico do carregador (OCPP connectorId), com o status real reportado por ele."""

    __tablename__ = "conectores"

    id = Column(Integer, primary_key=True, index=True)
    estacao_id = Column(Integer, ForeignKey("estacoes.id"), nullable=False)
    connector_id = Column(Integer, nullable=False)
    status = Column(String, default="Unavailable")  # status bruto do OCPP (Available, Charging, etc.)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    estacao = relationship("Estacao", back_populates="conectores")


class Pagamento(Base):
    __tablename__ = "pagamentos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    estacao_id = Column(Integer, ForeignKey("estacoes.id"), nullable=False)
    parceiro_id = Column(Integer, ForeignKey("parceiros.id"), nullable=True)
    valor = Column(Float, nullable=False)
    comissao_valor = Column(Float, nullable=True)  # parte retida pela plataforma (marketplace_fee)
    metodo = Column(String, default="pix")
    status = Column(String, default="pendente")  # pendente, aprovado, recusado, cancelado
    mp_preference_id = Column(String, nullable=True)
    mp_payment_id = Column(String, nullable=True)
    ocpp_id_tag = Column(String, nullable=True)  # identifica esta sessão perante o carregador (OCPP)
    ocpp_transaction_id = Column(Integer, nullable=True)  # transactionId devolvido pelo carregador
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="pagamentos")
    estacao = relationship("Estacao", back_populates="pagamentos")
    parceiro = relationship("Parceiro")
