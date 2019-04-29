import discord
from discord.ext import commands
from settings import *
import json
import os
from helpers.common import update_drop

client = commands.Bot(command_prefix='!')

extensions = [
    'cogs.misc',
    'cogs.wiki',
]


def migrate():
    loot_json = os.path.join('data', 'loot.json')
    monsters_col = DB['monsters']
    items_col = DB['items']
    with open(loot_json) as f_json:
        drop_list = json.load(f_json)

    for monster_name, desc in drop_list.items():
        desc['lowered_name'] = monster_name.lower()
        for item_name, item_desc in desc['drop'].items():
            update_drop(item_desc, desc['killed'])

            item_name_lower = item_name.lower()

            fitem = items_col.find_one(
                {'lowered_name': item_name_lower}
            )
            if fitem:
                if monster_name not in fitem['dropped_by']:
                    fitem['dropped_by'].append(monster_name)
                    c_id = fitem.pop('_id')
                    items_col.replace_one(
                        {'_id': c_id},
                        fitem
                    )
            else:
                item = {
                    'lowered_name': item_name.lower(),
                    'org_name': item_name,
                    'dropped_by': [monster_name],
                }
                items_col.insert_one(item)
        monsters_col.insert_one(desc)

    raise Exception


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

    await client.change_presence(activity=discord.Game(name='BloodStone Polska'))

if __name__ == '__main__':
    # migrate()

    for extension in extensions:
        try:
            client.load_extension(extension)
        except Exception as e:
            logger.exception("load_extension failed")

    client.run(TOKEN)
