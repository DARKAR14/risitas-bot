import discord
from discord import app_commands
from discord.ext import commands
from config import Config
import os
import sys
import importlib

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_file = "bot.log"
    
    # El comando /reload se movió a: commands.admin.reload
    
    
    @app_commands.command(name="testtwitch", description="Probar conexión con Twitch (solo desarrollador)")
    async def testtwitch(self, interaction: discord.Interaction):
        """Prueba la conexión con la API de Twitch"""
        if interaction.user.id != Config.DEVELOPER_ID:
            await interaction.response.send_message(
                "❌ Solo el desarrollador puede usar este comando.", 
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            embed = discord.Embed(
                title="🎮 Test de Twitch API",
                color=discord.Color.purple()
            )
            
            # Verificar configuración
            embed.add_field(
                name="⚙️ Configuración",
                value=f"Canal: `{Config.TWITCH_CHANNEL}`\n"
                      f"Client ID: `{Config.TWITCH_CLIENT_ID[:10]}...`",
                inline=False
            )
            
            # Renovar token
            token = await self.bot.twitch.get_token()
            if token:
                embed.add_field(
                    name="🔑 Token",
                    value=f"✅ Token obtenido: `{token[:10]}...`",
                    inline=False
                )
            else:
                embed.add_field(
                    name="🔑 Token",
                    value="❌ No se pudo obtener token",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Verificar si está en vivo
            is_live = await self.bot.twitch.is_live()
            stream_info = await self.bot.twitch.get_stream_info()
            
            if is_live and stream_info:
                embed.add_field(
                    name="🔴 Estado",
                    value=f"**EN VIVO**\n"
                          f"Título: {stream_info.get('title', 'N/A')}\n"
                          f"Juego: {stream_info.get('game_name', 'N/A')}\n"
                          f"Espectadores: {stream_info.get('viewer_count', 0)}",
                    inline=False
                )
                embed.color = discord.Color.red()
            else:
                embed.add_field(
                    name="⚫ Estado",
                    value="Offline - No está transmitiendo",
                    inline=False
                )
                embed.color = discord.Color.greyple()
            
            # Verificar presencia del bot
            current_activity = self.bot.activity
            if current_activity:
                embed.add_field(
                    name="🤖 Presencia Actual del Bot",
                    value=f"Tipo: {current_activity.type.name}\n"
                          f"Texto: {current_activity.name}",
                    inline=False
                )
            
            # Verificar si hay presencia personalizada
            saved_presence = self.bot.presence_manager.get_presence()
            if saved_presence:
                embed.add_field(
                    name="⚠️ Presencia Personalizada Activa",
                    value=f"Tipo: {saved_presence['type']}\n"
                          f"Texto: {saved_presence['text']}\n"
                          f"💡 Usa `/clearpresence` para desactivarla",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error en test: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="cumpleañostest", description="Prueba que los embeds funcionen correctamente")
    async def cumpleaños_test(self, interaction: discord.Interaction):
        """Comando de prueba para verificar que los embeds de cumpleaños funcionan"""
        if interaction.user.id != Config.DEVELOPER_ID:
            await interaction.response.send_message(
                "❌ Solo el desarrollador puede usar este comando.", 
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🎉 ¡Feliz cumple pai!",
            description="Que lo goces bacano 🎊",
            color=0x58B5FF
        )
        
        embed.set_image(url="https://images-ext-1.discordapp.net/external/lzhGE070LOFf8PlJD6P2_HV-5dP3lIWZqGJFrRzADU8/https/64.media.tumblr.com/e027f49565a711594c7c7b9e208c0749/0c580185984e1497-5b/s500x750/d5421285cd553ffd862487bc8072aa134e7e8f65.gif")
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        await interaction.response.send_message(
            content=f"🎂 ¡Hoy es cumpleaños de {interaction.user.mention}!",
            embed=embed
        )
    
    async def status(self, interaction: discord.Interaction):
        """Info del sistema"""
        if interaction.user.id != Config.DEVELOPER_ID:
            await interaction.response.send_message(
                "❌ Solo el desarrollador puede usar este comando.", 
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            import psutil
            process = psutil.Process(os.getpid())
            
            mem_info = process.memory_info()
            cpu_percent = process.cpu_percent(interval=1)
            
            embed = discord.Embed(
                title="📊 Estado del Bot",
                color=discord.Color.green()
            )
            
            embed.add_field(name="💾 RAM", value=f"{mem_info.rss / 1024 / 1024:.2f} MB", inline=True)
            embed.add_field(name="🔧 CPU", value=f"{cpu_percent}%", inline=True)
            embed.add_field(name="📡 Ping", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
            embed.add_field(name="🏠 Servers", value=f"{len(self.bot.guilds)}", inline=True)
            embed.add_field(name="📨 Programados", value=f"{self.bot.scheduler.count()}", inline=True)
            embed.add_field(name="🐍 Python", value=f"{sys.version.split()[0]}", inline=True)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except ImportError:
            await interaction.followup.send(
                "⚠️ Instala psutil: `pip install psutil`",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
