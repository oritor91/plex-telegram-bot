import os
import re
import logging
from typing import List, Optional
from pyrogram import Client
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    ConversationHandler,
    filters,
    CallbackQueryHandler,
)
from telegram_media_bot.utils import MovieData, ParsedURL, TorrentData, UserData, download_torrent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegram_media_bot")

GOT_SHOW, GOT_EPISODE, GOT_EPISODE_NAME = map(chr, range(3))
CHOOSE_SHOW, ASK_FOR_INPUT, ASK_FOR_EPISODE = map(chr, range(4, 7))
WAIT_FOR_TORRENT, GOT_TORRENT = map(chr, range(6, 8))
GET_MOVIE_LINK, CHOOSE_MOVIE = map(chr, range(9, 11))

MAX_SHOWS_PER_RAW = 3


class TelegramBot:
    """
    A class representing a Telegram Bot.

    Attributes:
        api_id (str): The API ID for the Telegram Bot.
        api_hash (str): The API Hash for the Telegram Bot.
        telegram_api_token (str): The API Token for the Telegram Bot.
        media_base_path (str): The base path for storing media files.
        application (Application): The Telegram Application instance.
        pyro_client (Client): The Pyrogram Client instance.
        user_data (UserData): The user data for the bot.

    Methods:
        start_pyro_client: Starts the Pyrogram client.
        shows_path: Returns the path for storing TV shows.
        movies_path: Returns the path for storing movies.
        parse_telegram_url: Parses a Telegram URL and returns the parsed data.
        receive_url: Receives a URL from the user and processes it.
        display_show_options: Displays the show options to the user.
        return_shows_options: Returns the available show options.
        list_shows: Lists the available shows.
        receive_show_name: Receives the selected show name from the user.
        receive_new_show_name: Receives the name of a new show from the user.
        handle_channel_message: Handles a message received from a channel.
        create_episode_path: Creates the path for storing an episode.
        process_media: Processes the media based on the user's input.
        cancel: Cancels the current operation.
        list_show_command: Lists all the available shows.
        error_handler: Handles errors that occur during the bot's operation.
        edit_show_command: Handles the edit show command.
        receive_show_to_update: Receives the show to update from the user.
        list_episodes: Lists the episodes of a show.
        receive_episode_to_update: Receives the episode to update from the user.
    """

    def __init__(self):
        self.api_id: str = os.getenv("API_ID")
        self.api_hash: str = os.getenv("API_HASH")
        self.telegram_api_token: str = os.getenv("TELEGRAM_API_TOKEN")
        self.media_base_path: str = os.getenv("MEDIA_BASE_PATH")
        self.application: Application = (
            Application.builder().token(self.telegram_api_token).build()
        )
        # self.application.concurrent_updates = False
        self.pyro_client: Client = Client(
            "nodim", api_id=self.api_id, api_hash=self.api_hash
        )
        self.user_data: UserData = UserData(torrent_data=TorrentData(), movie_data=MovieData())

    async def start_pyro_client(self):
        """
        Starts the Pyrogram client.
        """
        await self.pyro_client.start()

    @property
    def shows_path(self) -> str:
        """
        Returns the path for storing TV shows.
        """
        return os.path.join(self.media_base_path, "shows")

    @property
    def movies_path(self) -> str:
        """
        Returns the path for storing movies.
        """
        return os.path.join(self.media_base_path, "movies")

    def parse_telegram_url(self, url):
        """
        Parses a Telegram URL and returns the parsed data.

        Args:
            url (str): The Telegram URL to parse.

        Returns:
            ParsedURL: The parsed URL data.
        """
        patterns = [
            r"https://t.me/c/(?P<chat_id>[\d]+)/(?P<message_id>\d+)",
            r"https://web.telegram.org/a/#-(?P<chat_id>[\d]+)/(?P<message_id>\d+)",
            r"https://t.me/(?P<username>[\w]+)/(?P<message_id>\d+)",
        ]

        for pattern in patterns:
            match = re.match(pattern, url)
            if match:
                result = match.groupdict()
                return ParsedURL(**result)

    async def receive_url(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        """
        Receives a URL from the user and processes it.

        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        url = update.message.text

        parsed = self.parse_telegram_url(url)
        if not parsed:
            raise Exception("Invalid URL")

        self.user_data = UserData(parsed=parsed)

        await self.display_show_options(update, context, add_new_show=True)
        return CHOOSE_SHOW
    
    async def download_movie_entry_point(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await update.message.reply_text("Please attach the movie link")
        return GET_MOVIE_LINK

    async def display_show_options(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, add_new_show: bool = True
    ) -> str:
        """
        Displays the show options to the user.

        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        reply_keyboard = self.return_shows_options()
        if add_new_show:
            reply_keyboard.append(["New Show"])
        method = (
            update.message.reply_text
            if update.message is not None
            else update.callback_query.message.reply_text
        )
        await method(
            "Please select a show:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return CHOOSE_SHOW

    def return_shows_options(self) -> List:
        """
        Returns the available show options.

        Returns:
            list: The list of show options.
        """
        shows = self.list_shows()
        return [shows[i : i + MAX_SHOWS_PER_RAW] for i in range(0, len(shows), MAX_SHOWS_PER_RAW)]

    def list_shows(self) -> List:
        """
        Lists the available shows.

        Returns:
            list: The list of available shows.
        """
        try:
            shows = os.listdir(self.shows_path)
            return shows if shows else ["No shows found"]
        except Exception as e:
            logger.error(f"Failed to list shows: {str(e)}")
            return ["Error listing shows"]
        
    async def receive_movie_link(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        url = update.message.text
        parsed = self.parse_telegram_url(url)
        if not parsed:
            raise Exception("Invalid URL")
        
        self.user_data = UserData(parsed=parsed)
        
        await update.message.reply_text("Please send the movie name")
        return CHOOSE_MOVIE
    
    async def receive_movie_name(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        movie_name = update.message.text
        movie_data = MovieData(movie_name=movie_name)
        self.user_data.movie_data = movie_data
        await self.process_media(update, context)
        return

    async def receive_show_name(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> Optional[str]:
        """
        Receives the selected show name from the user.

        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        show_name = update.message.text
        if show_name == "New Show":
            await update.message.reply_text(
                text="Please send the name of the new show."
            )
            return ASK_FOR_INPUT
        self.user_data.show_name = show_name
        
        await update.message.reply_text(text=f"Selected option: {show_name} - Please send the season_episode number (e.g. 01_01)")
        return ASK_FOR_EPISODE
    
    async def receive_episode_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        season_episode = update.message.text
        season, episode = season_episode.split("_")
        return await self.process_media(update, context, season, episode)

    async def receive_new_show_name(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Receives the name of a new show from the user.

        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        show_name = update.message.text
        self.user_data.show_name = show_name
        await update.message.reply_text(f"New show name received: {show_name} - Please send the season_episode number (e.g. 01_01)")
        return ASK_FOR_EPISODE

    async def handle_channel_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handles a message received from a channel.

        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        message = update.message
        url_pattern = "https://t.me/plexmedia11/{message_id}"
        if message and message.video:
            logger.info(f"Message received from channel: {message.video}")
            message_id = message.api_kwargs.get("forward_from_message_id")
            url = url_pattern.format(message_id=message_id)
            self.user_data = UserData(parsed=self.parse_telegram_url(url))
            reply_keyboard = self.return_shows_options()
            await update.message.reply_text(
                "Please select a show:",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
            )
            return CHOOSE_SHOW

    async def create_episode_path(self, file_name: str = None) -> str:
        """
        Creates the path for storing an episode.

        Args:
            file_name (str, optional): The name of the episode file. Defaus to None.

        Returns:
            str: The path for storing the episode.
        """
        show_path = os.path.join(self.shows_path, self.user_data.show_name)
        os.makedirs(show_path, exist_ok=True)
        if file_name is None:
            return show_path
        episode_path = os.path.join(show_path, file_name)
        return episode_path

    async def process_media(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, season_number: str = None, episode_number: str = None
    ) -> None:
        """
        Processes the media based on the user's input.

        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        await update.message.reply_text("Processing media...")
        if self.user_data.torrent_data and self.user_data.torrent_data.torrent_link is not None:
            await update.message.reply_text("Downloading torrent...")
            episode_path = await self.create_episode_path()
            download_torrent(self.user_data.torrent_data.torrent_link, episode_path)
            await update.message.reply_text("Torrent downloaded successfully!")
            return ConversationHandler.END
        
        parsed: ParsedURL = self.user_data.parsed
        try:
            await self.start_pyro_client()
        except Exception as e:
            logger.error(f"Failed to start Pyrogram client: {str(e)}")

        try:
            chat_id = parsed.username if parsed.username else f"{parsed.chat_id}"
            message_id = parsed.message_id
            message = await self.pyro_client.get_messages(chat_id, message_id)

            if message.video:
                extension = message.video.file_name.split(".")[-1]
                if self.user_data.movie_data and self.user_data.movie_data.movie_name:
                    new_movie_path = f"{self.user_data.movie_data.movie_name}.{extension}"
                    file_path = os.path.join(self.movies_path, new_movie_path)
                else:
                    new_episode_path = f"{self.user_data.show_name}_s{season_number}e{episode_number}.{extension}"
                    file_path = await self.create_episode_path(new_episode_path)
                await self.pyro_client.download_media(message, file_name=file_path)
                file_size = os.path.getsize(file_path) / 1024 / 1024
                await update.message.reply_text(
                    "Media downloaded successfully! File size: {:.2f} MB".format(
                        file_size
                    )
                )
            else:
                await update.message.reply_text("Failed to find the video message.")
        except Exception as e:
            logger.error(f"Failed to download media: {str(e)}")
            await update.message.reply_text(f"Failed to download media: {str(e)}")
        finally:
            return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Cancels the current operation.

        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        await update.message.reply_text(
            "Operation cancelled.", reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    async def list_show_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Lists all the available shows.

        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        shows = self.list_shows()
        shows_text = "\n".join(shows)
        await update.message.reply_text(f"Shows:\n{shows_text}")

    async def error_handler(
        self, update: object, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handles errors that occur during the bot's operation.

        Args:
            update (object): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        error = context.error
        message = f"An error occurred: {error}"
        logger.error(message)
        # Notify the user about the error
        if update and update.message:
            await update.message.reply_text(message)
        elif update and update.callback_query:
            await update.callback_query.message.reply_text(message)

    async def edit_show_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        """
        Handles the edit show command.

        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        reply_keyboard = self.return_shows_options()
        await update.message.reply_text(
            "Please select a show to update:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return GOT_SHOW

    async def receive_show_to_update(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        """
        Receives the show to update from the user.

        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        show_name = update.message.text
        self.user_data.show_name = show_name
        await update.message.reply_text(
            f"Choosen show -> {show_name}",
            reply_markup=ReplyKeyboardRemove(),
        )
        episodes = self.list_episodes(self.user_data.show_name)
        await update.message.reply_text(
            "Please select an episode to update:",
            reply_markup=ReplyKeyboardMarkup(episodes, one_time_keyboard=True),
        )
        return GOT_EPISODE

    def list_episodes(self, show_name) -> List[str]:
        """
        Lists the episodes of a show.

        Args:
            show_name (str): The name of the show.

        Returns:
            list: The list of episodes.
        """
        show_path = os.path.join(self.shows_path, show_name)
        episodes = os.listdir(show_path)
        return [episodes[i : i + MAX_SHOWS_PER_RAW] for i in range(0, len(episodes), MAX_SHOWS_PER_RAW)]

    async def receive_episode_to_update(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Receives the episode to update from the user.

        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        episode_name = update.message.text
        self.user_data.episode_name = episode_name
        await update.message.reply_text(
            f"Please type the new episode name for {episode_name}:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return GOT_EPISODE_NAME

    async def torrent_entry_point(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await update.message.reply_text("Please send the torrent magnet link")
        return WAIT_FOR_TORRENT

    async def receive_torrent(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        torrent_link = update.message.text
        self.user_data.torrent_data.torrent_link = torrent_link
        buttons = [
            [
                InlineKeyboardButton("Yes", callback_data=str(CHOOSE_SHOW)),
                InlineKeyboardButton("No", callback_data=str(ConversationHandler.END)),
            ]
        ]
        keyboard = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(
            "Would you like to proceed?", reply_markup=keyboard
        )
        return GOT_TORRENT

    async def receive_new_episode_name(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        new_episode_name = update.message.text
        show_name = self.user_data.show_name
        episode_name = self.user_data.episode_name
        show_path = os.path.join(self.shows_path, show_name)
        episode_path = os.path.join(show_path, episode_name)
        new_episode_path = os.path.join(show_path, new_episode_name)
        os.rename(episode_path, new_episode_path)
        await update.message.reply_text(
            f"Episode {episode_name} renamed to {new_episode_name}"
        )
        return ConversationHandler.END

    def run(self) -> None:
        cancel_handler = CommandHandler("cancel", self.cancel)
        edit_show_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("edit_show", self.edit_show_command)],
            states={
                GOT_SHOW: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.receive_show_to_update
                    )
                ],
                GOT_EPISODE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.receive_episode_to_update
                    )
                ],
                GOT_EPISODE_NAME: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.receive_new_episode_name
                    )
                ],
            },
            fallbacks=[cancel_handler],
        )
        list_show_handler = CommandHandler("list_shows", self.list_show_command)
        conv_handler = ConversationHandler(
            entry_points=[
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_url),
                MessageHandler(
                    filters.FORWARDED, self.handle_channel_message
                ),
                CallbackQueryHandler(self.display_show_options),
            ],
            states={
                CHOOSE_SHOW: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.receive_show_name
                    ),
                ],
                ASK_FOR_INPUT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.receive_new_show_name
                    ),
                ],
                ASK_FOR_EPISODE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.receive_episode_number
                    )
                ]
            },
            fallbacks=[cancel_handler],
        )
        torrent_download_handler = ConversationHandler(
            entry_points=[CommandHandler("download_torrent", self.torrent_entry_point)],
            states={
                WAIT_FOR_TORRENT: [MessageHandler(filters.TEXT, self.receive_torrent)],
                GOT_TORRENT: [conv_handler],
            },
            fallbacks=[cancel_handler],
        )
        movies_handler = ConversationHandler(
            entry_points=[
                CommandHandler("download_movie", self.download_movie_entry_point)
            ],
            states={
                GET_MOVIE_LINK: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.receive_movie_link
                    )
                ],
                CHOOSE_MOVIE: {
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.receive_movie_name
                    )
                },
            },
            fallbacks=[cancel_handler],
        )
        self.application.add_handler(movies_handler)
        self.application.add_handler(torrent_download_handler)
        self.application.add_handler(edit_show_conv_handler)
        self.application.add_handler(list_show_handler)
        self.application.add_handler(conv_handler)
        self.application.add_error_handler(self.error_handler)

        logger.info("Starting the bot...")
        self.application.run_polling()


def main():
    """
    Entry point of the program.
    Creates an instance of TelegramBot and runs it.
    """
    bot = TelegramBot()
    bot.run()


if __name__ == "__main__":
    main()
