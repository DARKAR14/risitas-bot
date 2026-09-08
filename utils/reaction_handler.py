import discord
from discord.ext import commands
from config import Config
import random

class ReactionHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        """Reacciona con emoji cuando un usuario específico habla"""
        # No reaccionar a mensajes del bot mismo
        if message.author == self.bot.user:
            return

        # No reaccionar a mensajes en DM
        if not message.guild:
            return

        # ID del usuario específico desde .env
        special_user_id = Config.SPECIAL_USER_ID

        # Verificar que esté configurado
        if not special_user_id or special_user_id == 0:
            return

        # Solo reaccionar si es el usuario específico
        if message.author.id == special_user_id:
            try:
                # Emoji personalizado del servidor
                emoji = "<:jime01:1463053077673410724>"

                # Probabilidad de reacción (30% de las veces para no ser molesto)
                if random.random() < 0.3:
                    await message.add_reaction(emoji)
            except Exception as e:
                print(f"❌ Error reaccionando a mensaje de usuario especial: {e}")