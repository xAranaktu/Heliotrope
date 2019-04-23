import discord
import json
import re
import os
from requests import get
from bs4 import BeautifulSoup


class WikiCommands:
    def __init__(self, listen_channel_id):
        self.BASE_URL = 'http://bloodstonewiki.pl/index.php/'

        # ID kanału z którego zbieramy pastebiny
        self.channel_id = listen_channel_id

        # Pastebiny zapisujemy tutaj
        self.drop_files_dir = os.path.join('data', 'drop_files')

        # loot.json
        self.loot_json = os.path.join('data', 'loot.json')

        # monster_info.json
        self.monster_info_json = os.path.join('data', 'monster_info.json')

        # wczytanie info o potworach
        self._load_monster_data()

    def get_monster_info(self, message_content):
        monster_name = message_content.replace('!monster', '')
        if not monster_name or len(monster_name) <= 1:
            return "Nieprawidłowe użycie komendy.\nPodaj nazwę potwora, np.```!monster Rabbit```"

        if monster_name[0] == ' ':
            monster_name = monster_name[1:]

        monster_loot = self.get_monster_loot(monster_name.lower())
        if 'org_monster_name' in monster_loot:
            embed_monster_name = monster_loot['org_monster_name']
        else:
            embed_monster_name = monster_name

        if monster_name not in self.monster_info_list:
            monster_info = self._wiki_monster_info(embed_monster_name)
            if monster_info:
                self.monster_info_list[monster_name] = monster_info
        else:
            monster_info = self.monster_info_list[monster_name]

        embed = discord.Embed(
            title=embed_monster_name,
            url=self.BASE_URL + embed_monster_name.replace(' ', '_'),
            color=4446036,
        )

        embed.set_author(
            name='Bloodstone Wiki', url=self.BASE_URL,
            icon_url='http://bloodstonewiki.pl/resources/assets/wikiblood2.png?5dda8'
        )

        if 'gif' in monster_info:
            embed.set_thumbnail(
                url=monster_info['gif']
            )

        if 'EXP' in monster_info:
            embed.add_field(
                name='Info',
                value='\n**EXP**: {}\n**HP**: {}'.format(
                    monster_info['EXP'],
                    monster_info['HP']
                ),
                inline=True
            )
            embed.add_field(
                name='Zachowanie',
                value='\n**Zwarcie**: {}\n**Dystans**: {}\n**Specjalne**: {}'.format(
                    monster_info['Zwarcie'],
                    monster_info['Dystans'],
                    monster_info['Specjalne']
                ),
                inline=True
            )

        embed.add_field(name='Loot', value=monster_loot['human_readable_str'])
        return embed

    def _wiki_monster_info(self, monster_name):
        result = {}

        r = get(self.BASE_URL + monster_name.replace(' ', '_'))
        # Problemy z wiki
        if r.status_code != 200:
            return result

        soup = BeautifulSoup(r.text, 'lxml')
        main_content = soup.find(id="mw-content-text")

        # Brak zawartości
        if 'noarticletext' in main_content.div['class']:
            return result

        if main_content.img:
            result['gif'] = 'http://bloodstonewiki.pl' + main_content.img['src']

        tbody = main_content.table.find('tbody')
        for row in tbody.find_all('tr'):
            cells = row.find_all('td')
            if cells and len(cells) == 6:
                result.update({
                    'monster_name': soup.h1.find(text=True).replace('\n', '') or monster_name,
                    'EXP': cells[0].find(text=True).replace('\n', ''),
                    'HP': cells[1].find(text=True).replace('\n', ''),
                    'Zwarcie': cells[2].find(text=True).replace('\n', ''),
                    'Dystans': cells[3].find(text=True).replace('\n', ''),
                    'Specjalne': cells[4].find(text=True).replace('\n', ''),
                })

        return result

    def get_monster_loot(self, monster_name):
        if not monster_name in self.drop_list:
            return {
                'human_readable_str': '`Brak informacji`',
            }

        desc = self.drop_list[monster_name]

        readable = []
        for itm_name, dropped_desc in desc['drop'].items():
            if dropped_desc['min'] >= 1 and (dropped_desc['min'] == dropped_desc['max']):
                count = dropped_desc['min']
            else:
                count = "{}-{}".format(dropped_desc['min'], dropped_desc['max'])

            readable.append(
                "\n`{} {} (szansa: {}, średnio: {})`".format(
                    count,
                    itm_name,
                    str((dropped_desc['times_droped'] / desc['killed']) * 100)[:4] + '%',
                    str(dropped_desc['total'] / desc['killed'])[:4],
                )
            )
        readable = ''.join(readable)
        if readable[-2:] == ', ':
            readable = readable[:-2]

        return {
            'human_readable_str': "\nZabitych: **{}**\n{}".format(
                desc['killed'],
                readable or '`Brak loota`'
            ),
            'org_monster_name': desc['org_name']
        }

    def add_to_loot(self, message_content):
        # Get link from message conent
        regex = r"(https|http)://pastebin.com/(raw/)?([A-Za-z0-9]{8})"
        match = re.findall(regex, message_content)
        if not match:
            raise Exception("InvalidLink")

        # Download files
        for link in match:
            id = link[2]
            fname = os.path.join(self.drop_files_dir, '{}.txt'.format(id))

            if os.path.isfile(fname):
                continue

            with open(fname, 'wb') as f:
                # get request
                response = get('https://pastebin.com/raw/{}'.format(id))
                # write to file
                f.write(response.content)

            self.parse_loot_file(fname)

        # Update loot.json
        self._update_loot_json()

    def parse_loot_file(self, fname):
        regex = r"[\d]{1,2}:[\d]{1,2} : (.+):(.+)"
        with open(fname, 'r', encoding='UTF-8') as f:
            lines = f.readlines()
            for line in lines:
                if line[-1] == '.':
                    # You received... ignore this shit
                    continue

                match = re.findall(regex, line)
                if not match:
                    continue

                monster_name_org = match[0][0]
                monster_name = monster_name_org.lower()
                if monster_name not in self.drop_list:
                    self.drop_list[monster_name] = {
                        'org_name': monster_name_org,
                        'killed': 1,
                        'drop': {},
                        'no_drop': False,
                    }
                else:
                    self.drop_list[monster_name]['killed'] += 1

                monster_drop = match[0][1]
                if not monster_drop or len(monster_drop) <= 1:
                    self.drop_list[monster_name]['no_drop'] = True
                    continue

                monster_drop = monster_drop.split(',')
                for item_dropped in monster_drop:
                    if item_dropped[0] == ' ':
                        item_dropped = item_dropped[1:]

                    drop_re = r"([\d]{1,}) (.+)"
                    match = re.findall(drop_re, item_dropped)

                    count = 1
                    if match:
                        count = int(match[0][0])
                        item_dropped = match[0][1]

                    if item_dropped not in self.drop_list[monster_name]['drop']:
                        self.drop_list[monster_name]['drop'][item_dropped] = {
                            'min': count,
                            'max': count,
                            'times_droped': 1,
                            'total': count,
                        }
                    else:
                        for item in self.drop_list[monster_name]['drop'].keys():
                            if item not in item_dropped:
                                self.drop_list[monster_name]['drop'][item_dropped]['min'] = 0

                        self.drop_list[monster_name]['drop'][item_dropped]['times_droped'] += 1
                        self.drop_list[monster_name]['drop'][item_dropped]['total'] += count
                        if self.drop_list[monster_name]['drop'][item_dropped]['min'] > count:
                            self.drop_list[monster_name]['drop'][item_dropped]['min'] = count

                        if self.drop_list[monster_name]['drop'][item_dropped]['max'] < count:
                            self.drop_list[monster_name]['drop'][item_dropped]['max'] = count

            for monster_name, desc in self.drop_list.items():
                if desc['no_drop']:
                    for _, dropped in desc['drop'].items():
                        dropped['min'] = 0

    def _update_loot_json(self):
        # Save in loot.json
        with open(self.loot_json, 'w+') as f_json:
            json.dump(self.drop_list, f_json)

    def _update_monster_info_json(self):
        # Save in monster_info.json
        with open(self.monster_info_json, 'w+') as f_json:
            json.dump(self.monster_info_list, f_json)

    def _load_monster_data(self):
        # Reload drop list from file
        try:
            with open(self.loot_json) as f_json:
                self.drop_list = json.load(f_json)

            # Remove
            for m, d in self.drop_list.items():
                if m.islower():
                    continue

                d['org_name'] = m
                self.drop_list[m.lower()] = d
                self.drop_list.pop(m, None)

            self._update_loot_json()
        except Exception:
            self.drop_list = {}

        # Reload monster info from file
        try:
            with open(self.monster_info_json) as f_json:
                self.monster_info_list = json.load(f_json)
        except Exception:
            self.monster_info_list = {}
