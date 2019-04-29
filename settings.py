from environs import Env
import pymongo
import logging

env = Env()
env.read_env()

DEBUG = env.bool("DEBUG", False)
TOKEN = env("DISCORD_BOT_SECRET")

DB_CONN = env('DB_CONN')
DB_NAME = env('DB_NAME')

GRAB_LOOT_CHANNEL = env.int('DISCORD_LOOT_GRAB_CHANNEL')
WIKI_COMMANDS_ALLOW = env.int('DISCORD_WIKI_COMMANDS_ALLOW')

logger = logging.getLogger('discord')
logger.setLevel(logging.WARNING)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

DB_CLIENT = pymongo.MongoClient(DB_CONN)
DB = DB_CLIENT[DB_NAME]
