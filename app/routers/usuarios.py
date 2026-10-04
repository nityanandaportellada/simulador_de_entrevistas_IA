"""
routers/usuarios.py

Endpoints relacionados aos usuários
do Simulador de Entrevistas.

Versão: 0.3

Responsabilidades:

- consultar dados do próprio usuário;
- atualizar dados do próprio usuário;
- alterar senha;
- listar usuários;
- consultar usuários;
- alterar perfil;
- ativar usuários;
- inativar usuários;
- proteger o último administrador ativo.

Operações administrativas são protegidas
por autenticação e perfil administrador.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)


from ..models import Usuario


from ..schemas import (
    UsuarioResposta,
    UsuarioAtualizar,
    AlterarSenhaRequest,
    AlterarPerfilRequest
)


from ..usuarios import (
    listar_usuarios,
    buscar_usuario,
    atualizar_usuario,
    alterar_perfil,
    ativar_usuario,
    inativar_usuario
)


from ..auth import (
    alterar_senha
)


from ..security import (
    obter_usuario_atual,
    obter_administrador_atual
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuários"]
)


# ============================================================
# CONSULTAR O PRÓPRIO USUÁRIO
# ============================================================

@router.get(
    "/me",
    response_model=UsuarioResposta
)
def meu_usuario(
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Retorna os dados do usuário autenticado.
    """

    return usuario


# ============================================================
# ATUALIZAR OS PRÓPRIOS DADOS
# ============================================================

@router.put(
    "/me",
    response_model=UsuarioResposta
)
def atualizar_meus_dados(
    dados: UsuarioAtualizar,
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Permite ao usuário autenticado atualizar
    seu nome e e-mail.
    """

    try:

        atualizar_usuario(
            usuario.id,
            dados.nome,
            str(
                dados.email
            )
        )


        usuario_atualizado = buscar_usuario(
            usuario.id
        )


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
            detail=str(
                erro
            )
        )


# ============================================================
# ALTERAR A PRÓPRIA SENHA
# ============================================================

@router.put(
    "/me/senha",
    status_code=status.HTTP_204_NO_CONTENT
)
def alterar_minha_senha(
    dados: AlterarSenhaRequest,
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Permite ao usuário autenticado alterar
    sua própria senha.
    """

    try:

        alterar_senha(
            usuario.id,
            dados.senha_atual,
            dados.nova_senha
        )


        return None


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(
                erro
            )
        )


# ============================================================
# LISTAR USUÁRIOS
# ============================================================

@router.get(
    "",
    response_model=list[UsuarioResposta]
)
def usuarios(
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Lista todos os usuários cadastrados.

    Disponível somente para administradores.
    """

    return listar_usuarios()


# ============================================================
# BUSCAR USUÁRIO POR ID
# ============================================================

@router.get(
    "/{usuario_id}",
    response_model=UsuarioResposta
)
def usuario_por_id(
    usuario_id: int,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Busca determinado usuário.

    Disponível somente para administradores.
    """

    try:

        usuario = buscar_usuario(
            usuario_id
        )


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
            detail=str(
                erro
            )
        )


# ============================================================
# ALTERAR PERFIL
# ============================================================

@router.put(
    "/{usuario_id}/perfil"
)
def mudar_perfil(
    usuario_id: int,
    dados: AlterarPerfilRequest,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Altera o perfil de determinado usuário.

    Disponível somente para administradores.

    O último administrador ativo não pode
    perder o perfil administrativo.
    """

    try:

        alterado = alterar_perfil(
            usuario_id,
            dados.perfil
        )


        if not alterado:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado."
            )


        usuario_atualizado = buscar_usuario(
            usuario_id
        )


        return {

            "mensagem":
                "Perfil atualizado com sucesso.",

            "usuario":
                {

                    "id":
                        usuario_atualizado.id,

                    "nome":
                        usuario_atualizado.nome,

                    "email":
                        usuario_atualizado.email,

                    "perfil":
                        usuario_atualizado.perfil,

                    "ativo":
                        usuario_atualizado.ativo

                }

        }


    except HTTPException:

        raise


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(
                erro
            )
        )


# ============================================================
# INATIVAR USUÁRIO
# ============================================================

@router.put(
    "/{usuario_id}/inativar"
)
def inativar(
    usuario_id: int,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Inativa determinado usuário.

    O administrador não pode utilizar este
    endpoint para inativar a própria conta.

    Além disso, a camada de serviço impede
    a inativação do último administrador ativo.
    """

    if usuario_id == administrador.id:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "O administrador não pode "
                "inativar o próprio usuário."
            )
        )


    try:

        alterado = inativar_usuario(
            usuario_id
        )


        if not alterado:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado."
            )


        return {

            "mensagem":
                "Usuário inativado com sucesso."

        }


    except HTTPException:

        raise


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(
                erro
            )
        )


# ============================================================
# ATIVAR USUÁRIO
# ============================================================

@router.put(
    "/{usuario_id}/ativar"
)
def ativar(
    usuario_id: int,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Ativa determinado usuário.

    Disponível somente para administradores.
    """

    try:

        alterado = ativar_usuario(
            usuario_id
        )


        if not alterado:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado."
            )


        return {

            "mensagem":
                "Usuário ativado com sucesso."

        }


    except HTTPException:

        raise


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(
                erro
            )
        )