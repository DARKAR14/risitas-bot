import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta

class PollModal(discord.ui.Modal, title="Crear Encuesta"):
    poll_title = discord.ui.TextInput(
        label="Título de la encuesta",
        placeholder="¿Cuál es tu juego favorito?",
        required=True,
        max_length=256
    )
    
    description = discord.ui.TextInput(
        label="Descripción (opcional)",
        style=discord.TextStyle.paragraph,
        placeholder="Vota por tu juego favorito de 2024",
        required=False,
        max_length=1000
    )
    
    def __init__(self, channel, emojis, duration_minutes, interaction_user):
        super().__init__()
        self.channel = channel
        self.emojis = emojis
        self.duration_minutes = duration_minutes
        self.interaction_user = interaction_user
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Crear embed de la encuesta
            embed = discord.Embed(
                title=f"📊 {self.poll_title.value}",
                description=self.description.value if self.description.value else "",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            # Agregar tiempo límite
            end_time = datetime.now() + timedelta(minutes=self.duration_minutes)
            embed.add_field(
                name="⏰ Tiempo límite",
                value=f"<t:{int(end_time.timestamp())}:R>",
                inline=False
            )
            
            # Agregar opciones con emojis
            options_text = "\n".join([f"{emoji} - Reacciona para votar" for emoji in self.emojis])
            embed.add_field(
                name="📝 Opciones",
                value=options_text,
                inline=False
            )
            
            embed.set_footer(text=f"Encuesta creada por {self.interaction_user.display_name}")
            
            # Enviar encuesta
            poll_message = await self.channel.send(embed=embed)
            
            # Agregar reacciones
            for emoji in self.emojis:
                try:
                    await poll_message.add_reaction(emoji)
                except discord.HTTPException:
                    pass
            
            # Confirmar al usuario
            await interaction.followup.send(
                f"✅ Encuesta creada en {self.channel.mention}\n"
                f"⏰ Durará {self.duration_minutes} minutos\n"
                f"🔗 [Ir a la encuesta]({poll_message.jump_url})",
                ephemeral=True
            )
            
            # Esperar el tiempo límite
            await asyncio.sleep(self.duration_minutes * 60)
            
            # Obtener mensaje actualizado
            try:
                poll_message = await self.channel.fetch_message(poll_message.id)
                
                # Contar votos
                results = {}
                for reaction in poll_message.reactions:
                    if str(reaction.emoji) in self.emojis:
                        # Restar 1 porque el bot también reacciona
                        count = reaction.count - 1
                        results[str(reaction.emoji)] = count
                
                # Crear embed de resultados
                result_embed = discord.Embed(
                    title=f"📊 Resultados: {self.poll_title.value}",
                    description=self.description.value if self.description.value else "",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                
                # Ordenar resultados
                sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
                
                # Total de votos
                total_votes = sum(results.values())
                
                # Mostrar resultados
                results_text = []
                for emoji, count in sorted_results:
                    percentage = (count / total_votes * 100) if total_votes > 0 else 0
                    bar_length = int(percentage / 5)  # Barra de 20 caracteres máximo
                    bar = "█" * bar_length + "░" * (20 - bar_length)
                    results_text.append(f"{emoji} `{bar}` {count} votos ({percentage:.1f}%)")
                
                result_embed.add_field(
                    name=f"📈 Resultados Finales ({total_votes} votos totales)",
                    value="\n".join(results_text) if results_text else "No hubo votos",
                    inline=False
                )
                
                # Ganador
                if sorted_results and sorted_results[0][1] > 0:
                    winner = sorted_results[0]
                    result_embed.add_field(
                        name="🏆 Ganador",
                        value=f"{winner[0]} con {winner[1]} votos",
                        inline=False
                    )
                
                result_embed.set_footer(text=f"Encuesta finalizada • Creada por {self.interaction_user.display_name}")
                
                # Enviar resultados
                await self.channel.send(embed=result_embed)
                
                # Editar mensaje original para indicar que finalizó
                original_embed = poll_message.embeds[0]
                original_embed.color = discord.Color.red()
                original_embed.title = f"🔒 {self.poll_title.value} [FINALIZADA]"
                await poll_message.edit(embed=original_embed)
                
            except discord.NotFound:
                pass  # El mensaje fue eliminado
            except Exception as e:
                print(f"Error procesando resultados: {e}")
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error creando encuesta: {str(e)}",
                ephemeral=True
            )

class PollCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="poll", description="Crear una encuesta con emojis y tiempo límite")
    @app_commands.describe(
        canal="Canal donde se publicará la encuesta",
        emojis="Emojis separados por espacios (ej: 👍 👎 🤔)",
        duracion="Duración en minutos (1-1440)",
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def poll(self, interaction: discord.Interaction, 
                   canal: discord.TextChannel,
                   emojis: str,
                   duracion: int):
        """Crea una encuesta interactiva"""
        
        # Validar duración
        if duracion < 1 or duracion > 1440:  # Máximo 24 horas
            await interaction.response.send_message(
                "❌ La duración debe estar entre 1 y 1440 minutos (24 horas).",
                ephemeral=True
            )
            return
        
        # Procesar emojis
        emoji_list = emojis.split()
        
        if len(emoji_list) < 2:
            await interaction.response.send_message(
                "❌ Debes proporcionar al menos 2 emojis separados por espacios.\n"
                "Ejemplo: `👍 👎` o `🔴 🟢 🔵`",
                ephemeral=True
            )
            return
        
        if len(emoji_list) > 20:
            await interaction.response.send_message(
                "❌ Máximo 20 opciones permitidas.",
                ephemeral=True
            )
            return
        
        # Abrir modal
        modal = PollModal(canal, emoji_list, duracion, interaction.user)
        await interaction.response.send_modal(modal)
    
    @app_commands.command(name="quickpoll", description="Encuesta rápida Sí/No")
    @app_commands.describe(
        canal="Canal donde se publicará",
        pregunta="Pregunta de la encuesta",
        duracion="Duración en minutos (default: 5)"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def quickpoll(self, interaction: discord.Interaction,
                       canal: discord.TextChannel,
                       pregunta: str,
                       duracion: int = 5):
        """Crea una encuesta rápida Sí/No"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Crear embed
            embed = discord.Embed(
                title=f"📊 {pregunta}",
                description="Reacciona para votar",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            end_time = datetime.now() + timedelta(minutes=duracion)
            embed.add_field(
                name="⏰ Finaliza",
                value=f"<t:{int(end_time.timestamp())}:R>",
                inline=False
            )
            
            embed.add_field(
                name="📝 Opciones",
                value="✅ - Sí\n❌ - No",
                inline=False
            )
            
            embed.set_footer(text=f"Encuesta por {interaction.user.display_name}")
            
            # Enviar
            poll_msg = await canal.send(embed=embed)
            await poll_msg.add_reaction("✅")
            await poll_msg.add_reaction("❌")
            
            await interaction.followup.send(
                f"✅ Encuesta rápida creada en {canal.mention}",
                ephemeral=True
            )
            
            # Esperar
            await asyncio.sleep(duracion * 60)
            
            # Resultados
            try:
                poll_msg = await canal.fetch_message(poll_msg.id)
                
                yes_count = 0
                no_count = 0
                
                for reaction in poll_msg.reactions:
                    if str(reaction.emoji) == "✅":
                        yes_count = reaction.count - 1
                    elif str(reaction.emoji) == "❌":
                        no_count = reaction.count - 1
                
                total = yes_count + no_count
                
                result_embed = discord.Embed(
                    title=f"📊 Resultados: {pregunta}",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                
                if total > 0:
                    yes_percent = (yes_count / total * 100)
                    no_percent = (no_count / total * 100)
                    
                    result_embed.add_field(
                        name="✅ Sí",
                        value=f"{yes_count} votos ({yes_percent:.1f}%)",
                        inline=True
                    )
                    
                    result_embed.add_field(
                        name="❌ No",
                        value=f"{no_count} votos ({no_percent:.1f}%)",
                        inline=True
                    )
                    
                    winner = "✅ Sí" if yes_count > no_count else "❌ No" if no_count > yes_count else "🤝 Empate"
                    result_embed.add_field(
                        name="🏆 Resultado",
                        value=winner,
                        inline=False
                    )
                else:
                    result_embed.description = "No hubo votos"
                
                result_embed.set_footer(text=f"Total de votos: {total}")
                
                await canal.send(embed=result_embed)
                
                # Marcar como finalizada
                original_embed = poll_msg.embeds[0]
                original_embed.color = discord.Color.red()
                original_embed.title = f"🔒 {pregunta} [FINALIZADA]"
                await poll_msg.edit(embed=original_embed)
                
            except:
                pass
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
    
    @poll.error
    async def poll_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ Necesitas permisos para gestionar mensajes.",
                ephemeral=True
            )
    @quickpoll.error
    async def quickpoll_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ Necesitas permisos para gestionar mensajes.",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(PollCommands(bot))
