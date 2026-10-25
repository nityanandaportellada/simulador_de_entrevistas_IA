
"""Rotas autorizadas para dados pessoais e administração de usuários."""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from ..auth import alterar_senha, gerar_hash_senha, verificar_senha
from ..models import Usuario
from ..schemas import AlterarPerfilRequest, AlterarSenhaRequest, UsuarioAtualizar, UsuarioResposta
from ..security import obter_administrador_atual, obter_usuario_atual
from ..usuarios import (
    alterar_perfil, ativar_usuario, atualizar_senha_hash, atualizar_usuario, buscar_usuario,
    cadastrar_usuario, inativar_usuario, listar_usuarios
)

router = APIRouter(prefix="/usuarios", tags=["Usuários"])
logger = logging.getLogger(__name__)


class UsuarioAdminCriar(BaseModel):
    """Cadastro administrativo, incluindo escolha de perfil."""
    model_config = ConfigDict(extra="forbid")
    nome: str = Field(min_length=2, max_length=150)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=128)
    perfil: Literal["estudante", "administrador"] = "estudante"


class RedefinirSenhaAdmin(BaseModel):
    """Recebe a nova senha; para a própria conta exige também a atual."""
    model_config = ConfigDict(extra="forbid")
    nova_senha: str = Field(min_length=8, max_length=128)
    senha_atual: str | None = Field(default=None, max_length=128)


@router.get("/me", response_model=UsuarioResposta)
def meu_usuario(usuario: Usuario = Depends(obter_usuario_atual)):
    """Devolve somente os campos públicos da conta autenticada."""
    return usuario


@router.put("/me", response_model=UsuarioResposta)
def atualizar_meus_dados(dados: UsuarioAtualizar, usuario: Usuario = Depends(obter_usuario_atual)):
    """Atualiza somente o nome e o e-mail da conta do token."""
    try:
        alterado = atualizar_usuario(usuario.id, dados.nome, str(dados.email))
        if not alterado:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        usuario_atualizado = buscar_usuario(usuario.id)
        if usuario_atualizado is None:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        return usuario_atualizado
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro


@router.put("/me/senha", status_code=status.HTTP_204_NO_CONTENT)
def alterar_minha_senha(dados: AlterarSenhaRequest, usuario: Usuario = Depends(obter_usuario_atual)):
    """Exige a senha atual antes de modificar a credencial do próprio usuário."""
    try:
        alterada = alterar_senha(usuario.id, dados.senha_atual, dados.nova_senha)
        if not alterada:
            raise HTTPException(status_code=409, detail="Não foi possível atualizar a senha. Entre novamente.")
        # Um novo login será necessário porque o hash da senha participa da validação JWT.
        return None
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro


@router.get("", response_model=list[UsuarioResposta])
def usuarios(administrador: Usuario = Depends(obter_administrador_atual)):
    """Lista usuários somente para administradores, sem devolver hashes de senha."""
    return listar_usuarios()


@router.post("", response_model=UsuarioResposta, status_code=status.HTTP_201_CREATED)
def criar_usuario_admin(dados: UsuarioAdminCriar, administrador: Usuario = Depends(obter_administrador_atual)):
    """Cadastra estudante ou administrador, exclusivamente por usuário administrador."""
    try:
        usuario_id = cadastrar_usuario(dados.nome, str(dados.email), gerar_hash_senha(dados.senha), dados.perfil)
        usuario = buscar_usuario(usuario_id)
        if usuario is None:
            raise HTTPException(status_code=500, detail="Usuário criado, mas não foi possível consultá-lo.")
        logger.info("Usuário %s cadastrado pelo administrador %s", usuario_id, administrador.id)
        return usuario
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro


@router.put("/{usuario_id}", response_model=UsuarioResposta)
def editar_usuario_admin(
    dados: UsuarioAtualizar, usuario_id: int = Path(gt=0),
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Permite editar nome e e-mail; perfil e situação têm rotas próprias."""
    try:
        if buscar_usuario(usuario_id) is None:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        atualizar_usuario(usuario_id, dados.nome, str(dados.email))
        usuario = buscar_usuario(usuario_id)
        logger.info("Cadastro %s editado pelo administrador %s", usuario_id, administrador.id)
        return usuario
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro


@router.put("/{usuario_id}/senha", status_code=status.HTTP_204_NO_CONTENT)
def redefinir_senha_admin(
    dados: RedefinirSenhaAdmin, usuario_id: int = Path(gt=0),
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Redefine senha, revogando JWTs antigos; para a conta própria exige a senha atual."""
    usuario = buscar_usuario(usuario_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if not usuario.ativo:
        raise HTTPException(status_code=400, detail="Ative o usuário antes de redefinir a senha.")
    try:
        if usuario_id == administrador.id:
            if not dados.senha_atual:
                raise HTTPException(status_code=400, detail="Informe sua senha atual.")
            alterada = alterar_senha(usuario_id, dados.senha_atual, dados.nova_senha)
        else:
            if verificar_senha(dados.nova_senha, usuario.senha_hash):
                raise ValueError("A nova senha deve ser diferente da senha anterior.")
            alterada = atualizar_senha_hash(usuario_id, gerar_hash_senha(dados.nova_senha))
        if not alterada:
            raise HTTPException(status_code=409, detail="Não foi possível atualizar a senha.")
        logger.info("Senha do usuário %s redefinida pelo administrador %s", usuario_id, administrador.id)
        return None
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro


@router.get("/{usuario_id}", response_model=UsuarioResposta)
def usuario_por_id(
    usuario_id: int = Path(gt=0), administrador: Usuario = Depends(obter_administrador_atual)
):
    """Permite consultar outro cadastro somente com perfil de administrador."""
    usuario = buscar_usuario(usuario_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return usuario


@router.put("/{usuario_id}/perfil")
def mudar_perfil(
    dados: AlterarPerfilRequest,
    usuario_id: int = Path(gt=0),
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Controla alterações de perfil, inclusive a proteção da conta do administrador atual."""
    if usuario_id == administrador.id and dados.perfil != administrador.perfil:
        raise HTTPException(status_code=400, detail="O administrador não pode alterar o próprio perfil.")
    try:
        alterado = alterar_perfil(usuario_id, dados.perfil)
        if not alterado:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        usuario = buscar_usuario(usuario_id)
        if usuario is None:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        return {
            "mensagem": "Perfil atualizado com sucesso.",
            "usuario": {"id": usuario.id, "nome": usuario.nome, "email": usuario.email,
                        "perfil": usuario.perfil, "ativo": usuario.ativo}
        }
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro


@router.put("/{usuario_id}/inativar")
def inativar(
    usuario_id: int = Path(gt=0), administrador: Usuario = Depends(obter_administrador_atual)
):
    """Bloqueia inativação da própria conta e protege o último administrador ativo."""
    if usuario_id == administrador.id:
        raise HTTPException(status_code=400, detail="O administrador não pode inativar o próprio usuário.")
    try:
        if not inativar_usuario(usuario_id):
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        return {"mensagem": "Usuário inativado com sucesso."}
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro


@router.put("/{usuario_id}/ativar")
def ativar(
    usuario_id: int = Path(gt=0), administrador: Usuario = Depends(obter_administrador_atual)
):
    """Reativa cadastro existente sem modificar perfil ou senha."""
    try:
        if not ativar_usuario(usuario_id):
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        return {"mensagem": "Usuário ativado com sucesso."}
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro
