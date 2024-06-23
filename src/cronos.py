import discord
from discord.ext import commands
from datetime import date, time, datetime
import pytz
import sqlite3
import geopy.geocoders
from timezonefinder import TimezoneFinder
import re
import python_weather

    
def parse_time(time_string):
    """Devuelve una tupla de horas y minutos a partir de una cadena que represente una hora."""
    time_string = re.sub(r'[\W_]+', '', time_string)

    if not re.match('^[0-9]{1,4}([ap]m)?$', time_string):
        raise ValueError("This time isn't valid")

    num_of_num = sum([c.isdigit() for c in time_string])

    # The hour is either the first number or the first two numbers
    hour = int(time_string[:2]) if num_of_num in (2, 4) else int(time_string[:1])

    if hour > 23:
        raise ValueError("Hour above 23")

    # The minute is either the last two numbers or zero
    minute = int(time_string[num_of_num-2:num_of_num]) if num_of_num in (3, 4) else 0

    if minute > 59:
        raise ValueError("Minute above 59")

    if hour > 12:
        return hour, minute
    if hour == 12:
        return hour + (12 if 'am' in time_string else 0), minute
    if hour < 12:
        return hour + (12 if 'pm' in time_string else 0), minute


def get_time(hours, minutes, tz):
    """Devuelve un objeto de hora con zona horaria a partir de una zona horaria y una hora."""
    t = time(hours, minutes)
    d = date.today()
    naive = datetime.combine(d, t)
    aware = pytz.timezone(tz).localize(naive)
    return aware

def get_embed(name, value, title):
    embed = discord.Embed(color=discord.Color.green(), title=title)
    embed.add_field(name=name, value=value)
    return embed

def set_location(user_id, tz, city, conn):
    """Introduce (o cambia, si ya existe) la localización (ciudad) y zona horaria de un usuario en la base de datos."""
    cur = conn.cursor()
    cur.execute("SELECT timezone FROM users WHERE user_id=?", (user_id,))
    if cur.fetchone():
        cur.execute("UPDATE users SET timezone=?, city=? WHERE user_id=?", (tz, city, user_id))
    else:
        cur.execute("INSERT INTO users(user_id,timezone,city) VALUES(?,?,?)", (user_id, tz, city))
    conn.commit()

class Cronos(commands.Cog):
    db_file = 'cronos.db'

    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect(self.db_file)
        cur = self.conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
                                    user_id TEXT PRIMARY KEY,
                                    timezone TEXT,
                                    city TEXT,
                                    autotime INTEGER
                                    );              
                """)
        self.conn.commit()

    @commands.command(name='time', aliases=['hora', 't'])
    async def _time(self, ctx, *, time_str, tz_str=None):

        try:
            hours, minutes = parse_time(time_str)
        except ValueError:
            await ctx.send(f'Formato erróneo.')
            return
        hours = hours % 24

        if not tz_str:
            cur = self.conn.cursor()
            cur.execute("SELECT timezone FROM users WHERE user_id=?", (ctx.author.id,))
            tz_str = cur.fetchone()[0]

        aware = get_time(hours, minutes, tz_str)
        try:
            embed = get_embed('Hora', f'<t:{int(aware.timestamp())}:t>', 'Título')
        except Exception as e:
            print(e)
        await ctx.send(embed=embed)

    @commands.command(name='city', aliases=['ciudad'])
    async def _city(self, ctx, *,  city='Palencia'):
        geolocator = geopy.geocoders.Nominatim(user_agent='timezone_bot')
        location = geolocator.geocode(city)
        tz_finder = TimezoneFinder()
        tz = tz_finder.timezone_at(lng=location.longitude, lat=location.latitude)

        set_location(ctx.author.id, tz, city, self.conn)

        await ctx.send(f'Tu zona horaria es `{tz}`.')

    @commands.command(name='info')
    async def _info(self, ctx, *, user: discord.Member = None):
        if not user:
            user = ctx.author
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM users WHERE user_id=?', (user.id,))
        info = cur.fetchone()
        await ctx.send(f'Ciudad: {info[2]}. Zona horaria: {info[1]}')
        print(info)

    @commands.command(name='weather', aliases=['tiempo'])
    async def _weather(self, ctx, *, city=None):
        if not city:
            cur = self.conn.cursor()
            cur.execute('SELECT city FROM users WHERE user_id=?', (ctx.author.id,))
            city = cur.fetchone()[0]
        print(f'Fetching weather for {city}')
        async with python_weather.Client() as client:
            weather = await client.get(city)
            embed = discord.Embed(color=discord.Color.blue(),title=f'Tiempo en {city}')
            embed.add_field(name='🌡️ Temperatura', inline=False, value=f'{weather.temperature}°C')
            embed.add_field(name='💧 Humedad', inline=False, value=f'{weather.humidity}%')
            embed.add_field(name='🌧️ Precipitación', inline=False, value=f'{weather.precipitation}mm')
            embed.add_field(name='💨 Viento', inline=False, value=f'{weather.wind_speed}m/s')
            await ctx.send(embed=embed)
            

async def setup(bot):
    await bot.add_cog(Cronos(bot))
