# Telegram Media Manager Bot

## Overview

This Telegram bot allows authorized users to manage media content, including downloading videos from Telegram and torrent magnet links, as well as editing existing shows. The bot handle media download requests and store them in a designated directory to be synced into your existing Plex media server.

## Features

- **Media Management**: Manage your media content by downloading videos and editing existing shows.
- **Telegram Integration**: Download videos directly from Telegram.
- **Torrent Integration**: Download videos using torrent magnet links.
- **User Authorization**: Restrict bot usage to authorized users only.
- **Conversation Handler**: A structured conversation flow to collect necessary information from the user.

## Prerequisites

- Python 3.8 or higher
- Docker
- Telegram bot token


## Development

This bot relies on Mamba to manage dev virtual env

```sh
mamba env create -f env_dev.yaml
mamba activate telegram_bot
```

### Set up environment variables
Create a .env file in the project root and add your environment variables
TELEGRAM_API_ID=your-telegram-api-token
TELEGRAM_API_HASH=your-telegram-api-hash
TELEGRAM_API_TOKEN=your-telegram-api-token
MEDIA_BASE_PATH=/path/to/downloads


Then simply run the bot by running:
```sh
python -m telegram_media_bot.bot
```


