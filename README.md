# Telegram System Monitor Bot

A Telegram bot built with Python that provides system monitoring (CPU, RAM, disk usage), weather updates, and administrative controls. It uses the `python-telegram-bot` library, threading with locks for safe multi-user interactions, and scheduled tasks for periodic updates.

## Project Structure

first-telegram-bot/
│
├── src/                   # Source code directory
│   ├── __init__.py        # Makes src a package
│   ├── __version__.py     # Store application version
│   ├── ai.py              # Call AI API to help user interaction
│   ├── bot.py             # Main bot application logic
│   ├── config.py          # Configuration and environment variables
│   ├── commands.py        # Command handlers
│   ├── scheduler.py       # Scheduled tasks (weather updates, debug time)
│   ├── utils.py           # Utility functions (weather fetching, direction conversion)
│   └── lock.py            # Single-instance lock logic
│
├── sample.env             # Sample Environment variables file
├── requirements.txt       # List of dependencies
├── run.py                 # Entry point to start the bot
└── README.md              # Project Documentation
├── Dockerfile             # Dockerfile to build the container image
└── docker-compose.yaml    # Docker Compose configuration for running the bot

## Features

- `/start`: Starts or restarts bot activities and greets the user.
- `/help`: Displays a list of available commands.
- `/say <message>`: Echoes back the user's message.
- `/kiemtra`: Shows bot status with the current server time.
- `/cpu`: Reports current CPU usage percentage.
- `/ram`: Reports RAM usage in GB and percentage.
- `/disk`: Reports disk usage for the root directory in GB and percentage.
- `/info`: Provides detailed system info (OS, Python version, CPU cores) and resource usage (CPU, RAM, disk) with formatted output and emojis.
- `/weather <city>`: Fetches current weather for a specified city using OpenWeatherMap.
- `/uptime`: Shows how long the bot has been running.
- `/stop`: Stops all scheduled activities (admin only).
- __Scheduled Tasks__: Automatically sends weather updates and debug messages at configurable intervals.

## Prerequisites

- __Python__: 3.12 or higher (for local development)
- __Docker__: Docker Engine 24.x or later with `docker compose` (for containerized deployment)
- __Telegram__: A bot token from [BotFather](https://t.me/BotFather)
- __OpenWeatherMap__: An API key for weather features (optional)

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

### Docker Deployment

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

## Contributing

- Feel free to fork the repository, make improvements, and submit pull requests! or used as sample in another projects
