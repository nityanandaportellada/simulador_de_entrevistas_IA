"""Rotas públicas de cadastro, bootstrap administrativo e login."""

from fastapi import APIRouter, Header, HTTPException, status

from ..auth import (
    AdministradorJaExisteError,
    autenticar_usuario,
    cadastrar_estudante,
    cadastrar_primeiro_administrador
)
from ..schemas import LoginRequest, TokenResponse, UsuarioCriar, UsuarioResposta
from ..security import criar_token_acesso
from ..usuarios import buscar_usuario

# Agrupa as rotas de autenticação no endereço /auth.
router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/cadastro", response_model=UsuarioResposta, status_code=status.HTTP_201_CREATED)
def cadastro(dados: UsuarioCriar):
    """Realiza o cadastro público e sempre cria um usuário com perfil de estudante."""
    try:
        # O endpoint não recebe perfil para impedir que alguém se cadastre como administrador.
        usuario_id = cadastrar_estudante(
            nome=dados.nome,
            email=str(dados.email),
            senha=dados.senha
        )

        # Busca o cadastro criado para devolver os dados pela API.
        usuario = buscar_usuario(usuario_id)

        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Usuário criado, mas não foi possível recuperá-lo."
            )

        return usuario

    except HTTPException:
        raise
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.post("/bootstrap-admin", response_model=UsuarioResposta, status_code=status.HTTP_201_CREATED)
def bootstrap_admin(
    dados: UsuarioCriar,
    x_bootstrap_token: str | None = Header(default=None, alias="X-Bootstrap-Token")
):
    """Cria o primeiro administrador usando o token especial configurado no ambiente."""
    try:
        # A função confere o token e também impede um segundo bootstrap.
        usuario_id = cadastrar_primeiro_administrador(
            nome=dados.nome,
            email=str(dados.email),
            senha=dados.senha,
            token_bootstrap=x_bootstrap_token
        )

        # Recupera o administrador que acabou de ser criado.
        usuario = buscar_usuario(usuario_id)

        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Administrador criado, mas não foi possível recuperá-lo."
            )

        return usuario

    except AdministradorJaExisteError as erro:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(erro)
        )

    except PermissionError:
        # Não informa detalhes sobre o token recebido para não expor informação sensível.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de bootstrap inválido."
        )

    except RuntimeError as erro:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(erro)
        )

    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.post("/login", response_model=TokenResponse)
def login(dados: LoginRequest):
    """Confere as credenciais e devolve um token JWT quando o login é válido."""
    # Primeiro tenta localizar e autenticar o usuário.
    usuario = autenticar_usuario(
        email=str(dados.email),
        senha=dados.senha
    )

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos."
        )

    # O token guarda o ID e o perfil necessários para identificar o usuário nas próximas rotas.
    token = criar_token_acesso(
        usuario_id=usuario.id,
        perfil=usuario.perfil
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }