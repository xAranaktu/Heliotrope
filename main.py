# Work with Python 3.6
import logging
import discord
import datetime
from environs import Env

from commands import wiki

import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.WARNING)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

env = Env()
env.read_env()

DEBUG = env.bool("DEBUG", False)
TOKEN = env("DISCORD_BOT_SECRET")

wiki_cmd = wiki.WikiCommands(listen_channel_id=env.int("DISCORD_LOOT_GRAB_CHANNEL"))

client = discord.Client()


@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return

    if message.content.startswith('!br'):
        msg = ':flag_br:Lokalny czas w Brazylii (UTC -3):\n```\n{}\n```'.format(
            (datetime.datetime.utcnow() - datetime.timedelta(hours=3)).strftime('%d/%m/%y %H:%M:%S')
        )
        await message.channel.send(msg)

    if message.content.startswith('!status'):
        await message.channel.send('Sprawdzanie statusu serwera zotało wyłączone.')

    # Wiki commands
    if (message.channel.id == wiki_cmd.channel_id) and ('pastebin.com' in message.content):
        try:
            wiki_cmd.add_to_loot(message.content)
            msg = 'Dzięki {0.author.mention}! Dane zostały zaktualizowane.'.format(message)
            await message.channel.send(msg)
        except Exception as e:
            if str(e) == 'InvalidLink':
                msg = '{0.author.mention} mordeczko, wkleiłeś niepoprawny link do pastebina :('.format(message)
                await message.channel.send(msg)
            else:
                logger.exception("Loot error")

        #
        # try:
        #     await message.delete()
        # except Exception:
        #     pass

    if message.content.startswith('!monster'):
        try:
            monster = wiki_cmd.get_monster_info(message.content)
            if isinstance(monster, str):
                await message.channel.send(monster)
            else:
                await message.channel.send(embed=monster)
        except Exception:
            logger.exception("!monster error")

    # DEBUG
    if DEBUG and message.content.startswith('!killme'):
        await client.logout()


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

    await client.change_presence(activity=discord.Game(name='BloodStone Polska'))


client.run(TOKEN)
