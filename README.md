# Telegram System Monitor Bot

An advanced, modular Telegram bot built with Python for system monitoring (CPU, RAM, disk usage), weather updates, and administrative controls. Now featuring **AI-powered conversation history**, **RAG-enhanced context**, **Redis caching**, and **Qdrant vector database** integration alongside existing AI-powered natural language understanding, intent detection, and Model Context Protocol (MCP) support for intelligent responses and workflow automation. The bot uses the `python-telegram-bot` library, robust locking for safe multi-user interactions, scheduled tasks, and supports both classic and MCP-enhanced operation modes with **persistent conversation memory**. Easily extensible with a scalable architecture, N8N webhook integration, and future-ready for additional AI, database, and microservice features.

## ✨ Key Features

### 🧠 **NEW: Conversation History & Memory**
- **Redis-based caching** for fast recent conversation retrieval
- **Qdrant RAG integration** for intelligent long-term memory
- **Semantic search** through conversation history using sentence transformers
- **Smart context filtering** - only includes relevant previous messages
- **Conversation clearing** via commands or natural language ("clear all conversation")
- **Pattern detection** and conversation analytics
- **Chunked storage** for memory-efficient processing

### 🤖 **AI & Intelligence**
- MCP-enhanced natural language understanding
- Intent detection and context-aware responses
- Dynamic tool creation and execution
- N8N webhook integration for complex workflows

## Project Structure

```bash
first-telegram-bot/
├── config/                          # Configuration files
│   ├── __init__.py
│   └── config.py                    # Main configuration settings
├── src/
│   ├── __init__.py
│   ├── __version__.py               # Version information
│   ├── core/                        # Core application logic
│   │   ├── __init__.py
│   │   ├── bot.py                   # Main bot application
│   │   └── mcp_bot.py               # MCP-enhanced bot application
│   ├── handlers/                    # Message and command handlers
│   │   ├── __init__.py
│   │   ├── commands.py              # Command handlers (/start, /help, etc.)
│   │   ├── messages.py              # Regular message handlers
│   │   └── mcp_messages.py          # MCP-enhanced message handlers
│   ├── services/                    # External service integrations
│   │   ├── __init__.py
│   │   ├── scheduler.py             # Task scheduling service
│   │   ├── webhook_service.py       # N8N webhook integration
│   │   └── weather_service.py       # Weather API service
│   ├── ai/                          # AI processing and intelligence
│   │   ├── __init__.py
│   │   ├── ai_processor.py          # Basic AI processing
│   │   ├── mcp_processor.py         # MCP AI processing logic
│   │   └── mcp_instructions.py      # MCP AI instructions and prompts
│   ├── database/                    # Database operations and vector stores
│   │   ├── __init__.py
│   │   ├── qdrant_client.py         # Qdrant vector database client
│   │   └── models.py                # Database models (future)
│   ├── utils/                       # Utility functions and helpers
│   │   ├── __init__.py
│   │   ├── logging_utils.py         # Logging utilities
│   │   ├── lock.py                  # File locking utilities
│   │   └── system_utils.py          # System information utilities
│   └── middleware/                  # Request/response processing
│       ├── __init__.py
│       ├── auth_middleware.py       # Authentication middleware (future)
│       └── rate_limiter.py          # Rate limiting middleware (future)
├── logs/                            # Log files
├── requirements.txt
├── docker-compose.yaml
├── Dockerfile
└── README.md
```
## 📋 Module Responsibilities

### 🔧 Core (`src/core/`)
- **bot.py**: Main bot application entry point
- **mcp_bot.py**: MCP-enhanced bot with intelligent processing

### 🎮 Handlers (`src/handlers/`)
- **commands.py**: Telegram command handlers (/start, /help, /weather, etc.)
- **messages.py**: Regular message handlers (text, photo, document)
- **mcp_messages.py**: MCP-enhanced message handlers with AI processing

### 🌐 Services (`src/services/`)
- **scheduler.py**: Background task scheduling
- **webhook_service.py**: N8N webhook integration
- **weather_service.py**: Weather API integration

### 🤖 AI (`src/ai/`)
- **ai_processor.py**: Basic AI processing logic
- **mcp_processor.py**: MCP AI preprocessing and intent detection
- **mcp_instructions.py**: Centralized AI instructions and prompts

### 🗄️ Database (`src/database/`)
- **qdrant_client.py**: Qdrant vector database operations
- **models.py**: Database models and schemas (future)

### 🛠️ Utils (`src/utils/`)
- **logging_utils.py**: Logging configuration and utilities
- **lock.py**: File locking for single instance
- **system_utils.py**: System information and resource monitoring

### 🚦 Middleware (`src/middleware/`)
- **auth_middleware.py**: User authentication and authorization (future)
- **rate_limiter.py**: Request rate limiting (future)

### ⚙️ Config (`config/`)
- **config.py**: Application configuration and environment variables

## Features

