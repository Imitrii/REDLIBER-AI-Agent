import logging
import openai
import json
from typing import Dict, Any, List, Optional
import random

from app.core.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

class ChatGPTService:
    """
    Сервис для взаимодействия с ChatGPT API
    """
    
    def __init__(self):
        openai.api_key = OPENAI_API_KEY
        self.conversations = {}  # Словарь для хранения истории диалогов
    
    async def get_response(self, user_id: str, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Получение ответа от ChatGPT на сообщение пользователя
        
        Args:
            user_id: Идентификатор пользователя
            message: Сообщение от пользователя
            context: Дополнительный контекст (информация о пользователе, настройки и т.д.)
        
        Returns:
            Ответ от ChatGPT
        """
        try:
            # Инициализируем историю диалога, если её нет
            if user_id not in self.conversations:
                self.conversations[user_id] = []
            
            # Добавляем системное сообщение с инструкциями
            system_message = self._create_system_message(context)
            
            # Добавляем сообщение пользователя в историю
            self.conversations[user_id].append({"role": "user", "content": message})
            
            # Ограничиваем историю последними 10 сообщениями для экономии токенов
            conversation_history = self.conversations[user_id][-10:]
            
            # Формируем полный список сообщений для запроса
            messages = [system_message] + conversation_history
            
            # Отправляем запрос к API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # Можно изменить на другую модель
                messages=messages,
                temperature=0.7,        # Контролирует креативность ответов
                max_tokens=500,         # Максимальная длина ответа
                top_p=0.95,             # Контролирует разнообразие ответов
                frequency_penalty=0.5,  # Штраф за повторение одинаковых токенов
                presence_penalty=0.5,   # Штраф за повторение тем
            )
            
            # Извлекаем ответ
            assistant_response = response.choices[0].message.content
            
            # Добавляем ответ ассистента в историю
            self.conversations[user_id].append({"role": "assistant", "content": assistant_response})
            
            # Добавляем эмодзи в конец сообщения для более естественного общения
            assistant_response = self._add_emoji(assistant_response)
            
            # Обеспечиваем, что сообщение заканчивается вопросом
            assistant_response = self._ensure_question_ending(assistant_response)
            
            logger.info(f"ChatGPT generated response for user {user_id}")
            return assistant_response
            
        except Exception as e:
            logger.error(f"Error getting response from ChatGPT: {e}")
            # Возвращаем запасной ответ в случае ошибки
            return "Извините, у меня возникли технические проблемы. Можем продолжить немного позже?"
    
    def _create_system_message(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Создает системное сообщение с инструкциями для модели
        """
        # Базовые инструкции
        instructions = """
        Ты - дружелюбный ассистент, который ведет диалог от имени менеджера по продажам. 
        Следуй этим правилам:
        
        1. Используй неформальный, разговорный стиль с эмодзи
        2. Будь вежливым и позитивным
        3. Задавай открытые вопросы, чтобы поддерживать диалог
        4. Не пиши длинные сообщения - максимум 2-3 предложения
        5. Плавно подводи человека к цели (запись на консультацию)
        6. Не навязывайся, если человек отказывается
        7. Используй естественный язык, без шаблонных фраз
        8. Не указывай, что ты бот или ИИ
        """
        
        # Если есть дополнительный контекст, добавляем информацию о продукте/услуге
        if context and "product_info" in context:
            product_info = context["product_info"]
            instructions += f"\n\nИнформация о продукте/услуге:\n{product_info}"
        
        # Если есть скрипт продаж, добавляем его
        if context and "sales_script" in context:
            sales_script = context["sales_script"]
            instructions += f"\n\nСледуй этому скрипту продаж:\n{sales_script}"
        
        return {"role": "system", "content": instructions}
    
    def _add_emoji(self, message: str) -> str:
        """
        Добавляет случайные эмодзи в конец сообщения
        """
        emojis = ["😊", "👍", "🙌", "✨", "🔥", "💯", "👏", "🤩", "😉", "🎯"]
        # С вероятностью 70% добавляем эмодзи
        if random.random() < 0.7:
            # Добавляем 1-2 эмодзи
            emoji_count = random.randint(1, 2)
            selected_emojis = random.sample(emojis, emoji_count)
            message = message.rstrip() + " " + "".join(selected_emojis)
        
        return message
    
    def _ensure_question_ending(self, message: str) -> str:
        """
        Обеспечивает, что сообщение заканчивается вопросом
        """
        # Проверяем, заканчивается ли сообщение уже вопросом
        if message.rstrip().endswith("?"):
            return message
        
        # Если нет, добавляем вопрос
        questions = [
            "Что скажете?",
            "Как вам это?",
            "Интересно ваше мнение?",
            "Что думаете?",
            "Согласны?",
            "Хотите узнать больше?"
        ]
        
        return message.rstrip() + " " + random.choice(questions)
