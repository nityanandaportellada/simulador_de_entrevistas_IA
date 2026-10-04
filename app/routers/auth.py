"""
routers/auth.py

Endpoints relacionados à autenticação
do Simulador de Entrevistas.

Versão: 0.3

Responsabilidades:

- cadastrar estudantes;
- criar o primeiro administrador;
- autenticar usuários;
- gerar token JWT após autenticação válida.

O cadastro público normal sempre cria estudantes.

O primeiro administrador utiliza um endpoint
separado e protegido pelo header:

    X-Bootstrap-Token
"""

from fastapi import (
    APIRouter,
    Header,
    HTTPException,
    status
)


from ..schemas import (
    LoginRequest,
    TokenResponse,
    UsuarioCriar,
    UsuarioResposta
)


from ..auth import (
    AdministradorJaExisteError,
    autenticar_usuario,
    cadastrar_estudante,
    cadastrar_primeiro_administrador
)


from ..usuarios import (
    buscar_usuario
)


from ..security import (
    criar_token_acesso
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/auth",
    tags=["Autenticação"]
)


# ============================================================
# CADASTRAR ESTUDANTE
# ============================================================

@router.post(
    "/cadastro",
    response_model=UsuarioResposta,
    status_code=status.HTTP_201_CREATED
)
def cadastro(
    dados: UsuarioCriar
):
    """
    Realiza o cadastro público de um estudante.

    O perfil não é recebido pelo endpoint.

    Todo cadastro público será criado
    obrigatoriamente como estudante.
    """

    try:

        usuario_id = cadastrar_estudante(
            nome=dados.nome,
            email=str(
                dados.email
            ),
            senha=dados.senha
        )


        usuario = buscar_usuario(
            usuario_id
        )


        if usuario is None:

            raise HTTPException(
                status_code=(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                ),
                detail=(
                    "Usuário criado, mas não foi "
                    "possível recuperá-lo."
                )
            )


        return usuario


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(
                erro
            )
        )


# ============================================================
# BOOTSTRAP DO PRIMEIRO ADMINISTRADOR
# ============================================================

@router.post(
    "/bootstrap-admin",
    response_model=UsuarioResposta,
    status_code=status.HTTP_201_CREATED
)
def bootstrap_admin(
    dados: UsuarioCriar,

    x_bootstrap_token: str | None = Header(
        default=None,
        alias="X-Bootstrap-Token"
    )
):
    """
    Cria o primeiro administrador do sistema.

    Este endpoint somente funciona quando:

    - ADMIN_BOOTSTRAP_TOKEN estiver configurado;
    - o header X-Bootstrap-Token estiver correto;
    - ainda não existir administrador cadastrado.

    Depois que o primeiro administrador é criado,
    novas chamadas são permanentemente bloqueadas
    enquanto existir registro administrativo.
    """

    try:

        usuario_id = (
            cadastrar_primeiro_administrador(
                nome=dados.nome,
                email=str(
                    dados.email
                ),
                senha=dados.senha,
                token_bootstrap=(
                    x_bootstrap_token
                )
            )
        )


        usuario = buscar_usuario(
            usuario_id
        )


        if usuario is None:

            raise HTTPException(
                status_code=(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                ),
                detail=(
                    "Administrador criado, mas não foi "
                    "possível recuperá-lo."
                )
            )


        return usuario


    except AdministradorJaExisteError as erro:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(
                erro
            )
        )


    except PermissionError:

        # Não retornamos detalhes adicionais
        # sobre o token recebido.

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Token de bootstrap inválido."
            )
        )


    except RuntimeError as erro:

        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=str(
                erro
            )
        )


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(
                erro
            )
        )


# ============================================================
# LOGIN
# ============================================================

@router.post(
    "/login",
    response_model=TokenResponse
)
def login(
    dados: LoginRequest
):
    """
    Autentica o usuário e retorna
    um token JWT.
    """

    usuario = autenticar_usuario(
        email=str(
            dados.email
        ),
        senha=dados.senha
    )


    if usuario is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos."
        )


    token = criar_token_acesso(
        usuario_id=usuario.id,
        perfil=usuario.perfil
    )


    return {

        "access_token":
            token,

        "token_type":
            "bearer"

    }