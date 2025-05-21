import sys
import os
import asyncio
import logging
from pathlib import Path

# Добавляем корневую директорию проекта в путь
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.config import setup_logging, ENVIRONMENT, LOG_LEVEL, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD, OPENAI_API_KEY, WORKING_HOURS_START, WORKING_HOURS_END, INSTAGRAM_MAX_MESSAGES_PER_DAY, INSTAGRAM_MIN_INTERVAL_MINUTES
from app.core.core_system import CoreSystem

# Настраиваем логирование
setup_logging()
logger = logging.getLogger(__name__)

async def main():
    """Основная функция для запуска системы"""
    logger.info("Starting AI assistant...")
    
    # Создаем конфигурацию в формате словаря для передачи в CoreSystem
    config = {
        "instagram": {
            "username": INSTAGRAM_USERNAME,
            "password": INSTAGRAM_PASSWORD
        },
        "openai": {
            "api_key": OPENAI_API_KEY
        },
        "app": {
            "messenger": "instagram",
            "message_interval": INSTAGRAM_MIN_INTERVAL_MINUTES * 60,
            "working_hours": {
                "start": WORKING_HOURS_START,
                "end": WORKING_HOURS_END
            },
            "max_daily_messages": INSTAGRAM_MAX_MESSAGES_PER_DAY
        }
    }
    
    # Создаем экземпляр ядра системы с конфигурацией
    core_system = CoreSystem(config)
    
    # Запускаем систему
    success = await core_system.start()
    
    if success:
        logger.info("AI assistant started successfully!")
        try:
            # Держим систему активной
            while True:
                await asyncio.sleep(600)  # Проверка каждые 10 минут
                logger.info("System is running...")
        except KeyboardInterrupt:
            logger.info("Stopping AI assistant...")
            await core_system.stop()
            logger.info("AI assistant stopped")
    else:
        logger.error("Failed to start AI assistant")

if __name__ == "__main__":
    asyncio.run(main())
