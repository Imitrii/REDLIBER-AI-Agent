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
    
    # Создаем экземпляр ядра системы (без передачи конфигурации)
    core_system = CoreSystem()
    
    try:
        # Запускаем основной цикл системы
        await core_system.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, stopping AI assistant...")
        await core_system.stop()
    except Exception as e:
        logger.error(f"Critical error in main: {e}")
        await core_system.stop()
    finally:
        logger.info("AI assistant stopped")

if __name__ == "__main__":
    asyncio.run(main())