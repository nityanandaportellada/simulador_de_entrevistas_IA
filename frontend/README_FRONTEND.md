# Frontend — Simulador de Entrevistas FESP-PR

Versão inicial da Fase 18.

## Requisitos

- Node.js
- npm
- Backend FastAPI em `http://127.0.0.1:8000`
- Backend com `MOCK_OPENAI=true` durante o desenvolvimento do frontend.

## Instalação

Na pasta `frontend`:

```powershell
npm install
npm run dev
```

Acesse:

```text
http://localhost:5173
```

## Build

```powershell
npm run build
```

## Estrutura incluída

### Estudante

- Login
- Cadastro
- Dashboard
- Nova entrevista
- Entrevista em andamento
- Histórico
- Lista de relatórios
- Relatório detalhado
- Perfil

### Administração

- Dashboard administrativo
- Usuários
- Tipos de entrevista
- Competências
- Critérios
- Perguntas

## Escopo

As telas foram limitadas aos recursos existentes no backend já validado.

Não foram incluídos no frontend:
- agenda;
- próxima entrevista;
- notificações persistentes;
- materiais de apoio;
- configurações pessoais inexistentes na API;
- recuperação de senha;
- PDF;
- funções não suportadas pelo backend.

## Identidade

O símbolo FESP-PR fornecido para o projeto está em:

`src/assets/fesp-symbol.png`

O wordmark “FESP-PR / Simulador de Entrevistas” é composto via HTML/CSS ao lado do símbolo para evitar distorção do logotipo.
