import requests
import json
import os
from datetime import datetime, timedelta
import logging

class WeatherIntegration:
    def __init__(self, config_path):
        self.config_path = config_path
        self.settings = self.load_settings()
        self.last_update = None
        self.cached_weather = None
        
    def load_settings(self):
        default_settings = {
            'enabled': False,
            'zipcode': '',
            'api_key': '',
            'units': 'F',
            'update_interval': 6  # hours
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Error loading weather settings: {e}")
        return default_settings
        
    def save_settings(self, settings):
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(settings, f, indent=4)
            self.settings = settings
            return True
        except Exception as e:
            logging.error(f"Error saving weather settings: {e}")
            return False
            
    def get_weather(self, force_update=False):
        """Get current weather data, using cache if available."""
        now = datetime.now()
        
        # Check if we need to update
        if not force_update and self.cached_weather and self.last_update:
            age = now - self.last_update
            if age < timedelta(hours=self.settings.get('update_interval', 6)):
                logging.info("Using cached weather data")
                return self.cached_weather
        
        logging.info(f"Weather settings: {self.settings}")
        
        if not self.settings.get('enabled'):
            logging.error("Weather integration is not enabled")
            return None
        
        if not self.settings.get('api_key'):
            logging.error("Weather API key is not set")
            return None
        
        if not self.settings.get('zipcode'):
            logging.error("Weather zipcode is not set")
            return None
            
        try:
            logging.info("Fetching new weather data...")
            response = requests.get(
                'http://api.openweathermap.org/data/2.5/weather',
                params={
                    'zip': self.settings['zipcode'],
                    'appid': self.settings['api_key'],
                    'units': 'imperial' if self.settings['units'] == 'F' else 'metric'
                }
            )
            
            logging.info(f"Weather API response status: {response.status_code}")
            
            if response.status_code == 200:
                self.cached_weather = response.json()
                self.last_update = now
                logging.info(f"Weather data fetched successfully: {self.cached_weather}")
                return self.cached_weather
            else:
                logging.error(f"Weather API error: {response.text}")
                
        except Exception as e:
            logging.error(f"Error fetching weather: {e}", exc_info=True)
            
        return None 