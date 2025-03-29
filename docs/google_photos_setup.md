# Google Photos API Setup Guide

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Photos Library API:
   - Go to "APIs & Services" > "Library"
   - Search for "Photos Library API"
   - Click "Enable"

4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Desktop app" as the application type
   - Give it a name (e.g., "Photo Frame")
   - Click "Create"

5. Download the credentials:
   - Find your newly created OAuth 2.0 Client ID
   - Click the download button (⬇️)
   - Save the file as `google_credentials.json`

6. Place the credentials file:
   - Create a `credentials` folder in your photo_server directory:
     ```bash
     mkdir -p /home/pi/photo_server/credentials
     ```
   - Move the downloaded credentials file:
     ```bash
     mv ~/Downloads/google_credentials.json /home/pi/photo_server/credentials/
     ```

7. Set proper permissions:
   ```bash
   chmod 600 /home/pi/photo_server/credentials/google_credentials.json
   ```

8. Restart the photo server application 