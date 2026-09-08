import discord
from discord.ext import commands, tasks
from config import Config
from utils.database import Database
from utils.twitch import TwitchAPI
from utils.scheduler import MessageScheduler
from utils.presence_manager import PresenceManager
from datetime import datetime
import asyncio
import pytz
from pathlib import Path

from utils.api_server import BotAPIServer
from utils.command_manager import CommandManager
from utils.cloudflare_tunnel import CloudflareTunnel

class DiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(command_prefix="!", intents=intents)
        
        self.db = Database()
        self.twitch = TwitchAPI()
        self.scheduler = MessageScheduler()
        self.presence_manager = PresenceManager()
        self.custom_presence_active = False
        
        # Control de sesión de stream para clips
        self.stream_session_active = False
        self.stream_session_start = None
        self.clips_sent_this_session = 0
        
        # Control de cumpleaños
        self.last_birthday_check = None
        self.command_manager = CommandManager(self)
        self.api_server = BotAPIServer(self)
        self.cloudflare_tunnel = CloudflareTunnel()

    async def load_command_extensions(self):
        """Carga automáticamente las extensiones ubicadas en commands/."""
        commands_dir = Path(__file__).parent / "commands"
        loaded = []
        skipped = []

        for file_path in sorted(commands_dir.rglob("*.py")):
            if file_path.name == "__init__.py" or "__pycache__" in file_path.parts:
                continue

            module_name = ".".join(file_path.relative_to(commands_dir.parent).with_suffix("").parts)

            try:
                module = __import__(module_name, fromlist=["setup"])
                if not callable(getattr(module, "setup", None)):
                    skipped.append(module_name)
                    continue

                await self.load_extension(module_name)
                loaded.append(module_name)
            except Exception as error:
                print(
                    f"[ERROR] No se pudo cargar {module_name}: "
                    f"{type(error).__name__}: {error}",
                    flush=True,
                )

        print(f"[OK] Extensiones cargadas automaticamente: {len(loaded)}", flush=True)
        for module_name in loaded:
            print(f"  - {module_name}", flush=True)
        if skipped:
            print(
                "[INFO] Modulos sin setup() omitidos: " + ", ".join(skipped),
                flush=True,
            )
    
    async def setup_hook(self):
        """Se ejecuta antes de que el bot se conecte"""
        # Descubrir y cargar automáticamente los módulos de commands/.
        await self.load_command_extensions()

        # Este listener no es un comando y vive en utils/.
        from utils.reaction_handler import ReactionHandler
        await self.add_cog(ReactionHandler(self))

        # Guardar el catálogo completo y ocultar comandos desactivados.
        self.command_manager.capture()
        self.command_manager.apply_saved_state()

        # En Render, la API HTTP ya se inicia antes de conectar con Discord.
        await self.cloudflare_tunnel.start()
        
        # Iniciar tareas en segundo plano
        self.check_twitch.start()
        self.check_scheduled_messages.start()
        self.check_new_clips.start()
        self.check_birthdays.start()
        
        # Sincronizar comandos con Discord
        synced = await self.tree.sync()
        print(f"✅ {len(synced)} comandos sincronizados con Discord")
    
    async def on_ready(self):
        """Se ejecuta cuando el bot está listo"""
        print(f"✅ Bot conectado como {self.user}")
        print(f"🆔 ID: {self.user.id}")
        
        # Conectar a MongoDB
        db_connected = self.db.connect()
        if not db_connected:
            print("❌ No se pudo conectar a MongoDB. El bot continuará sin sistema de cumpleaños.")
        
        # Obtener token de Twitch
        await self.twitch.get_token()
        print(f"🎮 Conectado a Twitch API")
        
        # Restaurar presencia guardada o establecer por defecto
        await self.restore_presence()
        
        # Forzar primera verificación de Twitch después de 10 segundos
        await asyncio.sleep(10)
        await self.force_twitch_check()

    async def close(self):
        """Libera la API y la base de datos al apagar el bot."""
        await self.cloudflare_tunnel.close()
        await self.api_server.close()
        self.db.close()
        await super().close()
    
    async def force_twitch_check(self):
        """Fuerza una verificación inmediata de Twitch"""
        try:
            print("🔍 Verificación manual de Twitch...")
            
            # Si hay presencia personalizada, no actualizar
            saved = self.presence_manager.get_presence()
            if saved and self.custom_presence_active:
                print(f"ℹ️ Presencia personalizada activa: {saved['type']} - {saved['text']}")
                return
            
            is_live = await self.twitch.is_live()
            
            if is_live:
                await self.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.watching,
                        name=f"🔴 {Config.TWITCH_CHANNEL}",
                        url=f"https://www.twitch.tv/{Config.TWITCH_CHANNEL}"
                    )
                )
                print(f"✅ Presencia establecida: Viendo 🔴 {Config.TWITCH_CHANNEL}")
            else:
                await self.change_presence(
                    activity=discord.Game(name="DARKAR14")
                )
                print(f"✅ Presencia establecida: En espera")
        except Exception as e:
            print(f"❌ Error en verificación forzada: {e}")
            import traceback
            traceback.print_exc()
    
    async def restore_presence(self):
        """Restaura la presencia guardada del archivo JSON"""
        saved_presence = self.presence_manager.get_presence()
        
        if saved_presence:
            tipo = saved_presence.get("type")
            texto = saved_presence.get("text")
            
            activity_map = {
                "playing": discord.Game(name=texto),
                "watching": discord.Activity(type=discord.ActivityType.watching, name=texto),
                "listening": discord.Activity(type=discord.ActivityType.listening, name=texto),
            }
            
            if tipo in activity_map:
                await self.change_presence(activity=activity_map[tipo])
                self.custom_presence_active = True
                print(f"🎭 Presencia personalizada restaurada: {tipo} - {texto}")
                print(f"💡 Usa /clearpresence para desactivarla y permitir detección automática de Twitch")
            else:
                print(f"⚠️ Tipo de presencia desconocido: {tipo}")
                self.custom_presence_active = False
        else:
            self.custom_presence_active = False
            print("ℹ️ No hay presencia personalizada guardada")
            print("🔄 Se usará detección automática de Twitch")
    
    @tasks.loop(minutes=2)
    async def check_twitch(self):
        """Verifica el estado del stream cada 2 minutos"""
        try:
            # Verificar si hay presencia personalizada ACTIVA
            if self.custom_presence_active:
                saved = self.presence_manager.get_presence()
                if saved:
                    return
            
            print("🔍 Verificando estado de Twitch...")
            
            # Verificar si está en vivo
            is_live = await self.twitch.is_live()
            
            if is_live:
                # Usar ActivityType.watching para mostrar "Viendo"
                await self.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.watching,
                        name=f"🔴 {Config.TWITCH_CHANNEL}",
                        url=f"https://www.twitch.tv/{Config.TWITCH_CHANNEL}"
                    )
                )
                print(f"✅ Presencia actualizada: Viendo 🔴 {Config.TWITCH_CHANNEL}")
            else:
                await self.change_presence(
                    activity=discord.Game(name="DARKAR14")
                )
                print(f"⚪ Presencia actualizada: En espera")
        except Exception as e:
            print(f"❌ Error verificando Twitch: {e}")
            import traceback
            traceback.print_exc()
    
    @check_twitch.before_loop
    async def before_check_twitch(self):
        """Espera a que el bot esté listo antes de verificar Twitch"""
        await self.wait_until_ready()
        # Esperar 30 segundos antes de la primera verificación
        import asyncio
        await asyncio.sleep(30)
        print("⏰ Loop de Twitch iniciado - Verificando cada 2 minutos")
    
    @tasks.loop(minutes=1)
    async def check_scheduled_messages(self):
        """Envía mensajes programados"""
        pending = self.scheduler.get_pending_messages()
        
        for msg in pending:
            try:
                channel = self.get_channel(msg["channel_id"])
                if channel:
                    embed = discord.Embed(
                        title=msg["title"],
                        description=msg["body"],
                        color=discord.Color.blue()
                    )
                    
                    if msg.get("thumbnail"):
                        embed.set_thumbnail(url=msg["thumbnail"])
                    if msg.get("image"):
                        embed.set_image(url=msg["image"])
                    
                    embed.set_footer(text="Mensaje programado")
                    
                    await channel.send(embed=embed)
                    print(f"📨 Mensaje programado enviado a {channel.name}")
            except Exception as e:
                print(f"❌ Error enviando mensaje programado: {e}")
    
    @tasks.loop(minutes=5)
    async def check_new_clips(self):
        """Verifica clips nuevos de Twitch cada 5 minutos."""
        try:
            # Solo verificar si hay canal de clips configurado
            if Config.CLIPS_CHANNEL_ID == 0:
                print("⚠️ CLIPS_CHANNEL_ID no configurado en .env")
                return
            
            clips_channel = self.get_channel(Config.CLIPS_CHANNEL_ID)
            if not clips_channel:
                print(f"⚠️ No se encontró el canal con ID: {Config.CLIPS_CHANNEL_ID}")
                return
            
            # Verificar si el stream está en vivo
            is_live = await self.twitch.is_live()
            
            # Gestión de sesión de stream
            if is_live and not self.stream_session_active:
                # Stream comenzó - Enviar mensaje de inicio
                self.stream_session_active = True
                self.stream_session_start = datetime.now()
                self.clips_sent_this_session = 0
                
                fecha_inicio = self.stream_session_start.strftime("%d/%m/%Y %H:%M")
                
                embed = discord.Embed(
                    title="🔴 Stream en Vivo",
                    description=f"**{Config.TWITCH_CHANNEL}** comenzó a transmitir",
                    color=discord.Color.red(),
                    timestamp=self.stream_session_start
                )
                
                embed.add_field(
                    name="📅 Fecha",
                    value=fecha_inicio,
                    inline=True
                )
                
                embed.add_field(
                    name="📺 Ver Stream",
                    value=f"[Ir a Twitch](https://www.twitch.tv/{Config.TWITCH_CHANNEL})",
                    inline=True
                )
                
                await clips_channel.send(
                    f"╔══════════════════════════════════╗\n"
                    f"║  **🎬 INICIO CLIPS - {fecha_inicio}**  ║\n"
                    f"╚══════════════════════════════════╝",
                    embed=embed
                )
                
                print(f"🔴 Sesión de clips iniciada: {fecha_inicio}")
            
            elif not is_live and self.stream_session_active:
                # Stream terminó - Enviar mensaje de fin
                self.stream_session_active = False
                fecha_fin = datetime.now().strftime("%d/%m/%Y %H:%M")
                
                if self.stream_session_start:
                    duracion = datetime.now() - self.stream_session_start
                    horas = int(duracion.total_seconds() // 3600)
                    minutos = int((duracion.total_seconds() % 3600) // 60)
                    duracion_str = f"{horas}h {minutos}m" if horas > 0 else f"{minutos}m"
                else:
                    duracion_str = "N/A"
                
                embed = discord.Embed(
                    title="⚫ Stream Finalizado",
                    description=f"**{Config.TWITCH_CHANNEL}** terminó la transmisión",
                    color=discord.Color.dark_grey(),
                    timestamp=datetime.now()
                )
                
                embed.add_field(
                    name="📅 Inicio",
                    value=self.stream_session_start.strftime("%d/%m/%Y %H:%M") if self.stream_session_start else "N/A",
                    inline=True
                )
                
                embed.add_field(
                    name="📅 Fin",
                    value=fecha_fin,
                    inline=True
                )
                
                embed.add_field(
                    name="⏱️ Duración",
                    value=duracion_str,
                    inline=True
                )
                
                embed.add_field(
                    name="🎬 Clips Enviados",
                    value=f"{self.clips_sent_this_session} clips",
                    inline=True
                )
                
                await clips_channel.send(
                    f"╔══════════════════════════════════╗\n"
                    f"║  **🏁 FIN CLIPS - {fecha_fin}**  ║\n"
                    f"╚══════════════════════════════════╝",
                    embed=embed
                )
                
                print(f"⚫ Sesión de clips finalizada: {duracion_str}, {self.clips_sent_this_session} clips enviados")
                self.stream_session_start = None
                self.clips_sent_this_session = 0
            
            # Verificar clips solo si hay sesión activa
            if not self.stream_session_active:
                return
            
            # Obtener clips nuevos
            new_clips = await self.twitch.check_new_clips()
            
            if new_clips:
                print(f"🎬 Encontrados {len(new_clips)} clips nuevos!")
            
            for clip in new_clips:
                try:
                    # Crear embed del clip
                    embed = discord.Embed(
                        title=f"🎬 {clip.get('title', 'Sin título')}",
                        url=clip.get('url'),
                        description=f"Clip creado por **{clip.get('creator_name', 'Desconocido')}**",
                        color=discord.Color.purple(),
                        timestamp=discord.utils.utcnow()
                    )
                    
                    # Thumbnail del clip
                    if clip.get('thumbnail_url'):
                        embed.set_image(url=clip['thumbnail_url'])
                    
                    # Información adicional
                    embed.add_field(
                        name="👀 Vistas",
                        value=f"{clip.get('view_count', 0):,}",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="⏱️ Duración",
                        value=f"{clip.get('duration', 0):.1f}s",
                        inline=True
                    )
                    
                    if clip.get('game_name'):
                        embed.add_field(
                            name="🎮 Juego",
                            value=clip['game_name'],
                            inline=True
                        )
                    
                    embed.set_footer(
                        text=f"Creado por {clip.get('creator_name', 'Desconocido')}",
                        icon_url="https://static.twitchcdn.net/assets/favicon-32-e29e246c157142c94346.png"
                    )
                    
                    # Enviar al canal con el link
                    await clips_channel.send(
                        content=f"🔥 **Nuevo clip de {Config.TWITCH_CHANNEL}!**\n{clip.get('url')}",
                        embed=embed
                    )
                    
                    self.clips_sent_this_session += 1
                    print(f"✅ Clip enviado: {clip.get('title')} (Total sesión: {self.clips_sent_this_session})")
                    
                except Exception as e:
                    print(f"❌ Error enviando clip: {e}")
                    import traceback
                    traceback.print_exc()
                    
        except Exception as e:
            print(f"❌ Error verificando clips: {e}")
            import traceback
            traceback.print_exc()
    
    @check_new_clips.before_loop
    async def before_check_clips(self):
        """Espera a que el bot esté listo antes de verificar clips"""
        await self.wait_until_ready()
        # Esperar 1 minuto antes de la primera verificación.
        import asyncio
        await asyncio.sleep(60)
        print("🎬 Verificación de clips iniciada (cada 5 minutos)")
    
    @tasks.loop(hours=1)
    async def check_birthdays(self):
        """Verifica cumpleaños cada hora"""
        try:
            colombia_tz = pytz.timezone('America/Bogota')
            now = datetime.now(colombia_tz)
            current_date = now.strftime("%Y-%m-%d")
            
            # Solo verificar una vez al día
            if self.last_birthday_check == current_date:
                return
            
            # Verificar solo a las 7 AM hora colombiana
            if now.hour != 7:
                return
            
            print("🎂 Verificando cumpleaños del día...")
            
            # Obtener el cog de cumpleaños
            birthday_cog = self.get_cog("BirthdayCommands")
            if birthday_cog:
                await birthday_cog.check_birthdays_today()
                self.last_birthday_check = current_date
                print(f"✅ Verificación de cumpleaños completada")
            
        except Exception as e:
            print(f"❌ Error verificando cumpleaños: {e}")
            import traceback
            traceback.print_exc()
    
    @check_birthdays.before_loop
    async def before_check_birthdays(self):
        """Espera a que el bot esté listo antes de verificar cumpleaños"""
        await self.wait_until_ready()
        print("🎂 Sistema de cumpleaños iniciado")
