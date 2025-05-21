from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

class MessengerAdapter(ABC):
    """
    Абстрактный базовый класс для адаптеров мессенджеров.
    Все конкретные адаптеры (Instagram, Telegram, WhatsApp) должны реализовывать эти методы.
    """
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Аутентификация в сервисе мессенджера"""
        pass
    
    @abstractmethod
    async def send_message(self, recipient_id: str, message: str) -> Dict[str, Any]:
        """Отправка сообщения пользователю"""
        pass
    
    @abstractmethod
    async def receive_messages(self) -> List[Dict[str, Any]]:
        """Получение новых сообщений"""
        pass
    
    @abstractmethod
    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Получение информации о пользователе"""
        pass
    
    @abstractmethod
    async def is_within_limits(self) -> bool:
        """Проверка, не превышены ли лимиты использования API"""
        pass
