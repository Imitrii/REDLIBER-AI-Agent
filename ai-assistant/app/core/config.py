"""
Конфигурация мультиплатформенного ИИ-ассистента
Обновлено для поддержки Telegram
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Основные настройки
    APP_NAME: str = "AI Assistant"
    VERSION: str = "2.0"  # Обновили версию для поддержки Telegram
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # База данных
    DATABASE_URL: str = "sqlite:///./data/aibot.db"
    
    # OpenAI настройки
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_MAX_TOKENS: int = 1000
    OPENAI_TEMPERATURE: float = 0.7
    
    # Instagram настройки
    INSTAGRAM_USERNAME: str = ""
    INSTAGRAM_PASSWORD: str = ""
    INSTAGRAM_SESSION_FILE: str = "./data/instagram_session.json"
    INSTAGRAM_PROXY: Optional[str] = None
    
    # Telegram настройки
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: Optional[str] = None
    TELEGRAM_WEBHOOK_SECRET: Optional[str] = None
    TELEGRAM_MAX_MESSAGES_PER_SECOND: int = 30
    TELEGRAM_MESSAGE_DELAY: float = 1.0
    
    # WhatsApp настройки (для будущего использования)
    WHATSAPP_PHONE: str = ""
    WHATSAPP_API_KEY: str = ""
    WHATSAPP_WEBHOOK_URL: Optional[str] = None
    
    # Bitrix24 настройки (для будущего использования)
    BITRIX24_DOMAIN: str = ""
    BITRIX24_CLIENT_ID: str = ""
    BITRIX24_CLIENT_SECRET: str = ""
    BITRIX24_ACCESS_TOKEN: str = ""
    
    # Настройки безопасности
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Настройки лимитов
    MAX_MESSAGES_PER_DAY: int = 45  # Для Instagram
    MIN_MESSAGE_INTERVAL_MINUTES: int = 15  # Для Instagram
    WORK_START_HOUR: int = 10  # Начало рабочего дня (МСК)
    WORK_END_HOUR: int = 21    # Конец рабочего дня (МСК)
    
    # Настройки логирования
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"
    LOG_MAX_SIZE: int = 10485760  # 10MB
    LOG_BACKUP_COUNT: int = 5
    
    # Настройки мониторинга
    MONITORING_ENABLED: bool = True
    ANALYTICS_ENABLED: bool = True
    
    # Настройки уведомлений
    NOTIFICATION_EMAIL: str = ""
    SMTP_SERVER: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    
    # Настройки прокси
    USE_PROXY: bool = False
    PROXY_HOST: str = ""
    PROXY_PORT: int = 0
    PROXY_USERNAME: str = ""
    PROXY_PASSWORD: str = ""
    
    # Настройки платформ
    ENABLED_PLATFORMS: list = ["instagram"]  # По умолчанию только Instagram
    DEFAULT_PLATFORM: str = "instagram"
    
    # Настройки ChatGPT промптов
    SYSTEM_PROMPT: str = """Ты профессиональный менеджер по продажам. Веди диалог естественно, 
    используй эмодзи, задавай открытые вопросы. Твоя цель - понять потребности клиента и 
    предложить подходящее решение. Будь дружелюбным и профессиональным."""
    
    GREETING_PROMPT: str = "Поприветствуй клиента дружелюбно и спроси, как дела. Используй эмодзи."
    
    # Настройки сценариев
    MAX_CONVERSATION_LENGTH: int = 50  # Максимальное количество сообщений в диалоге
    CONVERSATION_TIMEOUT_HOURS: int = 24  # Таймаут диалога в часах
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Глобальный экземпляр настроек
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Получение экземпляра настроек (Singleton)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def update_enabled_platforms(platforms: list):
    """Обновление списка активных платформ"""
    settings = get_settings()
    settings.ENABLED_PLATFORMS = platforms


def is_platform_enabled(platform: str) -> bool:
    """Проверка, активна ли платформа"""
    settings = get_settings()
    return platform in settings.ENABLED_PLATFORMS


# Вспомогательные функции для работы с путями
def get_project_root() -> Path:
    """Получение корневой директории проекта"""
    return Path(__file__).parent.parent.parent


def get_data_dir() -> Path:
    """Получение директории для данных"""
    return get_project_root() / "data"


def get_logs_dir() -> Path:
    """Получение директории для логов"""
    return get_project_root() / "logs"


def ensure_directories():
    """Создание необходимых директорий"""
    dirs = [get_data_dir(), get_logs_dir()]
    for dir_path in dirs:
        dir_path.mkdir(exist_ok=True)