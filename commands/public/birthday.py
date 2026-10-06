import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from config import Config
from datetime import datetime
from utils.embed_templates import birthday_announcement_payload


def birthday_date_error(dia, mes):
    if mes < 1 or mes > 12:
        return "❌ El mes debe estar entre 1 y 12."
    if dia < 1 or dia > 31:
        return "❌ El día debe estar entre 1 y 31."
    try:
        datetime(2000, mes, dia)
    except ValueError:
        return f"❌ La fecha {dia}/{mes} no es válida."
    return None

class BirthdayCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="cumpleaños", description="Registra tu fecha de cumpleaños")
    @app_commands.describe(
        dia="Día de nacimiento (1-31)",
        mes="Mes de nacimiento (1-12)"
    )
    async def cumpleanos(self, interaction: discord.Interaction, dia: int, mes: int):
        """Registra el cumpleaños del usuario"""
        
        error = birthday_date_error(dia, mes)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return
        
        # Guardar cumpleaños en MongoDB
        self.bot.db.save_birthday(
            user_id=interaction.user.id,
            day=dia,
            month=mes,
            username=interaction.user.name,
            display_name=interaction.user.display_name
        )
        
        # Nombre del mes
        meses = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        
        embed = discord.Embed(
            title="🎂 Cumpleaños Registrado",
            description=f"¡Tu cumpleaños ha sido guardado exitosamente!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📅 Fecha",
            value=f"{dia} de {meses[mes]}",
            inline=True
        )
        
        embed.add_field(
            name="🎉 Recordatorio",
            value="El bot te felicitará automáticamente ese día",
            inline=False
        )
        
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        print(f"🎂 Cumpleaños registrado en MongoDB: {interaction.user.name} - {dia}/{mes}")
    
    @app_commands.command(name="setcumpleaños", description="Registra o actualiza el cumpleaños de otro usuario")
    @app_commands.guild_only()
    @app_commands.describe(
        usuario="Usuario cuyo cumpleaños quieres registrar",
        dia="Día de nacimiento (1-31)",
        mes="Mes de nacimiento (1-12)",
    )
    async def setcumpleanos(self, interaction: discord.Interaction, usuario: discord.Member, dia: int, mes: int):
        """Solo administradores del servidor o el desarrollador pueden registrar a otros."""
        # Check at execution time too; command visibility is not authorization.
        # Do not restrict default_permissions to admins: the developer may not be one.
        if interaction.guild_id is None or not (
            interaction.user.id == Config.DEVELOPER_ID or interaction.permissions.administrator
        ):
            await interaction.response.send_message(
                "❌ Solo un administrador del servidor o el desarrollador puede usar este comando.",
                ephemeral=True,
            )
            return

        error = birthday_date_error(dia, mes)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            await asyncio.to_thread(
                self.bot.db.save_birthday,
                user_id=usuario.id,
                day=dia,
                month=mes,
                username=usuario.name,
                display_name=usuario.display_name,
            )
        except Exception as error:
            print(f"[ERROR] No se pudo guardar el cumpleaños: {type(error).__name__}")
            await interaction.followup.send(
                "❌ No se pudo guardar el cumpleaños en MongoDB. Inténtalo de nuevo.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"✅ Cumpleaños de {usuario.mention} guardado: **{dia}/{mes}**.",
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(name="micumpleaños", description="Ver tu cumpleaños registrado")
    async def micumpleanos(self, interaction: discord.Interaction):
        """Muestra el cumpleaños del usuario"""
        birthday = self.bot.db.get_birthday(interaction.user.id)
        
        if not birthday:
            await interaction.response.send_message(
                "❌ No tienes un cumpleaños registrado.\n"
                "Usa `/cumpleaños` para registrarlo.",
                ephemeral=True
            )
            return
        
        dia = birthday["day"]
        mes = birthday["month"]
        
        meses = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        
        # Calcular días restantes
        today = datetime.now()
        this_year = datetime(today.year, mes, dia)
        
        if this_year < today:
            next_birthday = datetime(today.year + 1, mes, dia)
        else:
            next_birthday = this_year
        
        days_left = (next_birthday - today).days
        
        embed = discord.Embed(
            title="🎂 Tu Cumpleaños",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📅 Fecha",
            value=f"{dia} de {meses[mes]}",
            inline=True
        )
        
        embed.add_field(
            name="⏳ Faltan",
            value=f"{days_left} días",
            inline=True
        )
        
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="cumpleañeros", description="Ver todos los cumpleaños del mes")
    async def cumpleaneros(self, interaction: discord.Interaction):
        """Muestra cumpleaños del mes actual"""
        await interaction.response.defer()
        
        today = datetime.now()
        current_month = today.month
        
        meses = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        
        # Filtrar cumpleaños del mes desde MongoDB
        month_birthdays = self.bot.db.get_birthdays_by_month(current_month)
        
        if not month_birthdays:
            await interaction.followup.send(
                f"📅 No hay cumpleaños registrados en {meses[current_month]}."
            )
            return
        
        # Ordenar por día
        month_birthdays.sort(key=lambda x: x["day"])
        
        embed = discord.Embed(
            title=f"🎂 Cumpleaños de {meses[current_month].capitalize()}",
            description=f"Cumpleañeros del mes actual",
            color=discord.Color.gold()
        )
        
        birthday_list = []
        for birthday in month_birthdays:
            try:
                user = await self.bot.fetch_user(birthday["user_id"])
                birthday_list.append(f"🎉 **{birthday['day']}** - {user.mention}")
            except:
                birthday_list.append(f"🎉 **{birthday['day']}** - {birthday['display_name']}")
        
        embed.add_field(
            name=f"📅 {len(month_birthdays)} cumpleañeros",
            value="\n".join(birthday_list),
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="borrarcumpleaños", description="Eliminar tu cumpleaños registrado")
    async def borrarcumpleanos(self, interaction: discord.Interaction):
        """Elimina el cumpleaños del usuario"""
        deleted = self.bot.db.delete_birthday(interaction.user.id)
        
        if not deleted:
            await interaction.response.send_message(
                "❌ No tienes un cumpleaños registrado.",
                ephemeral=True
            )
            return
        
        await interaction.response.send_message(
            "✅ Tu cumpleaños ha sido eliminado de MongoDB.",
            ephemeral=True
        )
        print(f"🗑️ Cumpleaños eliminado de MongoDB: {interaction.user.name}")
    
    async def check_birthdays_today(self, settings=None, today=None):
        """Verifica y envía felicitaciones de cumpleaños"""
        import asyncio
        import pytz
        if settings is None:
            settings = (await asyncio.to_thread(self.bot.db.birthday_settings().read))["settings"]
        if not settings["enabled"] or not settings["channel_id"]:
            return
        
        birthday_channel = self.bot.get_channel(int(settings["channel_id"]))
        if not birthday_channel:
            return
        
        today = today or datetime.now(pytz.timezone(settings["timezone"]))
        birthdays_today = self.bot.db.get_birthdays_today(today.day, today.month)
        
        for birthday in birthdays_today:
            try:
                user = await self.bot.fetch_user(birthday["user_id"])
                
                payload = birthday_announcement_payload(
                    user_mention=user.mention,
                    avatar_url=user.display_avatar.url,
                    settings=settings,
                )
                embed = discord.Embed.from_dict(payload["embed"])
                
                await birthday_channel.send(
                    content=payload["content"],
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions(
                        everyone=False,
                        users=[user] if settings["mention_user"] else False,
                        roles=[discord.Object(id=int(settings["role_id"]))]
                        if settings["mention_role"] and settings["role_id"] else False,
                        replied_user=False,
                    ),
                )
                
                print(f"🎂 Felicitación enviada a {user.name}")
                
            except Exception as e:
                print(f"❌ Error enviando felicitación: {e}")


async def setup(bot):
    await bot.add_cog(BirthdayCommands(bot))
