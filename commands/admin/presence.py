import discord
from discord import app_commands
from discord.ext import commands
from config import Config

class PresenceCommands(commands.Cog):
    def __init__(self, bot, presence_manager):
        self.bot = bot
        self.presence_manager = presence_manager
    
    @app_commands.command(name="presence", description="Cambiar la presencia del bot (solo desarrollador)")
    @app_commands.describe(
        tipo="Tipo de actividad",
        texto="Texto a mostrar"
    )
    @app_commands.choices(tipo=[
        app_commands.Choice(name="Jugando", value="playing"),
        app_commands.Choice(name="Viendo", value="watching"),
        app_commands.Choice(name="Escuchando", value="listening"),
    ])
    async def presence(self, interaction: discord.Interaction, 
                      tipo: app_commands.Choice[str], texto: str):
        if interaction.user.id != Config.DEVELOPER_ID:
            await interaction.response.send_message(
                "❌ Solo el desarrollador puede usar este comando.", 
                ephemeral=True
            )
            return
        
        activity_map = {
            "playing": discord.Game(name=texto),
            "watching": discord.Activity(type=discord.ActivityType.watching, name=texto),
            "listening": discord.Activity(type=discord.ActivityType.listening, name=texto),
        }
        
        await self.bot.change_presence(activity=activity_map[tipo.value])
        
        # Guardar la presencia en el JSON
        self.presence_manager.save_presence(tipo.value, texto)
        
        await interaction.response.send_message(
            f"✅ Presencia cambiada y guardada: **{tipo.name}** {texto}", 
            ephemeral=True
        )
    
    @app_commands.command(name="clearpresence", description="Limpiar presencia guardada (solo desarrollador)")
    async def clearpresence(self, interaction: discord.Interaction):
        if interaction.user.id != Config.DEVELOPER_ID:
            await interaction.response.send_message(
                "❌ Solo el desarrollador puede usar este comando.", 
                ephemeral=True
            )
            return
        
        self.presence_manager.clear_presence()
        await self.bot.change_presence(activity=None)
        
        await interaction.response.send_message(
            "✅ Presencia limpiada. El bot usará la detección automática de Twitch.", 
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(PresenceCommands(bot, bot.presence_manager))
