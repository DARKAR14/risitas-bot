import discord
from discord import app_commands
from discord.ext import commands
import hashlib
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import aiohttp
import io
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Ship(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def download_avatar(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return Image.open(io.BytesIO(await resp.read())).convert("RGBA")

    def create_circle_avatar(self, avatar):
        size = 220
        avatar = avatar.resize((size, size))

        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)

        circle = Image.new("RGBA", (size, size))
        circle.paste(avatar, (0, 0), mask)

        glow = Image.new("RGBA", (size+30, size+30), (0,0,0,0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.ellipse((15,15,size+15,size+15), fill=(255,80,120,200))
        glow = glow.filter(ImageFilter.GaussianBlur(20))

        return circle, glow

    def get_phrase(self, percent):
        phrases = {
            (95, 100): [
                "💍 Esto ya es matrimonio. Vayan reservando iglesia.",
                "👑 El universo los creó el uno para el otro.",
                "💒 Solo falta la fecha de la boda.",
                "🌹 Romeo y Julieta se quedan cortos.",
            ],
            (80, 94): [
                "🔥 Hay química real aquí.",
                "💘 Esto huele a amor verdadero.",
                "✨ La conexión es innegable.",
                "🥰 Alguien debería confesarse ya.",
            ],
            (65, 79): [
                "💖 Nada mal… esto puede funcionar.",
                "😏 Hay chispa, solo falta atizarla.",
                "💌 Un café y esto despega.",
                "🌸 Potencial romántico detectado.",
            ],
            (45, 64): [
                "🤔 Fifty-fifty… la moneda está en el aire.",
                "😬 Podría funcionar… o no. Suerte.",
                "🎲 El destino aún no se decide.",
                "💫 Ni fu ni fa, pero nunca se sabe.",
            ],
            (25, 44): [
                "😅 Hay potencial… pero necesitan terapia.",
                "🛠️ Esto necesita mucho trabajo.",
                "😐 Como el arroz con leche: raro pero a algunos les gusta.",
                "🌧️ Hay nubarrones pero no todo está perdido.",
            ],
            (10, 24): [
                "💀 Esto está peligroso...",
                "🚑 Alguien va a salir herido.",
                "😬 Los astros dicen que no.",
                "🧊 Más fría que el Polo Norte esta relación.",
            ],
            (0, 9): [
                "🚨 Prohibido por la ley del amor.",
                "☠️ Ni en otra vida.",
                "🔥 El infierno se congela antes que esto funcione.",
                "💔 El amor no existe aquí.",
            ],
        }

        for (low, high), options in phrases.items():
            if low <= percent <= high:
                rng = random.Random(percent * 31337)
                return rng.choice(options)

        return "❓ Error cósmico."

    async def create_ship_image(self, user1, user2, percent):
        width, height = 900, 350
        IMAGE_PATH = os.path.join(BASE_DIR, "..", "..", "img", "naruto_bg.png")

        if os.path.exists(IMAGE_PATH):
            background = Image.open(IMAGE_PATH).resize((width, height)).convert("RGBA")
        else:
            background = Image.new("RGBA", (width, height), (255, 120, 120))

        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 120))
        background = Image.alpha_composite(background, overlay)

        avatar1 = await self.download_avatar(user1.display_avatar.url)
        avatar2 = await self.download_avatar(user2.display_avatar.url)

        circle1, glow1 = self.create_circle_avatar(avatar1)
        circle2, glow2 = self.create_circle_avatar(avatar2)

        background.paste(glow1, (120-15, 60-15), glow1)
        background.paste(circle1, (120, 60), circle1)
        background.paste(glow2, (560-15, 60-15), glow2)
        background.paste(circle2, (560, 60), circle2)

        draw = ImageDraw.Draw(background)

        heart = Image.new("RGBA", (200, 200), (0,0,0,0))
        heart_draw = ImageDraw.Draw(heart)
        heart_draw.polygon(
            [(100,180),(180,100),(150,50),(100,80),(50,50),(20,100)],
            fill=(255,50,100,255)
        )
        heart = heart.filter(ImageFilter.GaussianBlur(1))
        background.paste(heart, (350, 80), heart)

        try:
            font_big = ImageFont.truetype("arial.ttf", 60)
        except:
            font_big = ImageFont.load_default()

        text = f"{percent}%"
        bbox = draw.textbbox((0,0), text, font=font_big)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        draw.text(
            (450 - text_width//2, 170 - text_height//2),
            text, fill="white", font=font_big
        )

        buffer = io.BytesIO()
        background.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    @app_commands.command(name="ship", description="Calcula compatibilidad entre dos usuarios")
    async def ship(self, interaction: discord.Interaction, user1: discord.Member, user2: discord.Member):

        await interaction.response.defer()

        # Leer overrides desde el cog SetShip
        setship_cog = interaction.client.get_cog("SetShip")
        overrides = setship_cog.ship_overrides if setship_cog else {}

        key = frozenset({user1.id, user2.id})

        if key in overrides:
            percent = overrides[key]
        else:
            day_seed = discord.utils.utcnow().timetuple().tm_yday
            seed = f"{min(user1.id, user2.id)}-{max(user1.id, user2.id)}-{day_seed}"
            h = hashlib.sha256(seed.encode()).hexdigest()
            percent = int(h[:8], 16) % 101

        name1 = user1.display_name[:len(user1.display_name)//2]
        name2 = user2.display_name[len(user2.display_name)//2:]
        ship_name = name1 + name2

        phrase = self.get_phrase(percent)
        image_buffer = await self.create_ship_image(user1, user2, percent)
        file = discord.File(image_buffer, filename="ship.png")

        embed = discord.Embed(
            description=f"❤️ | El nombre del ship es **{ship_name}**\n"
                        f"❤️ | La compatibilidad es **{percent}%**\n\n"
                        f"{phrase}",
            color=discord.Color.from_rgb(255, 70, 120)
        )
        embed.set_image(url="attachment://ship.png")
        await interaction.followup.send(embed=embed, file=file)


async def setup(bot):
    await bot.add_cog(Ship(bot))