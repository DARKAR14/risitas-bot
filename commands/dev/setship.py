import discord
from discord import app_commands
from discord.ext import commands
import os
import json

DEVELOPER_ID = int(os.getenv("DEVELOPER_ID", 0))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OVERRIDES_PATH = os.path.join(BASE_DIR, "ship_overrides.json")


class SetShip(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.ship_overrides: dict[frozenset, int] = self._load_overrides()

    def _load_overrides(self) -> dict:
        if not os.path.exists(OVERRIDES_PATH):
            return {}
        with open(OVERRIDES_PATH, "r", encoding="utf-8") as f:
            raw: dict = json.load(f)
        return {
            frozenset(int(x) for x in k.split("-")): v
            for k, v in raw.items()
        }

    def _save_overrides(self) -> None:
        raw = {f"{min(k)}-{max(k)}": v for k, v in self.ship_overrides.items()}
        with open(OVERRIDES_PATH, "w", encoding="utf-8") as f:
            json.dump(raw, f, separators=(",", ":"))

    @app_commands.command(name="setship", description="[DEV] Fuerza el % de compatibilidad entre dos usuarios")
    @app_commands.describe(
        user1="Primer usuario",
        user2="Segundo usuario",
        percent="Porcentaje (0–100) o -1 para resetear",
    )
    async def setship(self, interaction: discord.Interaction, user1: discord.Member, user2: discord.Member, percent: int):
        if interaction.user.id != DEVELOPER_ID:
            await interaction.response.send_message("❌ Solo el desarrollador puede usar este comando.", ephemeral=True)
            return

        if percent != -1 and not (0 <= percent <= 100):
            await interaction.response.send_message("❌ El porcentaje debe estar entre **0** y **100** (o **-1** para resetear).", ephemeral=True)
            return

        key = frozenset({user1.id, user2.id})

        if percent == -1:
            self.ship_overrides.pop(key, None)
            self._save_overrides()
            await interaction.response.send_message(f"🔄 **{user1.display_name}** x **{user2.display_name}** reseteado.", ephemeral=True)
        else:
            self.ship_overrides[key] = percent
            self._save_overrides()
            await interaction.response.send_message(f"✅ **{user1.display_name}** x **{user2.display_name}** → **{percent}%**", ephemeral=True)


async def setup(bot):
    await bot.add_cog(SetShip(bot))