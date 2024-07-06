import os
import re
import logging
import aiofiles
from pyrogram import Client
from pyrogram.raw.types import InputFileLocation
from pyrogram.raw.functions.upload import GetFile
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SHOW_NAME = range(1)

class ParsedURL(BaseModel):
    chat_id: int | None = None
    message_id: int
    username: str | None = None

    def set_chat_id(cls, v, values):
        if 'username' in values and values['username']:
            return None
        return int(v) if v else None

    def set_username(cls, v, values):
        if 'chat_id' in values and values['chat_id']:
            return None
        return v

class UserData(BaseModel):
    url: str | None = None
    parsed: ParsedURL | None = None
    file_id: str | None = None
    show_name: str | None = None
    forwarded_video: bool = False


async def download_file_by_id(bot: Client, file_id, destination_path):
    try:
        file = bot.get_file(file_id)
        file.download(destination_path)
        logger.info(f'File downloaded successfully to {destination_path}')
    except Exception as e:
        logger.error(f'Failed to download file: {str(e)}')


class TelegramBot:
    def __init__(self):
        self.api_id = os.getenv('API_ID')
        self.api_hash = os.getenv('API_HASH')
        self.telegram_api_token = os.getenv('TELEGRAM_API_TOKEN')
        self.media_base_path = os.getenv('MEDIA_BASE_PATH')
        self.application = Application.builder().token(self.telegram_api_token).build()
        self.pyro_client = Client("nodim", api_id=self.api_id, api_hash=self.api_hash)

    async def start_pyro_client(self):
        await self.pyro_client.start()

    def parse_telegram_url(self, url):
        patterns = [
            r'https://t.me/c/(?P<chat_id>[\d]+)/(?P<message_id>\d+)',
            r'https://web.telegram.org/a/#-(?P<chat_id>[\d]+)/(?P<message_id>\d+)',
            r'https://t.me/(?P<username>[\w]+)/(?P<message_id>\d+)',
        ]

        for pattern in patterns:
            match = re.match(pattern, url)
            if match:
                result = match.groupdict()
                return ParsedURL(**result)

        return None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text('Welcome! Please forward a message containing a video or upload a video file directly.')
        
    async def handle_forwarded_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_data = context.user_data
        message = update.message

        if message.video:
            user_name = message.api_kwargs.get("forward_from_chat", {}).get("username")
            message_id = message.api_kwargs.get("forward_from_message_id")
            chat_id = message.api_kwargs.get("forward_from_chat", {}).get("id")
            # file_id = message.video.file_id
            # await download_file_by_id(self.pyro_client, message.video.file_id, f'{self.media_base_path}/{message.video.file_name}')
            user_data['user_data'] = UserData(
                parsed=ParsedURL(message_id=message_id, username=user_name, chat_id=chat_id),
                forwarded_video=True,
            )
            shows = await self.list_shows()
            show_list = '\n'.join(shows)
            await update.message.reply_text(f'Existing shows:\n{show_list}\n\nPlease send the name of the show or type a new show name.')
            return SHOW_NAME
        else:
            await update.message.reply_text('This message does not contain a valid forwarded video.')
            return ConversationHandler.END

    async def handle_file_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_data = context.user_data
        file = update.message.document

        user_data['user_data'] = {
            'file_id': file.file_id
        }
        shows = await self.list_shows()
        show_list = '\n'.join(shows)
        await update.message.reply_text(f'Existing shows:\n{show_list}\n\nPlease send the name of the show or type a new show name.')
        return SHOW_NAME
    
    async def list_shows(self):
        try:
            shows = os.listdir(self.media_base_path)
            return shows if shows else ['No shows found']
        except Exception as e:
            logger.error(f'Failed to list shows: {str(e)}')
            return ['Error listing shows']

    async def receive_show_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_data = context.user_data
        show_name = update.message.text
        user_data['user_data'].show_name = show_name

        await update.message.reply_text(f"Show name received: {show_name}")

        if user_data['user_data'].forwarded_video:
            await self.process_media(update, context)
        elif user_data['user_data'].file_id:
            await self.save_uploaded_file(update, context)
        context.chat_data['awaiting_show_name'] = False
        return ConversationHandler.END

    async def process_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_data = context.user_data['user_data']
        parsed = user_data.parsed
        show_name = user_data.show_name
        
        try:
            await self.start_pyro_client()
        except Exception as e:
            logger.error(f'Failed to start Pyrogram client: {str(e)}')

        try:
            chat_id = parsed.username if parsed.username else f"{parsed.chat_id}"
            message_id = parsed.message_id
            message = await self.pyro_client.get_messages(chat_id, message_id)

            if message.video:
                show_path = os.path.join(self.media_base_path, show_name)
                os.makedirs(show_path, exist_ok=True)

                file_name = message.video.file_name
                file_path = os.path.join(show_path, file_name)
                await self.pyro_client.download_media(message, file_name=file_path)
                await update.message.reply_text('Media downloaded successfully!')
            else:
                await update.message.reply_text('Failed to find the video message.')
        except Exception as e:
            logger.error(f'Failed to download media: {str(e)}')
            await update.message.reply_text(f'Failed to download media: {str(e)}')

    async def save_uploaded_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_data = context.user_data['user_data']
        file_id = user_data.file_id
        show_name = user_data.show_name

        try:
            file = await context.bot.get_file(file_id)
            show_path = os.path.join(self.media_base_path, show_name)
            os.makedirs(show_path, exist_ok=True)

            file_path = os.path.join(show_path, file.file_path.split('/')[-1])
            await file.download(file_path)
            await update.message.reply_text(f'File saved successfully to {file_path}!')
        except Exception as e:
            logger.error(f'Failed to save file: {str(e)}')
            await update.message.reply_text(f'Failed to save file: {str(e)}')

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text('Operation cancelled.')
        return ConversationHandler.END

    def run(self) -> None:
        conv_handler = ConversationHandler(
            entry_points=[
                MessageHandler(filters.FORWARDED & filters.VIDEO, self.handle_forwarded_message),
                MessageHandler(filters.Document.ALL, self.handle_file_upload),
            ],
            states={
                SHOW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_show_name)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )

        self.application.add_handler(conv_handler)

        self.application.run_polling()


if __name__ == '__main__':
    bot = TelegramBot()
    bot.run()
