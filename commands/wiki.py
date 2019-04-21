import json
import re
import os
import urllib.request


class WikiCommands:
    def __init__(self, listen_channel_id):
        self.channel_id = listen_channel_id
        self.lootjson_fullpath = os.path.join('data', 'loot.json')
        self.drop_files_dir = os.path.join('data', 'drop_files')
        self._load_drop_list()

    def get_monster_loot(self, message_content):
        monster_name = message_content.replace('!monster', '')
        if not monster_name or len(monster_name) <= 1:
            return "Nieprawidłowe użycie komendy.\nPodaj nazwę potwora, np.```!monster Rabbit```"

        if monster_name[0] == ' ':
            monster_name = monster_name[1:]

        for monster, desc in self.drop_list.items():
            if monster.lower() != monster_name.lower():
                continue

            readable = []
            for itm_name, dropped_desc in desc['drop'].items():
                if dropped_desc['min'] >= 1 and (dropped_desc['min'] == dropped_desc['max']):
                    count = dropped_desc['min']
                else:
                    count = "{}-{}".format(dropped_desc['min'], dropped_desc['max'])

                readable.append(
                    "{} {} (szansa: {}, średnio: {})\n".format(
                        count,
                        itm_name,
                        str((dropped_desc['times_droped'] / desc['killed']) * 100)[:4] + '%',
                        str(dropped_desc['total'] / desc['killed'])[:4],
                    )
                )
            readable = ''.join(readable)
            if readable[-2:] == ', ':
                readable = readable[:-2]

            return "**{}**\nZabitych: **{}**\nLoot:\n```{}```".format(
                monster,
                desc['killed'],
                readable or 'Brak'
            )

        return 'Niestety, nie mam informacji o {}'.format(monster_name)

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
                response = urllib.request.urlopen('https://pastebin.com/raw/{}'.format(id))
                # write to file
                f.write(response.read())

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

                monster_name = match[0][0]
                if monster_name not in self.drop_list:
                    self.drop_list[monster_name] = {
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
        with open(self.lootjson_fullpath, 'w+') as f_json:
            json.dump(self.drop_list, f_json)

    def _load_drop_list(self):
        # Reload drop list from file
        try:
            with open(self.lootjson_fullpath) as f_json:
                self.drop_list = json.load(f_json)
        except Exception:
            self.drop_list = {}
