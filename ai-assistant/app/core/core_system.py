import logging
import time
import asyncio
from datetime import datetime

from app.adapters.instagram import InstagramAdapter
from app.services.chatgpt_service import ChatGPTService
from app.models.database import SessionLocal, Client, Message

class CoreSystem:
    """Core system for the AI assistant."""
    
    def __init__(self, config):
        """Initialize the core system."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.messenger_type = config["app"]["messenger"]
        self.messenger = None
        self.chatgpt = None
        self.running = False
        self.user_states = {}  # Track state for each user
    
    async def start(self):
        """Start the AI assistant."""
        try:
            # Initialize messenger adapter
            self.logger.info("Initializing messenger adapter")
            if self.messenger_type == "instagram":
                self.messenger = InstagramAdapter()
            else:
                self.logger.error(f"Unsupported messenger type: {self.messenger_type}")
                return False

            # Authenticate with the messenger platform
            self.logger.info(f"Authenticating with {self.messenger_type}")
            auth_success = await self.messenger.authenticate()
            if not auth_success:
                self.logger.error(f"Failed to authenticate with {self.messenger_type}")
                return False

            # Initialize ChatGPT service
            self.logger.info("Initializing ChatGPT service")
            self.chatgpt = ChatGPTService()

            # Set initial state
            self.running = True
            self.logger.info("Core system started successfully")
            
            # Start processing messages
            asyncio.create_task(self.message_processing_loop())
            
            return True
        except Exception as e:
            self.logger.error(f"Error starting AI assistant: {str(e)}")
            return False
    
    async def stop(self):
        """Stop the AI assistant."""
        self.logger.info("Stopping AI assistant...")
        self.running = False
    
    def is_within_working_hours(self):
        """Check if current time is within working hours."""
        current_hour = datetime.now().hour
        start_hour = self.config["app"]["working_hours"]["start"]
        end_hour = self.config["app"]["working_hours"]["end"]
        return start_hour <= current_hour < end_hour
    
    async def message_processing_loop(self):
        """Основной цикл обработки сообщений"""
        while self.running:
            try:
                # Проверка запросов на переписку (для Instagram)
                if self.messenger_type == "instagram":
                    accepted_count = await self.messenger.accept_pending_requests()
                    if accepted_count > 0:
                        self.logger.info(f"Accepted {accepted_count} pending message requests")
                
                # Получаем новые сообщения
                messages = await self.messenger.receive_messages()
                
                if messages:
                    self.logger.info(f"Received {len(messages)} new messages")
                    
                    # Обрабатываем каждое сообщение
                    for message in messages:
                        await self.process_message(
                            platform=self.messenger_type,
                            user_id=message["user_id"],
                            message_text=message["text"],
                            message_id=message["message_id"],
                            thread_id=message.get("thread_id")
                        )
                
                # Пауза между проверками сообщений
                await asyncio.sleep(60)  # Проверяем сообщения каждую минуту
                
            except Exception as e:
                self.logger.error(f"Error in message processing loop: {e}")
                # Пауза перед следующей попыткой в случае ошибки
                await asyncio.sleep(300)  # 5 минут
    
    async def process_message(self, platform, user_id, message_text, message_id, thread_id=None):
        """
        Обработка входящего сообщения

        Args:
            platform: Платформа (instagram, telegram, whatsapp)
            user_id: ID пользователя на платформе
            message_text: Текст сообщения
            message_id: ID сообщения
            thread_id: ID треда/чата (опционально)
        """
        try:
            # Получаем или создаем запись о клиенте
            client = await self._get_or_create_client(platform, user_id)

            # Сохраняем входящее сообщение
            await self._save_message(client["id"], "incoming", message_text)

            # Проверяем на ключевые фразы отказа
            if self._is_rejection_message(message_text):
                self.logger.info(f"Rejection detected from user {user_id}")
                # Отправляем вежливое прощание
                goodbye_message = "Спасибо за общение! Если у вас возникнут вопросы в будущем, буду рад помочь."
                
                if platform == "instagram":
                    await self.messenger.send_message(user_id, goodbye_message)
                
                await self._save_message(client["id"], "outgoing", goodbye_message)
                return

            # Получаем контекст для ChatGPT
            context = await self._get_client_context(client["id"])

            # Получаем ответ от ChatGPT
            response = await self.chatgpt.get_response(user_id, message_text, context)

            # Отправляем ответ клиенту
            if platform == "instagram":
                # Проверяем, можно ли отправить сообщение с учетом лимитов
                if await self.messenger.is_within_limits():
                    result = await self.messenger.send_message(user_id, response)
                    if result.get("success", False):
                        # Сохраняем исходящее сообщение
                        await self._save_message(client["id"], "outgoing", response)
                    else:
                        self.logger.warning(f"Failed to send message to {user_id}: {result.get('error')}")
                else:
                    self.logger.warning(f"Message not sent to {user_id} due to rate limits")

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    async def _get_or_create_client(self, platform, platform_id):
        """
        Получение или создание записи о клиенте
        """
        db = SessionLocal()
        try:
            # Ищем существующего клиента
            client = db.query(Client).filter(
                Client.platform == platform,
                Client.platform_id == platform_id
            ).first()

            if not client:
                # Если клиент не найден, создаем новую запись
                client = Client(
                    platform=platform,
                    platform_id=platform_id
                )

                # Пытаемся получить дополнительную информацию о пользователе
                if platform == "instagram":
                    user_info = await self.messenger.get_user_info(platform_id)
                    if user_info:
                        client.username = user_info.get("username")
                        client.full_name = user_info.get("full_name")

                db.add(client)
                db.commit()
                db.refresh(client)
                self.logger.info(f"Created new client record for {platform}:{platform_id}")

            return {
                "id": client.id,
                "platform": client.platform,
                "platform_id": client.platform_id,
                "username": client.username,
                "full_name": client.full_name
            }
        finally:
            db.close()

    async def _save_message(self, client_id, direction, content):
        """
        Сохранение сообщения в базу данных
        """
        db = SessionLocal()
        try:
            message = Message(
                client_id=client_id,
                direction=direction,
                content=content
            )
            db.add(message)
            db.commit()
        finally:
            db.close()

    async def _get_client_context(self, client_id):
        """
        Получение контекста диалога с клиентом
        """
        db = SessionLocal()
        try:
            # Получаем информацию о клиенте
            client = db.query(Client).filter(Client.id == client_id).first()

            # Получаем историю сообщений (последние 10)
            messages = db.query(Message).filter(
                Message.client_id == client_id
            ).order_by(Message.timestamp.desc()).limit(10).all()

            # Формируем контекст
            context = {
                "client_info": {
                    "username": client.username,
                    "full_name": client.full_name,
                    "platform": client.platform,
                    "created_at": client.created_at.isoformat() if client.created_at else None
                },
                # Информация о продукте
                "product_info": """
                Мы — книжное издательство полного цикла. Создаём готовые книги «под ключ»: редактура, дизайн обложки, верстка, присвоение ISBN, выпуск электронной и печатной версий, маркетинговое сопровождение и дистрибуция по ключевым площадкам.
                Наша цель — помогать авторам реализовать свои идеи в комфортном, прозрачном формате сотрудничества и доводить их рукописи до коммерчески успешной книги.
                Первая консультация бесплатна и проходит онлайн — видеовстреча в Zoom с экспертом издательства.
                """,
                # Инструкции по общению
                "instructions": """
                1. Представься и узнай имя клиента
                2. Выяви, на какой стадии находится рукопись клиента
                3. Расскажи о преимуществах работы с нашим издательством
                4. Предложи записаться на бесплатную онлайн-консультацию
                5. Если клиент согласен, предложи удобное время для Zoom-встречи
                6. Если клиент не готов, предложи прислать полезные материалы
                """
            }

            return context
        finally:
            db.close()

    def _is_rejection_message(self, message):
        """
        Проверка, является ли сообщение отказом
        """
        rejection_phrases = [
            "нет", "неинтересно", "не интересует", "не пиши мне",
            "отстань", "отписаться", "отпишись", "не хочу", "не беспокой",
            "заблокирую", "спам"
        ]

        message_lower = message.lower()
        for phrase in rejection_phrases:
            if phrase in message_lower:
                return True

        return False
