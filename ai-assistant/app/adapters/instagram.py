import logging
import time
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from instagrapi import Client as InstagrapiClient
from instagrapi.exceptions import LoginRequired, ChallengeRequired, ClientError

from app.adapters.base import MessengerAdapter
from app.core.config import (
    INSTAGRAM_USERNAME,
    INSTAGRAM_PASSWORD,
    INSTAGRAM_VERIFICATION_CODE,
    INSTAGRAM_MAX_MESSAGES_PER_DAY,
    INSTAGRAM_MIN_INTERVAL_MINUTES,
    WORKING_HOURS_START,
    WORKING_HOURS_END
)
from app.models.database import SessionLocal, AccountActivity, Message

logger = logging.getLogger(__name__)

class InstagramAdapter(MessengerAdapter):
    """
    Адаптер для взаимодействия с Instagram через instagrapi
    """
    def __init__(self):
        self.client = InstagrapiClient()
        self.username = INSTAGRAM_USERNAME
        self.password = INSTAGRAM_PASSWORD
        self.verification_code = INSTAGRAM_VERIFICATION_CODE
        self.authenticated = False
        self.last_message_sent = None
        self.messages_sent_today = 0
        self.session_file = f"/home/aibot/ai-assistant/data/{self.username}_session.json"
        self._load_session_counter()

    def _load_session_counter(self):
        """Загрузка счетчика сообщений из базы данных"""
        try:
            db = SessionLocal()
            today = datetime.now().date()
            today_start = datetime.combine(today, datetime.min.time())
            today_end = datetime.combine(today, datetime.max.time())
            
            # Получаем количество сообщений, отправленных сегодня
            count = db.query(AccountActivity).filter(
                AccountActivity.platform == "instagram",
                AccountActivity.account_name == self.username,
                AccountActivity.action_type == "message_sent",
                AccountActivity.timestamp.between(today_start, today_end)
            ).count()
            
            self.messages_sent_today = count
            
            # Получаем время последнего отправленного сообщения
            last_message = db.query(AccountActivity).filter(
                AccountActivity.platform == "instagram",
                AccountActivity.account_name == self.username,
                AccountActivity.action_type == "message_sent"
            ).order_by(AccountActivity.timestamp.desc()).first()
            
            if last_message:
                self.last_message_sent = last_message.timestamp
                
            logger.info(f"Loaded session counter: {self.messages_sent_today} messages sent today")
        except Exception as e:
            logger.error(f"Error loading session counter: {e}")
        finally:
            db.close()

    async def authenticate(self) -> bool:
        """Аутентификация в Instagram"""
        try:
            # Прямая авторизация без попытки загрузки сессии
            logger.info(f"Direct login attempt as {self.username}")
            if self.verification_code:
                # Если у нас есть код верификации для 2FA
                self.client.login(
                    self.username, 
                    self.password,
                    verification_code=self.verification_code
                )
            else:
                # Обычный логин
                self.client.login(self.username, self.password)
            
            # Сохраняем сессию для последующего использования
            try:
                self.client.dump_settings(self.session_file)
                logger.info(f"Session saved to {self.session_file}")
            except Exception as save_error:
                logger.warning(f"Could not save session: {save_error}")
            
            # Сохраняем активность в БД
            try:
                db = SessionLocal()
                db.add(AccountActivity(
                    platform="instagram",
                    account_name=self.username,
                    action_type="login",
                    details="Successful login"
                ))
                db.commit()
                db.close()
            except Exception as db_error:
                logger.warning(f"Could not save login activity to database: {db_error}")
            
            self.authenticated = True
            logger.info("Successfully authenticated with Instagram")
            return True
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            self.authenticated = False
            return False

    async def is_within_working_hours(self) -> bool:
        """Проверка, находимся ли мы в рабочее время (МСК)"""
        now = datetime.now()  # Предполагается, что сервер настроен на МСК
        current_hour = now.hour
        return WORKING_HOURS_START <= current_hour < WORKING_HOURS_END

    async def is_within_limits(self) -> bool:
        """Проверка, не превышены ли лимиты использования API"""
        # Проверяем, в рабочее ли время
        if not await self.is_within_working_hours():
            logger.info("Outside of working hours, not sending messages")
            return False
        
        # Проверяем количество сообщений за день
        if self.messages_sent_today >= INSTAGRAM_MAX_MESSAGES_PER_DAY:
            logger.warning(f"Daily message limit reached: {self.messages_sent_today}/{INSTAGRAM_MAX_MESSAGES_PER_DAY}")
            return False
        
        # Проверяем интервал между сообщениями
        if self.last_message_sent:
            time_since_last = datetime.now() - self.last_message_sent
            min_interval = timedelta(minutes=INSTAGRAM_MIN_INTERVAL_MINUTES)
            if time_since_last < min_interval:
                logger.info(f"Not enough time since last message: {time_since_last.total_seconds()/60:.2f} min < {INSTAGRAM_MIN_INTERVAL_MINUTES} min")
                return False
                
        return True

    async def send_message(self, recipient_id: str, message: str) -> Dict[str, Any]:
        """Отправка сообщения пользователю в Instagram"""
        if not self.authenticated:
            if not await self.authenticate():
                return {"success": False, "error": "Authentication failed"}
        
        # Проверяем лимиты
        if not await self.is_within_limits():
            return {"success": False, "error": "Rate limits would be exceeded"}
        
        try:
            # Эмуляция печатания (задержка пропорциональна длине сообщения)
            typing_delay = min(len(message) * 0.05, 5)  # Не более 5 секунд
            typing_delay += random.uniform(0.5, 2.0)  # Добавляем случайную составляющую
            logger.info(f"Emulating typing for {typing_delay:.2f} seconds")
            await asyncio.sleep(typing_delay)
            
            # Отправка сообщения
            result = self.client.direct_send(message, [recipient_id])
            
            # Обновляем счетчики
            self.last_message_sent = datetime.now()
            self.messages_sent_today += 1
            
            # Записываем в БД
            db = SessionLocal()
            db.add(AccountActivity(
                platform="instagram",
                account_name=self.username,
                action_type="message_sent",
                details=f"Message sent to {recipient_id}"
            ))
            db.commit()
            db.close()
            
            logger.info(f"Message sent to {recipient_id}")
            return {"success": True, "message_id": result.id}
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            
            # Проверка, не требуется ли повторная аутентификация
            if isinstance(e, (LoginRequired, ChallengeRequired)):
                logger.info("Session expired, trying to re-authenticate")
                self.authenticated = False
                if await self.authenticate():
                    # Повторяем попытку отправки после повторной аутентификации
                    return await self.send_message(recipient_id, message)
                    
            return {"success": False, "error": str(e)}

    async def receive_messages(self) -> List[Dict[str, Any]]:
        """Получение новых сообщений из Instagram"""
        if not self.authenticated:
            if not await self.authenticate():
                return []
        
        try:
            messages = []
            
            # Получаем входящие сообщения используя прямой метод для доступа к inbox
            logger.info("Fetching inbox")
            try:
                # Попытка использовать direct_threads
                if hasattr(self.client, 'direct_threads'):
                    threads = self.client.direct_threads()
                    
                    # Обрабатываем каждый тред (диалог)
                    for thread in threads:
                        thread_id = getattr(thread, 'id', None)
                        if not thread_id:
                            continue
                            
                        # Проверяем, есть ли непрочитанные сообщения
                        unread_count = getattr(thread, 'unread_count', 0)
                        if unread_count > 0:
                            # Получаем полную информацию о треде
                            full_thread = self.client.direct_thread(thread_id)
                            
                            # Обрабатываем сообщения в треде
                            items = getattr(full_thread, 'items', [])
                            for item in items:
                                # Проверяем, что сообщение не от нас
                                if (hasattr(item, 'user_id') and 
                                    hasattr(item, 'text') and 
                                    item.user_id != self.client.user_id):
                                    
                                    logger.info(f"Found message from user {item.user_id}: {item.text}")
                                    
                                    messages.append({
                                        "message_id": getattr(item, 'id', ''),
                                        "thread_id": thread_id,
                                        "user_id": item.user_id,
                                        "text": item.text,
                                        "timestamp": getattr(item, 'timestamp', datetime.now())
                                    })
                else:
                    logger.error("No suitable method found to fetch direct messages")
            except Exception as e:
                logger.error(f"Error fetching inbox: {e}")
            
            logger.info(f"Total messages to process: {len(messages)}")
            return messages
                
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
            
            # Проверка, не требуется ли повторная аутентификация
            if isinstance(e, (LoginRequired, ChallengeRequired)):
                logger.info("Session expired, trying to re-authenticate")
                self.authenticated = False
                if await self.authenticate():
                    # Повторяем попытку после повторной аутентификации
                    return await self.receive_messages()
                    
            return []

    async def accept_pending_requests(self) -> int:
        """Принять все запросы на переписку"""
        if not self.authenticated:
            if not await self.authenticate():
                return 0
        
        try:
            # Получение запросов на переписку
            logger.info("Checking pending message requests")
            try:
                pending_requests = self.client.direct_pending_inbox()
                
                # Проверяем, что ответ это список объектов
                if isinstance(pending_requests, list):
                    if not pending_requests:
                        logger.info("No pending message requests found")
                        return 0
                        
                    logger.info(f"Found {len(pending_requests)} pending message requests")
                    
                    # Принимаем каждый запрос
                    accepted_count = 0
                    for thread in pending_requests:
                        thread_id = getattr(thread, 'id', None) or getattr(thread, 'thread_id', None)
                        if thread_id:
                            try:
                                logger.info(f"Accepting message request for thread {thread_id}")
                                self.client.direct_thread_approve(thread_id)
                                accepted_count += 1
                                logger.info(f"Successfully accepted message request for thread {thread_id}")
                            except Exception as e:
                                logger.error(f"Error accepting message request for thread {thread_id}: {e}")
                    
                    return accepted_count
                    
                # Если ответ это словарь (другая версия API)
                elif isinstance(pending_requests, dict):
                    threads = pending_requests.get('inbox', {}).get('threads', [])
                    if not threads:
                        logger.info("No pending message requests found")
                        return 0
                        
                    logger.info(f"Found {len(threads)} pending message requests")
                    
                    # Принимаем каждый запрос
                    accepted_count = 0
                    for thread in threads:
                        thread_id = thread.get('thread_id')
                        if thread_id:
                            try:
                                logger.info(f"Accepting message request for thread {thread_id}")
                                self.client.direct_thread_approve(thread_id)
                                accepted_count += 1
                                logger.info(f"Successfully accepted message request for thread {thread_id}")
                            except Exception as e:
                                logger.error(f"Error accepting message request for thread {thread_id}: {e}")
                    
                    return accepted_count
                else:
                    logger.info(f"Unexpected type for pending_requests: {type(pending_requests)}")
                    return 0
            except AttributeError:
                logger.error("Method direct_pending_inbox not found")
                return 0
                
        except Exception as e:
            logger.error(f"Error handling pending requests: {e}")
            return 0

    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Получение информации о пользователе Instagram"""
        if not self.authenticated:
            if not await self.authenticate():
                return {}
        
        try:
            # Получаем информацию о пользователе
            user_info = self.client.user_info(user_id)
            
            return {
                "user_id": user_info.pk,
                "username": user_info.username,
                "full_name": user_info.full_name,
                "is_private": user_info.is_private,
                "media_count": user_info.media_count,
                "follower_count": user_info.follower_count,
                "following_count": user_info.following_count,
                "biography": user_info.biography
            }
            
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            
            # Проверка, не требуется ли повторная аутентификация
            if isinstance(e, (LoginRequired, ChallengeRequired)):
                logger.info("Session expired, trying to re-authenticate")
                self.authenticated = False
                if await self.authenticate():
                    # Повторяем попытку после повторной аутентификации
                    return await self.get_user_info(user_id)
                    
            return {}
