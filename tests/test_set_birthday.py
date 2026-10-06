import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import discord
from pymongo.errors import AutoReconnect

from config import Config
from commands.public.birthday import BirthdayCommands
from utils.database import Database


class SetBirthdayTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = Database()
        self.db.birthdays = Mock()
        self.cog = BirthdayCommands(SimpleNamespace(db=self.db))
        self.target = SimpleNamespace(id=222, name="persona", display_name="Persona", mention="<@222>")
        self.developer = patch.object(Config, "DEVELOPER_ID", 999)
        self.developer.start()
        self.addCleanup(self.developer.stop)

    def interaction(self, user_id=111, admin=False, guild_id=123):
        return SimpleNamespace(user=SimpleNamespace(id=user_id), guild_id=guild_id,
            permissions=discord.Permissions(administrator=admin),
            response=SimpleNamespace(send_message=AsyncMock(), defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()))

    async def invoke(self, interaction, day=15, month=8):
        await BirthdayCommands.setcumpleanos.callback(self.cog, interaction, self.target, day, month)

    async def test_admin_saves_selected_user_not_invoker_and_upserts(self):
        interaction = self.interaction(admin=True)
        await self.invoke(interaction)
        self.db.birthdays.update_one.assert_called_once_with(
            {"user_id": 222}, {"$set": {"user_id": 222, "day": 15, "month": 8,
                "username": "persona", "display_name": "Persona"}}, upsert=True)
        interaction.response.defer.assert_awaited_once_with(ephemeral=True)
        self.assertTrue(interaction.followup.send.call_args.kwargs["ephemeral"])
        self.assertIn("15/8", interaction.followup.send.call_args.args[0])

    async def test_developer_without_admin_permissions_can_save_leap_day(self):
        await self.invoke(self.interaction(user_id=999), 29, 2)
        self.assertEqual(self.db.birthdays.update_one.call_args.args[1]["$set"]["day"], 29)

    async def test_ordinary_user_and_dm_cannot_write(self):
        for interaction in (self.interaction(), self.interaction(user_id=999, guild_id=None)):
            await self.invoke(interaction)
            interaction.response.send_message.assert_awaited_once()
            interaction.response.defer.assert_not_awaited()
        self.db.birthdays.update_one.assert_not_called()

    async def test_invalid_dates_never_write(self):
        for day, month in ((0, 5), (32, 1), (2, 0), (2, 13), (31, 4), (30, 2)):
            with self.subTest(day=day, month=month):
                interaction = self.interaction(admin=True)
                await self.invoke(interaction, day, month)
                interaction.response.send_message.assert_awaited_once()
                interaction.response.defer.assert_not_awaited()
        self.db.birthdays.update_one.assert_not_called()

    async def test_mongo_failure_does_not_report_success(self):
        self.db.birthdays.update_one.side_effect = AutoReconnect("test unavailable")
        interaction = self.interaction(admin=True)
        await self.invoke(interaction)
        self.assertIn("No se pudo guardar", interaction.followup.send.call_args.args[0])
        self.assertTrue(interaction.followup.send.call_args.kwargs["ephemeral"])

    async def test_self_registration_still_uses_invoker(self):
        interaction = self.interaction()
        interaction.user = SimpleNamespace(id=111, name="yo", display_name="Yo",
            display_avatar=SimpleNamespace(url="https://cdn.discordapp.com/embed/avatars/0.png"))
        await BirthdayCommands.cumpleanos.callback(self.cog, interaction, 15, 8)
        self.assertEqual(self.db.birthdays.update_one.call_args.args[0], {"user_id": 111})

    def test_slash_command_has_required_target_day_month_and_allows_dev_override(self):
        command = BirthdayCommands.setcumpleanos
        self.assertEqual(command.name, "setcumpleaños")
        self.assertTrue(command.guild_only)
        self.assertEqual([p.name for p in command.parameters], ["usuario", "dia", "mes"])
        self.assertTrue(all(p.required for p in command.parameters))
        self.assertIsNone(command.default_permissions)
