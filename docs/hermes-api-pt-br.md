# API FastAPI do Hermes Agent

Esta documentação mostra como executar, configurar, testar e consumir a API
FastAPI criada no pacote `hermes_api`.

A API é uma camada HTTP externa ao `AIAgent`: ela chama o runtime existente do
Hermes, mas não altera o loop do agente, não adiciona ferramentas core e não
substitui a CLI, o TUI, o gateway ou o dashboard.

## Quando usar esta API

Use esta API quando você precisa:

- chamar o Hermes por HTTP;
- executar um turno de chat via `POST /api/v1/chat`;
- listar sessões em cache do processo FastAPI;
- descobrir toolsets disponíveis;
- expor métricas simples;
- gerar configuração de conector MCP para clientes MCP externos.

Se você precisa de uma API compatível com OpenAI (`/v1/chat/completions`) para
frontends como Open WebUI ou LobeChat, use a página **API Server** do Hermes. A
API FastAPI documentada aqui é uma superfície própria e versionada em `/api/v1`.

## Subir a aplicação

Execute na raiz do repositório ou em uma instalação do pacote:

```bash
hermes-api --host 127.0.0.1 --port 8000
```

Modo desenvolvimento com reload:

```bash
hermes-api --host 127.0.0.1 --port 8000 --reload
```

Por segurança, o host padrão recomendado é `127.0.0.1`. Para expor em rede, use
`0.0.0.0` somente atrás de controles de produção, como proxy reverso, ingress,
firewall, autenticação e HTTPS.

## Documentação interativa

Com a aplicação rodando, abra:

```text
http://127.0.0.1:8000/docs
```

Também estão disponíveis:

```text
http://127.0.0.1:8000/redoc
http://127.0.0.1:8000/openapi.json
```

## Configuração

### Segredo via variável de ambiente

A autenticação usa um token bearer opcional:

```bash
export HERMES_API_TOKEN="troque-por-um-token-longo-e-aleatorio"
```

Quando `HERMES_API_TOKEN` estiver definido, rotas privadas exigem:

```http
Authorization: Bearer troque-por-um-token-longo-e-aleatorio
```

Sem esse token configurado, a API opera em modo local/desenvolvimento sem exigir
autenticação.

### Configurações não secretas em `config.yaml`

Configurações comportamentais ficam em `~/.hermes/config.yaml`:

```yaml
api:
  environment: development
  cors_origins:
    - http://localhost:3000
  request_log_enabled: true
  rate_limit_per_minute: 60
```

| Chave | Padrão | Descrição |
| --- | --- | --- |
| `api.environment` | `development` | Nome do ambiente. |
| `api.cors_origins` | `[]` | Origens permitidas pelo CORS. Lista vazia não instala middleware CORS. |
| `api.request_log_enabled` | `true` | Liga logs sanitizados de conclusão de requests. |
| `api.rate_limit_per_minute` | `0` | Limite process-local por host de cliente. `0` desativa. |

## Endpoints

| Método | Caminho | Autenticação | Descrição |
| --- | --- | --- | --- |
| `GET` | `/health` | Não | Verifica se o serviço está vivo. |
| `GET` | `/metrics` | Não | Retorna métricas process-local em texto estilo Prometheus. |
| `POST` | `/api/v1/chat` | Bearer opcional | Executa um turno de chat no Hermes. |
| `GET` | `/api/v1/sessions` | Bearer opcional | Lista sessões em cache no processo da API. |
| `GET` | `/api/v1/sessions/{session_id}` | Bearer opcional | Consulta uma sessão em cache. |
| `DELETE` | `/api/v1/sessions/{session_id}` | Admin | Remove uma sessão em cache. |
| `GET` | `/api/v1/toolsets` | Não | Lista toolsets disponíveis. |
| `GET` | `/api/v1/mcp/connector` | Bearer opcional | Gera configuração para cliente MCP. |

“Bearer opcional” significa que a rota fica aberta quando `HERMES_API_TOKEN` não
está configurado e passa a exigir token quando ele existe.

## Health check

```bash
curl http://127.0.0.1:8000/health
```

Resposta:

```json
{
  "status": "ok"
}
```

## Chat

### Request

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "Explique o Hermes Agent em um parágrafo.",
    "session_id": "demo",
    "enabled_toolsets": ["web"],
    "disabled_toolsets": ["terminal"]
  }'
