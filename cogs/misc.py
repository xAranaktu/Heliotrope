import datetime
import re
import discord
from discord.ext import commands
from requests import get
from settings import *
from helpers.common import update_drop

pastebin_pattern = re.compile(r"(https|http)://pastebin.com/(raw/)?([A-Za-z0-9]{8})")
loot_line_pattern = re.compile(r"[\d]{1,2}:[\d]{1,2} : (.+):(.+)")
drop_pattern = re.compile(r"([\d]{1,}) (.+)")


class Misc(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.monsters_col = DB['monsters']
        self.items_col = DB['items']

        self.GRAB_LOOT_CHANNEL = GRAB_LOOT_CHANNEL

    def parse_loot(self, pastebins):
        output = {}
        for link in pastebins:
            id = link[2]

            response = get('https://pastebin.com/raw/{}'.format(id))
            if response.status_code != 200:
                continue

            output.update(
                self._parse_loot_content(response.text)
            )

        if not output:
            return False

        # sort by monsters killed
        sorted_output = sorted(output, key=lambda x: output[x]['killed'], reverse=True)
        total_killed_num = 0
        top_killed_num = 0
        top_killed = []

        for i, k in enumerate(sorted_output):
            v = output[k]
            total_killed_num += v['killed']

            # TOP 5
            if i < 5:
                top_killed_num += v['killed']
                top_killed.append(
                    '**{}** zabitych **{}**'.format(v['killed'], v['org_name'])
                )

        result = 'Twój wkład to:\n' + '\n'.join(top_killed)

        num_killed_other = total_killed_num - top_killed_num
        if num_killed_other > 0:
            result += '\n\n...oraz **{}** innych potworów!'.format(
                num_killed_other
            )

        return result

    def _parse_loot_content(self, content):
        lines = content.split('\r\n')

        # Current loot
        output = {}

        for line in lines:
            if line[-1] == '.':
                # You received... ignore this shit
                continue

            match = loot_line_pattern.findall(line)
            if not match:
                continue

            monster_name_org = match[0][0]
            monster_name = monster_name_org.lower()

            if monster_name not in output:
                output[monster_name] = {
                    'lowered_name': monster_name,
                    'org_name': monster_name_org,
                    'killed': 1,
                    'drop': {},
                    'no_drop': False,
                }
            else:
                output[monster_name]['killed'] += 1

            monster_drop = match[0][1]
            if not monster_drop or len(monster_drop) <= 1:
                output[monster_name]['no_drop'] = True
                continue

            monster_drop = monster_drop.split(',')
            for item_dropped in monster_drop:
                if item_dropped[0] == ' ':
                    item_dropped = item_dropped[1:]
                
                match = drop_pattern.findall(item_dropped)

                count = 1
                if match:
                    count = int(match[0][0])
                    item_dropped = match[0][1]

                if item_dropped not in output[monster_name]['drop']:
                    output[monster_name]['drop'][item_dropped] = {
                        'min': count,
                        'max': count,
                        'times_droped': 1,
                        'total': count,
                    }
                else:
                    for item in output[monster_name]['drop'].keys():
                        if item not in item_dropped:
                            output[monster_name]['drop'][item_dropped]['min'] = 0

                    output[monster_name]['drop'][item_dropped]['times_droped'] += 1
                    output[monster_name]['drop'][item_dropped]['total'] += count
                    if output[monster_name]['drop'][item_dropped]['min'] > count:
                        output[monster_name]['drop'][item_dropped]['min'] = count

                    if output[monster_name]['drop'][item_dropped]['max'] < count:
                        output[monster_name]['drop'][item_dropped]['max'] = count

        for monster_name, desc in output.items():
            fmonster = self.monsters_col.find_one(
                {'lowered_name': monster_name}
            )

            if fmonster:
                fmonster['killed'] += desc['killed']
                if desc['no_drop']:
                    fmonster['no_drop'] = True

                if 'drop' in desc and desc['drop']:
                    for item_name, item_desc in desc['drop'].items():
                        if desc['no_drop']:
                            item_desc['min'] = 0

                        if item_name in fmonster['drop']:
                            drop_min = min(
                                fmonster['drop'][item_name]['min'],
                                item_desc['min'],
                            )
                            drop_max = max(
                                fmonster['drop'][item_name]['max'],
                                item_desc['max'],
                            )

                            times_dropped = fmonster['drop'][item_name]['times_droped'] + item_desc['times_droped']
                            total = fmonster['drop'][item_name]['total'] + item_desc['total']

                            item_desc.update({
                                'min': drop_min,
                                'max': drop_max,
                                'times_droped': times_dropped,
                                'total': total,
                            })
                            update_drop(
                                item_desc, fmonster['killed'],
                                times_dropped=times_dropped, total=total,
                            )
                        else:
                            update_drop(
                                item_desc, desc['killed'],
                            )

                        fmonster['drop'][item_name] = item_desc

                c_id = fmonster.pop('_id')
                self.monsters_col.replace_one(
                    {'_id': c_id},
                    fmonster
                )
            else:
                if 'drop' in desc and desc['drop']:
                    for item_name, item_desc in desc['drop'].items():
                        if desc['no_drop']:
                            item_desc['min'] = 0

                        update_drop(
                            item_desc, desc['killed'],
                        )
                self.monsters_col.insert_one(desc)

            for item_name, item_desc in desc['drop'].items():
                item_name_lower = item_name.lower()

                fitem = self.items_col.find_one(
                    {'lowered_name': item_name_lower}
                )

                if fitem:
                    if monster_name not in fitem['dropped_by']:
                        fitem['dropped_by'].append(monster_name)
                        c_id = fitem.pop('_id')
                        self.items_col.replace_one(
                            {'_id': c_id},
                            fitem
                        )
                else:
                    item = {
                        'lowered_name': item_name.lower(),
                        'org_name': item_name,
                        'dropped_by': [monster_name],
                    }
                    self.items_col.insert_one(item)

        return output

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if (
                (message.channel.id == self.GRAB_LOOT_CHANNEL) and
                ('pastebin.com' in message.content)
        ):
            match = pastebin_pattern.findall(message.content)
            if not match:
                msg = '{0.author.mention} mordeczko, wkleiłeś niepoprawny link do pastebina :('.format(message)
                await message.channel.send(msg)
                return

            parsed_loot = self.parse_loot(pastebins=match)
            if not parsed_loot:
                await message.channel.send('Error')
                return

            await message.channel.send('Dzięki {0.author.mention}! Dane zostały zaktualizowane.\n\n'.format(
                message,
            ) + parsed_loot)

    @commands.command()
    async def status(self, ctx):
        await ctx.send('Sprawdzanie statusu serwera zotało wyłączone.')

    @commands.command()
    async def br(self, ctx):
        msg = ':flag_br:Lokalny czas w Brazylii (UTC -3):\n```\n{}\n```'.format(
            (datetime.datetime.utcnow() - datetime.timedelta(hours=3)).strftime('%d/%m/%y %H:%M:%S')
        )
        await ctx.send(msg)

    @commands.command()
    async def killme(self, ctx):
        if not DEBUG:
            return

        DB_CLIENT.close()
        await self.client.logout()


def setup(client):
    client.add_cog(Misc(client))
