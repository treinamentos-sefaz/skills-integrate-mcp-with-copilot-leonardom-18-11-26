# API de Atividades da Mergington High School

Uma aplicação FastAPI super simples que permite aos estudantes visualizar e se inscrever em atividades extracurriculares.

## Funcionalidades

- Visualizar todas as atividades extracurriculares disponíveis
- Inscrever-se em atividades

## Primeiros Passos

1. Instale as dependências:

   ```
   pip install fastapi uvicorn
   ```

2. Crie um arquivo JSON **fora do repositório**, acessível somente ao usuário
   que executa o servidor (por exemplo, com `chmod 600`). Cadastre cada conta
   com seu e-mail, papel (`student` ou `admin`) e um token único. Gere cada
   token com `python -c 'import secrets; print(secrets.token_urlsafe(32))'` e
   entregue-o ao usuário por um canal seguro. Exemplo de formato:

   ```json
   [
     {"email": "aluno@mergington.edu", "role": "student", "token": "SUBSTITUA_POR_UM_TOKEN_ALEATORIO_UNICO"},
     {"email": "admin@mergington.edu", "role": "admin", "token": "SUBSTITUA_POR_OUTRO_TOKEN_ALEATORIO_UNICO"}
   ]
   ```

   Não use os valores de exemplo como credenciais. Tokens devem ter pelo menos
   32 caracteres ASCII sem espaços. Defina `AUTH_ACCOUNTS_FILE` como o caminho
   absoluto do arquivo. Não há cadastro público; o administrador provisiona
   as contas e pode revogar ou trocar tokens editando o arquivo.

3. Execute a aplicação a partir da raiz do repositório:

   ```sh
   export AUTH_ACCOUNTS_FILE=/caminho/privado/accounts.json
   uvicorn src.app:app --reload
   ```

4. Abra seu navegador e vá para:
   - Aplicação: http://localhost:8000/
   - Documentação da API: http://localhost:8000/docs
   - Documentação alternativa: http://localhost:8000/redoc

Na interface, entre com seu token para fazer alterações. Alunos podem gerenciar
somente a própria inscrição; administradores podem gerenciar qualquer
participante. A lista de atividades permanece pública. O token fica apenas na
memória da página e deve ser informado novamente após recarregar.

Use HTTPS ao transmitir tokens fora de um ambiente local confiável. O servidor
retorna 503 para operações autenticadas se a configuração estiver ausente ou
inválida; não há credenciais padrão.

## Endpoints da API

| Método | Endpoint                                                          | Descrição                                                           |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Obter todas as atividades com seus detalhes e contagem atual de participantes |
| GET    | `/auth/me`                                                        | Identificar a conta autenticada |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Inscrever-se em uma atividade                                       |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Cancelar uma inscrição |

Os três últimos endpoints exigem o cabeçalho `Authorization: Bearer <token>`.
Operações sobre o e-mail de outra pessoa retornam 403 para alunos. Professores
ou responsáveis precisam de uma conta `admin` para gerenciar outras inscrições.

## Modelo de Dados

A aplicação usa um modelo de dados simples com identificadores significativos:

1. **Atividades** - Usa o nome da atividade como identificador:

   - Descrição
   - Cronograma
   - Número máximo de participantes permitidos
   - Lista de emails de estudantes que estão inscritos

2. **Estudantes** - Usa email como identificador:
   - Nome
   - Nível da série

Todos os dados são armazenados na memória, o que significa que os dados serão resetados quando o servidor reiniciar.
