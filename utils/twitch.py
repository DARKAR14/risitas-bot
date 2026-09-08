import aiohttp
from config import Config
import json
import os

class TwitchAPI:
    def __init__(self):
        self.token = None
        self.client_id = Config.TWITCH_CLIENT_ID
        self.client_secret = Config.TWITCH_CLIENT_SECRET
        self.channel = Config.TWITCH_CHANNEL
        self.token_expires_at = 0
        self.broadcaster_id = None
        self.last_clips_file = "last_clips.json"
        self.max_clips_stored = 10  # Máximo de clips a almacenar
        self.known_clips = self.load_known_clips()
    
    def load_known_clips(self):
        """Carga los IDs de clips conocidos y limpia si es un día nuevo"""
        from datetime import datetime
        
        if os.path.exists(self.last_clips_file):
            try:
                with open(self.last_clips_file, 'r') as f:
                    data = json.load(f)
                    
                    # Manejo de formato antiguo (lista simple)
                    if isinstance(data, list):
                        return set(data)
                    
                    # Nuevo formato con fecha
                    if isinstance(data, dict):
                        last_date = data.get("last_update_date")
                        today = datetime.now().strftime("%Y-%m-%d")
                        
                        # Si es un día nuevo, limpiar
                        if last_date != today:
                            print(f"🔄 Nuevo día detectado ({today}). Limpiando clips anteriores.")
                            return set()
                        
                        return set(data.get("clips", []))
                    
                    return set()
            except:
                return set()
        return set()
    
    def save_known_clips(self):
        """Guarda los últimos N clips conocidos con fecha para ahorrar espacio"""
        from datetime import datetime
        
        try:
            # Mantener solo los últimos N clips
            clips_list = list(self.known_clips)[-self.max_clips_stored:]
            
            data = {
                "clips": clips_list,
                "last_update_date": datetime.now().strftime("%Y-%m-%d"),
                "count": len(clips_list)
            }
            
            with open(self.last_clips_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error guardando clips conocidos: {e}")
    
    async def get_token(self):
        """Obtiene el token de acceso de Twitch"""
        import time
        
        # Si el token aún es válido, no renovarlo
        if self.token and time.time() < self.token_expires_at - 300:  # 5 min de margen
            return self.token
        
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.token = data.get("access_token")
                        # Guardar tiempo de expiración (tokens duran ~60 días)
                        expires_in = data.get("expires_in", 3600)
                        import time
                        self.token_expires_at = time.time() + expires_in
                        print(f"✅ Token de Twitch obtenido (válido por {expires_in/86400:.1f} días)")
                        return self.token
                    else:
                        print(f"❌ Error obteniendo token de Twitch: {resp.status}")
                        error_text = await resp.text()
                        print(f"Respuesta: {error_text}")
                        return None
        except Exception as e:
            print(f"❌ Excepción al obtener token de Twitch: {e}")
            return None
    
    async def get_broadcaster_id(self):
        """Obtiene el ID del broadcaster"""
        if self.broadcaster_id:
            return self.broadcaster_id
        
        if not self.token:
            await self.get_token()
        
        url = f"https://api.twitch.tv/helix/users?login={self.channel}"
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.token}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("data"):
                            self.broadcaster_id = data["data"][0]["id"]
                            print(f"✅ Broadcaster ID obtenido: {self.broadcaster_id}")
                            return self.broadcaster_id
        except Exception as e:
            print(f"❌ Error obteniendo broadcaster ID: {e}")
        
        return None
    
    async def is_live(self):
        """Verifica si el canal está transmitiendo"""
        # Renovar token si es necesario
        if not self.token:
            await self.get_token()
        
        if not self.token:
            print("⚠️ No hay token de Twitch disponible")
            return False
        
        url = f"https://api.twitch.tv/helix/streams?user_login={self.channel}"
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.token}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        is_streaming = len(data.get("data", [])) > 0
                        
                        if is_streaming:
                            stream_data = data["data"][0]
                            print(f"🔴 {self.channel} está en vivo: {stream_data.get('title', 'Sin título')}")
                        
                        return is_streaming
                    elif resp.status == 401:
                        # Token expirado, renovar
                        print("⚠️ Token de Twitch expirado, renovando...")
                        self.token = None
                        await self.get_token()
                        return False
                    else:
                        print(f"❌ Error verificando stream: {resp.status}")
                        error_text = await resp.text()
                        print(f"Respuesta: {error_text}")
                        return False
        except Exception as e:
            print(f"❌ Excepción verificando stream: {e}")
            return False
    
    async def get_stream_info(self):
        """Obtiene información detallada del stream si está en vivo"""
        if not self.token:
            await self.get_token()
        
        if not self.token:
            return None
        
        url = f"https://api.twitch.tv/helix/streams?user_login={self.channel}"
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.token}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if len(data.get("data", [])) > 0:
                            return data["data"][0]
                    return None
        except Exception as e:
            print(f"❌ Error obteniendo info del stream: {e}")
            return None
    
    async def get_recent_clips(self, limit=20):
        """Obtiene los clips más recientes del canal"""
        if not self.token:
            await self.get_token()
        
        if not self.token:
            return []
        
        # Obtener broadcaster ID si no lo tenemos
        if not self.broadcaster_id:
            await self.get_broadcaster_id()
        
        if not self.broadcaster_id:
            print("❌ No se pudo obtener el broadcaster ID")
            return []
        
        # Obtener clips de las últimas 24 horas
        from datetime import datetime, timedelta
        started_at = (datetime.utcnow() - timedelta(hours=24)).isoformat() + "Z"
        
        url = f"https://api.twitch.tv/helix/clips?broadcaster_id={self.broadcaster_id}&first={limit}&started_at={started_at}"
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.token}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("data", [])
                    elif resp.status == 401:
                        print("⚠️ Token expirado al obtener clips")
                        self.token = None
                        return []
                    else:
                        print(f"❌ Error obteniendo clips: {resp.status}")
                        return []
        except Exception as e:
            print(f"❌ Error obteniendo clips: {e}")
            return []
    
    async def check_new_clips(self):
        """Verifica si hay clips nuevos y retorna solo los que no conocemos"""
        clips = await self.get_recent_clips()
        new_clips = []
        
        for clip in clips:
            clip_id = clip.get("id")
            if clip_id and clip_id not in self.known_clips:
                new_clips.append(clip)
                self.known_clips.add(clip_id)
        
        # Guardar clips conocidos
        if new_clips:
            self.save_known_clips()
        
        return new_clips