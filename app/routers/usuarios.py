"""Rotas usadas para consultar e administrar os usuários do sistema."""

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import alterar_senha
from ..models import Usuario
from ..schemas import (
    AlterarPerfilRequest,
    AlterarSenhaRequest,
    UsuarioAtualizar,
    UsuarioResposta
)
from ..security import obter_administrador_atual, obter_usuario_atual
from ..usuarios import (
    alterar_perfil,
    ativar_usuario,
    atualizar_usuario,
    buscar_usuario,
    inativar_usuario,
    listar_usuarios
)

# Agrupa todas as rotas relacionadas aos usuários.
router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.get("/me", response_model=UsuarioResposta)
def meu_usuario(usuario: Usuario = Depends(obter_usuario_atual)):
    """Retorna os dados do usuário identificado pelo token da requisição."""
    return usuario


@router.put("/me", response_model=UsuarioResposta)
def atualizar_meus_dados(
    dados: UsuarioAtualizar,
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Permite ao usuário autenticado alterar o próprio nome e e-mail."""
    try:
        # Atualiza somente o usuário que veio do token, evitando alteração de outra conta.
        atualizar_usuario(
            usuario.id,
            dados.nome,
            str(dados.email)
        )

        # Busca novamente para devolver os dados já atualizados.
        usuario_atualizado = buscar_usuario(usuario.id)

        if usuario_atualizado is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado."
            )

        return usuario_atualizado

    except HTTPException:
        raise

    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.put("/me/senha", status_code=status.HTTP_204_NO_CONTENT)
def alterar_minha_senha(
    dados: AlterarSenhaRequest,
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Permite ao usuário autenticado trocar a própria senha."""
    try:
        # A camada de autenticação confere a senha atual antes de realizar a troca.
        alterar_senha(
            usuario.id,
            dados.senha_atual,
            dados.nova_senha
        )

        return None

    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.get("", response_model=list[UsuarioResposta])
def usuarios(administrador: Usuario = Depends(obter_administrador_atual)):
    """Lista todos os usuários e permite o acesso somente para administradores."""
    return listar_usuarios()


@router.get("/{usuario_id}", response_model=UsuarioResposta)
def usuario_por_id(
    usuario_id: int,
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Busca um usuário pelo ID quando a requisição é feita por um administrador."""
    try:
        usuario = buscar_usuario(usuario_id)

        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado."
            )

        return usuario

    except HTTPException:
        raise

    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.put("/{usuario_id}/perfil")
def mudar_perfil(
    usuario_id: int,
    dados: AlterarPerfilRequest,
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Altera o perfil de um usuário e mantém a proteção do último administrador ativo."""
    try:
        # A regra que protege o último administrador fica na camada de usuários.
        alterado = alterar_perfil(
            usuario_id,
            dados.perfil
        )

        if not alterado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado."
            )

        # Recupera os dados atuais para devolver o resultado da alteração.
        usuario_atualizado = buscar_usuario(usuario_id)

        return {
            "mensagem": "Perfil atualizado com sucesso.",
            "usuario": {
                "id": usuario_atualizado.id,
                "nome": usuario_atualizado.nome,
                "email": usuario_atualizado.email,
                "perfil": usuario_atualizado.perfil,
                "ativo": usuario_atualizado.ativo
            }
        }

    except HTTPException:
        raise

    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.put("/{usuario_id}/inativar")
def inativar(
    usuario_id: int,
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Inativa um usuário sem permitir que o administrador inative a própria conta."""
    # Além dessa verificação, a camada de usuários protege o último administrador ativo.
    if usuario_id == administrador.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O administrador não pode inativar o próprio usuário."
        )

    try:
        alterado = inativar_usuario(usuario_id)

        if not alterado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado."
            )

        return {
            "mensagem": "Usuário inativado com sucesso."
        }

    except HTTPException:
        raise

    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.put("/{usuario_id}/ativar")
def ativar(
    usuario_id: int,
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Ativa novamente um usuário quando a operação é feita por um administrador."""
    try:
        alterado = ativar_usuario(usuario_id)

        if not alterado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado."
            )

        return {
            "mensagem": "Usuário ativado com sucesso."
        }

    except HTTPException:
        raise

    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )