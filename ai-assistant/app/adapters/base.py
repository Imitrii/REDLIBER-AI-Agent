"""
Базовый абстрактный класс для всех адаптеров мессенджеров
Обновлен для поддержки мультиплатформенной архитектуры с Telegram интеграцией
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime


class MessengerAdapter(ABC):
    """
    Абстрактный базовый класс для адаптеров мессенджеров.
    Все конкретные адаптеры (Instagram, Telegram, WhatsApp) должны реализовывать эти методы.
    """
    
    def __init__(self):
        """Инициализация базового адаптера"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.is_authenticated = False
        self.is_running = False
        
        # Статистика работы адаптера
        self.statistics = {
            'sent_messages': 0,
            'received_messages': 0,
            'errors': 0,
            'start_time': None,
            'last_activity': None
        }
        
        # Настройки лимитов (могут быть переопределены в наследниках)
        self.rate_limits = {
            'messages_per_hour': 100,
            'messages_per_day': 1000,
            'min_delay_between_messages': 1.0
        }
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Аутентификация в сервисе мессенджера
        Returns:
            bool: True если аутентификация прошла успешно
        """
        pass
    
    @abstractmethod
    async def send_message(self, recipient_id: str, message: str, **kwargs) -> Dict[str, Any]:
        """
        Отправка сообщения пользователю
        Args:
            recipient_id: ID получателя в мессенджере
            message: Текст сообщения
            **kwargs: Дополнительные параметры (кнопки, медиа и т.д.)
        Returns:
            Dict: Результат отправки с метаданными
        """
        pass
    
    @abstractmethod
    async def receive_messages(self) -> List[Dict[str, Any]]:
        """
        Получение новых сообщений
        Returns:
            List[Dict]: Список новых сообщений с метаданными
        """
        pass
    
    @abstractmethod
    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """
        Получение информации о пользователе
        Args:
            user_id: ID пользователя в мессенджере
        Returns:
            Dict: Информация о пользователе
        """
        pass
    
    @abstractmethod
    async def is_within_limits(self) -> bool:
        """
        Проверка, не превышены ли лимиты использования API
        Returns:
            bool: True если лимиты не превышены
        """
        pass
    
    # Новые абстрактные методы для расширенной функциональности
    
    @abstractmethod
    async def start(self) -> bool:
        """
        Запуск адаптера и начало обработки сообщений
        Returns:
            bool: True если запуск прошел успешно
        """
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """
        Остановка адаптера
        Returns:
            bool: True если остановка прошла успешно
        """
        pass
    
    @abstractmethod
    async def get_platform_info(self) -> Dict[str, Any]:
        """
        Получение информации о платформе и её состоянии
        Returns:
            Dict: Информация о платформе
        """
        pass
    
    # Методы с базовой реализацией (могут быть переопределены)
    
    async def send_media(self, recipient_id: str, media_path: str, 
                        caption: str = "", **kwargs) -> Dict[str, Any]:
        """
        Отправка медиафайла пользователю
        Args:
            recipient_id: ID получателя
            media_path: Путь к медиафайлу
            caption: Подпись к медиафайлу
            **kwargs: Дополнительные параметры
        Returns:
            Dict: Результат отправки
        """
        self.logger.warning(f"Media sending not implemented for {self.__class__.__name__}")
        return {
            'success': False,
            'error': 'Media sending not implemented',
            'platform': self.get_platform_name()
        }
    
    async def mark_as_read(self, message_id: str) -> bool:
        """
        Отметка сообщения как прочитанного
        Args:
            message_id: ID сообщения
        Returns:
            bool: True если успешно отмечено
        """
        self.logger.debug(f"Mark as read not implemented for {self.__class__.__name__}")
        return True
    
    async def block_user(self, user_id: str) -> bool:
        """
        Блокировка пользователя
        Args:
            user_id: ID пользователя
        Returns:
            bool: True если пользователь заблокирован
        """
        self.logger.warning(f"User blocking not implemented for {self.__class__.__name__}")
        return False
    
    async def unblock_user(self, user_id: str) -> bool:
        """
        Разблокировка пользователя
        Args:
            user_id: ID пользователя
        Returns:
            bool: True если пользователь разблокирован
        """
        self.logger.warning(f"User unblocking not implemented for {self.__class__.__name__}")
        return False
    
    def get_platform_name(self) -> str:
        """
        Получение названия платформы
        Returns:
            str: Название платформы
        """
        class_name = self.__class__.__name__.lower()
        if 'instagram' in class_name:
            return 'instagram'
        elif 'telegram' in class_name:
            return 'telegram'
        elif 'whatsapp' in class_name:
            return 'whatsapp'
        else:
            return 'unknown'
    
    def update_statistics(self, action: str, increment: int = 1):
        """
        Обновление статистики работы адаптера
        Args:
            action: Тип действия ('sent', 'received', 'error')
            increment: На сколько увеличить счетчик
        """
        current_time = datetime.now()
        
        if action == 'sent':
            self.statistics['sent_messages'] += increment
        elif action == 'received':
            self.statistics['received_messages'] += increment
        elif action == 'error':
            self.statistics['errors'] += increment
        
        self.statistics['last_activity'] = current_time
        
        if not self.statistics['start_time']:
            self.statistics['start_time'] = current_time
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики работы адаптера
        Returns:
            Dict: Статистические данные
        """
        return {
            'platform': self.get_platform_name(),
            'is_authenticated': self.is_authenticated,
            'is_running': self.is_running,
            **self.statistics
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Проверка состояния здоровья адаптера
        Returns:
            Dict: Информация о состоянии адаптера
        """
        try:
            # Базовые проверки
            platform_info = await self.get_platform_info()
            within_limits = await self.is_within_limits()
            
            is_healthy = (
                self.is_authenticated and 
                self.is_running and 
                within_limits
            )
            
            return {
                'healthy': is_healthy,
                'authenticated': self.is_authenticated,
                'running': self.is_running,
                'within_limits': within_limits,
                'platform': self.get_platform_name(),
                'platform_info': platform_info,
                'statistics': self.get_statistics(),
                'last_check': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed for {self.__class__.__name__}: {e}")
            return {
                'healthy': False,
                'error': str(e),
                'platform': self.get_platform_name(),
                'last_check': datetime.now().isoformat()
            }
    
    async def initialize(self) -> bool:
        """
        Инициализация адаптера
        Базовая реализация - может быть переопределена
        Returns:
            bool: True если инициализация прошла успешно
        """
        try:
            self.logger.info(f"Initializing {self.__class__.__name__}...")
            
            # Попытка аутентификации
            auth_result = await self.authenticate()
            
            if auth_result:
                self.is_authenticated = True
                self.logger.info(f"{self.__class__.__name__} initialized successfully")
                return True
            else:
                self.logger.error(f"Authentication failed for {self.__class__.__name__}")
                return False
                
        except Exception as e:
            self.logger.error(f"Initialization failed for {self.__class__.__name__}: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """
        Корректное завершение работы адаптера
        Returns:
            bool: True если завершение прошло успешно
        """
        try:
            self.logger.info(f"Shutting down {self.__class__.__name__}...")
            
            # Остановка адаптера
            stop_result = await self.stop()
            
            # Сброс состояния
            self.is_running = False
            self.is_authenticated = False
            
            self.logger.info(f"{self.__class__.__name__} shut down {'successfully' if stop_result else 'with errors'}")
            return stop_result
            
        except Exception as e:
            self.logger.error(f"Shutdown failed for {self.__class__.__name__}: {e}")
            return False
    
    def set_rate_limits(self, **limits):
        """
        Установка лимитов для адаптера
        Args:
            **limits: Словарь с лимитами (messages_per_hour, messages_per_day, etc.)
        """
        self.rate_limits.update(limits)
        self.logger.info(f"Rate limits updated for {self.__class__.__name__}: {self.rate_limits}")
    
    def get_rate_limits(self) -> Dict[str, Any]:
        """
        Получение текущих лимитов
        Returns:
            Dict: Текущие лимиты
        """
        return self.rate_limits.copy()
    
    async def validate_message(self, message: str) -> tuple[bool, Optional[str]]:
        """
        Валидация сообщения перед отправкой
        Args:
            message: Текст сообщения
        Returns:
            tuple: (is_valid, error_message)
        """
        if not message or not message.strip():
            return False, "Message is empty"
        
        if len(message) > 4096:  # Общий лимит для большинства платформ
            return False, "Message too long"
        
        return True, None
    
    def __str__(self) -> str:
        """Строковое представление адаптера"""
        return f"{self.__class__.__name__}(platform={self.get_platform_name()}, authenticated={self.is_authenticated}, running={self.is_running})"
    
    def __repr__(self) -> str:
        """Подробное представление адаптера"""
        return self.__str__()


# Дополнительные вспомогательные классы и функции

class AdapterError(Exception):
    """Базовое исключение для ошибок адаптеров"""
    def __init__(self, message: str, platform: str = None, error_code: str = None):
        super().__init__(message)
        self.platform = platform
        self.error_code = error_code


class RateLimitError(AdapterError):
    """Исключение для ошибок превышения лимитов"""
    def __init__(self, message: str, platform: str = None, retry_after: int = None):
        super().__init__(message, platform, "RATE_LIMIT")
        self.retry_after = retry_after


class AuthenticationError(AdapterError):
    """Исключение для ошибок аутентификации"""
    def __init__(self, message: str, platform: str = None):
        super().__init__(message, platform, "AUTH_ERROR")


class PlatformError(AdapterError):
    """Исключение для платформо-специфичных ошибок"""
    def __init__(self, message: str, platform: str = None, platform_code: str = None):
        super().__init__(message, platform, "PLATFORM_ERROR")
        self.platform_code = platform_code


def create_message_response(success: bool, message_id: str = None, 
                          error: str = None, platform: str = None, 
                          metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Создание стандартизированного ответа для операций с сообщениями
    Args:
        success: Успешность операции
        message_id: ID отправленного сообщения
        error: Текст ошибки (если есть)
        platform: Название платформы
        metadata: Дополнительные метаданные
    Returns:
        Dict: Стандартизированный ответ
    """
    response = {
        'success': success,
        'timestamp': datetime.now().isoformat(),
        'platform': platform
    }
    
    if success and message_id:
        response['message_id'] = message_id
    
    if not success and error:
        response['error'] = error
    
    if metadata:
        response['metadata'] = metadata
    
    return response