#!/bin/bash
set -e

echo "Starting Photo Server initialization..."

# Create necessary directories
mkdir -p uploads logs credentials db_backups

# Initialize the database
echo "Checking database..."
python db_manager.py

# Check exit status
if [ $? -ne 0 ]; then
    echo "ERROR: Database initialization failed!"
    exit 1
fi

# Check for required configuration files
if [ ! -f server_settings.json ]; then
    echo "Creating default server_settings.json..."
    echo '{
    "server_name": "photo-frame-assistant",
    "timezone": "UTC",
    "cleanup_interval": 24,
    "log_level": "INFO",
    "max_upload_size": 10,
    "discovery_port": 5000,
    "ai_analysis_enabled": false,
    "dark_mode": false
}' > server_settings.json
fi

if [ ! -f photogen_settings.json ] && [ -f photogen_settings.json.example ]; then
    echo "Creating photogen_settings.json from example..."
    cp photogen_settings.json.example photogen_settings.json
elif [ ! -f photogen_settings.json ]; then
    echo "Creating default photogen_settings.json..."
    echo '{
    "openai_api_key": "",
    "stability_api_key": "",
    "default_service": "openai",
    "default_model": "dall-e-3",
    "default_style": "vivid",
    "default_size": "1024x1024",
    "default_quality": "standard",
    "default_steps": 30,
    "default_cfg_scale": 7.5,
    "default_sampler": "k_euler_ancestral"
}' > photogen_settings.json
fi

# Make sure permissions are correct
chmod -R 777 uploads logs credentials db_backups

echo "Initialization complete. Starting Photo Server..."
exec python server.py 