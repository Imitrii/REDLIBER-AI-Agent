import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Any, List

from app.adapters.instagram import InstagramAdapter
from app.services.chatgpt_service import ChatGPTService
from app.models.database import SessionLocal, Message

logger = logging.getLogger(__name__)

class CoreSystem:
    """
    Ядро системы, координирующее работу всех компонентов
    """
    
    def __init__(self):
        """Инициализация ядра системы"""
        logger.info("Initializing messenger adapter")
        self.instagram_adapter = InstagramAdapter()
        
        logger.info("Initializing ChatGPT service")
        self.chatgpt_service = ChatGPTService()
        
        self.running = False
        
    async def start(self) -> bool:
        """Запуск системы"""
        try:
            logger.info("Starting core system")
            
            # Пытаемся аутентифицироваться в Instagram
            logger.info("Authenticating with instagram")
            auth_success = await self.instagram_adapter.authenticate()
            
            if not auth_success:
                # Проверяем статус аккаунта
                status = self.instagram_adapter.get_account_status()
                if status.get("challenge_required"):
                    logger.warning("Instagram account requires challenge verification")
                    logger.warning("Please resolve the challenge through Instagram web/app")
                    logger.warning("System will continue in limited mode")
                else:
                    logger.error("Failed to authenticate with Instagram")
                    return False
            
            self.running = True
            logger.info("Core system started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start core system: {e}")
            return False
    
    async def stop(self):
        """Остановка системы"""
        logger.info("Stopping core system")
        self.running = False
    
    async def process_message(self, message_data: Dict[str, Any]) -> bool:
        """
        Обработка входящего сообщения
        
        Args:
            message_data: Данные сообщения
            
        Returns:
            bool: Успешно ли обработано сообщение
        """
        try:
            user_id = message_data.get("user_id")
            text = message_data.get("text", "")
            thread_id = message_data.get("thread_id")
            
            if not user_id or not text or not thread_id:
                logger.warning(f"Incomplete message data: {message_data}")
                return False
            
            logger.info(f"Processing message from user {user_id}: {text[:50]}...")
            
            # Получаем информацию о пользователе для контекста
            user_info = await self.instagram_adapter.get_user_info(user_id)
            
            # Формируем контекст для ChatGPT
            context = {
                "user_info": user_info,
                "platform": "instagram",
                "product_info": "Мы — книжное издательство полного цикла. Создаём готовые книги «под ключ»: редактура, дизайн обложки, верстка, присвоение ISBN, выпуск электронной и печатной версий, маркетинговое сопровождение и дистрибуция по ключевым площадкам. Наша цель — помогать авторам реализовать свои идеи в комфортном, прозрачном формате сотрудничества и доводить их рукописи до коммерчески успешной книги. Первая консультация бесплатна и проходит онлайн — видеовстреча в Zoom с экспертом издательства.",
                "sales_script": """
1. Поприветствуйте клиента дружелюбно
2. Выясните его потребности в издании книги
3. Предложите бесплатную консультацию в Zoom
4. Получите контакты для связи
"""
            }
            
            # Получаем ответ от ChatGPT
            response = await self.chatgpt_service.get_response(str(user_id), text, context)
            
            # Отмечаем сообщение как прочитанное
            await self.instagram_adapter.mark_seen(thread_id)
            
            # Добавляем задержку перед ответом для естественности
            await asyncio.sleep(2)
            
            # Отправляем ответ
            send_result = await self.instagram_adapter.send_message(user_id, response)
            
            if send_result.get("success"):
                logger.info(f"Response sent to user {user_id}")
                
                # Сохраняем сообщения в базу данных
                try:
                    db = SessionLocal()
                    # Входящее сообщение
                    db.add(Message(
                        platform="instagram",
                        user_id=str(user_id),
                        message_type="incoming",
                        message_text=text,
                        thread_id=thread_id,
                        timestamp=datetime.now()
                    ))
                    # Исходящее сообщение
                    db.add(Message(
                        platform="instagram",
                        user_id=str(user_id),
                        message_type="outgoing",
                        message_text=response,
                        thread_id=thread_id,
                        timestamp=datetime.now()
                    ))
                    db.commit()
                    logger.info("Messages saved to database")
                except Exception as db_error:
                    logger.error(f"Error saving messages to database: {db_error}")
                finally:
                    db.close()
                    
                return True
            else:
                logger.error(f"Failed to send response: {send_result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return False
    
    async def run_cycle(self) -> None:
        """Один цикл обработки сообщений"""
        try:
            # Проверяем статус аккаунта
            status = self.instagram_adapter.get_account_status()
            
            if status.get("challenge_required"):
                logger.warning("Instagram account requires challenge verification - skipping message processing")
                return
            
            if not status.get("authenticated"):
                logger.info("Not authenticated, attempting authentication")
                auth_success = await self.instagram_adapter.authenticate()
                if not auth_success:
                    logger.warning("Authentication failed, skipping this cycle")
                    return
            
            # Получаем новые сообщения
            messages = await self.instagram_adapter.receive_messages()
            
            if messages:
                logger.info(f"Received {len(messages)} new messages")
                
                # Обрабатываем каждое сообщение
                for message in messages:
                    success = await self.process_message(message)
                    if success:
                        # Добавляем паузу между обработкой сообщений
                        await asyncio.sleep(30)  # 30 секунд между сообщениями
            else:
                logger.info("No new messages to process")
                
        except Exception as e:
            logger.error(f"Error in run cycle: {e}")
    
    async def run(self) -> None:
        """
        Основной цикл работы системы
        """
        try:
            # Запускаем систему
            if not await self.start():
                logger.error("Failed to start system")
                return
            
            logger.info("Starting main processing loop")
            
            # Обрабатываем существующие непрочитанные сообщения
            logger.info("Processing existing unread messages")
            await self.run_cycle()
            
            # Основной цикл
            while self.running:
                try:
                    await self.run_cycle()
                    
                    # Пауза между циклами (1-2 минуты с имитацией человеческого поведения)
                    wait_time = random.uniform(60, 120)  # От 1 до 2 минут
                    logger.info(f"Waiting {wait_time:.1f} seconds before next cycle")
                    await asyncio.sleep(wait_time)
                    
                except KeyboardInterrupt:
                    logger.info("Received interrupt signal")
                    break
                except Exception as cycle_error:
                    logger.error(f"Error in main cycle: {cycle_error}")
                    # Пауза перед повторной попыткой в случае ошибки (5-10 минут)
                    error_wait = random.uniform(300, 600)
                    logger.info(f"Waiting {error_wait/60:.1f} minutes before retry due to error")
                    await asyncio.sleep(error_wait)
                    
        except Exception as e:
            logger.error(f"Critical error in run method: {e}")
        finally:
            await self.stop()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Получить статус системы"""
        instagram_status = self.instagram_adapter.get_account_status()
        
        return {
            "system_running": self.running,
            "instagram_status": instagram_status,
            "current_time": datetime.now().isoformat()
        }