# Conversation History System Documentation

## Overview

The Conversation History System provides intelligent conversation management with Redis caching and RAG integration using Qdrant for your Telegram bot. This system enables contextual conversations, memory across sessions, and smart conversation management.

## Features

### 🚀 Core Features
- **Redis-based Caching**: Fast retrieval of recent conversation history
- **RAG Integration**: Long-term storage and semantic search using Qdrant vector database
- **Intelligent Context Filtering**: Only includes relevant previous messages in context
- **Conversation Clearing**: Users can clear their history with commands or natural language
- **Pattern Detection**: Analyzes conversation patterns for insights
- **Chunked Storage**: Efficient memory management for long conversations

### 🧠 Smart Features
- **Semantic Similarity**: Uses sentence transformers to find relevant past conversations
- **Confidence Scoring**: Only includes context when confidence is high enough
- **Topic Tracking**: Identifies and tracks conversation topics
- **Intent-based Organization**: Groups conversations by detected intents
- **Automatic Summarization**: Generates conversation summaries

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Telegram Bot  │────│  Message Handler │────│ Conversation    │
│                 │    │                  │    │ History Service │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                              ┌─────────────────────────┼─────────────────────────┐
                              │                         │                         │
                    ┌─────────▼─────────┐    ┌──────────▼──────────┐    ┌─────────▼─────────┐
                    │   Redis Cache     │    │   Qdrant Vector     │    │ Conversation      │
                    │ (Recent Messages) │    │   Database (RAG)    │    │ Processor         │
                    └───────────────────┘    └─────────────────────┘    └───────────────────┘
```

## Installation

### Dependencies
```bash
pip install redis==5.0.1 qdrant-client==1.9.1 sentence-transformers==2.7.0 numpy==1.26.4
```

### Environment Setup
Add to your `.env` file:
```bash
# Redis Configuration
REDIS_URL="redis://localhost:6379"

# Qdrant Configuration  
QDRANT_API_URL="http://localhost:6333"
QDRANT_API_KEY=""  # Optional, for Qdrant Cloud
```

### External Services

#### Redis Setup
```bash
# Using Docker
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Or install locally
brew install redis  # macOS
redis-server
```

#### Qdrant Setup
```bash
# Using Docker
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant

# Or using Docker Compose (recommended)
# Add to your docker-compose.yml:
services:
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
volumes:
  qdrant_data:
```

## Usage

### Bot Commands

#### User Commands
- `/clear_conversation` - Clear all conversation history
- `/conversation_status` - Show conversation statistics

#### Natural Language Clearing
Users can also clear conversations naturally:
- "clear all conversation"
- "forget everything"  
- "start fresh"
- "reset our chat"

### Code Integration

#### Basic Usage
```python
from src.services.conversation_history import conversation_service

# Initialize (call once at startup)
await conversation_service.initialize()

# Add conversation
await conversation_service.add_conversation(
    user_id="user123",
    username="John",
    user_message="Hello, how are you?",
    bot_response="I'm doing well, thank you!",
    intent="GREETING"
)

# Get conversation context
context_messages = await conversation_service.get_conversation_context(
    user_id="user123",
    current_message="What did we discuss about Python?",
    include_semantic=True
)

# Format for AI
context_text = conversation_service.format_context_for_ai(context_messages)
```

#### Advanced Processing
```python
from src.services.conversation_processor import conversation_processor

# Get intelligent context
context_data = await conversation_processor.process_conversation_for_context(
    user_id="user123",
    current_message="Tell me more about that topic",
    max_context_length=3000
)

# Access detailed information
context_text = context_data["context_text"]
confidence_score = context_data["confidence_score"] 
relevant_topics = context_data["relevant_topics"]
summary = context_data["context_summary"]
```

## Configuration

### Service Configuration
```python
# In conversation_history.py
class ConversationHistoryService:
    def __init__(self):
        self.max_redis_messages = 50      # Recent messages in Redis
        self.max_context_messages = 10    # Messages to include in context  
        self.context_relevance_threshold = 0.3  # Minimum similarity
        self.redis_ttl = 7 * 24 * 3600    # 7 days TTL for Redis
```

### Processor Configuration
```python
# In conversation_processor.py  
class ConversationProcessor:
    def __init__(self):
        self.chunk_size = 10              # Messages per chunk
        self.chunk_overlap = 2            # Overlap between chunks
        self.max_context_tokens = 4000    # Token limit for context
