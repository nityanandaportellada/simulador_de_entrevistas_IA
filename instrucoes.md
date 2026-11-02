MANUAL DE INSTALAÇÃO E EXECUÇÃO
Simulador de Entrevistas de Emprego Baseado em Inteligência Artificial
Projeto acadêmico — FESPPR
1. Objetivo
Este manual orienta os integrantes do grupo e os avaliadores na instalação e execução do Simulador de Entrevistas, incluindo a configuração da chave de acesso à API da OpenAI.
O sistema permite realizar entrevistas simuladas, responder perguntas técnicas, receber avaliações por inteligência artificial e consultar relatórios de desempenho.
2. Programas necessários
Antes de iniciar, instale:
•	Python: versão 3.14, utilizada no desenvolvimento do projeto.
•	Node.js: versão 24 ou compatível.
•	Git: necessário para clonar o projeto do GitHub, caso não utilize o ZIP.
•	Editor de código: Visual Studio Code ou outro de preferência.
Também será necessário ter acesso à internet para instalar as dependências e utilizar a OpenAI.
3. Obter os arquivos do projeto
1.	Receba o ZIP disponibilizado pelo grupo.
2.	Extraia o conteúdo para uma pasta no computador.
3.	Para facilitar os comandos deste manual, utilize o caminho:
C:\Projetos\Simulador de Entrevista
A entrega inclui o backend Python, o frontend React e o banco SQLite data\entrevistas.db, contendo o catálogo necessário ao funcionamento do sistema.
4. Instalar as dependências do backend
Abra o PowerShell e acesse a pasta principal:
cd "C:\Projetos\Simulador de Entrevista"
Instale as bibliotecas Python:
py -3.14 -m pip install -r requirements.txt
Caso o comando py -3.14 não esteja disponível, utilize o caminho do Python instalado no computador.
5. Instalar as dependências do frontend
No PowerShell, execute:
cd "C:\Projetos\Simulador de Entrevista\frontend"
npm.cmd ci
Esse comando instalará as dependências do React utilizando as versões registradas no package-lock.json.
6. Configurar a chave da OpenAI
A chave da API será encaminhada pelo responsável pelo projeto em um canal separado.
Atenção: a chave não está incluída no GitHub nem no ZIP. Não é necessário criar uma nova chave pessoal se você recebeu uma chave válida do grupo.
Abra o PowerShell e execute:
cd "C:\Projetos\Simulador de Entrevista"

$chave = Read-Host "Cole a chave OpenAI" -AsSecureString
$ponteiro = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($chave)

try {
    $env:OPENAI_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ponteiro)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ponteiro)
    Remove-Variable chave
}

$env:OPENAI_MODEL = "gpt-4.1-mini"
$env:MOCK_OPENAI = "false"
Quando aparecer a mensagem Cole a chave OpenAI:, cole a chave recebida e pressione Enter.
Os caracteres da chave não aparecerão na tela.
Não substitua o texto dentro de Read-Host pela chave. A chave deve ser informada somente quando o PowerShell solicitar.
7. Configurar a autenticação do sistema
O backend também utiliza uma variável denominada JWT_SECRET para proteger os tokens de autenticação dos usuários.
Na mesma janela do PowerShell utilizada na etapa anterior, execute:
$env:JWT_SECRET = py -3.14 -c "import secrets; print(secrets.token_hex(32))"
Esse comando gera um segredo aleatório para a sessão de execução.
8. Conferir as configurações
Para verificar se o ambiente está preparado, execute:
Write-Host "Chave configurada:" (-not [string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY))
Write-Host "Modelo:" $env:OPENAI_MODEL
Write-Host "Modo MOCK:" $env:MOCK_OPENAI
Write-Host "JWT configurado:" (-not [string]::IsNullOrWhiteSpace($env:JWT_SECRET))
O resultado esperado é:
Chave configurada: True
Modelo: gpt-4.1-mini
Modo MOCK: false
JWT configurado: True
Esses comandos não enviam requisições à OpenAI e não consomem créditos.
Importante: essas variáveis ficam disponíveis na janela do PowerShell em que foram definidas e nos processos iniciados a partir dela. Ao fechar a janela, será necessário configurá-las novamente.
9. Iniciar o backend
Na mesma janela do PowerShell em que a chave e as demais variáveis foram configuradas, execute:
cd "C:\Projetos\Simulador de Entrevista"
py -3.14 -m uvicorn app.main:app --reload
O servidor deverá iniciar, normalmente, no endereço:
http://127.0.0.1:8000
Para consultar a documentação da API:
http://127.0.0.1:8000/docs
Mantenha essa janela aberta enquanto estiver utilizando o sistema.
10. Iniciar o frontend
Abra uma segunda janela do PowerShell, sem encerrar a primeira.
Execute:
cd "C:\Projetos\Simulador de Entrevista\frontend"
npm.cmd run dev
O Vite informará o endereço local em que o frontend está disponível, normalmente:
http://localhost:5173
Abra esse endereço no navegador.
Caso o frontend esteja configurado para uma URL de API diferente, ajuste a configuração VITE_API_URL conforme o ambiente. Em uma instalação local padrão, o backend estará em http://127.0.0.1:8000.
11. Utilizar o Simulador de Entrevistas
Com backend e frontend em execução:
1.	Abra a página inicial no navegador.
2.	Faça login ou crie uma conta de estudante.
3.	Acesse a opção de nova entrevista.
4.	Selecione o tipo de entrevista, a área, a subárea e o perfil profissional.
5.	Responda às oito perguntas apresentadas.
6.	Finalize a entrevista.
7.	Solicite a avaliação pela inteligência artificial.
8.	Aguarde a conclusão do processamento.
9.	Consulte o relatório de desempenho.
10.	Utilize o histórico para acompanhar os resultados das entrevistas.
O sistema utiliza critérios de avaliação e gera uma pontuação final de acordo com as respostas fornecidas.
12. Problemas comuns
Problema: a página do sistema não abre.
Verifique se o frontend está em execução com npm.cmd run dev e utilize o endereço exibido no terminal.
Problema: o frontend abre, mas não consegue acessar os dados.
Verifique se o backend está funcionando na porta 8000 e se a URL da API está corretamente configurada.
Problema: aparece erro relacionado à chave OpenAI.
Verifique se OPENAI_API_KEY foi configurada na mesma sessão utilizada para iniciar o backend.
Problema: a avaliação não é concluída.
Confira a conexão com a internet, o saldo ou faturamento disponível, a validade da chave e as mensagens do terminal do backend.
Problema: o PowerShell informa que não reconhece py ou npm.cmd.
Verifique se Python e Node.js estão instalados e disponíveis no PATH do Windows.
Problema: a autenticação apresenta erro.
Verifique a configuração de JWT_SECRET. Se o segredo for alterado após iniciar o servidor, será necessário reiniciar o backend e efetuar login novamente.
14. Encerrar o sistema
Para encerrar a execução:
1.	Na janela do frontend, pressione Ctrl + C.
2.	Na janela do backend, pressione Ctrl + C.
3.	Feche as janelas do PowerShell.
A configuração da chave será perdida ao encerrar a sessão, mas os dados gravados no banco SQLite permanecerão disponíveis.
15. Orientações de segurança
•	Não publique a chave da OpenAI no GitHub.
•	Não envie capturas de tela mostrando a chave.
•	Não coloque a chave nos arquivos React ou TypeScript.
•	Utilize apenas a chave fornecida pelo responsável pelo projeto.
•	Não compartilhe o banco com dados pessoais de usuários reais.
•	Após a avaliação acadêmica, o responsável poderá revogar a chave utilizada nos testes.

