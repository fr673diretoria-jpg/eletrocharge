from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UsuarioCreate(BaseModel):
    nome: str = Field(min_length=2)
    email: EmailStr
    senha: str = Field(min_length=6)
    telefone: Optional[str] = None


class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str


class UsuarioOut(BaseModel):
    id: int
    nome: str
    email: EmailStr
    telefone: Optional[str] = None
    is_admin: bool = False

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


class EsqueciSenha(BaseModel):
    email: EmailStr


class RedefinirSenha(BaseModel):
    token: str
    nova_senha: str = Field(min_length=6)


class ContatoCreate(BaseModel):
    assunto: str = Field(min_length=3, max_length=120)
    mensagem: str = Field(min_length=5, max_length=2000)


class EmailContatoConfig(BaseModel):
    email: EmailStr


class EstacaoCreate(BaseModel):
    nome: str = Field(min_length=2)
    endereco: str = Field(min_length=3)
    latitude: float
    longitude: float
    preco_kwh: float = Field(gt=0)
    potencia_kw: int = Field(gt=0)
    conector: str
    rapido: bool = False
    vagas_total: int = Field(gt=0)
    status: str = "livre"
    ocpp_identity: Optional[str] = None


class EstacaoUpdate(BaseModel):
    nome: Optional[str] = None
    endereco: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    preco_kwh: Optional[float] = None
    potencia_kw: Optional[int] = None
    conector: Optional[str] = None
    rapido: Optional[bool] = None
    vagas_livres: Optional[int] = None
    vagas_total: Optional[int] = None
    status: Optional[str] = None
    ocpp_identity: Optional[str] = None


class EstacaoOut(BaseModel):
    id: int
    nome: str
    endereco: str
    latitude: float
    longitude: float
    preco_kwh: float
    potencia_kw: int
    conector: str
    rapido: bool
    vagas_livres: int
    vagas_total: int
    status: str
    distancia_km: Optional[float] = None
    ocpp_identity: Optional[str] = None
    ocpp_conectado: bool = False

    class Config:
        from_attributes = True


class PagamentoCreate(BaseModel):
    estacao_id: int
    valor: float = Field(gt=0)
    metodo: str = "pix"  # pix, cartao, boleto (a escolha final ocorre no checkout)
    lat: float
    lng: float


class FinalizarCarregamento(BaseModel):
    lat: float
    lng: float


class PagamentoOut(BaseModel):
    id: int
    estacao_id: int
    valor: float
    metodo: str
    status: str
    criado_em: datetime
    checkout_url: Optional[str] = None
    ocpp_connector_id: Optional[int] = None

    class Config:
        from_attributes = True


class ParceiroCreate(BaseModel):
    nome: str = Field(min_length=2)
    email: EmailStr
    telefone: Optional[str] = None
    comissao_percentual: Optional[float] = Field(default=None, ge=0, le=100)


class ParceiroOut(BaseModel):
    id: int
    nome: str
    email: EmailStr
    telefone: Optional[str] = None
    comissao_percentual: Optional[float] = None
    conectado: bool = False

    class Config:
        from_attributes = True


class PagamentoAdminOut(BaseModel):
    id: int
    valor: float
    comissao_valor: Optional[float] = None
    metodo: str
    status: str
    criado_em: datetime
    usuario_nome: Optional[str] = None
    usuario_email: Optional[str] = None
    estacao_nome: Optional[str] = None
    parceiro_nome: Optional[str] = None
    ocpp_id_tag: Optional[str] = None
    ocpp_transaction_id: Optional[int] = None

    class Config:
        from_attributes = True
