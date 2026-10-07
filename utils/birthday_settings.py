"""Persistent birthday configuration; preview and delivery share one renderer."""
import copy
import re
from urllib.parse import urlparse

import pytz
from pymongo.errors import DuplicateKeyError

from config import Config
from utils.embed_templates import BIRTHDAY_ANNOUNCEMENT, birthday_announcement_payload


class SettingsConflict(ValueError):
    pass


def defaults():
    return {
        "enabled": True,
        "channel_id": str(Config.BIRTHDAY_CHANNEL_ID or ""),
        "role_id": str(Config.BIRTHDAY_ROLE_ID or ""),
        "hour": 7,
        "timezone": "America/Bogota",
        "mention_user": True,
        "mention_role": True,
        "content": BIRTHDAY_ANNOUNCEMENT["content"],
        "title": BIRTHDAY_ANNOUNCEMENT["title"],
        "description": BIRTHDAY_ANNOUNCEMENT["description"],
        "color": BIRTHDAY_ANNOUNCEMENT["color"],
        "image_url": BIRTHDAY_ANNOUNCEMENT["image_url"],
        "thumbnail_url": "{avatar_url}",
        "footer": "",
        "author": "",
        "fields": [],
    }


def validate_settings(value):
    if not isinstance(value, dict) or set(value) != set(defaults()):
        raise ValueError("Envía todos los campos de configuración, sin campos desconocidos.")
    result = copy.deepcopy(value)
    for key in ("enabled", "mention_user", "mention_role"):
        if not isinstance(result[key], bool):
            raise ValueError(f"{key} debe ser booleano.")
    for key in ("channel_id", "role_id"):
        if not isinstance(result[key], str) or (result[key] and not re.fullmatch(r"[1-9][0-9]{14,19}", result[key])):
            raise ValueError(f"{key} debe ser un ID de Discord válido.")
    if result["mention_role"] and not result["role_id"]:
        raise ValueError("Selecciona un rol para activar la mención del rol de cumpleaños.")
    if result["enabled"] and not result["channel_id"]:
        raise ValueError("Selecciona un canal antes de activar los cumpleaños.")
    for key, maximum in (("hour", 23), ("color", 0xFFFFFF)):
        if type(result[key]) is not int or not 0 <= result[key] <= maximum:
            raise ValueError(f"{key} está fuera del rango permitido.")
    if not isinstance(result["timezone"], str) or result["timezone"] not in pytz.all_timezones_set:
        raise ValueError("Zona horaria inválida.")
    limits = {"content": 2000, "title": 256, "description": 4096, "footer": 2048, "author": 256,
              "image_url": 2048, "thumbnail_url": 2048}
    for key, maximum in limits.items():
        text = result[key]
        if not isinstance(text, str) or len(text) > maximum:
            raise ValueError(f"{key}: máximo {maximum} caracteres.")
        for token in re.findall(r"\{([^{}]+)\}", text):
            if token not in {"user_mention", "avatar_url", "role_id"}:
                raise ValueError(f"Variable desconocida: {{{token}}}.")
    for key in ("image_url", "thumbnail_url"):
        url = result[key]
        if not url or url == "{avatar_url}":
            continue
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError(f"{key} debe ser una URL HTTPS pública.")
    fields = result["fields"]
    if not isinstance(fields, list) or len(fields) > 25:
        raise ValueError("El embed admite hasta 25 campos.")
    for field in fields:
        if not isinstance(field, dict) or set(field) != {"name", "value", "inline"}:
            raise ValueError("Campo del embed inválido.")
        if type(field["inline"]) is not bool:
            raise ValueError("inline debe ser booleano.")
        for key, maximum in (("name", 256), ("value", 1024)):
            if not isinstance(field[key], str) or not field[key].strip() or len(field[key]) > maximum:
                raise ValueError(f"Campo {key}: entre 1 y {maximum} caracteres.")
            if any(token not in {"user_mention", "avatar_url", "role_id"} for token in re.findall(r"\{([^{}]+)\}", field[key])):
                raise ValueError("Variable desconocida en un campo del embed.")
    # Validate rendered lengths too: substitutions can be longer than placeholders.
    preview = birthday_announcement_payload(user_mention="<@12345678901234567890>", settings=result)
    embed = preview["embed"]
    total = 0
    for text, maximum in [(embed.get("title", ""), 256), (embed.get("description", ""), 4096),
                          (embed.get("footer", {}).get("text", ""), 2048), (embed.get("author", {}).get("name", ""), 256)]:
        if len(text) > maximum:
            raise ValueError("El texto con las variables sustituidas excede el límite de Discord.")
        total += len(text)
    for field in embed.get("fields", []):
        if len(field["name"]) > 256 or len(field["value"]) > 1024:
            raise ValueError("Un campo supera el límite después de sustituir variables.")
        total += len(field["name"]) + len(field["value"])
    if total > 6000 or len(preview["content"]) > 2000:
        raise ValueError("El mensaje supera los límites de Discord (embed: 6000; mensaje: 2000).")
    if not total and not result["image_url"] and not result["thumbnail_url"]:
        raise ValueError("El embed necesita texto o una imagen.")
    return result


class BirthdaySettings:
    def __init__(self, collection):
        self.collection = collection

    def read(self):
        document = self.collection.find_one({"_id": "birthday"})
        return {"settings": {**defaults(), **(document or {}).get("settings", {})},
                "revision": (document or {}).get("revision", 0)}

    def save(self, settings, revision):
        settings = validate_settings(settings)
        if type(revision) is not int or revision < 0:
            raise ValueError("Revisión inválida; vuelve a cargar la configuración.")
        try:
            if revision == 0:
                self.collection.insert_one({"_id": "birthday", "settings": settings, "revision": 1})
            else:
                result = self.collection.update_one({"_id": "birthday", "revision": revision},
                    {"$set": {"settings": settings}, "$inc": {"revision": 1}})
                if not result.matched_count:
                    raise SettingsConflict("Otra persona modificó la configuración. Recarga antes de guardar.")
        except DuplicateKeyError as error:
            raise SettingsConflict("Otra persona modificó la configuración. Recarga antes de guardar.") from error
        return {"settings": settings, "revision": revision + 1}
