#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import yaml
import time
from app.core.core_system import CoreSystem

# Setup logging
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from YAML file."""
    try:
        # Try loading from config.yml first
        if os.path.exists('config.yml'):
            with open('config.yml', 'r') as file:
                return yaml.safe_load(file)
        # Fall back to config directory
        elif os.path.exists('config/config.yml'):
            with open('config/config.yml', 'r') as file:
                return yaml.safe_load(file)
        else:
            logger.error("No configuration file found")
            return None
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        return None

def main():
    """Main entry point for the AI assistant."""
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Could not load configuration. Exiting.")
        return
    
    try:
        # Initialize and start the AI assistant
        logger.info("Starting AI assistant...")
        ai_assistant = CoreSystem(config)
        success = ai_assistant.start()
        
        if not success:
            logger.error("Failed to start AI assistant")
            return
        
        # Keep the application running
        try:
            while ai_assistant.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutdown requested...")
            ai_assistant.stop()
            
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
