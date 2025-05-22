"""
Конфигурация мультиплатформенного ИИ-ассистента
Обновлено для поддержки Google Sheets интеграции
"""

import os
from pathlib import Path
from typing import Optional, List

try:
    # Попытка импорта из pydantic-settings (Pydantic v2)
    from pydantic_settings import BaseSettings
    from pydantic import Field
    HAS_PYDANTIC_SETTINGS = True
except ImportError:
    try:
        # Fallback для старых версий Pydantic
        from pydantic import BaseSettings, Field
        HAS_PYDANTIC_SETTINGS = True
    except ImportError:
        # Если Pydantic не установлен, создаем простую замену
        HAS_PYDANTIC_SETTINGS = False
        class BaseSettings:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        def Field(**kwargs):
            return None


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Основные настройки
    APP_NAME: str = "AI Assistant"
    VERSION: str = "2.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # База данных
    DATABASE_URL: str = "sqlite:///./data/aibot.db"
    
    # OpenAI настройки
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_MAX_TOKENS: int = 1000
    OPENAI_TEMPERATURE: float = 0.7
    
    # Instagram настройки
    INSTAGRAM_USERNAME: str = ""
    INSTAGRAM_PASSWORD: str = ""
    INSTAGRAM_SESSION_FILE: str = "./data/instagram_session.json"
    INSTAGRAM_PROXY: Optional[str] = None
    
    # Instagram лимиты (добавлены недостающие поля)
    instagram_max_messages_per_day: str = "45"
    instagram_min_interval_minutes: str = "15"
    working_hours_start: str = "10"
    working_hours_end: str = "21"
    
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
    
    # Google Sheets настройки
    GOOGLE_SHEETS_CREDENTIALS_FILE: str = "./credentials/google-sheets-credentials.json"
    GOOGLE_SHEETS_SPREADSHEET_ID: str = ""
    
    # Bot настройки
    BOT_NAME: str = "Ассистент"
    SERVICE_TYPE: str = "различными услугами"
    
    # Настройки безопасности
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Настройки лимитов (используем правильные имена)
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
    ENABLED_PLATFORMS: str = "instagram,telegram"
    DEFAULT_PLATFORM: str = "instagram"
    
    # Настройки ChatGPT промптов
    SYSTEM_PROMPT: str = """Ты профессиональный менеджер по продажам. Веди диалог естественно, используй эмодзи, задавай открытые вопросы. Твоя цель - понять потребности клиента и предложить подходящее решение. Будь дружелюбным и профессиональным."""
    
    GREETING_PROMPT: str = "Поприветствуй клиента дружелюбно и спроси, как дела. Используй эмодзи."
    
    # Настройки сценариев
    MAX_CONVERSATION_LENGTH: int = 50
    CONVERSATION_TIMEOUT_HOURS: int = 24
    
    # Настройки планировщика исходящих сообщений
    OUTBOUND_CHECK_INTERVAL: int = 300  # Проверка каждые 5 минут
    OUTBOUND_DAILY_LIMIT_TELEGRAM: int = 50
    OUTBOUND_DAILY_LIMIT_INSTAGRAM: int = 45
    OUTBOUND_WORKING_HOURS_START: int = 10
    OUTBOUND_WORKING_HOURS_END: int = 21
    
    @property
    def enabled_platforms_list(self) -> List[str]:
        """Получение списка активных платформ"""
        if isinstance(self.ENABLED_PLATFORMS, str):
            return [p.strip() for p in self.ENABLED_PLATFORMS.split(',') if p.strip()]
        return self.ENABLED_PLATFORMS if isinstance(self.ENABLED_PLATFORMS, list) else []
    
    @property
    def max_messages_per_day_int(self) -> int:
        """Получение максимального количества сообщений в день как int"""
        try:
            return int(self.instagram_max_messages_per_day)
        except (ValueError, AttributeError):
            return self.MAX_MESSAGES_PER_DAY
    
    @property
    def min_interval_minutes_int(self) -> int:
        """Получение минимального интервала как int"""
        try:
            return int(self.instagram_min_interval_minutes)
        except (ValueError, AttributeError):
            return self.MIN_MESSAGE_INTERVAL_MINUTES
    
    @property
    def work_start_hour_int(self) -> int:
        """Получение часа начала работы как int"""
        try:
            return int(self.working_hours_start)
        except (ValueError, AttributeError):
            return self.WORK_START_HOUR
    
    @property
    def work_end_hour_int(self) -> int:
        """Получение часа окончания работы как int"""
        try:
            return int(self.working_hours_end)
        except (ValueError, AttributeError):
            return self.WORK_END_HOUR
    
    if HAS_PYDANTIC_SETTINGS:
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            # Разрешаем дополнительные поля для совместимости
            extra = "allow"


