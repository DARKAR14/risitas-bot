import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

class ScheduleModal(discord.ui.Modal, title="Programar Mensaje"):
    msg_title = discord.ui.TextInput(
        label="Título del mensaje",
        placeholder="Escribe el título aquí...",
        required=True,
        max_length=256
    )
    
    body = discord.ui.TextInput(
        label="Contenido del mensaje",
        style=discord.TextStyle.paragraph,
        placeholder="Escribe el contenido aquí...",
        required=True,
        max_length=4000
    )
    
    thumbnail = discord.ui.TextInput(
        label="URL de la miniatura (opcional)",
        placeholder="https://ejemplo.com/imagen.png",
        required=False
    )
    
    image = discord.ui.TextInput(
        label="URL de la imagen (opcional)",
        placeholder="https://ejemplo.com/imagen.png",
        required=False
    )
    
    def __init__(self, scheduled_time, channel_id, scheduler):
        super().__init__()
        self.scheduled_time = scheduled_time
        self.channel_id = channel_id
        self.scheduler = scheduler
    
    async def on_submit(self, interaction: discord.Interaction):
        self.scheduler.add_message(
            self.scheduled_time,
            self.channel_id,
            self.msg_title.value,
            self.body.value,
            self.thumbnail.value if self.thumbnail.value else None,
            self.image.value if self.image.value else None
        )
        
        await interaction.response.send_message(
            f"✅ Mensaje programado para {self.scheduled_time.strftime('%d/%m/%Y %H:%M')}",
            ephemeral=True
        )

class ScheduleCommands(commands.Cog):
    def __init__(self, bot, scheduler):
        self.bot = bot
        self.scheduler = scheduler
    
    @app_commands.command(name="schedule", description="Programar un mensaje (solo administradores)")
    @app_commands.describe(
        fecha="Fecha en formato DD/MM/YYYY",
        hora="Hora en formato HH:MM (24h)",
        canal="Canal donde se enviará el mensaje"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def schedule(self, interaction: discord.Interaction,
                      fecha: str, hora: str, canal: discord.TextChannel):
        try:
            datetime_str = f"{fecha} {hora}"
            scheduled_time = datetime.strptime(datetime_str, "%d/%m/%Y %H:%M")
            
            # Permitir programar si falta al menos 30 segundos
            now = datetime.now()
            if scheduled_time <= now:
                time_diff = (now - scheduled_time).total_seconds()
                await interaction.response.send_message(
                    f"❌ La fecha y hora deben ser en el futuro.\n"
                    f"⏰ Hora actual: {now.strftime('%d/%m/%Y %H:%M:%S')}\n"
                    f"📅 Hora programada: {scheduled_time.strftime('%d/%m/%Y %H:%M')}\n"
                    f"⏱️ Diferencia: {int(time_diff)} segundos en el pasado",
                    ephemeral=True
                )
                return
            
            modal = ScheduleModal(scheduled_time, canal.id, self.scheduler)
            await interaction.response.send_modal(modal)
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Formato incorrecto. Usa:\n"
                "- Fecha: DD/MM/YYYY (ej: 31/12/2025)\n"
                "- Hora: HH:MM (ej: 15:30)",
                ephemeral=True
            )
    
    @schedule.error
    async def schedule_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ Necesitas permisos de administrador.", 
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(ScheduleCommands(bot, bot.scheduler))
