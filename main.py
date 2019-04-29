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




# @client.event
# async def on_message(message):
#     # we do not want the bot to reply to itself
#     if message.author == client.user:
#         return
#
#     # DEBUG
#     if DEBUG and message.content.startswith('!killme'):
#         await client.logout()
#
#     # Wiki commands
#     if (
#             (message.channel.id == GRAB_LOOT_CHANNEL) and
#             ('pastebin.com' in message.content)
#     ):
#         print('Add to loot')


    #     try:
    #         wiki_cmd.add_to_loot(message.content)
    #         msg = 'Dzięki {0.author.mention}! Dane zostały zaktualizowane.'.format(message)
    #         await message.channel.send(msg)
    #     except Exception as e:
    #         if str(e) == 'InvalidLink':
    #             msg = '{0.author.mention} mordeczko, wkleiłeś niepoprawny link do pastebina :('.format(message)
    #             await message.channel.send(msg)
    #         else:
    #             logger.exception("Loot error")
    #
    #     #
    #     # try:
    #     #     await message.delete()
    #     # except Exception:
    #     #     pass
    #
    # if message.content.startswith('!monster'):
    #     if message.channel.id == wiki_cmd.monster_allow_ch_id:
    #         try:
    #             monster = wiki_cmd.get_monster_info(message.content)
    #             if isinstance(monster, str):
    #                 await message.channel.send(monster)
    #             else:
    #                 await message.channel.send(embed=monster)
    #         except Exception:
    #             logger.exception("!monster error")
    #     else:
    #         await message.author.send(
    #             'Z komendy !monster można korzystać tylko na kanale <#{}>'.format(wiki_cmd.monster_allow_ch_id)
    #         )


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

    await client.change_presence(activity=discord.Game(name='BloodStone Polska'))

if __name__ == '__main__':
    migrate()

    for extension in extensions:
        try:
            client.load_extension(extension)
        except Exception as e:
            logger.exception("load_extension failed")

    client.run(TOKEN)
