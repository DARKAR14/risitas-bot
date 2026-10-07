import copy
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from pymongo.errors import DuplicateKeyError
from aiohttp.test_utils import TestClient, TestServer

from utils.birthday_settings import BirthdaySettings, SettingsConflict, defaults, validate_settings
from utils.embed_templates import birthday_announcement_payload
from utils.api_server import BotAPIServer
from commands.public.birthday import BirthdayCommands

CHANNEL = "123456789012345678"
ROLE = "223456789012345678"


class Collection:
    def __init__(self):
        self.document = None

    def find_one(self, query):
        return copy.deepcopy(self.document)

    def insert_one(self, document):
        if self.document:
            raise DuplicateKeyError("exists")
        self.document = copy.deepcopy(document)

    def update_one(self, query, update):
        matches = self.document and self.document["revision"] == query["revision"]
        if matches:
            self.document.update(copy.deepcopy(update["$set"]))
            self.document["revision"] += 1
        return SimpleNamespace(matched_count=int(bool(matches)))


def example():
    return {**defaults(), "channel_id": CHANNEL, "role_id": ROLE, "title": "Feliz día, {user_mention}",
            "description": "**Que disfrutes**\nTexto con {llaves literales sin variable}", "footer": "Comunidad"}


class SettingsTests(unittest.TestCase):
    def test_missing_role_never_renders_unknown_role_mention(self):
        settings = {**example(), "role_id": "", "description": "Feliz día"}
        payload = birthday_announcement_payload(settings=settings)
        self.assertEqual(payload["content"], "🎂 ¡Hoy es el cumpleaños de @Usuario!")
        with self.assertRaisesRegex(ValueError, "Selecciona un rol"):
            validate_settings(settings)
        validate_settings({**settings, "mention_role": False})

    def test_selected_role_is_preserved_in_mention(self):
        payload = birthday_announcement_payload(settings=example())
        self.assertIn(f"<@&{ROLE}>", payload["content"])

    def test_persists_exact_template_and_rejects_concurrent_overwrite(self):
        collection = Collection()
        store = BirthdaySettings(collection)
        settings = {**example(), "description": "**Que disfrutes**\nTexto original 🎂"}
        saved = store.save(settings, 0)
        self.assertEqual(saved["settings"], settings)
        self.assertEqual(BirthdaySettings(collection).read(), saved)
        with self.assertRaises(SettingsConflict):
            store.save(settings, 0)
        store.save({**settings, "title": "Otro título"}, 1)
        with self.assertRaises(SettingsConflict):
            store.save(settings, 1)

    def test_discord_limits_and_unknown_variables_are_rejected(self):
        settings = {**example(), "description": "Descripción"}
        for invalid in [{"title": "x" * 257}, {"description": "{unknown}"}, {"color": True},
                        {"image_url": "javascript:alert(1)"}, {"timezone": "bad-zone"},
                        {"fields": [{"name": "", "value": "a", "inline": False}]}]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_settings({**settings, **invalid})
        with self.assertRaises(ValueError):
            validate_settings({**settings, "description": "x" * 4096, "footer": "x" * 2048})


class BirthdayAPITests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.collection = Collection()
        self.store = BirthdaySettings(self.collection)
        role = SimpleNamespace(id=int(ROLE), name="Cumpleaños", is_default=lambda: False)
        self.channel = SimpleNamespace(id=int(CHANNEL), name="cumpleaños", send=AsyncMock(),
            permissions_for=lambda _: SimpleNamespace(view_channel=True, send_messages=True, embed_links=True))
        guild = SimpleNamespace(id=333333333333333333, name="Comunidad", me=object(), text_channels=[self.channel], roles=[role])
        self.user = SimpleNamespace(id=444444444444444444, mention="<@444444444444444444>", name="Persona",
                                    display_avatar=SimpleNamespace(url="https://cdn.discordapp.com/embed/avatars/0.png"))
        self.bot = SimpleNamespace(guilds=[guild], db=SimpleNamespace(birthday_settings=lambda: self.store,
            get_birthdays_today=lambda *_: [{"user_id": self.user.id}]),
            get_channel=lambda _: self.channel, fetch_user=AsyncMock(return_value=self.user))
        self.api = BotAPIServer(self.bot)
        self.api.api_key = "test-private-key"
        self.client = TestClient(TestServer(self.api.create_app()))
        await self.client.start_server()
        self.headers = {"X-API-Key": self.api.api_key}

    async def asyncTearDown(self):
        await self.client.close()

    async def test_preview_save_reload_and_actual_delivery_share_payload(self):
        settings = {**example(), "description": "**Feliz cumpleaños**", "mention_role": False}
        response = await self.client.post("/api/v1/birthday/preview", json={"settings": settings}, headers=self.headers)
        self.assertEqual(response.status, 200)
        preview = (await response.json())["preview"]
        self.assertIsNone(self.collection.document)
        response = await self.client.put("/api/v1/birthday/settings", json={"settings": settings, "revision": 0}, headers=self.headers)
        self.assertEqual(response.status, 200)
        saved = await response.json()
        response = await self.client.get("/api/v1/birthday/settings", headers=self.headers)
        self.assertEqual((await response.json())["settings"], saved["settings"])
        self.assertEqual(saved["preview"], preview)
        cog = BirthdayCommands(self.bot)
        await cog.check_birthdays_today()
        sent = self.channel.send.call_args.kwargs
        expected = birthday_announcement_payload(user_mention=self.user.mention, avatar_url=self.user.display_avatar.url, settings=settings)
        self.assertEqual(sent["content"], expected["content"])
        self.assertEqual(sent["embed"].to_dict(), expected["embed"])
        self.assertFalse(sent["allowed_mentions"].roles)
        self.assertFalse(sent["allowed_mentions"].everyone)

    async def test_auth_conflict_validation_and_unreachable_channel(self):
        settings = {**example(), "description": "Hola"}
        response = await self.client.put("/api/v1/birthday/settings", json={"settings": settings, "revision": 0})
        self.assertEqual(response.status, 401)
        response = await self.client.put("/api/v1/birthday/settings", json={"settings": settings, "revision": 0}, headers=self.headers)
        self.assertEqual(response.status, 200)
        response = await self.client.put("/api/v1/birthday/settings", json={"settings": settings, "revision": 0}, headers=self.headers)
        self.assertEqual(response.status, 409)
        response = await self.client.put("/api/v1/birthday/settings", json={"settings": {**settings, "channel_id": "999999999999999999"}, "revision": 1}, headers=self.headers)
        self.assertEqual(response.status, 400)
        self.assertEqual(self.store.read()["revision"], 1)
