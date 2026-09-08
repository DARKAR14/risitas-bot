from pymongo import MongoClient
from config import Config

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.birthdays = None
        
    def connect(self):
        """Conecta a MongoDB"""
        try:
            self.client = MongoClient(Config.MONGODB_URI)
            self.db = self.client.botdb
            
            # Colección de cumpleaños
            self.birthdays = self.db.birthdays
            
            # Verificar conexión
            self.client.admin.command('ping')
            print("✅ Conectado a MongoDB")
            
            # Crear índice único en user_id
            self.birthdays.create_index("user_id", unique=True)
            
            return True
        except Exception as e:
            print(f"❌ Error conectando a MongoDB: {e}")
            return False
    
    def close(self):
        """Cierra la conexión"""
        if self.client:
            self.client.close()
            print("🔌 Desconectado de MongoDB")
    
    # === CUMPLEAÑOS ===
    def save_birthday(self, user_id: int, day: int, month: int, username: str, display_name: str):
        """Guarda un cumpleaños"""
        self.birthdays.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "day": day,
                    "month": month,
                    "username": username,
                    "display_name": display_name
                }
            },
            upsert=True
        )
    
    def get_birthday(self, user_id: int):
        """Obtiene el cumpleaños de un usuario"""
        return self.birthdays.find_one({"user_id": user_id})
    
    def get_birthdays_by_month(self, month: int):
        """Obtiene todos los cumpleaños de un mes"""
        return list(self.birthdays.find({"month": month}))
    
    def get_birthdays_today(self, day: int, month: int):
        """Obtiene cumpleaños de hoy"""
        return list(self.birthdays.find({"day": day, "month": month}))
    
    def delete_birthday(self, user_id: int):
        """Elimina un cumpleaños"""
        result = self.birthdays.delete_one({"user_id": user_id})
        return result.deleted_count > 0