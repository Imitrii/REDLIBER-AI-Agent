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
            # Сначала пытаемся загрузить сессию из файла
            logger.info(f"Trying to load session from file")
            try:
                self.client.load_settings(self.session_file)
                # Проверяем, действительна ли сессия
                self.client.get_timeline_feed()
                self.authenticated = True
                logger.info("Successfully loaded session from file")
                return True
            except Exception as e:
                logger.error(f"Authentication error: {e}")
                
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
        # Временно отключаем проверку рабочих часов для тестирования
        # Когда бот будет работать корректно, можно вернуть эту проверку
        # if not await self.is_within_working_hours():
        #     logger.info("Outside of working hours, not sending messages")
        #     return False
        
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

    async def mark_seen(self, thread_id: str) -> Dict[str, Any]:
        """Отметить сообщения треда как прочитанные"""
        if not self.authenticated:
            if not await self.authenticate():
                return {"success": False, "error": "Authentication failed"}
        
        try:
            logger.info(f"Marking thread {thread_id} as seen")
            
            # Отправляем запрос на отметку сообщений как прочитанных
            try:
                # В Instagram API v1 нет прямого эндпоинта для пометки сообщений как прочитанных,
                # поэтому используем специальный запрос к direct_v2/threads/{thread_id}
                
                # Сначала получаем последнее сообщение треда
                thread_data = self.client.private_request(f"direct_v2/threads/{thread_id}/", 
                                               params={"visual_message_return_type": "unseen", 
                                                      "direction": "older", 
                                                      "seq_id": "0", 
                                                      "limit": "1"})
                
                if not thread_data or "thread" not in thread_data or "items" not in thread_data["thread"] or not thread_data["thread"]["items"]:
                    logger.warning(f"No thread data or messages found for thread_id {thread_id}")
                    return {"success": False, "error": "No messages found in thread"}
                
                # Получаем ID последнего сообщения и отметку времени
                last_item = thread_data["thread"]["items"][0]
                last_item_id = last_item.get("item_id")
                thread_id = thread_data["thread"]["thread_id"]
                
                if not last_item_id:
                    logger.warning(f"Failed to get last item ID for thread {thread_id}")
                    return {"success": False, "error": "Failed to get last item ID"}
                
                # Используем более правильный API endpoint для отметки сообщений как прочитанных
                response = self.client.private_request(
                    "direct_v2/threads/mark_seen/",
                    {
                        "thread_ids": f"[{thread_id}]",
                        "item_ids": f"[{last_item_id}]",
                        "_uuid": self.client.uuid,
                        "_uid": self.client.user_id,
                        "_csrftoken": self.client.private.cookies.get("csrftoken", "")
                    }
                )
                
                if response.get("status") == "ok":
                    logger.info(f"Successfully marked thread {thread_id} as seen")
                    return {"success": True}
                else:
                    logger.warning(f"Failed to mark thread {thread_id} as seen: {response}")
                    return {"success": False, "error": str(response)}
                    
            except Exception as e:
                logger.error(f"Error marking thread as seen: {e}")
                
                # Альтернативный метод - загружаем всю ветку и отметим её как прочитанную
                try:
                    # Пытаемся использовать метод from_id из instagrapi для получения объекта треда
                    self.client.direct_send("", [], thread_ids=[thread_id])
                    logger.info(f"Successfully marked thread {thread_id} as seen using dummy message method")
                    return {"success": True}
                except Exception as alt_e:
                    logger.error(f"Alternative method also failed: {alt_e}")
                    return {"success": False, "error": str(alt_e)}
        
        except Exception as e:
            logger.error(f"Error marking thread as seen: {e}")
            
            # Проверка, не требуется ли повторная аутентификация
            if isinstance(e, (LoginRequired, ChallengeRequired)):
                logger.info("Session expired, trying to re-authenticate")
                self.authenticated = False
                if await self.authenticate():
                    # Повторяем попытку после повторной аутентификации
                    return await self.mark_seen(thread_id)
                    
            return {"success": False, "error": str(e)}

    async def receive_messages(self) -> List[Dict[str, Any]]:
        """Получение новых сообщений из Instagram"""
        if not self.authenticated:
            if not await self.authenticate():
                return []
        
        try:
            messages = []
            
            # Проверяем наличие новых запросов на сообщения и принимаем их
            await self.accept_pending_requests()
            
            # Получение входящих сообщений с использованием прямых запросов к API
            try:
                logger.info("Fetching inbox")
                # Получаем входящие сообщения через API
                inbox_data = self.client.private_request("direct_v2/inbox/", 
                                                  params={"visual_message_return_type": "unseen", 
                                                          "thread_message_limit": 20, 
                                                          "persistentBadging": "true", 
                                                          "limit": 20, 
                                                          "is_prefetching": "false"})
                
                if not inbox_data or "inbox" not in inbox_data or "threads" not in inbox_data["inbox"]:
                    logger.warning("No inbox data returned from API")
                    return []
                
                threads = inbox_data["inbox"]["threads"]
                logger.info(f"Total threads to process: {len(threads)}")
                
                # Детально логируем информацию о каждом треде для отладки
                for i, thread in enumerate(threads):
                    thread_id = thread.get("thread_id")
                    thread_title = thread.get("thread_title")
                    unread_count = thread.get("unread_count", 0)
                    has_newer = thread.get("has_newer", False)
                    is_group = thread.get("is_group", False)
                    participants = [p.get("username") for p in thread.get("users", [])]
                    logger.info(f"Thread {i+1}: ID={thread_id}, Title={thread_title}, Unread={unread_count}, " +
                                f"Has newer={has_newer}, Is group={is_group}, Participants={participants}")
                
                for thread in threads:
                    # Обрабатываем все треды, даже если они отмечены как прочитанные
                    thread_id = thread.get("thread_id")
                    unread_count = thread.get("unread_count", 0)
                    
                    logger.info(f"Processing thread {thread_id}, unread count: {unread_count}")
                    
                    # Получаем сообщения треда независимо от статуса прочтения
                    logger.info(f"Fetching messages for thread {thread_id}")
                    thread_data = self.client.private_request(f"direct_v2/threads/{thread_id}/", 
                                                       params={"visual_message_return_type": "unseen", 
                                                               "direction": "older", 
                                                               "seq_id": "0", 
                                                               "limit": "20"})
                    
                    if not thread_data or "thread" not in thread_data or "items" not in thread_data["thread"]:
                        logger.warning(f"No thread data returned for thread_id {thread_id}")
                        continue
                    
                    items = thread_data["thread"]["items"]
                    logger.info(f"Found {len(items)} messages in thread {thread_id}")
                    
                    # Получаем текущее время в миллисекундах
                    current_time = int(time.time() * 1000000)
                    # Получаем время 24 часа назад
                    time_24h_ago = current_time - (24 * 60 * 60 * 1000000)
                    
                    # Логируем первые несколько сообщений для отладки
                    for i, item in enumerate(items[:5]):  # Логируем только первые 5 сообщений
                        item_type = item.get("item_type")
                        item_id = item.get("item_id")
                        user_id = item.get("user_id")
                        timestamp = item.get("timestamp", 0)
                        text = item.get("text", "")
                        logger.info(f"Message {i+1}: ID={item_id}, Type={item_type}, " +
                                   f"User={user_id}, Time={timestamp}, Text={text}")
                        
                        # Проверяем, было ли сообщение отправлено в последние 24 часа
                        is_recent = int(timestamp) > time_24h_ago
                        logger.info(f"Message is recent (within last 24h): {is_recent}")
                    
                    processed_messages = []
                    # Обрабатываем только текстовые сообщения, не от нас, и полученные за последние 24 часа
                    for item in items:
                        if (item.get("item_type") == "text" and 
                            str(item.get("user_id")) != str(self.client.user_id) and
                            int(item.get("timestamp", 0)) > time_24h_ago):
                            
                            logger.info(f"Adding recent message to process: {item.get('text', '')[:30]}...")
                            processed_messages.append({
                                "message_id": item.get("item_id"),
                                "thread_id": thread_id,
                                "user_id": item.get("user_id"),
                                "text": item.get("text", ""),
                                "timestamp": datetime.fromtimestamp(int(item.get("timestamp", time.time())) / 1000000.0)
                            })
                    
                    # Добавляем сообщения в общий список для обработки
                    messages.extend(processed_messages)
                    
                    if processed_messages:
                        logger.info(f"Added {len(processed_messages)} recent messages from thread {thread_id}")
                    else:
                        logger.info(f"No recent messages to process in thread {thread_id}")
                    
                # Логируем итоговое количество собранных сообщений
                logger.info(f"Total messages collected for processing: {len(messages)}")
                
            except Exception as e:
                logger.error(f"Error fetching inbox: {e}")
            
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
                # Используем прямой запрос к API для получения запросов
                pending_inbox = self.client.private_request("direct_v2/pending_inbox/", 
                                                     params={"visual_message_return_type": "unseen", 
                                                             "persistentBadging": "true", 
                                                             "is_prefetching": "false"})
                
                if not pending_inbox or "inbox" not in pending_inbox or "threads" not in pending_inbox["inbox"]:
                    logger.info("No pending message requests found")
                    return 0
                
                threads = pending_inbox["inbox"]["threads"]
                
                if not threads:
                    logger.info("No pending message requests found")
                    return 0
                    
                logger.info(f"Found {len(threads)} pending message requests")
                
                # Принимаем каждый запрос
                accepted_count = 0
                for thread in threads:
                    thread_id = thread.get("thread_id")
                    if thread_id:
                        try:
                            logger.info(f"Accepting message request for thread {thread_id}")
                            # Используем прямой запрос к API для одобрения запроса
                            response = self.client.private_request(
                                "direct_v2/threads/approve_multiple/",
                                params={},
                                data={"thread_ids": f"[{thread_id}]"}
                            )
                            logger.info(f"Successfully accepted message request for thread {thread_id}")
                            accepted_count += 1
                            
                        except Exception as e1:
                            logger.warning(f"First method failed: {e1}, trying alternative methods...")
                            
                            try:
                                # Альтернативный метод - попытка прямой отправки форм-данных
                                import requests
                                from requests.utils import dict_from_cookiejar
                                
                                # Извлекаем все необходимые токены и куки
                                cookies_dict = dict_from_cookiejar(self.client.private.cookies)
                                csrf_token = cookies_dict.get("csrftoken", "")
                                
                                # Формируем заголовки с токенами
                                headers = {
                                    "User-Agent": self.client.user_agent,
                                    "Accept": "*/*",
                                    "Accept-Language": "en-US",
                                    "Accept-Encoding": "gzip, deflate",
                                    "X-CSRFToken": csrf_token,
                                    "X-IG-App-ID": "936619743392459",
                                    "X-Instagram-AJAX": "1",
                                    "X-IG-WWW-Claim": "0",
                                    "Content-Type": "application/x-www-form-urlencoded",
                                    "Origin": "https://www.instagram.com",
                                    "Referer": "https://www.instagram.com/direct/inbox/"
                                }
                                
                                # Последняя попытка - использовать другой API endpoint
                                url2 = "https://i.instagram.com/api/v1/direct_v2/threads/approve_multiple/"
                                data2 = {"thread_ids": f"[{thread_id}]"}
                                
                                response2 = requests.post(
                                    url2, 
                                    headers=headers, 
                                    cookies=cookies_dict, 
                                    data=data2
                                )
                                
                                if response2.status_code == 200:
                                    logger.info(f"Successfully accepted message request for thread {thread_id} (approve_multiple)")
                                    accepted_count += 1
                                else:
                                    logger.error(f"All methods failed. Status: {response2.status_code}, Response: {response2.text}")
                            
                            except Exception as e2:
                                logger.error(f"Alternative method failed too: {e2}")
                
                return accepted_count
            except Exception as e:
                logger.error(f"Error handling pending requests: {e}")
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