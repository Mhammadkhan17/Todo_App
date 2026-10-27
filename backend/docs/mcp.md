# TodoFlow MCP Server

The MCP server exposes the authenticated user's tasks over stdio and (Phase 2) Streamable HTTP.

## Requirements

- A valid user id in the TodoFlow database.
- `MCP_USER_ID` set to that user's id.
- `DATABASE_URL` available in `backend/.env`.

## Run

```bash
cd backend
MCP_USER_ID=1 .venv/bin/python -m src.mcp.server
```

## Claude Desktop configuration

```json
{
  "mcpServers": {
    "todoflow": {
      "command": "/absolute/path/to/Todo_App/backend/.venv/bin/python",
      "args": ["-m", "src.mcp.server"],
      "cwd": "/absolute/path/to/Todo_App/backend",
      "env": {
        "MCP_USER_ID": "1",
        "DATABASE_URL": "postgresql://..."
      }
    }
  }
}
```

## Tools

| Tool | Read-only | Destructive | Purpose |
|---|---|---|---|
| `todo_create_task` | no | no | Create a task |
| `todo_list_tasks` | yes | no | List, filter, search, paginate |
| `todo_get_task` | yes | no | Fetch one task |
| `todo_update_task` | no | no | Update fields |
| `todo_complete_task` | no | no | Mark completed |
| `todo_reopen_task` | no | no | Mark active |
| `todo_delete_task` | no | yes | Permanently delete |
| `todo_summary` | yes | no | Counts and overdue total |

## Resources (Phase 2)

Read-only JSON views of the signed-in user's tasks. All are scoped to the MCP
identity (`MCP_USER_ID` or the bearer token subject); reading another user's
task id fails with a resource error.

| URI | Contents |
|---|---|
| `todo://tasks/active` | Up to 200 active (not completed) tasks |
| `todo://tasks/completed` | Up to 200 completed tasks |
| `todo://tasks/{task_id}` | One task by id (template; 404s cross-user) |

## Prompts (Phase 2)

Read-only chat prompts that summarize the signed-in user's active tasks
(again via `TaskService`, never accepting a user id):

| Prompt | Output |
|---|---|
| `daily_review` | Task count, one line per task, overdue flagged |
| `prioritize_my_day` | Active tasks ranked HIGH → MEDIUM → LOW |
| `weekly_plan` | Active tasks sorted by due date |

## Streamable HTTP (Phase 2)

Runs as a separate ASGI process next to the REST API. Every request must
present a JWT access token issued by the REST API (`POST /api/auth/login`);
the caller's identity is the token's subject claim.

```bash
cd backend
.venv/bin/python -m src.mcp.http
# MCP endpoint: http://127.0.0.1:8001/mcp
```

Configuration (environment variables):

| Variable | Default | Purpose |
|---|---|---|
| `MCP_HTTP_ISSUER_URL` | `http://127.0.0.1:8000` | OAuth issuer (REST API base) |
| `MCP_HTTP_RESOURCE_URL` | `http://127.0.0.1:8001/mcp` | This server's public URL |
| `MCP_HTTP_HOST` | `127.0.0.1` | Bind host |
| `MCP_HTTP_PORT` | `8001` | Bind port |

```bash
# Obtain a token from the REST API, then call MCP tools over HTTP:
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "..."}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s -X POST http://127.0.0.1:8001/mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl","version":"0"}}}'
```

Requests without a valid, unexpired token get `401 Unauthorized`. The
process clears `MCP_USER_ID` on startup so HTTP identity can only ever come
from the bearer token.

## Security

- Tools never accept a user id.
- stdio identity comes from `MCP_USER_ID`.
- HTTP identity comes from a verified bearer token subject; missing,
  invalid, or expired tokens are rejected with `401`.
- `todo_delete_task` is permanent and cannot be undone.