### 📱 **Core Commands**
- `/start`: Starts or restarts bot activities and greets the user.
- `/help`: Displays a list of available commands.
- `/say <message>`: Echoes back the user's message.
- `/status`: Shows bot status with the current server time.
- `/cpu`: Reports current CPU usage percentage.
- `/ram`: Reports RAM usage in GB and percentage.
- `/disk`: Reports disk usage for the root directory in GB and percentage.
- `/info`: Provides detailed system info (OS, Python version, CPU cores) and resource usage (CPU, RAM, disk) with formatted output and emojis.
- `/weather <city>`: Fetches current weather for a specified city using OpenWeatherMap.
- `/uptime`: Shows how long the bot has been running.
- `/stop`: Stops all scheduled activities (admin only).

### 💬 **NEW: Conversation Commands**
- `/clear_conversation`: Clear all conversation history for smart reset
- `/conversation_status`: View conversation statistics and history summary
- **Natural Language Clearing**: Say "clear all conversation", "forget everything", or "start fresh"

### 🕒 **Scheduler Commands**  
- `/schedule`: Show scheduler usage help and examples
- `/tasks`: List all your scheduled tasks
- `/cancel <task_id>`: Cancel a specific scheduled task

### 🤖 **AI Features**
- **Natural Language Commands**: Use `info`, `weather in London`, `uptime` directly without `/`
- **Smart Context**: Bot remembers previous conversations for better responses
- **Intent Detection**: Automatically understands what you want to do
- **RAG Memory**: Long-term conversation storage with semantic search

### ⏰ **Scheduled Tasks**
- Automatically sends weather updates and debug messages at configurable intervals.

## Prerequisites

- __Python__: 3.12 or higher (for local development)
- __Docker__: Docker Engine 24.x or later with `docker compose` (for containerized deployment)
- __Telegram__: A bot token from [BotFather](https://t.me/BotFather)
- __OpenWeatherMap__: An API key for weather features (optional)
- __Ollama__: Local Ollama install and model

## Installation

### Local Development (Without Docker)

1. __Clone the Repository__:

```bash
git clone https://github.com/henry0hai/first-telegram-bot.git
cd first-telegram-bot
```

2. __Set Up a Virtual Environment__:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. __Install Dependencies__:

```bash
pip install -r requirements.txt
```

4. __Configure Environment Variables: Create a .env file in the root directory__:

- Create .env file in the root directory with sample in sample.env and configure with your own credentials

5. __Run the Bot__:

```bash
python run.py
```

### 💬 **NEW: Conversation History Setup**

To enable the conversation history features:

1. **Install Additional Dependencies** (already included in requirements.txt):
```bash
pip install redis==5.0.1 qdrant-client==1.9.1 sentence-transformers==2.7.0 numpy==1.26.4
```

2. **Set up Redis** (for fast conversation caching):
```bash
# Using Docker (recommended)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Or install locally on macOS
brew install redis && redis-server
```

3. **Set up Qdrant** (for RAG and long-term memory):
```bash
# Using Docker (recommended) 
docker run -d --name qdrant -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

4. **Update .env file**:
```bash
# Add these to your .env file
REDIS_URL="redis://localhost:6379"
QDRANT_API_URL="http://localhost:6333"
QDRANT_API_KEY=""  # Optional, for Qdrant Cloud
```

5. **Verify Setup**:
```bash
python setup_conversation_history.py  # Check configuration
python test_conversation_history.py   # Run comprehensive tests
python demo_conversation_history.py   # See how it works
```

📚 **Full Documentation**: See [CONVERSATION_HISTORY.md](CONVERSATION_HISTORY.md) for detailed setup and usage.

## 🔄 Running the Application

### Regular Bot:

```bash
python -m src.core.bot
```

or

```bash
python run.py
```

### MCP-Enhanced Bot:
```bash
python -m src.core.mcp_bot
```

or

```bash
python run.py
```

### Docker Deployment 

- I'm currently deploy on Rasberries 4, 4Gb RAM. Seem working well.

1. __Clone the Repository__:

```bash
git clone https://github.com/henry0hai/first-telegram-bot.git
cd first-telegram-bot
```

2. __Configure Environment Variables__:
  
- Create .env file with sample in sample.env and configure with your own credentials
  
3. __Build and Run with Docker Compose__:

```bash
docker compose build --no-cache
docker compose up -d
```

- *-d* runs the container in detached mode
- If *COMPOSE_BAKE=true* is in *.env*, the build will use *buildx bake* for optimization

4. __View Logs__:

```bash
docker compose logs -f
docker logs telegram-bot -f 
```

5. __Stop the Bot__:

```bash
docker compose down
```

## Usage

- The bot started in Telegram by default
- In case it stopped, restart by */start* command
- User */help* to see all available commands
- Admin-only commands like */stop* require the username to match *ADMIN_USER_NAME*
- MCP-enhanced bot can process commands like `info`, `weather in London`, `uptime` directly without `/`
- MCP-enhanced bot can also handle more complex queries and provide richer responses and connect via webhook n8n to connect with MCP AI AGENT for more complex task
- MCP-enhanced bot can integrate with external APIs and services for additional functionality

## 📈 Future Enhancements

- Multiple AI providers
- Database integrations
- Authentication systems
- Rate limiting
- Monitoring and analytics
- Multi-language support
- Plugin architecture
- Microservices deployment

## Contributing

- Feel free to fork the repository, make improvements, and submit pull requests! or used as sample in another projects
