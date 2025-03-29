import os
import json
import logging
import shutil
from datetime import datetime
import requests
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)

class ImmichIntegration:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = self.load_config()
        
    def load_config(self):
        """Load Immich configuration from config file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading Immich configuration: {e}")
        return {"url": "", "api_key": "", "auto_import": []}
        
    def save_config(self, config):
        """Save Immich configuration to config file."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=4)
            self.config = config
            return True
        except Exception as e:
            logger.error(f"Error saving Immich configuration: {e}")
            return False
            
    def update_config(self, url, api_key):
        """Update Immich server URL and API key."""
        config = self.load_config()
        
        # Ensure URL is properly formatted (remove trailing slash but preserve port)
        url = url.rstrip('/')
        
        # Validate URL format - ensure it has http/https protocol
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        
        config["url"] = url
        config["api_key"] = api_key
        return self.save_config(config)
        
    def get_api_url(self, endpoint):
        """Helper method to construct API URLs consistently."""
        base_url = self.config["url"]
        # Ensure endpoint starts with / if not already
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        return f"{base_url}{endpoint}"
        
    def test_connection(self):
        """Test connection to Immich server."""
        if not self.config["url"] or not self.config["api_key"]:
            return False, "URL and API key are required"
            
        try:
            # Update header format to match Immich API requirements
            headers = {
                'Accept': 'application/json',
                'x-api-key': self.config["api_key"]
            }
            api_url = self.get_api_url('/api/server/about')
            
            logger.error(f"Testing connection to Immich server at: {api_url}")
            
            # Use requests.request method with "GET" parameter
            response = requests.request("GET", api_url, headers=headers, data={})
            
            if response.status_code == 200:
                return True, "Connection successful"
            elif response.status_code == 401:
                return False, "Authentication failed. Please check your API key."
            else:
                return False, f"Connection failed with status code: {response.status_code}"
        except requests.exceptions.RequestException as e:
            logger.error(f"Immich connection error: {str(e)}")
            return False, f"Connection error: {str(e)}"
            
    def get_albums(self):
        """Get list of albums from Immich server."""
        if not self.config["url"] or not self.config["api_key"]:
            return []
            
        try:
            # Update header format to match Immich API requirements
            headers = {
                'Accept': 'application/json',
                'x-api-key': self.config["api_key"]
            }
            api_url = self.get_api_url('/api/albums')
            
            # Use requests.request method with "GET" parameter
            response = requests.request("GET", api_url, headers=headers, data={})
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get albums: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting albums: {e}")
            return []
            
    def get_faces(self):
        """Get list of faces from Immich server."""
        if not self.config["url"] or not self.config["api_key"]:
            return []
            
        try:
            headers = {"X-API-Key": self.config["api_key"]}
            response = requests.get(f"{self.config['url']}/api/faces", headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get faces: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting faces: {e}")
            return []
            
    def get_album_assets(self, album_id):
        """Get assets in an album."""
        if not self.config["url"] or not self.config["api_key"]:
            return []
            
        try:
            headers = {"X-API-Key": self.config["api_key"]}
            response = requests.get(f"{self.config['url']}/api/albums/{album_id}", headers=headers, timeout=10)
            
            if response.status_code == 200:
                album_data = response.json()
                return album_data.get("assets", [])
            else:
                logger.error(f"Failed to get album assets: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting album assets: {e}")
            return []
            
    def get_face_assets(self, person_id):
        """Get assets for a face/person."""
        if not self.config["url"] or not self.config["api_key"]:
            return []
            
        try:
            headers = {"X-API-Key": self.config["api_key"]}
            response = requests.get(f"{self.config['url']}/api/person/{person_id}/assets", headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get face assets: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting face assets: {e}")
            return []
            
    def download_asset(self, asset_id, destination_path):
        """Download an asset from Immich server."""
        if not self.config["url"] or not self.config["api_key"]:
            return False, "URL and API key are required"
            
        try:
            headers = {"X-API-Key": self.config["api_key"]}
            response = requests.get(
                f"{self.config['url']}/api/assets/{asset_id}/original", 
                headers=headers, 
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                with open(destination_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True, "Asset downloaded successfully"
            else:
                return False, f"Failed to download asset: {response.status_code}"
        except Exception as e:
            logger.error(f"Error downloading asset: {e}")
            return False, f"Error downloading asset: {str(e)}"
            
    def add_auto_import(self, source_type, source_id, source_name, frame_id):
        """Add an auto-import configuration."""
        config = self.load_config()
        
        # Check if this source is already configured for auto-import
        for item in config.get("auto_import", []):
            if item.get("source_type") == source_type and item.get("source_id") == source_id:
                # Update existing configuration
                item["frame_id"] = frame_id
                return self.save_config(config)
                
        # Add new configuration
        auto_import_item = {
            "id": str(uuid.uuid4()),
            "source_type": source_type,  # "album" or "face"
            "source_id": source_id,
            "source_name": source_name,
            "frame_id": frame_id,
            "last_checked": None,
            "imported_assets": []
        }
        
        if "auto_import" not in config:
            config["auto_import"] = []
            
        config["auto_import"].append(auto_import_item)
        return self.save_config(config)
        
    def remove_auto_import(self, auto_import_id):
        """Remove an auto-import configuration."""
        config = self.load_config()
        
        if "auto_import" in config:
            config["auto_import"] = [item for item in config["auto_import"] if item.get("id") != auto_import_id]
            return self.save_config(config)
            
        return True
        
    def get_auto_import_configs(self):
        """Get all auto-import configurations."""
        config = self.load_config()
        return config.get("auto_import", [])
        
    def update_imported_assets(self, auto_import_id, asset_ids):
        """Update the list of imported assets for an auto-import configuration."""
        config = self.load_config()
        
        if "auto_import" in config:
            for item in config["auto_import"]:
                if item.get("id") == auto_import_id:
                    item["imported_assets"] = asset_ids
                    item["last_checked"] = datetime.now().isoformat()
                    return self.save_config(config)
                    
        return False 