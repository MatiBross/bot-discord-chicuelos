import discord
from discord.ext import commands
import os
import sqlite3
import random
import requests

# --- CONFIGURACIÓN DE APIS ---
TMDB_API_KEY = os.environ.get('TMDB_API_KEY') 
RAWG_API_KEY = os.environ.get('RAWG_API_KEY')

# Configuración de Intents
intents = discord.Intents.default()
intents.voice_states = True 
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

ID_CANAL = 1446630362917896243

@bot.event
async def on_ready():
    configurar_bd()
    print(f'Bot conectado como: {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"🌲 Se han sincronizado {len(synced)} comandos Slash.")
    except Exception as e:
        print(e)


# ---------AVISOS DE CANALES------------
@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel == after.channel:
        return
    
    channel = bot.get_channel(ID_CANAL)
    canal_publico = bot.get_channel(1499208975307112548)

    if after.channel is not None:

        if after.channel.name == "General":
            await channel.send(f"Se acabó la tranquilidad, {member.mention} ha llegado al canal de voz.")
        elif after.channel.name == "Musiquita":
            await channel.send(f"{member.mention} está aquí. Si pone Lali, lo baneamos.")
        elif after.channel.name == "Canal-publico":
            await canal_publico.send(f"{member.mention} se unió al canal público")


# ________RULETA DE JUEGOS__________

def conectar_bd():
    # CREA LA BD "RULETA"
    conn = sqlite3.connect('ruleta.db')
    return conn

def configurar_bd():
    # SE CONECTA Y CREA UNA TABLA
    conn = conectar_bd()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS opciones_ruleta (
            nombre TEXT PRIMARY KEY
        )
    ''')
    conn.commit()
    conn.close()

# 1. COMANDO PARA AGREGAR OPCIONES
@bot.hybrid_command(name='agregar', description='Agrega una opción a la lista.')
async def agregar_opcion(ctx, *, opcion: str):
    """Agrega una opción a la lista."""
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        # Insertamos el juego (el (?) es por seguridad para evitar inyección SQL)
        cursor.execute("INSERT INTO opciones_ruleta (nombre) VALUES (?)", (opcion,))
        conn.commit()
        conn.close()
        await ctx.send(f'✅ Joya, agregué **{opcion}** a la lista.')
    except sqlite3.IntegrityError:
        await ctx.send(f'⚠️ Epa, **{opcion}** ya estaba en la lista.')

# 2. COMANDO PARA ELIMINAR JUEGOS
@bot.hybrid_command(name='eliminar', description='Elimina una opción de la lista.')
async def eliminar_opcion(ctx, *, opcion: str):
    """Elimina una opción de la lista."""
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM opciones_ruleta WHERE nombre = ?", (opcion,))
    
    # Verificamos si realmente borró algo (rowcount > 0)
    if cursor.rowcount > 0:
        await ctx.send(f'🗑️ Listo, **{opcion}** eliminado. Ya no lo volveremos a hacer.')
    else:
        await ctx.send(f'❌ No encontré **{opcion}** en la lista. Fíjate si lo escribiste bien.')
    
    conn.commit()
    conn.close()

# 3. COMANDO PARA VER LA LISTA
@bot.hybrid_command(name='lista', description='Muestra todas las opciones disponibles.')
async def ver_lista(ctx):
    """Muestra todas las opciones disponibles."""
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre FROM opciones_ruleta")
    opciones = cursor.fetchall() # Esto nos devuelve una lista de tuplas: [('LoL',), ('CSGO',)]
    conn.close()

    if not opciones:
        await ctx.send('📭 La lista está vacía. Usá `!agregar <Nombre>` para agregar opciones a la ruleta.')
        return

    # Formateamos bonito: sacamos el texto de las tuplas y los unimos
    lista_texto = "\n".join([f"• {j[0]}" for j in opciones])
    
    # Creamos un Embed (tarjeta con diseño)
    embed = discord.Embed(title="🎮 Lista de opciones", description=lista_texto, color=discord.Color.blue())
    await ctx.send(embed=embed)

# 4. COMANDO DE LA RULETA
@bot.hybrid_command(name='ruleta', description='Elige una opción al azar de la lista.')
async def tirar_ruleta(ctx):
    """Elige una opción al azar de la base de datos."""
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre FROM opciones_ruleta")
    opciones = cursor.fetchall()
    conn.close()

    if not opciones:
        await ctx.send('🤷‍♂️ No hay opciones en la lista para elegir.')
        return

    elegido = random.choice(opciones)[0] # [0] porque viene como tupla ('Juego',)
    await ctx.send(f'🎲 La ruleta giró y el destino eligió: **{elegido}** 🏆')

#5. COMANDO PARA LIMPIAR LA LISTA
@bot.hybrid_command(name='limpiar', description='Limpia todas las opciones de la lista.')
async def limpiar_lista(ctx):
    """Limpia todas las opciones de la lista."""
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM opciones_ruleta")
    conn.commit()
    conn.close()
    await ctx.send('🧹 La lista ha sido limpiada. Ahora está vacía.')

# --- COMANDO DE PELÍCULAS (TMDB) ---
@bot.hybrid_command(name='peli', description='Busca información de una película.')
async def buscar_peli(ctx, *, nombre: str):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={nombre}&language=es-ES"
    response = requests.get(url).json()

    if not response['results']:
        return await ctx.send(f"No encontré ninguna película que se llame '{nombre}'.")

    movie = response['results'][0]
    titulo = movie['title']
    original = movie['original_title']
    sinopsis = movie['overview'] or "Sin descripción disponible."
    poster = f"https://image.tmdb.org/t/p/w500{movie['poster_path']}"
    rating = movie['vote_average']
    fecha = movie['release_date']

    embed = discord.Embed(title=titulo, description=sinopsis, color=discord.Color.red())
    embed.set_image(url=poster)
    embed.add_field(name="🎬 Título original", value=original, inline=True)
    embed.add_field(name="⭐ Calificación", value=rating, inline=True)
    embed.add_field(name="📅 Lanzamiento", value=fecha, inline=True)
    embed.set_footer(text="Información provista por TMDB")

    await ctx.send(embed=embed)

# --- COMANDO DE SERIES (TMDB) ---
@bot.hybrid_command(name='serie', description='Busca información de una serie de TV.')
async def buscar_serie(ctx, *, nombre: str):
    # El endpoint cambia a /search/tv
    url = f"https://api.themoviedb.org/3/search/tv?api_key={TMDB_API_KEY}&query={nombre}&language=es-ES"
    response = requests.get(url).json()

    if not response['results']:
        return await ctx.send(f"No encontré ninguna serie que se llame '{nombre}'.")

    serie = response['results'][0]
    titulo = serie['name']
    original = serie['original_name']
    sinopsis = serie['overview'] or "Sin descripción disponible."
    poster = f"https://image.tmdb.org/t/p/w500{serie['poster_path']}"
    rating = serie['vote_average']
    estreno = serie['first_air_date']

    embed = discord.Embed(title=titulo, description=sinopsis, color=discord.Color.dark_magenta())
    if serie['poster_path']:
        embed.set_image(url=poster)
    embed.add_field(name="🎬 Título original", value=original, inline=True)
    embed.add_field(name="⭐ Rating", value=rating, inline=True)
    embed.add_field(name="📅 Primera emisión", value=estreno, inline=True)
    embed.set_footer(text="Información de TMDB")

    await ctx.send(embed=embed)

# --- COMANDO DE JUEGOS (RAWG) ---
@bot.hybrid_command(name='juego', description='Busca información de un videojuego.')
async def buscar_juego(ctx, *, nombre: str):
    url = f"https://api.rawg.io/api/games?key={RAWG_API_KEY}&search={nombre}"
    response = requests.get(url).json()

    if not response['results']:
        return await ctx.send(f"No encontré el juego '{nombre}'.")

    game = response['results'][0]
    nombre_juego = game['name']
    fecha_lanzamiento = game.get('released', 'N/A')
    imagen = game.get('background_image')
    rating = game.get('metacritic', 'N/A')
    
    # RAWG no da una descripción larga en el endpoint de búsqueda, 
    # pero podemos mostrar las plataformas
    plataformas = ", ".join([p['platform']['name'] for p in game['platforms']])

    embed = discord.Embed(title=nombre_juego, color=discord.Color.green())
    if imagen:
        embed.set_image(url=imagen)
    embed.add_field(name="📅 Lanzamiento", value=fecha_lanzamiento, inline=True)
    embed.add_field(name="🎮 Plataformas", value=plataformas, inline=False)
    embed.add_field(name="📈 Metacritic", value=rating, inline=True)
    embed.set_footer(text="Información provista por RAWG.io")

    await ctx.send(embed=embed)

# --- COMANDO DE LIBROS (Google Books) ---
@bot.hybrid_command(name='libro', description='Busca información de un libro.')
async def buscar_libro(ctx, *, nombre: str):
    url = f"https://www.googleapis.com/books/v1/volumes?q={nombre}"
    response = requests.get(url).json()

    if 'items' not in response:
        return await ctx.send(f"No encontré el libro '{nombre}'.")

    # Tomamos el primer resultado
    book_info = response['items'][0]['volumeInfo']
    titulo = book_info.get('title', 'Título no disponible')
    autores = ", ".join(book_info.get('authors', ['Autor desconocido']))
    descripcion = book_info.get('description', 'Sin descripción.')
    # Cortamos la descripción si es muy larga para que no rompa el Embed
    descripcion = (descripcion[:300] + '...') if len(descripcion) > 300 else descripcion
    
    # Conseguimos la portada
    portada = book_info.get('imageLinks', {}).get('thumbnail')

    embed = discord.Embed(title=titulo, description=descripcion, color=discord.Color.orange())
    if portada:
        # Google devuelve links http, Discord prefiere https
        embed.set_thumbnail(url=portada.replace("http://", "https://"))
    
    embed.add_field(name="✍️ Autor/es", value=autores, inline=True)
    embed.add_field(name="📖 Páginas", value=book_info.get('pageCount', 'N/A'), inline=True)
    embed.set_footer(text="Información de Google Books")

    await ctx.send(embed=embed)


TOKEN = os.environ.get('DISCORD_TOKEN') 

if TOKEN is None:
    print("ERROR DE CONFIGURACIÓN: La variable de entorno 'DISCORD_TOKEN' no está configurada.")
else:
    bot.run(TOKEN)
