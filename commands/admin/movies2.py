import discord
from discord import app_commands
from discord.ext import commands
from config import Config
import asyncio
from datetime import datetime, timedelta
import pytz
import json
import os

class ContinueButton(discord.ui.View):
    """Vista con botón para continuar al siguiente modal"""
    def __init__(self, cog, movie_num, movies_count, modal_classes):
        super().__init__(timeout=300)
        self.cog = cog
        self.movie_num = movie_num
        self.movies_count = movies_count
        self.modal_classes = modal_classes
    
    @discord.ui.button(label="Siguiente Película", style=discord.ButtonStyle.primary)
    async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.movie_num < self.movies_count:
            next_modal = self.modal_classes[self.movie_num + 1]()
            await interaction.response.send_modal(next_modal)
        else:
            await interaction.response.defer(ephemeral=True)
            await self.cog.create_movie_voting(interaction)

class MovieVoteView(discord.ui.View):
    """Vista para los botones de votación"""
    def __init__(self, num_movies, movies_data_dict):
        super().__init__(timeout=None)
        self.votes = {i: [] for i in range(1, num_movies + 1)}
        self.movies_data_dict = movies_data_dict
        self._create_buttons()
    
    def _create_buttons(self):
        for i in range(1, len(self.movies_data_dict) + 1):
            if i in self.movies_data_dict:
                button = discord.ui.Button(
                    label=self.movies_data_dict[i]['nombre'][:80],
                    style=discord.ButtonStyle.primary,
                    custom_id=f"movie_{i}"
                )
                button.callback = self._create_vote_callback(i)
                self.add_item(button)
    
    def _create_vote_callback(self, movie_id):
        async def vote_callback(interaction: discord.Interaction):
            user_id = interaction.user.id
            
            # Si ya votó por esta película -> quitar voto (toggle off)
            if user_id in self.votes[movie_id]:
                self.votes[movie_id].remove(user_id)
                movie_name = self.movies_data_dict[movie_id]['nombre']
                await interaction.response.send_message(
                    f"❌ Deseleccionaste: **{movie_name}**",
                    ephemeral=True
                )
                return

            # Al votar por una película, eliminar el voto del usuario en cualquier otra película
            for mid, voters in self.votes.items():
                if mid != movie_id and user_id in voters:
                    voters.remove(user_id)

            # Añadir el voto a la película seleccionada
            self.votes[movie_id].append(user_id)
            movie_name = self.movies_data_dict[movie_id]['nombre']
            await interaction.response.send_message(
                f"✅ Seleccionaste: **{movie_name}**",
                ephemeral=True
            )
        
        return vote_callback

