from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from . import config, models
from .database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))


def criar_token(dados: dict) -> str:
    payload = dados.copy()
    expira = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload.update({"exp": expira})
    return jwt.encode(payload, config.SECRET_KEY, algorithm=config.ALGORITHM)


def criar_token_reset_senha(usuario_id: int) -> str:
    expira = datetime.utcnow() + timedelta(minutes=config.RESET_SENHA_EXPIRA_MINUTOS)
    payload = {"sub": str(usuario_id), "finalidade": "reset_senha", "exp": expira}
    return jwt.encode(payload, config.SECRET_KEY, algorithm=config.ALGORITHM)


def validar_token_reset_senha(token: str) -> int:
    """Retorna o id do usuário se o token for válido, ou levanta HTTPException 400."""
    erro = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Link inválido ou expirado")
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
    except JWTError:
        raise erro

    if payload.get("finalidade") != "reset_senha" or payload.get("sub") is None:
        raise erro

    return int(payload["sub"])


def obter_usuario_atual(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.Usuario:
    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credenciais_invalidas

    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        usuario_id = payload.get("sub")
        if usuario_id is None:
            raise credenciais_invalidas
    except JWTError:
        raise credenciais_invalidas

    usuario = db.query(models.Usuario).filter(models.Usuario.id == int(usuario_id)).first()
    if usuario is None:
        raise credenciais_invalidas

    return usuario


def sincronizar_admin(usuario: models.Usuario, db: Session) -> models.Usuario:
    """Promove automaticamente a admin quem estiver na lista ADMIN_EMAILS do .env."""
    deveria_ser_admin = usuario.email.lower() in config.ADMIN_EMAILS
    if deveria_ser_admin and not usuario.is_admin:
        usuario.is_admin = True
        db.commit()
        db.refresh(usuario)
    return usuario


def exigir_admin(usuario: models.Usuario = Depends(obter_usuario_atual)) -> models.Usuario:
    if not usuario.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a administradores")
    return usuario
