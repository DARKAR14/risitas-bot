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
):
    role_id = Config.BIRTHDAY_ROLE_ID
    template = BIRTHDAY_ANNOUNCEMENT
    embed = discord.Embed(
        title=template["title"],
        description=template["description"],
        color=template["color"],
    )
    embed.set_image(url=template["image_url"])
    embed.set_thumbnail(url=avatar_url)

    return {
        "content": template["content"].format(
            role_id=role_id,
            user_mention=user_mention,
        ),
        "embed": embed.to_dict(),
        "placeholders": {
            "user_mention": "Usuario que cumple años",
            "avatar_url": "Avatar del usuario",
            "role_id": "BIRTHDAY_ROLE_ID",
        },
    }
