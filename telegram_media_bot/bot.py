import os
import re
import logging
import traceback
from typing import List, Optional
from pyrogram import Client
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    BotCommand,
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
from telegram_media_bot.utils import (
    MovieData,
    ParsedURL,
    UserData,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegram_media_bot")

GOT_SHOW, GOT_EPISODE, GOT_EPISODE_NAME = map(chr, range(3))
CHOOSE_SHOW, GET_SHOW_LINK, ASK_FOR_INPUT, ASK_FOR_EPISODE = map(chr, range(4, 8))
GET_MOVIE_LINK, CHOOSE_MOVIE = map(chr, range(8, 10))
GET_MESSAGE = map(chr, range(10, 11))
GET_POLL_MESSAGE = map(chr, range(11, 12))
DELETE_SHOW_MESSAGE = map(chr, range(12, 13))
DELETE_MOVIE_MESSAGE = map(chr, range(13, 14))

MAX_SHOWS_PER_RAW = 3
MAX_MOVIES_PER_RAW = 3


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
        self.pyro_client: Client = Client(
            "nodim", api_id=self.api_id, api_hash=self.api_hash
        )
        self.user_data: UserData = UserData(movie_data=MovieData())

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
        urls = update.message.text.split("\n")
        await update.message.reply_text(
            "Found {} Episodes to download".format(len(urls))
        )
        parsed_urls = []
        for url in urls:
            parsed = self.parse_telegram_url(url)
            if not parsed:
                raise Exception("Invalid URL")
            parsed_urls.append(parsed)

        self.user_data = UserData(parsed=parsed_urls)

        await self.display_show_options(update, context, add_new_show=True)
        return CHOOSE_SHOW

    async def download_show_entry_point(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await update.message.reply_text("Please attach the show link")
        return GET_SHOW_LINK

    async def download_movie_entry_point(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await update.message.reply_text("Please attach the movie link")
        return GET_MOVIE_LINK

    async def display_show_options(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        add_new_show: bool = True,
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
        return [
            shows[i : i + MAX_SHOWS_PER_RAW]
            for i in range(0, len(shows), MAX_SHOWS_PER_RAW)
        ]

    def return_movies_options(self) -> List:
        """
        Returns the available movie options.

        Returns:
            list: The list of movie options.
        """
        movies = self.list_movies()
        return [
            movies[i : i + MAX_MOVIES_PER_RAW]
            for i in range(0, len(movies), MAX_MOVIES_PER_RAW)
        ]

    def list_movies(self) -> List:
        """
        Lists the available movies.

        Returns:
            list: The list of available movies.
        """
        try:
            movies = os.listdir(self.movies_path)
            return movies if movies else ["No movies found"]
        except Exception as e:
            logger.error(f"Failed to list movies: {str(e)}")
            return ["Error listing movies"]

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

        self.user_data = UserData(parsed=[parsed])

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

        await update.message.reply_text(
            text=f"Selected option: {show_name} - Please send the season_episode number (e.g. 01_01)"
        )
        return ASK_FOR_EPISODE

    async def receive_episode_number(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
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
        await update.message.reply_text(
            f"New show name received: {show_name} - Please send the season_episode number (e.g. 01_01)"
        )
        return ASK_FOR_EPISODE

    async def create_episode_path(self, file_name: str = None) -> str:
        """
        Creates the path for storing an episode.

        Args:
            file_name (str, optional): The name of the episode file. Defaus to None.

        Returns:
            str: The path for storing the episode.
        """
        if self.user_data and self.user_data.movie_data:
            movie_path = os.path.join(
                self.movies_path, self.user_data.movie_data.movie_name
            )
            os.makedirs(movie_path, exist_ok=True)
            return movie_path
        show_path = os.path.join(self.shows_path, self.user_data.show_name)
        os.makedirs(show_path, exist_ok=True)
        if file_name is None:
            return show_path
        episode_path = os.path.join(show_path, file_name)
        return episode_path

    async def notify_client(self, message: str, message_id=None) -> None:
        """
        Notifies the client about the new media.

        Args:
            message (str): The message to send to the client.
        """
        try:
            if message_id is None:
                sent_message = await self.application.bot.send_message(
                    chat_id="@plexmedia11", text=message
                )
                return sent_message.message_id
            await self.application.bot.edit_message_text(
                chat_id="@plexmedia11", text=message, message_id=message_id
            )
            return None
        except Exception as e:
            logger.warning(f"Failed to notify client: {str(e)}")

    def get_updated_message(self, number_of_new_contents):
        if self.user_data.movie_data and self.user_data.movie_data.movie_name:
            return f"New movie alert - {self.user_data.movie_data.movie_name.capitalize()} downloaded 🎥"
        return f"{self.user_data.show_name.capitalize()} [{number_of_new_contents} episodes downloaded] 📺"

    async def process_media(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        season_number: str = None,
        episode_number: str = None,
    ) -> None:
        """
        Processes the media based on the user's input.

        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        await update.message.reply_text("Processing media...")
        parsed: ParsedURL = self.user_data.parsed
        try:
            await self.start_pyro_client()
        except Exception as e:
            logger.error(f"Failed to start Pyrogram client: {str(e)}")
        number_of_contents = 0
        try:
            notify_message = "New content coming your way! 🎬"
            notify_message_id = await self.notify_client(notify_message)
            for parsed_url in parsed:
                parsed_url: ParsedURL
                chat_id = (
                    parsed_url.username
                    if parsed_url.username
                    else f"{parsed_url.chat_id}"
                )
                message_id = parsed_url.message_id
                message = await self.pyro_client.get_messages(chat_id, message_id)
                if message.video or message.document:
                    file_name = (
                        message.video.file_name
                        if message.video
                        else message.document.file_name
                    )
                    extension = file_name.rsplit(".", 1)[-1] if file_name else "mp4"
                    notify_message = ""
                    if (
                        self.user_data.movie_data
                        and self.user_data.movie_data.movie_name
                    ):
                        new_movie_path = (
                            f"{self.user_data.movie_data.movie_name}.{extension}"
                        )
                        file_path = os.path.join(
                            self.movies_path,
                            self.user_data.movie_data.movie_name,
                            new_movie_path,
                        )
                    else:
                        new_episode_path = f"{self.user_data.show_name}_s{season_number}e{episode_number}.{extension}"
                        file_path = await self.create_episode_path(new_episode_path)
                        incremented_episode = int(episode_number) + 1
                        episode_number = f"{incremented_episode:02}"
                    download_media = (
                        message if message.video else message.document.file_id
                    )
                    await self.pyro_client.download_media(
                        download_media, file_name=file_path
                    )
                    number_of_contents += 1
                    await self.notify_client(
                        self.get_updated_message(number_of_contents),
                        message_id=notify_message_id,
                    )
                else:
                    await update.message.reply_text("Failed to find the video message.")
        except Exception as e:
            traceback_str = traceback.format_exc()
            logger.error(f"Failed to download media: {str(e)}")
            logger.error(traceback_str)
            await update.message.reply_text(
                f"Failed to download media: {str(e)}\n{traceback_str}"
            )
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

    async def list_movie_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Lists all the available movies.

        Args:
            update (Update): The update object.
            context (ContextTypes.DEFAULT_TYPE): The context object.
        """
        movies = self.list_movies()
        movies_text = "\n".join(movies)
        await update.message.reply_text(f"Movies:\n{movies_text}")

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
        return ConversationHandler.END

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
        return [
            episodes[i : i + MAX_SHOWS_PER_RAW]
            for i in range(0, len(episodes), MAX_SHOWS_PER_RAW)
        ]

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

    async def download_movie_torrent(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        if self.user_data.torrent_data:
            await update.callback_query.message.reply_text("Choose movie name: ")
            return CHOOSE_MOVIE
        else:
            return ConversationHandler.END

    async def notify_clients(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Please send the message to notify clients")
        return GET_MESSAGE

    async def receive_message_to_notify(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        message = update.message.text
        await self.notify_client(message)
        return ConversationHandler.END

    async def create_poll_entry(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        await update.message.reply_text("Please send the message for the poll")
        return GET_POLL_MESSAGE

    async def create_poll(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message.text
        options = ["לא", "כן"]

        # Send the poll
        await context.bot.send_poll(
            chat_id="@plexmedia11",
            question=message,
            options=options,
            is_anonymous=True,  # Set to False if you want to see who voted
            allows_multiple_answers=False,  # Change to True for multiple-choice polls
        )
        return ConversationHandler.END

    async def delete_show_entry_point(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        reply_keyboard = self.return_shows_options()
        await update.message.reply_text(
            "Please select a show to delete:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return DELETE_SHOW_MESSAGE

    async def receive_show_to_delete(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        show_name = update.message.text
        show_path = os.path.join(self.shows_path, show_name)
        os.rmdir(show_path)
        await update.message.reply_text(f"Show {show_name} deleted")
        return ConversationHandler.END

    async def delete_movie_entry_point(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        reply_keyboard = self.return_movies_options()
        await update.message.reply_text(
            "Please select a movie to delete:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return DELETE_MOVIE_MESSAGE

    async def receive_movie_to_delete(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        movie_name = update.message.text
        movie_path = os.path.join(self.movies_path, movie_name)
        os.rmdir(movie_path)
        await update.message.reply_text(f"Movie {movie_name} deleted")
        return ConversationHandler.END

    async def set_bot_commands(self):
        """
        Set bot commands using Telegram Bot API
        """
        commands = [
            BotCommand(
                "download_show", "Download TV show episodes from Telegram links"
            ),
            BotCommand("download_movie", "Download movies from Telegram links"),
            BotCommand("edit_show", "Edit and rename TV show episodes"),
            BotCommand("list_shows", "List all available TV shows"),
            BotCommand("list_movies", "List all available movies"),
            BotCommand("create_poll", "Create a poll for the media channel"),
            BotCommand("notify_client", "Send notification messages to clients"),
            BotCommand("delete_show", "Delete a TV show from the collection"),
            BotCommand("delete_movie", "Delete a movie from the collection"),
            BotCommand("cancel", "Cancel current operation"),
        ]

        try:
            await self.application.bot.set_my_commands(commands)
            logger.info("Bot commands set successfully")
        except Exception as e:
            logger.error(f"Failed to set bot commands: {str(e)}")

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
        list_movie_handler = CommandHandler("list_movies", self.list_movie_command)
        create_poll_handler = ConversationHandler(
            entry_points=[CommandHandler("create_poll", self.create_poll_entry)],
            states={
                GET_POLL_MESSAGE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.create_poll)
                ]
            },
            fallbacks=[cancel_handler],
        )
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("download_show", self.download_show_entry_point),
            ],
            states={
                GET_SHOW_LINK: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_url)
                ],
                CHOOSE_SHOW: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.receive_show_name
                    ),
                    CallbackQueryHandler(self.display_show_options),
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
                ],
            },
            fallbacks=[cancel_handler],
        )
        movies_handler = ConversationHandler(
            entry_points=[
                CommandHandler("download_movie", self.download_movie_entry_point),
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
                    ),
                    CallbackQueryHandler(self.download_movie_torrent),
                },
            },
            fallbacks=[cancel_handler],
        )
        notify_clients_handler = ConversationHandler(
            entry_points=[CommandHandler("notify_client", self.notify_clients)],
            states={
                GET_MESSAGE: [
                    MessageHandler(filters.TEXT, self.receive_message_to_notify)
                ],
            },
            fallbacks=[cancel_handler],
        )
        delete_show_handler = ConversationHandler(
            entry_points=[CommandHandler("delete_show", self.delete_show_entry_point)],
            states={
                DELETE_SHOW_MESSAGE: [
                    MessageHandler(filters.TEXT, self.receive_show_to_delete)
                ],
            },
            fallbacks=[cancel_handler],
        )
        delete_movie_handler = ConversationHandler(
            entry_points=[
                CommandHandler("delete_movie", self.delete_movie_entry_point)
            ],
            states={
                DELETE_MOVIE_MESSAGE: [
                    MessageHandler(filters.TEXT, self.receive_movie_to_delete)
                ],
            },
            fallbacks=[cancel_handler],
        )
        self.application.add_handler(movies_handler)
        self.application.add_handler(conv_handler)
        self.application.add_handler(edit_show_conv_handler)
        self.application.add_handler(list_show_handler)
        self.application.add_handler(list_movie_handler)
        self.application.add_handler(create_poll_handler)
        self.application.add_handler(notify_clients_handler)
        self.application.add_handler(delete_show_handler)
        self.application.add_handler(delete_movie_handler)
        self.application.add_error_handler(self.error_handler)

        logger.info("Starting the bot...")

        # Set up bot commands on startup
        async def post_init(application):
            await self.set_bot_commands()

        self.application.post_init = post_init
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
