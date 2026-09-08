import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
    TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
    TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL", "el_smail")
    DEVELOPER_ID = int(os.getenv("DEVELOPER_ID", 0))
    CLIPS_CHANNEL_ID = int(os.getenv("CLIPS_CHANNEL_ID", 0))
    BIRTHDAY_CHANNEL_ID = int(os.getenv("BIRTHDAY_CHANNEL_ID", 0))
    BIRTHDAY_ROLE_ID = int(os.getenv("BIRTHDAY_ROLE_ID", 0))
    MONGODB_URI = os.getenv("MONGODB_URI")
    SPECIAL_USER_ID = int(os.getenv("SPECIAL_USER_ID", 0))
    ATERNOS_EMAIL = os.getenv("ATERNOS_EMAIL")
    ATERNOS_PASSWORD = os.getenv("ATERNOS_PASSWORD")
    MOVIES_ROLE_ID = int(os.getenv("MOVIES_ROLE_ID", 0))
    MOVIES_CHANNEL_ID = int(os.getenv("MOVIES_CHANNEL_ID", 0))
    MOVIES_ANNOUNCEMENT_CHANNEL_ID = int(os.getenv("MOVIES_ANNOUNCEMENT_CHANNEL_ID", 0))
    
    @classmethod
    def validate(cls):
        """Valida que todas las configuraciones necesarias estén presentes"""
        if not cls.DISCORD_TOKEN:
            raise ValueError("DISCORD_TOKEN no está configurado en .env")
        if not cls.TWITCH_CLIENT_ID:
            raise ValueError("TWITCH_CLIENT_ID no está configurado en .env")
        if not cls.TWITCH_CLIENT_SECRET:
            raise ValueError("TWITCH_CLIENT_SECRET no está configurado en .env")
        if cls.DEVELOPER_ID == 0:
            raise ValueError("DEVELOPER_ID no está configurado en .env")
        if not cls.MONGODB_URI:
            raise ValueError("MONGODB_URI no está configurado en .env")
