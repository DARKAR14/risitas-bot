from datetime import datetime
from typing import List, Dict

class MessageScheduler:
    def __init__(self):
        self.scheduled_messages: List[Dict] = []
    
    def add_message(self, scheduled_time: datetime, channel_id: int, 
                   title: str, body: str, thumbnail: str = None, image: str = None):
        """Agrega un mensaje programado"""
        self.scheduled_messages.append({
            "time": scheduled_time,
            "channel_id": channel_id,
            "title": title,
            "body": body,
            "thumbnail": thumbnail,
            "image": image
        })
    
    def get_pending_messages(self):
        """Obtiene mensajes que deben enviarse ahora"""
        now = datetime.now()
        pending = [msg for msg in self.scheduled_messages if now >= msg["time"]]
        
        # Eliminar mensajes pendientes de la lista
        for msg in pending:
            self.scheduled_messages.remove(msg)
        
        return pending
    
    def count(self):
        """Retorna la cantidad de mensajes programados"""
        return len(self.scheduled_messages)