```

Campos aceitos:

| Campo | Obrigatório | Descrição |
| --- | --- | --- |
| `message` | Sim | Mensagem do usuário. Deve ter pelo menos 1 caractere. |
| `session_id` | Não | Reutiliza um agente cacheado para a sessão. |
| `model` | Não | Override de modelo passado ao `AIAgent`. |
| `provider` | Não | Override de provider passado ao `AIAgent`. |
| `enabled_toolsets` | Não | Lista de toolsets habilitados. Padrão: `['web']`. |
| `disabled_toolsets` | Não | Lista de toolsets desabilitados. Padrão: `['terminal']`. |

### Response

```json
{
  "data": {
    "response": "Hermes Agent é ...",
    "session_id": "demo"
  },
  "message": "Chat completed successfully"
}
```

Erros comuns:

| Status | Motivo |
| --- | --- |
| `401` | Token ausente ou inválido quando autenticação está ativa. |
| `422` | Payload inválido, por exemplo `message` vazio. |
| `429` | Rate limit process-local excedido. |
| `500` | Falha inesperada durante o turno do Hermes. |

## Sessões

Listar sessões em cache:

```bash
curl 'http://127.0.0.1:8000/api/v1/sessions?limit=50&offset=0'
```

Consultar uma sessão:

```bash
curl http://127.0.0.1:8000/api/v1/sessions/demo
```

Remover uma sessão:

```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/sessions/demo \
  -H 'Authorization: Bearer troque-por-um-token-longo-e-aleatorio'
```

A sessão listada aqui é o cache process-local da API. Se o processo FastAPI
reiniciar, esse cache é limpo. A persistência real de conversas continua sendo
responsabilidade do runtime Hermes quando o `AIAgent` roda com `session_id`.

## Toolsets

```bash
curl 'http://127.0.0.1:8000/api/v1/toolsets?limit=10&name=web'
```

Exemplo de resposta:

```json
{
  "limit": 10,
  "offset": 0,
  "total": 1,
  "data": [
    {
      "name": "web",
      "tools": ["web_search", "web_extract"]
    }
  ]
}
```

## Conector MCP

O endpoint de conector MCP retorna um fragmento de configuração para clientes MCP
iniciarem o servidor MCP existente do Hermes via `hermes mcp serve`.

```bash
curl 'http://127.0.0.1:8000/api/v1/mcp/connector?server_name=hermes&verbose=false'
```

Resposta:

```json
{
  "data": {
    "server_name": "hermes",
    "transport": "stdio",
    "command": "hermes",
    "args": ["mcp", "serve"],
    "client_config": {
      "mcpServers": {
        "hermes": {
          "command": "hermes",
          "args": ["mcp", "serve"]
        }
      }
    },
    "usage": "hermes mcp serve"
  },
  "message": "MCP connector configuration generated"
}
```

## Métricas

```bash
curl http://127.0.0.1:8000/metrics
```

Exemplo:

```text
# HELP hermes_api_requests_total Total HTTP requests handled by the Hermes API.
# TYPE hermes_api_requests_total counter
hermes_api_requests_total 12
# HELP hermes_api_errors_total Total HTTP 5xx responses from the Hermes API.
# TYPE hermes_api_errors_total counter
hermes_api_errors_total 0
```

## Testar sem abrir porta de rede

Use `TestClient`:

```bash
uv run --with fastapi --with httpx python - <<'PY'
from fastapi.testclient import TestClient
from hermes_api.app import app

client = TestClient(app)
for path in ["/health", "/metrics", "/openapi.json", "/api/v1/toolsets?limit=1"]:
    response = client.get(path)
    print(path, response.status_code, response.headers.get("content-type"))
PY
```

## Rodar testes automatizados

```bash
uv run --with pytest --with fastapi --with uvicorn --with httpx \
  python -m pytest tests/hermes_api/test_app.py -q
```

Lint:

```bash
uv run --with ruff python -m ruff check hermes_api tests/hermes_api
```

## Notas de produção

- Use HTTPS no proxy, load balancer ou ingress.
- Configure `HERMES_API_TOKEN` em qualquer ambiente exposto em rede.
- Restrinja `api.cors_origins` às origens reais do frontend.
- Use rate limit distribuído na infraestrutura se houver múltiplos processos.
- Não exponha toolsets perigosos sem política explícita.
- A API começa conservadora: `web` habilitado e `terminal` desabilitado por padrão.
