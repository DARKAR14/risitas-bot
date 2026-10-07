import discord

from config import Config


BIRTHDAY_ANNOUNCEMENT = {
    "content": "🎂 ¡Hoy es el <@&{role_id}> de {user_mention}!",
    "title": "🎉 ¡Feliz cumple pai!",
    "description": "Que lo goces bacano 🎊",
    "color": 0x58B5FF,
    "image_url": (
        "https://images-ext-1.discordapp.net/external/"
        "lzhGE070LOFf8PlJD6P2_HV-5dP3lIWZqGJFrRzADU8/"
        "https/64.media.tumblr.com/e027f49565a711594c7c7b9e208c0749/"
        "0c580185984e1497-5b/s500x750/d5421285cd553ffd862487bc8072aa134e7e8f65.gif"
    ),
}


def birthday_announcement_payload(
    user_mention="@Usuario",
    avatar_url="https://cdn.discordapp.com/embed/avatars/0.png",
    settings=None,
):
    template = settings if settings is not None else BIRTHDAY_ANNOUNCEMENT
    role_id = template.get("role_id", Config.BIRTHDAY_ROLE_ID) or 0
    values = {"role_id": str(role_id), "user_mention": str(user_mention), "avatar_url": str(avatar_url)}
    def render(text):
        import re
        # Missing role IDs must never become an invalid Discord mention (<@&0>).
        if not role_id:
            text = text.replace("<@&{role_id}>", "cumpleaños")
        return re.sub(r"\{(role_id|user_mention|avatar_url)\}", lambda match: values[match[1]], text)
    embed = discord.Embed(
        title=render(template["title"]) or None,
        description=render(template["description"]) or None,
        color=template["color"],
    )
    if template["image_url"]:
        embed.set_image(url=render(template["image_url"]))
    thumbnail = template.get("thumbnail_url", "{avatar_url}")
    if thumbnail:
        embed.set_thumbnail(url=render(thumbnail))
    if template.get("footer"):
        embed.set_footer(text=render(template["footer"]))
    if template.get("author"):
        embed.set_author(name=render(template["author"]))
    for field in template.get("fields", []):
        embed.add_field(name=render(field["name"]), value=render(field["value"]), inline=field["inline"])

    return {
        "content": render(template["content"]),
        "embed": embed.to_dict(),
        "placeholders": {
            "user_mention": "Usuario que cumple años",
            "avatar_url": "Avatar del usuario",
            "role_id": "BIRTHDAY_ROLE_ID",
        },
    }
