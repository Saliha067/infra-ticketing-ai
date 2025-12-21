# Infrastructure Inquiry Bot

AI-powered Slack bot for infrastructure support using LangChain + Ollama. Intelligently routes inquiries using RAG knowledge base or creates JIRA tickets.

## Features

- **Slack Integration**: `/infra-inquiry` command with modal forms
- **RAG Knowledge Base**: ChromaDB vector search with semantic relevance filtering
- **Smart Routing**: LangChain supervisor agent classifies and routes to teams
- **JIRA Tickets**: Auto-creates tickets with team labels and priority
- **Metrics Dashboard**: `/infra-metrics` command + standalone CLI
- **PostgreSQL Storage**: Tracks all inquiries with metadata
- **Redis Caching**: Caches knowledge base search results

## Architecture

```
User → Slack → Supervisor Agent → Knowledge Agent (ChromaDB)
                                 ↓
                                 Router Agent → JIRA Ticket
```

**Agents:**
- **Supervisor**: Orchestrates workflow, classifies urgency/category
- **Knowledge**: RAG search with strict relevance threshold (<0.4)
- **Router**: Routes to teams (platform/devops/database/security/network)

## Tech Stack

- **LangChain 0.3.13** + **langchain-ollama 0.2.2**
- **Ollama**: `llama3.1:8b` (main), `nomic-embed-text` (embeddings)
- **Slack Bolt 1.21.2** (Socket Mode)
- **ChromaDB 0.5.20** (vector store)
- **PostgreSQL 15** (inquiry tracking)
- **Redis 7** (caching)
- **SQLAlchemy 2.0.36** (ORM)

## Quick Start

### Prerequisites
- Ollama installed with models:
  ```bash
  ollama pull llama3.1:8b
  ollama pull nomic-embed-text
  ```
- Docker (for postgres, redis, chromadb)
- Slack workspace (admin access)
- JIRA Cloud account (free tier)

### Setup

**1. Clone & Install**
```bash
pip install -r requirements.txt
```

**2. Start Services**
```bash
docker-compose up -d
```

**3. Configure Environment**
Copy `.env.example` to `.env` and fill:
```env
# Ollama
OLLAMA_URL=http://localhost:11434
LLM_MODEL=llama3.1:8b
EMBEDDING_MODEL=nomic-embed-text

# Slack (see slack-jira-setup.md)
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

# JIRA
JIRA_URL=https://your-site.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=INFRA
JIRA_ENABLED=true

# Database
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin123
POSTGRES_DB=infra_bot
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

**4. Initialize Database**
```bash
python src/db/models.py
```

**5. Load Knowledge Base**
```bash
python src/db/init_knowledge_base.py
```

**6. Start Bot**
```bash
python src/main.py
```

## Usage

### Slack Commands

**Submit Inquiry:**
```
/infra-inquiry How to restart a Kubernetes pod?
```
Modal opens with:
- Question (pre-filled from command)
- Environment (multi-select: PROD/STG/PERF/DEV)
- Deadline (date picker)

**View Metrics:**
```
/infra-metrics           # Today
/infra-metrics week      # This week
/infra-metrics month     # This month
/infra-metrics all       # All-time
```

### CLI Metrics
```bash
python metrics.py
```

Shows:
- Daily/weekly/monthly/all-time stats
- KB hit rate
- Team distribution
- Category breakdown
- Recent 10 inquiries

## Project Structure

```
infra-ticketing-ai/
├── src/
│   ├── agents/
│   │   ├── supervisor.py       # Orchestration agent
│   │   ├── knowledge_agent.py  # RAG agent
│   │   └── router_agent.py     # Team routing
│   ├── db/
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── vector_store.py     # ChromaDB wrapper
│   │   └── init_knowledge_base.py
│   ├── tools/
│   │   └── jira_tools.py       # JIRA API integration
│   ├── slack_bot.py            # Slack integration
│   └── main.py                 # Entry point
├── config/
│   ├── prompts.py              # Agent prompts
│   └── knowledge_base.json     # Sample Q&As
├── tests/
│   └── test_system.py          # Integration tests
├── docker-compose.yml
├── metrics.py                  # Metrics CLI
├── .env
└── slack-jira-setup.md         # Setup guide
```

## Configuration

### Knowledge Base
Edit `config/knowledge_base.json` to add Q&As:
```json
{
  "question": "How do I restart a Kubernetes pod?",
  "answer": "Use kubectl delete pod <pod-name> -n <namespace>",
  "category": "kubernetes",
  "tags": ["kubernetes", "pod", "restart"]
}
```

Reload:
```bash
python src/db/init_knowledge_base.py
```

### Team Routing
Edit `src/agents/router_agent.py` → `TEAM_DESCRIPTIONS` to customize teams.

### Relevance Threshold
Adjust in `src/db/vector_store.py`:
- High: distance < 0.3
- Medium: distance < 0.6

## Testing

```bash
pytest tests/ -v
```

**System Tests:**
- Knowledge base search
- KB resolution flow
- Ticket creation flow
- Agent classification
- JIRA integration
- Database persistence

## Troubleshooting

**Bot not responding:**
- Check Ollama is running: `ollama list`
- Verify Docker containers: `docker-compose ps`
- Check logs: `tail -f logs/bot.log`

**JIRA tickets not creating:**
- Set `JIRA_ENABLED=true` in `.env`
- Verify API token: `curl -u email:token $JIRA_URL/rest/api/2/myself`

**ChromaDB errors:**
- Ensure version 0.5.20: `pip show chromadb`
- Clear data: `docker-compose down -v && docker-compose up -d`

## Metrics

All inquiries stored in PostgreSQL with:
- Question, environment, deadline
- Urgency, category, assigned team
- KB resolution status
- JIRA ticket ID
- Full metadata JSON

Query via `/infra-metrics` or `metrics.py`.

## License

MIT
