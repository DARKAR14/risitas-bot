import asyncio

from bot import DiscordBot
from config import Config


async def run():
    """Inicia primero el servicio web y luego la conexion con Discord."""
    Config.validate()
    bot = DiscordBot()

    # Render necesita que el proceso escuche en PORT aunque Discord siga iniciando.
    await bot.api_server.start()

    try:
        await bot.start(Config.DISCORD_TOKEN, reconnect=True)
    finally:
        if not bot.is_closed():
            await bot.close()


def main():
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