class Movie1Modal(discord.ui.Modal, title="Información - Película 1"):
    nombre = discord.ui.TextInput(
        label="Nombre de la película",
        placeholder="Ej: El Planeta del Tesoro",
        required=True,
        max_length=256
    )
    imagen_url = discord.ui.TextInput(
        label="URL de la imagen (portada)",
        placeholder="https://ejemplo.com/imagen.jpg",
        required=True,
        max_length=500
    )
    trailer_url = discord.ui.TextInput(
        label="URL del trailer (opcional)",
        placeholder="https://youtube.com/...",
        required=False,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("MovieCommands")
        await cog.handle_movie_modal(interaction, 1, self.nombre.value, self.imagen_url.value, self.trailer_url.value)

class Movie2Modal(discord.ui.Modal, title="Información - Película 2"):
    nombre = discord.ui.TextInput(
        label="Nombre de la película",
        required=True,
        max_length=256
    )
    imagen_url = discord.ui.TextInput(
        label="URL de la imagen (portada)",
        required=True,
        max_length=500
    )
    trailer_url = discord.ui.TextInput(
        label="URL del trailer (opcional)",
        required=False,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("MovieCommands")
        await cog.handle_movie_modal(interaction, 2, self.nombre.value, self.imagen_url.value, self.trailer_url.value)

class Movie3Modal(discord.ui.Modal, title="Información - Película 3"):
    nombre = discord.ui.TextInput(
        label="Nombre de la película",
        required=True,
        max_length=256
    )
    imagen_url = discord.ui.TextInput(
        label="URL de la imagen (portada)",
        required=True,
        max_length=500
    )
    trailer_url = discord.ui.TextInput(
        label="URL del trailer (opcional)",
        required=False,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("MovieCommands")
        await cog.handle_movie_modal(interaction, 3, self.nombre.value, self.imagen_url.value, self.trailer_url.value)

class Movie4Modal(discord.ui.Modal, title="Información - Película 4"):
    nombre = discord.ui.TextInput(
        label="Nombre de la película",
        required=True,
        max_length=256
    )
    imagen_url = discord.ui.TextInput(
        label="URL de la imagen (portada)",
        required=True,
        max_length=500
    )
    trailer_url = discord.ui.TextInput(
        label="URL del trailer (opcional)",
        required=False,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("MovieCommands")
        await cog.handle_movie_modal(interaction, 4, self.nombre.value, self.imagen_url.value, self.trailer_url.value)

class Movie5Modal(discord.ui.Modal, title="Información - Película 5"):
    nombre = discord.ui.TextInput(
        label="Nombre de la película",
        required=True,
        max_length=256
    )
    imagen_url = discord.ui.TextInput(
        label="URL de la imagen (portada)",
        required=True,
        max_length=500
    )
    trailer_url = discord.ui.TextInput(
        label="URL del trailer (opcional)",
        required=False,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("MovieCommands")
        await cog.handle_movie_modal(interaction, 5, self.nombre.value, self.imagen_url.value, self.trailer_url.value)

class Movie6Modal(discord.ui.Modal, title="Información - Película 6"):
    nombre = discord.ui.TextInput(
        label="Nombre de la película",
        required=True,
        max_length=256
    )
    imagen_url = discord.ui.TextInput(
        label="URL de la imagen (portada)",
        required=True,
        max_length=500
    )
    trailer_url = discord.ui.TextInput(
        label="URL del trailer (opcional)",
        required=False,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("MovieCommands")
        await cog.handle_movie_modal(interaction, 6, self.nombre.value, self.imagen_url.value, self.trailer_url.value)

class Movie7Modal(discord.ui.Modal, title="Información - Película 7"):
    nombre = discord.ui.TextInput(
        label="Nombre de la película",
        required=True,
        max_length=256
    )
    imagen_url = discord.ui.TextInput(
        label="URL de la imagen (portada)",
        required=True,
        max_length=500
    )
    trailer_url = discord.ui.TextInput(
        label="URL del trailer (opcional)",
        required=False,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("MovieCommands")
        await cog.handle_movie_modal(interaction, 7, self.nombre.value, self.imagen_url.value, self.trailer_url.value)

class Movie8Modal(discord.ui.Modal, title="Información - Película 8"):
    nombre = discord.ui.TextInput(
        label="Nombre de la película",
        required=True,
        max_length=256
    )
    imagen_url = discord.ui.TextInput(
        label="URL de la imagen (portada)",
        required=True,
        max_length=500
    )
    trailer_url = discord.ui.TextInput(
        label="URL del trailer (opcional)",
        required=False,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("MovieCommands")
        await cog.handle_movie_modal(interaction, 8, self.nombre.value, self.imagen_url.value, self.trailer_url.value)

class Movie9Modal(discord.ui.Modal, title="Información - Película 9"):
    nombre = discord.ui.TextInput(
        label="Nombre de la película",
        required=True,
        max_length=256
    )
    imagen_url = discord.ui.TextInput(
        label="URL de la imagen (portada)",
        required=True,
        max_length=500
    )
    trailer_url = discord.ui.TextInput(
        label="URL del trailer (opcional)",
        required=False,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("MovieCommands")
        await cog.handle_movie_modal(interaction, 9, self.nombre.value, self.imagen_url.value, self.trailer_url.value)

class Movie10Modal(discord.ui.Modal, title="Información - Película 10"):
    nombre = discord.ui.TextInput(
        label="Nombre de la película",
        required=True,
        max_length=256
    )
    imagen_url = discord.ui.TextInput(
        label="URL de la imagen (portada)",
        required=True,
        max_length=500
    )
    trailer_url = discord.ui.TextInput(
        label="URL del trailer (opcional)",
        required=False,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("MovieCommands")
        await cog.handle_movie_modal(interaction, 10, self.nombre.value, self.imagen_url.value, self.trailer_url.value)

class MovieCommands(commands.Cog):
    MOVIES_JSON_FILE = "movies_data.json"
    
    def __init__(self, bot):
        self.bot = bot
        self.movies_data = {}
        self.movies_count = 0
        self.voting_view = None
        self.fecha_cierre_votacion = None
        
        # Cargar películas guardadas si existen
        self._load_movies_from_json()
    
    def _load_movies_from_json(self):
        """Carga películas del archivo JSON si existe"""
        if os.path.exists(self.MOVIES_JSON_FILE):
            try:
                with open(self.MOVIES_JSON_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.movies_data = {int(k): v for k, v in data.get("movies_data", {}).items()}
                    self.movies_count = data.get("movies_count", 0)
                    self.fecha_cierre_votacion = None
                    if data.get("fecha_cierre"):
                        self.fecha_cierre_votacion = datetime.strptime(data["fecha_cierre"], "%Y-%m-%d")
                    print(f"✅ Películas cargadas del JSON: {len(self.movies_data)} películas")
            except Exception as e:
                print(f"⚠️ Error cargando JSON: {e}")
    
    def _save_movies_to_json(self):
        """Guarda películas en archivo JSON minificado"""
        try:
            data = {
                "movies_data": {str(k): v for k, v in self.movies_data.items()},
                "movies_count": self.movies_count,
                "fecha_cierre": self.fecha_cierre_votacion.strftime("%Y-%m-%d") if self.fecha_cierre_votacion else None
            }
            with open(self.MOVIES_JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, separators=(',', ':'), ensure_ascii=False)
            print(f"✅ Películas guardadas en JSON")
        except Exception as e:
            print(f"❌ Error guardando JSON: {e}")
    
    def _delete_movies_json(self):
        """Borra el archivo JSON de películas"""
        try:
            if os.path.exists(self.MOVIES_JSON_FILE):
                os.remove(self.MOVIES_JSON_FILE)
                self.movies_data = {}
                self.movies_count = 0
                self.fecha_cierre_votacion = None
                print(f"✅ Archivo JSON eliminado")
        except Exception as e:
            print(f"❌ Error eliminando JSON: {e}")
    @app_commands.command(name="peliculas", description="Crear una votación de películas")
    @app_commands.describe(numero="Número de películas a votar (máximo 10)", fecha_cierre="Fecha de cierre de votaciones (YYYY-MM-DD)")
    @app_commands.checks.has_permissions(administrator=True)
    async def peliculas(self, interaction: discord.Interaction, numero: int, fecha_cierre: str = None):
        """Crea una votación de películas con embeds y toggles para votar"""
        
        if numero < 1 or numero > 10:
            await interaction.response.send_message(
                "❌ El número de películas debe estar entre 1 y 10.",
                ephemeral=True
            )
            return
        
        # Validar y guardar fecha de cierre
        self.fecha_cierre_votacion = None
        if fecha_cierre:
            try:
                from datetime import datetime as dt
                self.fecha_cierre_votacion = dt.strptime(fecha_cierre, "%Y-%m-%d")
            except ValueError:
                await interaction.response.send_message(
                    "❌ Formato de fecha inválido. Usa: YYYY-MM-DD (Ejemplo: 2026-02-19)",
                    ephemeral=True
                )
                return
        
        # Inicializar datos
        self.movies_data = {}
        self.movies_count = numero
        
        # Mapeo de modales
        modal_classes = [
            Movie1Modal, Movie2Modal, Movie3Modal, Movie4Modal, Movie5Modal,
            Movie6Modal, Movie7Modal, Movie8Modal, Movie9Modal, Movie10Modal
        ]
        
        # Mostrar el primer modal
        modal = modal_classes[0]()
        await interaction.response.send_modal(modal)
    
    async def handle_movie_modal(self, interaction: discord.Interaction, movie_num: int, 
                                 nombre: str, imagen_url: str, trailer_url: str):
        """Maneja el envío de cada modal de película"""
        
        # Guardar datos
        self.movies_data[movie_num] = {
            "nombre": nombre,
            "imagen_url": imagen_url,
            "trailer_url": trailer_url
        }
        
        # Mapeo de modales
        modal_classes = [
            None, Movie1Modal, Movie2Modal, Movie3Modal, Movie4Modal, Movie5Modal,
            Movie6Modal, Movie7Modal, Movie8Modal, Movie9Modal, Movie10Modal
        ]
        
        # Crear respuesta
        response_text = f"✅ **Película {movie_num}** guardada:\n**{nombre}**"
        
        if movie_num < self.movies_count:
            # Mostrar botón para continuar
            view = ContinueButton(self, movie_num, self.movies_count, modal_classes)
            await interaction.response.send_message(
                f"{response_text}\n\nHaz clic en el botón para agregar la siguiente película.",
                ephemeral=True,
                view=view
            )
        else:
            # Todas las películas ingresadas, crear votación
            await interaction.response.defer(ephemeral=True)
            await self.create_movie_voting(interaction)
    
    async def create_movie_voting(self, interaction: discord.Interaction):
        """Crea la votación con las películas ingresadas"""
        try:
            movies_channel = self.bot.get_channel(Config.MOVIES_CHANNEL_ID)
            
            if not movies_channel:
                await interaction.followup.send(
                    "❌ No se pudo encontrar el canal de películas.",
                    ephemeral=True
                )
                return
            
            # Crear mensaje inicial
            await movies_channel.send(
                content=(
                    f"<@&{Config.MOVIES_ROLE_ID}>\n\n"
                    f"🎬 **Miércoles de películas loquitos** 🎬\n\n"
                    f"Vean el trailer, den click al nombre de la película "
                    f"y elijan cuál se verá esta semana "   
                ),
                allowed_mentions=discord.AllowedMentions(roles=True)
            )
            
            # Mostrar fecha de cierre si existe
            if self.fecha_cierre_votacion:
                fecha_str = self.fecha_cierre_votacion.strftime("%d de %B de %Y")
                await movies_channel.send(
                    f"⏰ **Las votaciones se cierran el:** {fecha_str}"
                )
            
            # Crear embeds para cada película
            embeds = []
            for i in range(1, self.movies_count + 1):
                if i in self.movies_data:
                    movie = self.movies_data[i]
                    embed = discord.Embed(
                        title=f"🎬 {i}. {movie['nombre']}",
                        description="📌 **Película disponible para votar**",
                        color=discord.Color.purple()
                    )
                    
                    # Agregar imagen de portada
                    if movie['imagen_url']:
                        embed.set_image(url=movie['imagen_url'])
                    
                    # Agregar trailer
                    if movie['trailer_url']:
                        embed.add_field(
                            name="🎥 Ver Trailer",
                            value=f"[Haz clic aquí para ver el trailer]({movie['trailer_url']})",
                            inline=False
                        )
                    
                    # Agregar instrucciones
                    embed.add_field(
                        name="📋 Para votar",
                        value="Haz clic en el botón con el nombre de esta película en la sección de **Votación de Películas** abajo.",
                        inline=False
                    )
                    
                    embed.set_footer(text=f"Película {i} de {self.movies_count}")
                    
                    embeds.append(embed)
            
            # Enviar embeds
            if embeds:
                for i in range(0, len(embeds), 10):
                    await movies_channel.send(embeds=embeds[i:i+10])
            
            # Crear vista con botones DESPUÉS de tener los datos
            self.voting_view = MovieVoteView(self.movies_count, self.movies_data)
            
            # Guardar películas en JSON
            self._save_movies_to_json()
            
            # Enviar mensaje con botones
            await movies_channel.send(
                "🎬 **Votación de Películas** 🎬\nSelecciona las películas que quieres ver:",
                view=self.voting_view
            )
            
            await interaction.followup.send(
                f"✅ Votación de películas creada en {movies_channel.mention}\n"
                f"📽️ Número de películas: {self.movies_count}\n"
                f"⏰ Se enviará recordatorio en 50 minutos",
                ephemeral=True
            )
            
            # Zona horaria de Colombia
            colombian_tz = pytz.timezone('America/Bogota')
            
            # Esperar 50 minutos antes de enviar recordatorio
            await asyncio.sleep(50 * 60)
            
            # Enviar recordatorio
            announcement_channel = self.bot.get_channel(Config.MOVIES_ANNOUNCEMENT_CHANNEL_ID)
            if announcement_channel:
                current_time = datetime.now(colombian_tz)
                embed_reminder = discord.Embed(
                    title="⏰ Recordatorio de Votación",
                    description=f"||<@&{Config.MOVIES_ROLE_ID}> ||\n\n"
                                f"Las votaciones para la película del miércoles **se cerrarán en 10 minutos**.\n"
                                f"¡Ve al canal de películas y vota por tu película favorita!",
                    color=discord.Color.orange(),
                    timestamp=current_time
                )
                embed_reminder.add_field(
                    name="🕐 Hora Colombiana",
                    value=current_time.strftime("%H:%M:%S"),
                    inline=False
                )
                
                await announcement_channel.send(embed=embed_reminder)
            
            # Esperar 10 minutos más
            await asyncio.sleep(10 * 60)
            
            # Mostrar resultados
            embed_results = discord.Embed(
                title="🏆 Resultados de la Votación",
                description="Estas fueron las películas más votadas:",
                color=discord.Color.gold()
            )
            
            # Ordenar películas por votos
            sorted_movies = sorted(
                self.voting_view.votes.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )
            
            for idx, (movie_id, voters) in enumerate(sorted_movies, 1):
                if movie_id in self.movies_data:
                    movie_name = self.movies_data[movie_id]['nombre']
                    embed_results.add_field(
                        name=f"#{idx} - {movie_name}",
                        value=f"🗳️ {len(voters)} voto{'s' if len(voters) != 1 else ''}",
                        inline=False
                    )
            
            # Ganadora
            if sorted_movies:
                winner_id = sorted_movies[0][0]
                if winner_id in self.movies_data:
                    winner_name = self.movies_data[winner_id]['nombre']
                    embed_results.add_field(
                        name="🎬 Película Ganadora",
                        value=f"**{winner_name}**",
                        inline=False
                    )
            
            # Enviar resultados
            await movies_channel.send(embed=embed_results)
            
            if announcement_channel:
                await announcement_channel.send(embed=embed_results)
            
            # Borrar archivo JSON después de mostrar resultados
            self._delete_movies_json()
            
            print(f"✅ Votación completada")
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
            print(f"Error en peliculas: {e}")
    
    @peliculas.error
    async def peliculas_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ Solo los administradores pueden crear votaciones.",
                ephemeral=True
            )
    
    @app_commands.command(name="testpeliculas", description="Testear resultados de la votación (muestra ganador inmediatamente)")
    @app_commands.checks.has_permissions(administrator=True)
    async def testpeliculas(self, interaction: discord.Interaction):
        """Muestra los resultados de la votación actual sin esperar"""
        
        if not self.voting_view or not self.movies_data:
            await interaction.response.send_message(
                "❌ No hay una votación activa. Crea una primero con /peliculas",
                ephemeral=True
            )
            return
        
        try:
            movies_channel = self.bot.get_channel(Config.MOVIES_CHANNEL_ID)
            
            if not movies_channel:
                await interaction.response.send_message(
                    "❌ No se pudo encontrar el canal de películas.",
                    ephemeral=True
                )
                return
            
            # Zona horaria de Colombia
            colombian_tz = pytz.timezone('America/Bogota')
            current_time = datetime.now(colombian_tz)
            
            # Mostrar resultados
            embed_results = discord.Embed(
                title="🏆 Resultados de la Votación (TEST)",
                description="Estas fueron las películas más votadas:",
                color=discord.Color.gold(),
                timestamp=current_time
            )
            
            # Ordenar películas por votos
            sorted_movies = sorted(
                self.voting_view.votes.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )
            
            # Mostrar todos los votos
            for idx, (movie_id, voters) in enumerate(sorted_movies, 1):
                if movie_id in self.movies_data:
                    movie_name = self.movies_data[movie_id]['nombre']
                    voter_list = ", ".join([f"<@{uid}>" for uid in voters]) if voters else "Sin votos"
                    embed_results.add_field(
                        name=f"#{idx} - {movie_name}",
                        value=f"🗳️ {len(voters)} voto{'s' if len(voters) != 1 else ''}\n👥 {voter_list}",
                        inline=False
                    )
            
            # Ganadora
            if sorted_movies:
                winner_id = sorted_movies[0][0]
                if winner_id in self.movies_data:
                    winner_name = self.movies_data[winner_id]['nombre']
                    embed_results.add_field(
                        name="🎬 Película Ganadora",
                        value=f"**{winner_name}**",
                        inline=False
                    )
            else:
                embed_results.add_field(
                    name="⚠️ Sin votos",
                    value="Aún no hay votos registrados",
                    inline=False
                )
            
            embed_results.add_field(
                name="🕐 Hora Colombiana",
                value=current_time.strftime("%H:%M:%S"),
                inline=False
            )
            
            # Enviar resultados
            await movies_channel.send(embed=embed_results)
            
            await interaction.response.send_message(
                f"✅ Resultados de prueba enviados a {movies_channel.mention}",
                ephemeral=True
            )
            
            # Borrar archivo JSON después del test
            self._delete_movies_json()
            
            print(f"✅ Test de votación realizado")
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
            print(f"Error en testpeliculas: {e}")
