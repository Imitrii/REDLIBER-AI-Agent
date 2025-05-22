"""
Ядро мультиплатформенной системы ИИ-ассистента
Обновлено для поддержки Telegram и кросс-платформенного взаимодействия
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from ..core.config import get_settings, is_platform_enabled
from ..services.chatgpt_service import ChatGPTService
from ..models.database import get_db_session, Client, Message, Conversation
from ..adapters.base import MessengerAdapter


class CoreSystem:
    """Основная система управления мультиплатформенным ИИ-ассистентом"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        
        # Адаптеры платформ
        self.adapters: Dict[str, MessengerAdapter] = {}
        
        # Сервисы
        self.chatgpt_service = ChatGPTService()
        
        # Состояние системы
        self.is_running = False
        self.active_conversations: Dict[str, Dict] = {}
        
        # Статистика
        self.statistics = {
            'total_messages_sent': 0,
            'total_messages_received': 0,
            'active_conversations': 0,
            'total_clients': 0,
            'start_time': None
        }
        
        self.logger.info("Core system initialized")
    
    async def initialize(self):
        """Инициализация системы"""
        try:
            self.logger.info("Initializing core system...")
            
            # Инициализация ChatGPT сервиса
            await self.chatgpt_service.initialize()
            
            # Инициализация адаптеров для активных платформ
            await self._initialize_adapters()
            
            self.statistics['start_time'] = datetime.now()
            self.logger.info("Core system initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize core system: {e}")
            raise
    
    async def _initialize_adapters(self):
        """Инициализация адаптеров для активных платформ"""
        enabled_platforms = self.settings.enabled_platforms_list
        
        for platform in enabled_platforms:
            try:
                if platform == "instagram":
                    await self._initialize_instagram_adapter()
                elif platform == "telegram":
                    await self._initialize_telegram_adapter()
                elif platform == "whatsapp":
                    await self._initialize_whatsapp_adapter()
                else:
                    self.logger.warning(f"Unknown platform: {platform}")
                    
            except Exception as e:
                self.logger.error(f"Failed to initialize {platform} adapter: {e}")
    
    async def _initialize_instagram_adapter(self):
        """Инициализация Instagram адаптера"""
        try:
            from ..adapters.instagram import InstagramAdapter
            
            adapter = InstagramAdapter(
                username=self.settings.INSTAGRAM_USERNAME,
                password=self.settings.INSTAGRAM_PASSWORD
            )
            
            if await adapter.initialize():
                self.adapters['instagram'] = adapter
                self.logger.info("Instagram adapter initialized")
            else:
                self.logger.error("Failed to initialize Instagram adapter")
                
        except ImportError:
            self.logger.error("Instagram adapter not available")
        except Exception as e:
            self.logger.error(f"Error initializing Instagram adapter: {e}")
    
    async def _initialize_telegram_adapter(self):
        """Инициализация Telegram адаптера"""
        try:
            from ..adapters.telegram import TelegramAdapter
            
            if not self.settings.TELEGRAM_BOT_TOKEN:
                self.logger.warning("Telegram bot token not provided")
                return
            
            adapter = TelegramAdapter(bot_token=self.settings.TELEGRAM_BOT_TOKEN)
            
            if await adapter.initialize():
                self.adapters['telegram'] = adapter
                self.logger.info("Telegram adapter initialized")
            else:
                self.logger.error("Failed to initialize Telegram adapter")
                
        except Exception as e:
            self.logger.error(f"Error initializing Telegram adapter: {e}")
    
    async def _initialize_whatsapp_adapter(self):
        """Инициализация WhatsApp адаптера (заглушка для будущего)"""
        self.logger.info("WhatsApp adapter not implemented yet")
    
    async def start(self):
        """Запуск системы"""
        try:
            self.logger.info("Starting core system...")
            
            # Запуск всех адаптеров
            for platform, adapter in self.adapters.items():
                self.logger.info(f"Starting {platform} adapter...")
                if await adapter.start():
                    self.logger.info(f"{platform} adapter started successfully")
                else:
                    self.logger.error(f"Failed to start {platform} adapter")
            
            self.is_running = True
            self.logger.info("Core system started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start core system: {e}")
            raise
    
    async def stop(self):
        """Остановка системы"""
        try:
            self.logger.info("Stopping core system...")
            
            # Остановка всех адаптеров
            for platform, adapter in self.adapters.items():
                self.logger.info(f"Stopping {platform} adapter...")
                await adapter.stop()
            
            self.is_running = False
            self.logger.info("Core system stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping core system: {e}")
    
    async def process_message(self, platform: str, user_id: str, message_text: str, 
                             user_info: Dict = None) -> bool:
        """
        Обработка входящего сообщения
        Args:
            platform: Платформа (instagram, telegram, whatsapp)
            user_id: ID пользователя на платформе
            message_text: Текст сообщения
            user_info: Дополнительная информация о пользователе
        Returns:
            bool: True если сообщение обработано успешно
        """
        try:
            self.logger.info(f"Processing message from {platform}:{user_id}")
            
            # Получение или создание клиента
            client_id = await self._get_or_create_client(platform, user_id, user_info)
            
            # Сохранение входящего сообщения
            await self._save_message(client_id, message_text, is_outgoing=False)
            
            # Обновление статистики
            self.statistics['total_messages_received'] += 1
            
            # Проверка на негативные реакции
            if self._is_negative_response(message_text):
                await self._handle_negative_response(platform, user_id, client_id)
                return True
            
            # Получение контекста разговора
            conversation_context = await self._get_conversation_context(client_id)
            
            # Получаем информацию о клиенте для промпта
            client_info = await self._get_client_info(client_id)
            
            # Генерация ответа через ChatGPT
            response = await self._generate_response(
                message_text, 
                conversation_context, 
                client_info, 
                platform
            )
            
            if response:
                # Отправка ответа
                success = await self._send_response(platform, user_id, response)
                
                if success:
                    # Сохранение исходящего сообщения
                    await self._save_message(client_id, response, is_outgoing=True)
                    self.statistics['total_messages_sent'] += 1
                    
                    # Обновление статуса клиента
                    await self._update_client_status(client_id, message_text, response)
                
                return success
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return False
    
    async def _get_or_create_client(self, platform: str, user_id: str, 
                                   user_info: Dict = None) -> int:
        """Получение или создание клиента, возвращает ID"""
        session = get_db_session()
        
        try:
            # Поиск существующего клиента
            client = session.query(Client).filter_by(
                platform_id=user_id,
                platform=platform
            ).first()
            
            if not client:
                # Создание нового клиента
                client = Client(
                    platform_id=user_id,
                    platform=platform,
                    username=user_info.get('username', '') if user_info else '',
                    first_name=user_info.get('first_name', '') if user_info else '',
                    last_name=user_info.get('last_name', '') if user_info else '',
                    status='new',
                    created_at=datetime.now()
                )
                session.add(client)
                session.commit()
                
                self.statistics['total_clients'] += 1
                self.logger.info(f"Created new client: {platform}:{user_id}")
                
                client_id = client.id
            else:
                # Обновление времени последней активности
                client.last_activity = datetime.now()
                if user_info:
                    client.username = user_info.get('username', client.username)
                    client.first_name = user_info.get('first_name', client.first_name)
                    client.last_name = user_info.get('last_name', client.last_name)
                session.commit()
                
                client_id = client.id
            
            return client_id
            
        finally:
            session.close()
    
    async def _get_client_info(self, client_id: int) -> Dict:
        """Получение информации о клиенте"""
        session = get_db_session()
        
        try:
            client = session.query(Client).get(client_id)
            if client:
                return {
                    'id': client.id,
                    'first_name': client.first_name,
                    'last_name': client.last_name,
                    'username': client.username,
                    'status': client.status
                }
            return {}
            
        finally:
            session.close()
    
    async def _save_message(self, client_id: int, message_text: str, is_outgoing: bool):
        """Сохранение сообщения в базу данных"""
        session = get_db_session()
        
        try:
            message = Message(
                client_id=client_id,
                message_text=message_text,
                is_outgoing=is_outgoing,
                created_at=datetime.now()
            )
            session.add(message)
            session.commit()
            
        finally:
            session.close()
    
    async def _get_conversation_context(self, client_id: int, limit: int = 10) -> List[Dict]:
        """Получение контекста разговора"""
        session = get_db_session()
        
        try:
            messages = session.query(Message).filter_by(
                client_id=client_id
            ).order_by(Message.created_at.desc()).limit(limit).all()
            
            context = []
            for message in reversed(messages):
                context.append({
                    'role': 'assistant' if message.is_outgoing else 'user',
                    'content': message.message_text,
                    'timestamp': message.created_at.isoformat()
                })
            
            return context
            
        finally:
            session.close()
    
    async def _generate_response(self, message_text: str, context: List[Dict], 
                                client_info: Dict, platform: str) -> Optional[str]:
        """Генерация ответа через ChatGPT"""
        try:
            # Подготовка промпта с учетом платформы
            system_prompt = self._prepare_system_prompt(platform, client_info)
            
            # Генерация ответа
            response = await self.chatgpt_service.generate_response(
                message=message_text,
                context=context,
                system_prompt=system_prompt
            )
            
            # Адаптация ответа под платформу
            adapted_response = self._adapt_response_for_platform(response, platform)
            
            return adapted_response
            
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return None
    
    def _prepare_system_prompt(self, platform: str, client_info: Dict) -> str:
        """Подготовка системного промпта с учетом платформы"""
        base_prompt = self.settings.SYSTEM_PROMPT
        
        # Адаптация под платформу
        if platform == "telegram":
            platform_prompt = " Используй HTML-форматирование (жирный шрифт, курсив). Можешь предлагать кнопки для важных действий."
        elif platform == "instagram":
            platform_prompt = " Используй эмодзи и неформальный стиль. Пиши коротко и ярко."
        elif platform == "whatsapp":
            platform_prompt = " Более формальный стиль. Будь вежлив и профессионален."
        else:
            platform_prompt = ""
        
        # Персонализация под клиента
        client_prompt = ""
        if client_info.get('first_name'):
            client_prompt = f" Клиента зовут {client_info['first_name']}."
        
        return base_prompt + platform_prompt + client_prompt
    
    def _adapt_response_for_platform(self, response: str, platform: str) -> str:
        """Адаптация ответа под особенности платформы"""
        if platform == "telegram":
            # Для Telegram можем добавить HTML-форматирование
            return response
        elif platform == "instagram":
            # Для Instagram убираем излишнее форматирование
            return response.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
        elif platform == "whatsapp":
            # Для WhatsApp минимальное форматирование
            return response.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
        
        return response
    
    async def _send_response(self, platform: str, user_id: str, response: str) -> bool:
        """Отправка ответа через соответствующий адаптер"""
        if platform not in self.adapters:
            self.logger.error(f"Adapter for {platform} not available")
            return False
        
        adapter = self.adapters[platform]
        
        # Для Telegram можем добавить кнопки
        kwargs = {}
        if platform == "telegram" and "встреча" in response.lower():
            kwargs['buttons'] = [
                [{"text": "Записаться на встречу", "callback_data": "schedule_meeting"}],
                [{"text": "Узнать больше", "callback_data": "learn_more"}]
            ]
        
        # Отправляем сообщение через адаптер
        result = await adapter.send_message(user_id, response, **kwargs)
        return result.get('success', False) if isinstance(result, dict) else bool(result)
    
    def _is_negative_response(self, message: str) -> bool:
        """Проверка на негативную реакцию"""
        negative_keywords = [
            'нет', 'неинтересно', 'не интересует', 'не пиши', 'отстань',
            'не надо', 'удали', 'блок', 'спам', 'не беспокой'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in negative_keywords)
    
    async def _handle_negative_response(self, platform: str, user_id: str, client_id: int):
        """Обработка негативной реакции"""
        # Используем обычный текст вместо эмодзи для избежания проблем с кодировкой
        farewell_message = "Понял, больше не буду беспокоить. Хорошего дня!"
        
        await self._send_response(platform, user_id, farewell_message)
        
        # Обновление статуса клиента
        session = get_db_session()
        try:
            client = session.query(Client).get(client_id)
            if client:
                client.status = 'rejected'
                session.commit()
        finally:
            session.close()
    
    async def _update_client_status(self, client_id: int, user_message: str, bot_response: str):
        """Обновление статуса клиента на основе диалога"""
        session = get_db_session()
        
        try:
            client = session.query(Client).get(client_id)
            if not client:
                return
            
            # Простая логика определения статуса
            if "встреча" in user_message.lower() or "записаться" in user_message.lower():
                new_status = 'interested'
            elif len(user_message) > 50:  # Развернутый ответ
                new_status = 'engaged'
            elif client.status == 'new':
                new_status = 'contacted'
            else:
                new_status = client.status
            
            if new_status != client.status:
                client.status = new_status
                session.commit()
                self.logger.info(f"Client {client_id} status updated to {new_status}")
                
        finally:
            session.close()
    
    async def get_system_statistics(self) -> Dict[str, Any]:
        """Получение статистики системы"""
        # Статистика адаптеров
        adapter_stats = {}
        for platform, adapter in self.adapters.items():
            adapter_stats[platform] = adapter.get_statistics()
        
        return {
            'system': self.statistics,
            'adapters': adapter_stats,
            'is_running': self.is_running,
            'enabled_platforms': self.settings.enabled_platforms_list
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Проверка состояния системы"""
        adapter_health = {}
        overall_healthy = True
        
        for platform, adapter in self.adapters.items():
            health = await adapter.health_check()
            adapter_health[platform] = health
            if not health.get('healthy', False):
                overall_healthy = False
        
        return {
            'healthy': overall_healthy and self.is_running,
            'system_running': self.is_running,
            'adapters': adapter_health,
            'statistics': self.statistics
        }


# Глобальный экземпляр системы
_core_system: Optional[CoreSystem] = None


def get_core_system() -> CoreSystem:
    """Получение экземпляра основной системы (Singleton)"""
    global _core_system
    if _core_system is None:
        _core_system = CoreSystem()
    return _core_system