# Простая версия без Pydantic для совместимости
class SimpleSettings:
    """Упрощенная версия настроек без Pydantic"""
    
    def __init__(self):
        # Настройки по умолчанию
        self.APP_NAME = "AI Assistant"
        self.VERSION = "2.0"
        self.DEBUG = False
        self.ENVIRONMENT = "production"
        
        # OpenAI
        self.OPENAI_API_KEY = ""
        self.OPENAI_MODEL = "gpt-3.5-turbo"
        self.OPENAI_MAX_TOKENS = 1000
        self.OPENAI_TEMPERATURE = 0.7
        
        # Instagram
        self.INSTAGRAM_USERNAME = ""
        self.INSTAGRAM_PASSWORD = ""
        self.INSTAGRAM_SESSION_FILE = "./data/instagram_session.json"
        self.INSTAGRAM_PROXY = None
        
        # Telegram
        self.TELEGRAM_BOT_TOKEN = ""
        self.TELEGRAM_MAX_MESSAGES_PER_SECOND = 30
        self.TELEGRAM_MESSAGE_DELAY = 1.0
        
        # Google Sheets
        self.GOOGLE_SHEETS_CREDENTIALS_FILE = "./credentials/google-sheets-credentials.json"
        self.GOOGLE_SHEETS_SPREADSHEET_ID = ""
        
        # Bot настройки
        self.BOT_NAME = "Ассистент"
        self.SERVICE_TYPE = "различными услугами"
        
        # Лимиты
        self.MAX_MESSAGES_PER_DAY = 45
        self.MIN_MESSAGE_INTERVAL_MINUTES = 15
        self.WORK_START_HOUR = 10
        self.WORK_END_HOUR = 21
        
        # Платформы
        self.ENABLED_PLATFORMS = "instagram,telegram"
        self.DEFAULT_PLATFORM = "instagram"
        
        # Промпты
        self.SYSTEM_PROMPT = "Ты профессиональный менеджер по продажам. Веди диалог естественно, используй эмодзи, задавай открытые вопросы."
        self.GREETING_PROMPT = "Поприветствуй клиента дружелюбно и спроси, как дела."
        
        # Логирование
        self.LOG_LEVEL = "INFO"
        self.LOG_FILE = "./logs/app.log"
        
        # Мониторинг
        self.MONITORING_ENABLED = True
        self.ANALYTICS_ENABLED = True
        
        # Планировщик
        self.OUTBOUND_CHECK_INTERVAL = 300
        self.OUTBOUND_DAILY_LIMIT_TELEGRAM = 50
        self.OUTBOUND_DAILY_LIMIT_INSTAGRAM = 45
        self.OUTBOUND_WORKING_HOURS_START = 10
        self.OUTBOUND_WORKING_HOURS_END = 21
        
        # Загружаем из .env
        self._load_from_env()
    
    def _load_from_env(self):
        """Загрузка настроек из .env файла"""
        env_file = Path(".env")
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        
                        # Сохраняем все значения как строки, конвертируем при необходимости
                        setattr(self, key, value)
    
    @property
    def enabled_platforms_list(self) -> List[str]:
        """Получение списка активных платформ"""
        if isinstance(self.ENABLED_PLATFORMS, str):
            return [p.strip() for p in self.ENABLED_PLATFORMS.split(',') if p.strip()]
        return []


# Глобальный экземпляр настроек
_settings: Optional[Settings] = None


def get_settings():
    """Получение экземпляра настроек (Singleton)"""
    global _settings
    if _settings is None:
        try:
            if HAS_PYDANTIC_SETTINGS:
                _settings = Settings()
            else:
                _settings = SimpleSettings()
        except Exception as e:
            print(f"Ошибка создания настроек с Pydantic: {e}")
            print("Используем упрощенную версию настроек...")
            _settings = SimpleSettings()
    return _settings


def update_enabled_platforms(platforms: List[str]):
    """Обновление списка активных платформ"""
    settings = get_settings()
    settings.ENABLED_PLATFORMS = ','.join(platforms)


def is_platform_enabled(platform: str) -> bool:
    """Проверка, активна ли платформа"""
    settings = get_settings()
    return platform in settings.enabled_platforms_list


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
    dirs = [get_data_dir(), get_logs_dir(), get_project_root() / "credentials"]
    for dir_path in dirs:
        dir_path.mkdir(exist_ok=True)