# Telegram System Monitor Bot

An advanced, modular Telegram bot built with Python for system monitoring (CPU, RAM, disk usage), weather updates, and administrative controls. Now featuring AI-powered natural language understanding, intent detection, and integration with Model Context Protocol (MCP) for intelligent responses and workflow automation. The bot uses the `python-telegram-bot` library, robust locking for safe multi-user interactions, scheduled tasks, and supports both classic and MCP-enhanced operation modes. Easily extensible with a scalable architecture, N8N webhook integration, and future-ready for additional AI, database, and microservice features.

**Noted**: Just added the feature using simple AI model make it more useful.

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
- __Scheduled Tasks__: Automatically sends weather updates and debug messages at configurable intervals.

> With AI model, now can directly command using: `info` or `weather in London`, `uptime` directly without `/` for some command

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
