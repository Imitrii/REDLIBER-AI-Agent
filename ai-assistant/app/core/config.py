import os
import logging
from dotenv import load_dotenv
from pathlib import Path

# Загружаем переменные окружения из файла .env
dotenv_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path)

# Базовые настройки
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# OpenAI API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Instagram
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "")
INSTAGRAM_VERIFICATION_CODE = os.getenv("INSTAGRAM_VERIFICATION_CODE", "")

# Настройки базы данных
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/aibot.db")

# Лимиты Instagram
INSTAGRAM_MAX_MESSAGES_PER_DAY = int(os.getenv("INSTAGRAM_MAX_MESSAGES_PER_DAY", "45"))
INSTAGRAM_MIN_INTERVAL_MINUTES = int(os.getenv("INSTAGRAM_MIN_INTERVAL_MINUTES", "15"))

# Рабочие часы (время Москвы)
WORKING_HOURS_START = int(os.getenv("WORKING_HOURS_START", "10"))
WORKING_HOURS_END = int(os.getenv("WORKING_HOURS_END", "21"))

# Настройка логирования
def setup_logging():
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Path(__file__).resolve().parent.parent.parent / 'logs' / 'app.log'),
            logging.StreamHandler()
        ]
    )
