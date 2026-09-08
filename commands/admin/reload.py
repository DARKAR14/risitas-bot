import discord
from discord import app_commands
from discord.ext import commands
import importlib
import sys

class ReloadCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Mapa centralizado: nombre → (ruta del módulo, clase, *args extra)
    MODULES = {
        "admin":    ("commands.admin.admin",    "AdminCommands",    []),
        "poll":     ("commands.admin.poll",     "PollCommands",     []),
        "presence": ("commands.admin.presence", "PresenceCommands", ["presence_manager"]),
        "schedule": ("commands.admin.schedule", "ScheduleCommands", ["scheduler"]),
        "movies":   ("commands.admin.movies",   "MovieCommands",    []),
        "birthday": ("commands.public.birthday","BirthdayCommands", []),
        "ship":     ("commands.public.ship",    "Ship",             []),
        "setship":  ("commands.dev.setship",    "SetShip",          []),
    }

    @app_commands.command(name="reload", description="Recargar comandos y sincronizar con Discord")
    async def reload_command(self, interaction: discord.Interaction):
        from config import Config

        if interaction.user.id != Config.DEVELOPER_ID:
            await interaction.response.send_message("❌ Solo el desarrollador puede usar este comando.", ephemeral=True)
            return

        await interaction.response.send_message("⏳ Recargando comandos...", ephemeral=True)

        reloaded, errors = [], []

        # 1. Recargar config
        importlib.reload(sys.modules["config"]) if "config" in sys.modules else importlib.import_module("config")

        # 2. Recargar cada módulo
        for mod_name, (module_path, cog_class_name, extra_attrs) in self.MODULES.items():
            try:
                # Quitar cog existente
                for cog_name, cog in list(self.bot.cogs.items()):
                    if hasattr(cog, "__module__") and module_path in cog.__module__:
                        await self.bot.remove_cog(cog_name)
                        break

                # Recargar módulo
                if module_path in sys.modules:
                    importlib.reload(sys.modules[module_path])
                else:
                    importlib.import_module(module_path)

                # Instanciar y añadir cog
                module = sys.modules[module_path]
                cog_class = getattr(module, cog_class_name)
                extra_args = [getattr(self.bot, attr) for attr in extra_attrs]
                await self.bot.add_cog(cog_class(self.bot, *extra_args))

                reloaded.append(mod_name)

            except Exception as e:
                errors.append(f"{mod_name}: {e}")

        # 3. Sincronizar con Discord
        synced = await self.bot.tree.sync()

        # 4. Responder
        embed = discord.Embed(
            title="🔄 Recarga Completada",
            description="Los comandos han sido recargados y sincronizados",
            color=discord.Color.green() if not errors else discord.Color.orange()
        )
        embed.add_field(name=f"✅ Módulos Recargados ({len(reloaded)})", value=", ".join(reloaded) or "Ninguno", inline=False)
        embed.add_field(name="📡 Comandos Sincronizados", value=f"{len(synced)} comandos en Discord", inline=False)
        if errors:
            embed.add_field(name="⚠️ Errores", value="\n".join(errors)[:1000], inline=False)
        embed.set_footer(text="Disponible inmediatamente en Discord")

        await interaction.edit_original_response(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(ReloadCommands(bot))