```

## How It Works

### 1. Message Storage
When a conversation happens:
1. **Redis Storage**: Recent message stored in Redis list with TTL
2. **Qdrant Storage**: Message embedded using sentence-transformers and stored in vector DB
3. **Metadata**: Timestamps, intents, user info stored with each message

### 2. Context Retrieval
When generating context:
1. **Recent Messages**: Fetch last N messages from Redis cache
2. **Semantic Search**: Query Qdrant for semantically similar conversations
3. **Relevance Filtering**: Filter messages by similarity threshold
4. **Confidence Scoring**: Calculate confidence based on multiple factors
5. **Context Assembly**: Combine and format selected messages

### 3. Intelligent Features

#### Confidence Scoring
Based on:
- Message count (more messages = higher confidence)
- Recency (newer messages weighted higher)
- Semantic relevance (similarity scores)
- Intent consistency (focused conversations score higher)

#### Pattern Detection
Identifies patterns like:
- Rapid conversations (messages < 1 minute apart)
- Sporadic conversations (messages > 1 hour apart)
- Focused topics (same intent repeatedly)
- Message length patterns

## Testing

Run the test suite to verify everything works:
```bash
python test_conversation_history.py
```

The test covers:
- ✅ Redis connection and operations
- ✅ Qdrant connection and collection setup
- ✅ Conversation storage and retrieval
- ✅ Context formatting and filtering
- ✅ Semantic search functionality
- ✅ Conversation clearing
- ✅ Pattern detection
- ✅ Advanced conversation processing

## Bot Integration

The system is automatically integrated into your bot through:

1. **Message Handler**: `src/handlers/mcp_messages.py`
   - Automatically gets conversation context
   - Enhances messages with relevant history
   - Stores new conversations

2. **Command Handlers**: `src/handlers/conversation_commands.py`
   - Handles `/clear_conversation` and `/conversation_status`
   - Detects natural language clear intents

3. **Bot Initialization**: `src/core/mcp_bot.py`
   - Initializes conversation service on startup
   - Registers conversation commands

## Example Bot Interaction

```
User: Hello, I'm learning Python
Bot: Great! Python is an excellent language to learn. What would you like to know about?
[Conversation stored: intent=SEARCH_QUERY, context_score=0.0]

User: What are functions?
Bot: Functions in Python are reusable blocks of code...
[Using context from previous message, confidence: 0.8]

User: Can you show me an example?
Bot: [Gets context about Python functions discussion] 
     Sure! Here's a simple function example...
[Using context from 2 previous messages, confidence: 0.9]

User: Clear our conversation
Bot: 🗑️ Understood! I've cleared our conversation history as requested...
[All history cleared from Redis and Qdrant]
```

## Performance Considerations

### Redis Optimization
- Messages auto-expire after 7 days
- Limited to 50 recent messages per user
- Uses Redis lists for chronological ordering

### Qdrant Optimization  
- Vector embeddings use efficient MiniLM model (384 dimensions)
- Cosine similarity for fast semantic search
- Filtered queries by user_id for performance

### Memory Management
- Context limited to configurable token counts
- Conversation chunking for long histories
- Lazy loading of embedding model

## Troubleshooting

### Common Issues

#### "Redis connection failed"
- Ensure Redis is running: `redis-server`
- Check Redis URL in .env file
- Test connection: `redis-cli ping`

#### "Qdrant collection not found"
- Ensure Qdrant is running on port 6333
- Collection auto-creates on first use
- Check Qdrant logs for errors

#### "Embedding model loading failed"
- Ensure sentence-transformers is installed
- Model downloads on first use (requires internet)
- Check disk space for model storage

#### "No conversation context retrieved"
- Check if conversations are being stored
- Verify user_id consistency
- Check confidence threshold settings

### Debugging

Enable debug logging:
```python
import logging
logging.getLogger('src.services.conversation_history').setLevel(logging.DEBUG)
logging.getLogger('src.services.conversation_processor').setLevel(logging.DEBUG)
```

Check service status:
```python
# Check Redis
await conversation_service.redis_client.ping()

# Check Qdrant  
collections = await conversation_service.qdrant_client.get_collections()

# Check embedding model
print(conversation_service.embedding_model)
```

## Future Enhancements

### Planned Features
- [ ] Conversation export/import
- [ ] Multi-language support
- [ ] Custom embedding models
- [ ] Conversation analytics dashboard
- [ ] Auto-summarization with LLMs
- [ ] Conversation search API
- [ ] User conversation preferences

### Potential Optimizations
- [ ] Redis clustering for scale
- [ ] Qdrant sharding
- [ ] Async embedding processing
- [ ] Context caching
- [ ] Conversation compression

---

For questions or issues, check the logs or run the test suite to diagnose problems.
