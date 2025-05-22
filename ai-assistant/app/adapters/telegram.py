import asyncio
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import random

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
from telegram.error import TelegramError, RetryAfter, TimedOut

from .base import MessengerAdapter
from ..core.config import get_settings
from ..models.database import get_db_session, Client, Message


class TelegramAdapter(MessengerAdapter):
    def __init__(self, bot_token: str):
        super().__init__()
        self.bot_token = bot_token
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
        self.settings = get_settings()
        
        self.message_delay = 1.0
        self.max_messages_per_second = 30
        self.last_message_time = 0
        
        self.logger.info("TelegramAdapter initialized")
    
    async def authenticate(self) -> bool:
        try:
            self.application = Application.builder().token(self.bot_token).build()
            self.bot = self.application.bot
            
            bot_info = await self.bot.get_me()
            self.logger.info(f"Telegram bot authenticated: @{bot_info.username}")
            
            await self._setup_handlers()
            
            self.is_authenticated = True
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to authenticate Telegram bot: {e}")
            return False
    
    async def _setup_handlers(self):
        self.application.add_handler(
            CommandHandler("start", self._handle_start_command)
        )
        
        self.application.add_handler(
            CommandHandler("help", self._handle_help_command)
        )
        
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )
        
        self.application.add_handler(
            CallbackQueryHandler(self._handle_callback_query)
        )
        
        self.application.add_error_handler(self._handle_error)
    
    async def start(self) -> bool:
        try:
            if not self.application:
                await self.authenticate()
            
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )
            
            self.is_running = True
            self.update_statistics('start')
            self.logger.info("Telegram bot started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start Telegram bot: {e}")
            return False
    
    async def stop(self) -> bool:
        try:
            if self.application and self.is_running:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            
            self.is_running = False
            self.logger.info("Telegram bot stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop Telegram bot: {e}")
            return False
    
    async def send_message(self, recipient_id: str, message: str, **kwargs) -> Dict[str, Any]:
        try:
            await self._respect_rate_limits()
            
            is_valid, error = await self.validate_message(message)
            if not is_valid:
                return {
                    'success': False,
                    'error': error,
                    'platform': 'telegram'
                }
            
            formatted_message = self._format_message(message)
            
            reply_markup = None
            if 'buttons' in kwargs:
                reply_markup = self._create_inline_keyboard(kwargs['buttons'])
            
            sent_message = await self.bot.send_message(
                chat_id=int(recipient_id),
                text=formatted_message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                disable_web_page_preview=kwargs.get('disable_preview', True)
            )
            
            await self._save_message_to_db(
                user_id=recipient_id,
                message_text=message,
                is_outgoing=True,
                platform_message_id=str(sent_message.message_id)
            )
            
            self.update_statistics('sent')
            self.logger.info(f"Message sent to {recipient_id}: {message[:50]}...")
            
            return {
                'success': True,
                'message_id': str(sent_message.message_id),
                'platform': 'telegram',
                'timestamp': datetime.now().isoformat()
            }
            
        except RetryAfter as e:
            self.logger.warning(f"Rate limited, waiting {e.retry_after} seconds")
            await asyncio.sleep(e.retry_after)
            return await self.send_message(recipient_id, message, **kwargs)
            
        except TelegramError as e:
            self.logger.error(f"Telegram error sending message to {recipient_id}: {e}")
            self.update_statistics('error')
            return {
                'success': False,
                'error': str(e),
                'platform': 'telegram'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to send message to {recipient_id}: {e}")
            self.update_statistics('error')
            return {
                'success': False,
                'error': str(e),
                'platform': 'telegram'
            }
    
    async def receive_messages(self) -> List[Dict[str, Any]]:
        return []
    
    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        try:
            chat = await self.bot.get_chat(int(user_id))
            
            return {
                'id': str(chat.id),
                'username': chat.username,
                'first_name': chat.first_name,
                'last_name': chat.last_name,
                'type': chat.type,
                'platform': 'telegram'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get user info for {user_id}: {e}")
            return {
                'id': user_id,
                'error': str(e),
                'platform': 'telegram'
            }
    
    async def is_within_limits(self) -> bool:
        return self.is_running and self.is_authenticated
    
    async def get_platform_info(self) -> Dict[str, Any]:
        try:
            if self.bot:
                bot_info = await self.bot.get_me()
                return {
                    'platform': 'telegram',
                    'bot_username': bot_info.username,
                    'bot_id': bot_info.id,
                    'bot_name': bot_info.first_name,
                    'is_running': self.is_running,
                    'is_authenticated': self.is_authenticated
                }
            else:
                return {
                    'platform': 'telegram',
                    'is_running': self.is_running,
                    'is_authenticated': self.is_authenticated,
                    'error': 'Bot not initialized'
                }
        except Exception as e:
            self.logger.error(f"Error getting platform info: {e}")
            return {
                'platform': 'telegram',
                'error': str(e),
                'is_running': self.is_running
            }
    
    async def _handle_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or "Unknown"
        
        await self._save_user_info(update.effective_user)
        
        welcome_message = "Добро пожаловать! Как дела?"
        
        await self.send_message(
            recipient_id=user_id,
            message=welcome_message,
            buttons=[
                [{"text": "Узнать больше", "callback_data": "learn_more"}],
                [{"text": "Связаться с менеджером", "callback_data": "contact_manager"}]
            ]
        )
        
        self.logger.info(f"Start command from user {username} ({user_id})")
    
    async def _handle_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
<b>Помощь по боту</b>

Я ваш персональный ассистент! Могу помочь с:
• Ответами на вопросы о наших услугах
• Записью на консультацию
• Предоставлением актуальной информации

Просто напишите мне сообщение, и я отвечу!
        """
        
        await self.send_message(
            recipient_id=str(update.effective_user.id),
            message=help_text
        )
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        message_text = update.message.text
        
        await self._save_message_to_db(
            user_id=user_id,
            message_text=message_text,
            is_outgoing=False,
            platform_message_id=str(update.message.message_id)
        )
        
        self.update_statistics('received')
        
        await self._process_incoming_message(user_id, message_text, update.effective_user)
        
        self.logger.info(f"Message received from {user_id}: {message_text[:50]}...")
    
    async def _handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = str(query.from_user.id)
        callback_data = query.data
        
        await query.answer()
        
        await self._process_incoming_message(
            user_id, 
            f"[BUTTON_CLICK] {callback_data}", 
            query.from_user
        )
        
        self.logger.info(f"Button clicked by {user_id}: {callback_data}")
    
    async def _handle_error(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        self.logger.error(f"Telegram bot error: {context.error}")
        self.update_statistics('error')
        
        if update and hasattr(update, 'effective_user'):
            user_id = str(update.effective_user.id)
            error_message = "Произошла временная ошибка. Попробуйте позже."
            
            try:
                await self.send_message(user_id, error_message)
            except:
                pass
    
    async def _process_incoming_message(self, user_id: str, message_text: str, user_info):
        try:
            user_data = {
                'id': user_id,
                'username': user_info.username,
                'first_name': user_info.first_name,
                'last_name': user_info.last_name,
                'platform': 'telegram'
            }
            
            from ..core.core_system import get_core_system
            core_system = get_core_system()
            await core_system.process_message('telegram', user_id, message_text, user_data)
            
        except Exception as e:
            self.logger.error(f"Error processing message from {user_id}: {e}")
            try:
                await self.send_message(user_id, "Извините, произошла ошибка при обработке вашего сообщения. Попробуйте еще раз.")
            except:
                pass
    
    async def _save_user_info(self, user):
        try:
            session = get_db_session()
            
            client = session.query(Client).filter_by(
                platform_id=str(user.id),
                platform='telegram'
            ).first()
            
            if not client:
                client = Client(
                    platform_id=str(user.id),
                    platform='telegram',
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    status='new'
                )
                session.add(client)
            else:
                client.username = user.username
                client.first_name = user.first_name
                client.last_name = user.last_name
                client.last_activity = datetime.now()
            
            session.commit()
            session.close()
            
        except Exception as e:
            self.logger.error(f"Error saving user info: {e}")
    
    async def _save_message_to_db(self, user_id: str, message_text: str, 
                                 is_outgoing: bool, platform_message_id: str):
        try:
            session = get_db_session()
            
            client = session.query(Client).filter_by(
                platform_id=user_id,
                platform='telegram'
            ).first()
            
            if client:
                message = Message(
                    client_id=client.id,
                    message_text=message_text,
                    is_outgoing=is_outgoing,
                    platform_message_id=platform_message_id,
                    created_at=datetime.now()
                )
                session.add(message)
                session.commit()
            
            session.close()
            
        except Exception as e:
            self.logger.error(f"Error saving message to DB: {e}")
    
    def _format_message(self, message: str) -> str:
        formatted = message.replace('**', '<b>').replace('**', '</b>')
        formatted = formatted.replace('*', '<i>').replace('*', '</i>')
        
        return formatted
    
    def _create_inline_keyboard(self, buttons: List[List[Dict]]) -> InlineKeyboardMarkup:
        keyboard = []
        
        for row in buttons:
            keyboard_row = []
            for button in row:
                keyboard_row.append(
                    InlineKeyboardButton(
                        text=button['text'],
                        callback_data=button['callback_data']
                    )
                )
            keyboard.append(keyboard_row)
        
        return InlineKeyboardMarkup(keyboard)
    
    async def _respect_rate_limits(self):
        current_time = asyncio.get_event_loop().time()
        
        time_since_last = current_time - self.last_message_time
        if time_since_last < self.message_delay:
            sleep_time = self.message_delay - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_message_time = asyncio.get_event_loop().time()