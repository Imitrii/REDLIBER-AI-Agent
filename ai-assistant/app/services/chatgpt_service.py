import openai
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from app.core.config import get_settings


class ChatGPTService:
    def __init__(self):
        self.settings = get_settings()
        self.client = None
        self.logger = logging.getLogger(__name__)
        self.is_initialized = False
        
        self.usage_stats = {
            'total_requests': 0,
            'total_tokens': 0,
            'errors': 0,
            'last_request': None
        }
    
    async def initialize(self):
        try:
            if not self.settings.OPENAI_API_KEY:
                self.logger.error("OPENAI_API_KEY not found in settings")
                return False
            
            self.client = openai.OpenAI(api_key=self.settings.OPENAI_API_KEY)
            self.is_initialized = True
            self.logger.info("ChatGPT service initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ChatGPT service: {e}")
            return False
    
    async def generate_response(self, message: str, context: List[Dict] = None, 
                              system_prompt: str = None) -> Optional[str]:
        try:
            if not self.is_initialized:
                await self.initialize()
            
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                messages.append({"role": "system", "content": self.settings.SYSTEM_PROMPT})
            
            if context:
                for ctx_msg in context[-10:]:
                    messages.append({
                        "role": ctx_msg.get("role", "user"),
                        "content": ctx_msg.get("content", "")
                    })
            
            messages.append({"role": "user", "content": message})
            
            response = self.client.chat.completions.create(
                model=self.settings.OPENAI_MODEL,
                messages=messages,
                max_tokens=self.settings.OPENAI_MAX_TOKENS,
                temperature=self.settings.OPENAI_TEMPERATURE
            )
            
            self._update_usage_stats(response)
            generated_response = response.choices[0].message.content
            
            self.logger.info(f"Generated response: {generated_response[:100]}...")
            return generated_response
            
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            self.usage_stats['errors'] += 1
            return None
    
    async def generate_greeting(self, user_name: str = None) -> str:
        try:
            greeting_prompt = self.settings.GREETING_PROMPT
            
            if user_name:
                message = f"Поприветствуй пользователя по имени {user_name}"
            else:
                message = "Поприветствуй нового пользователя"
            
            response = await self.generate_response(
                message=message,
                system_prompt=greeting_prompt
            )
            
            return response or "Привет! Как дела?"
            
        except Exception as e:
            self.logger.error(f"Error generating greeting: {e}")
            return "Привет! Как дела?"
    
    def _update_usage_stats(self, response):
        self.usage_stats['total_requests'] += 1
        self.usage_stats['last_request'] = datetime.now()
        
        if hasattr(response, 'usage') and response.usage:
            self.usage_stats['total_tokens'] += response.usage.total_tokens
    
    def get_usage_stats(self) -> Dict[str, Any]:
        return {
            **self.usage_stats,
            'is_initialized': self.is_initialized,
            'model': self.settings.OPENAI_MODEL,
            'last_request_iso': self.usage_stats['last_request'].isoformat() if self.usage_stats['last_request'] else None
        }
    
    async def health_check(self) -> Dict[str, Any]:
        try:
            if not self.is_initialized:
                return {
                    'healthy': False,
                    'error': 'Service not initialized',
                    'initialized': False
                }
            
            test_response = await self.generate_response("ping", system_prompt="Ответь 'pong'")
            
            return {
                'healthy': test_response is not None,
                'initialized': self.is_initialized,
                'api_responsive': test_response is not None,
                'usage_stats': self.get_usage_stats()
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'initialized': self.is_initialized
            }
