# Telegram Media Manager Bot

## Overview

This Telegram bot allows authorized users to manage media content, including downloading videos from Telegram and torrent magnet links, as well as editing existing shows. The bot integrates with FastAPI to handle media download requests and store them in a designated directory.

## Features

- **Media Management**: Manage your media content by downloading videos and editing existing shows.
- **Telegram Integration**: Download videos directly from Telegram.
- **Torrent Integration**: Download videos using torrent magnet links.
- **User Authorization**: Restrict bot usage to authorized users only.
- **Conversation Handler**: A structured conversation flow to collect necessary information from the user.

## Prerequisites

- Python 3.10 or higher
- Docker
- Telegram bot token

## Installation

1. **Clone the repository**:

    ```sh
    git clone https://github.com/oritor91/plex-telegram-bot.git telegram-bot-repo
    cd telegram-bot-repo
    ```

2. **Create a virtual environment and activate it**:
    Depends on Mamba
    ```sh
    mamba env create -f env_dev.yaml
    conda activate telegram_bot
    ```

4. **Set up environment variables**:

    Create a `.env` file in the project root and add your environment variables:

    ```env
    TELEGRAM_API_ID="****"
    TELEGRAM_API_HASH="****"
    TELEGRAM_API_TOKEN="****"
    MEDIA_BASE_PATH="path/to/download/dir"

    ```

## Configuration

- **Telegram API Token**: Obtain it from [BotFather](https://t.me/BotFather) on Telegram.
- **Download Directory**: Specify the path to the directory where downloaded files will be stored.
- **Authorized Users**: List of Telegram user IDs authorized to use the bot.

## Usage

### Running with Docker

1. **Build the Docker image**:

    ```sh
    docker build -t telegram-media-manager-bot .
    ```

2. **Run the Docker container**:

    ```sh
    docker run -d -v <path-to-plex-library>:/data \
    -e TELEGRAM_API_ID=<id> -e TELEGRAM_API_HASH=<hash> \
    -e TELEGRAM_API_TOKEN=<token> -e MEDIA_BASE_PATH=/data telegram-media-manager-bot
    ```

### Running Locally

2. **Run the Telegram bot**:

    ```sh
    python -m telegram_media_bot.bot
    ```

## Example Commands

### list_shows
Will display existing shows on the screen

### edit_show
1. Display keyboard to choose an existing show to update
2. Display keyboard to choosean existing episode to update
3. Provide input to change the episode name

### torrent_download
1. Ask for a torrent manget uri to be downloaded
2. Ask for a show to download the torrent into
3. Downloads the torrent into the choosen show


### For any provided telegram video message (i.e https://t.me/plexmedia11/67)
1. Ask to choose a show to download the video into
2. Download the video into the giving show


## Editing Shows

The bot allows editing existing shows by providing commands to update show details. Ensure that you follow the conversation prompts to correctly update the information.

## Error Handling

The bot includes error handling to notify users if something goes wrong. Any exceptions are logged, and users are informed about the error.

## Contributing

If you find any issues or have suggestions for improvements, please feel free to create an issue or submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


---
