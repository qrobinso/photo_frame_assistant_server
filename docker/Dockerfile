services:
  photo-server:
    image: ghcr.io/qrobinso/photo_frame_assistant_server:latest  # We would host the image on GitHub Container Registry
    # Alternatively, build directly from GitHub
    build:
      context: https://github.com/qrobinso/photo_frame_assistant_server.git#main
      dockerfile: docker/Dockerfile
    container_name: photo-frame-assistant
    network_mode: "host"  # Use host networking mode
    volumes:
      - photo_data:/app/data  # Single volume for all persistent data
      - ./config:/app/config  # Mount local config directory
    environment:
      - TZ=UTC  # Set your timezone here
      # Add any other configuration options here
      - CONFIG_PATH=/app/config  # Config location
      - UPLOAD_PATH=/app/data/uploads
      - LOG_PATH=/app/data/logs
    restart: unless-stopped
    privileged: true  # For hardware access
    devices:
      - /dev/i2c-1:/dev/i2c-1  # For Raspberry Pi hardware

volumes:
  photo_data:
    driver: local 