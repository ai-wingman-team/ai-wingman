docs/PHASE_1C_GUIDE.md << 'EOF'
# Phase 1C: Database Models & Application Foundation

## Overview

Phase 1C provides the Python application layer that connects to the PostgreSQL database. It includes models, operations, configuration, and testing infrastructure.

## What Was Built

### 1. Configuration Management
**File:** `src/ai_wingman/config/settings.py`

Loads and validates environment variables from `.env`:
- Database connection settings
- Embedding model configuration
- Ollama LLM settings
- Slack API credentials
- Application behavior settings

**Usage:**
from ai_wingman.config import settings

print(settings.database_url)
print(settings.embedding_dimension)

### 2. Database Connection
**File:** `src/ai_wingman/database/connection.py`

Async connection pooling with automatic retry:
from ai_wingman.database import get_session

async with get_session() as session:
# Your database operations here
await session.commit()

### 3. ORM Models
**File:** `src/ai_wingman/database/models.py`

Three main models:
- `SlackMessage` - Messages with vector embeddings
- `UserContext` - User statistics and preferences
- `ConversationThread` - Thread metadata

**Usage:**
from ai_wingman.database.models import SlackMessage

message = SlackMessage(
slack_message_id="123",
user_id="U001",
message_text="Hello!",
embedding=[0.1] * 384,
)

### 4. CRUD Operations
**File:** `src/ai_wingman/database/operations.py`

Helper functions for common tasks:
from ai_wingman.database import operations

Create message
message = await operations.create_slack_message(
session,
slack_message_id="123",
user_id="U001",
message_text="Hello!",
)

Search similar messages
similar = await operations.search_similar_messages(
session,
query_embedding=[0.1] * 384,
limit=5,
)

## Running Tests
All tests
pytest

Specific test file
pytest tests/test_models.py

With coverage
pytest --cov=src/ai_wingman

Integration tests only
pytest -m integration

## Running the Demo
Activate venv
source venv/bin/activate

Run demo
python scripts/demo_database.py

The demo showcases:
1. Database health check
2. Creating messages
3. Querying messages
4. User context management
5. Similarity search
6. Soft delete
7. Summary statistics

## Next Steps

After Phase 1C, you can:
1. **Phase 2**: Build Slack integration to fetch real messages
2. **Phase 3**: Implement query generation and retrieval
3. **Phase 4**: Add LLM response generation

## Common Operations

### Connect to Database
from ai_wingman.database import get_session

async with get_session() as session:
# Your code here
pass

### Create a Message with Embedding
from ai_wingman.database import operations

message = await operations.create_slack_message(
session,
slack_message_id="msg_123",
channel_id="C001",
user_id="U001",
message_text="Sample message",
slack_timestamp=1234567890.0,
embedding=[0.1] * 384, # From sentence-transformers
)
await session.commit()

### Search Similar Messages
query_embedding = [0.2] * 384 # Your query embedding

results = await operations.search_similar_messages(
session,
query_embedding=query_embedding,
similarity_threshold=0.7,
limit=5,
)

for message, score in results:
print(f"{score:.3f}: {message.message_text}")

## Troubleshooting

### Tests Fail with "Database not accessible"
Check database is running
make start

Verify connection
docker ps | grep ai_wingman_db

### Import Errors
Make sure venv is activated
source venv/bin/activate

Reinstall dependencies
pip install -r requirements.txt

### Database Connection Errors
Check .env file exists
cat .env | grep POSTGRES

Test connection manually
docker compose exec db psql -U wingman -d ai_wingman

## Architecture
User Code
↓
operations.py (CRUD functions)
↓
models.py (ORM models)
↓
connection.py (Session management)
↓
PostgreSQL + pgvector

All database operations go through this stack for consistency and type safety.
