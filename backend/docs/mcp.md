# TodoFlow MCP Server

The MCP server exposes the authenticated user's tasks over stdio.

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

## Security

- Tools never accept a user id.
- stdio identity comes from `MCP_USER_ID`.
- Phase 2 HTTP identity comes from a verified bearer token subject.
- `todo_delete_task` is permanent and cannot be undone.
