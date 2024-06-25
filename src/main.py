import discord, asyncio
from discord.ext import commands
from datetime import datetime

bot = commands.Bot('.', intents=discord.Intents.all())

@bot.command(name="load", hidden=True)
async def load_cog(ctx, *, cog: str):
    try:
        await bot.load_extension(cog)
    except (commands.ExtensionAlreadyLoaded, commands.ExtensionNotFound, commands.NoEntryPointError,
            commands.ExtensionFailed) as e:
        await bot.reload_extension(cog)
    finally:
        await ctx.send(f"Extensión {cog} recargada con éxito.")

@bot.command(name='kill',hidden=True)
async def kill(ctx):
    await ctx.send("Apagando bot...")
    await bot.close()

@bot.event
async def on_ready():
    print(f'Sesión inciada: {bot.user.name} - {bot.user.id}')
    print(f'Versión de discord.py: {discord.__version__}')
    await bot.load_extension('cronos')


async def main():
    with open('token.txt') as f:
        token = f.read()
    await bot.start(token)

asyncio.run(main())
