
"""Rotas autorizadas para dados pessoais e administração de usuários."""

from fastapi import APIRouter, Depends, HTTPException, Path, status

from ..auth import alterar_senha
from ..models import Usuario
from ..schemas import AlterarPerfilRequest, AlterarSenhaRequest, UsuarioAtualizar, UsuarioResposta
from ..security import obter_administrador_atual, obter_usuario_atual
from ..usuarios import (
    alterar_perfil, ativar_usuario, atualizar_usuario, buscar_usuario,
    inativar_usuario, listar_usuarios
)

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


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
