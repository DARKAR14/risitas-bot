import json
import os
from typing import Optional, Dict

class PresenceManager:
    def __init__(self, filename="presence.json"):
        self.filename = filename
        self.presence_data = self.load_presence()
    
    def load_presence(self) -> Optional[Dict]:
        """Carga la presencia guardada desde el archivo JSON"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error cargando presence.json: {e}")
                return None
        return None
    
    def save_presence(self, tipo: str, texto: str):
        """Guarda la presencia actual en el archivo JSON"""
        self.presence_data = {
            "type": tipo,
            "text": texto
        }
        
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.presence_data, f, ensure_ascii=False, indent=2)
            print(f"💾 Presencia guardada: {tipo} - {texto}")
        except Exception as e:
            print(f"❌ Error guardando presence.json: {e}")
    
    def get_presence(self) -> Optional[Dict]:
        """Obtiene la presencia guardada"""
        return self.presence_data
    
    def clear_presence(self):
        """Elimina la presencia guardada"""
        self.presence_data = None
        if os.path.exists(self.filename):
            try:
                os.remove(self.filename)
                print("🗑️ Presencia eliminada")
            except Exception as e:
                print(f"❌ Error eliminando presence.json: {e}")