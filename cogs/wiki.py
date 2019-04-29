import re
import discord
from decimal import Decimal
from discord.ext import commands
from settings import *
from requests import get
from bs4 import BeautifulSoup


class Wikipedia(commands.Cog):
    def __init__(self, client):
        self.BASE_URL = 'http://bloodstonewiki.pl/index.php/'
        self.monsters_col = DB['monsters']
        self.items_col = DB['items']
        self.WIKI_COMMANDS_ALLOW = WIKI_COMMANDS_ALLOW
        self.client = client

    def _wiki_monster_info(self, monster_name):
        result = {}

        r = get(self.BASE_URL + monster_name.replace(' ', '_'))
        # Problemy z wiki ?
        if r.status_code != 200:
            return result

        soup = BeautifulSoup(r.text, 'lxml')
        main_content = soup.find(id="mw-content-text")

        # Brak zawartości
        if 'noarticletext' in main_content.div['class']:
            return result

        if main_content.img:
            result['img'] = 'http://bloodstonewiki.pl' + main_content.img['src']

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

    def get_monster_loot(self, monster):
        readable = []
        for itm_name, dropped_desc in monster['drop'].items():
            if dropped_desc['min'] >= 1 and (dropped_desc['min'] == dropped_desc['max']):
                count = dropped_desc['min']
            else:
                count = "{}-{}".format(dropped_desc['min'], dropped_desc['max'])

            readable.append(
                "\n`{} {} (szansa: {}, średnio: {})`".format(
                    count,
                    itm_name,
                    dropped_desc['drop_chance'],
                    dropped_desc['avg_drop'],
                )
            )
        readable = ''.join(readable)
        if readable[-2:] == ', ':
            readable = readable[:-2]

        return readable or '`Brak loota`'

    def _wiki_item_info(self, item_name):
        result = {}

        r = get(self.BASE_URL + item_name.replace(' ', '_'))
        # Problemy z wiki ?
        if r.status_code != 200:
            return result

        soup = BeautifulSoup(r.text, 'lxml')
        main_content = soup.find(id="mw-content-text")

        # Brak zawartości
        if 'noarticletext' in main_content.div['class']:
            return result

        if main_content.img:
            result['img'] = 'http://bloodstonewiki.pl' + main_content.img['src']

        return result

    def get_dropped_by(self, item):
        if ('dropped_by' not in item) or (not item['dropped_by']):
            return 'Brak informacji'

        dropped_by = [x + '$' for x in item['dropped_by']]
        pattern = re.compile(r'^' + r'|^'.join(dropped_by))
        monsters = self.monsters_col.find(
            {'lowered_name': pattern}
        )

        if not monsters:
            return 'Brak informacji'

        to_sort = {}

        for monster in monsters:
            try:
                item_info = monster['drop'][item['org_name']]
            except KeyError:
                print('ou')
                from pprint import pprint as pp
                import pdb
                pdb.set_trace()
            to_sort[monster['org_name']] = {
                'item_info': item_info,
            }

        sorted_by_avg_drop = sorted(to_sort.items(), key=lambda x: Decimal(x[1]['item_info']['avg_drop']), reverse=True)
        result = []
        for monster_name, item_info in sorted_by_avg_drop:
            item_info = item_info['item_info']
            if item_info['min'] >= 1 and (item_info['min'] == item_info['max']):
                count = item_info['min']
            else:
                count = "{}-{}".format(item_info['min'], item_info['max'])

            result.append(
                "\n`{}: {} (szansa: {}, średnio: {})`".format(
                    monster_name,
                    count,
                    item_info['drop_chance'],
                    item_info['avg_drop'],
                )
            )

        if result:
            return ''.join(result)
        else:
            return 'Brak informacji'

    @commands.command()
    async def monsterhelp(self, ctx, *, contains):
        if ctx.channel.id != self.WIKI_COMMANDS_ALLOW:
            await ctx.message.author.send('Komenda {}{} jest dostępna tylko na kanale <#{}>'.format(
                self.client.command_prefix,
                ctx.command.name,
                self.WIKI_COMMANDS_ALLOW
            ))
            return

        if len(contains) < 2:
            await ctx.send('W celu wyszukiwania proszę o podanie min. 2 znaków')
            return
        pattern = re.compile(contains, re.IGNORECASE)
        monsters = self.monsters_col.find(
            {'lowered_name': pattern}
        )
        if not monsters.count():
            await ctx.send('Brak w bazie danych potworów które zawierają w nazwie **{}**'.format(contains))
            return

        matching_startwith = []
        matching = []
        contains = contains.lower()
        for monster in monsters:
            if contains in monster['lowered_name']:
                if monster['lowered_name'].startswith(contains):
                    matching_startwith.append(monster['org_name'])
                else:
                    matching.append(monster['org_name'])

        matching_startwith.sort()
        matching.sort()

        msg = 'Potwory które znajduja się w bazie danych i zawieraja w nazwie **{}** to:\n\n{}'.format(
            contains, '\n'.join(matching_startwith + matching)
        )

        if len(msg) > 2000:
            msg = msg[:1900] + '\n\nZbyt długa wiadomość, usunięto **{}** znaków'.format(
                len(msg) - 1900
            )

        await ctx.send(msg)

    @commands.command()
    async def monster(self, ctx, *, monster_name):
        if ctx.channel.id != self.WIKI_COMMANDS_ALLOW:
            await ctx.message.author.send('Komenda {}{} jest dostępna tylko na kanale <#{}>'.format(
                self.client.command_prefix,
                ctx.command.name,
                self.WIKI_COMMANDS_ALLOW
            ))
            return

        if not monster_name or len(monster_name) <= 1:
            msg = "Nieprawidłowe użycie komendy.\nPodaj nazwę potwora, np.```!monster Rabbit```"
            await ctx.send(msg)
            return

        monster = self.monsters_col.find_one(
            {'lowered_name': monster_name.lower()}
        )

        if monster and 'org_name' in monster:
            loot = "\nZabitych: **{}**\n{}".format(
                monster['killed'],
                self.get_monster_loot(monster)
            )
            embed_monster_name = monster['org_name']
        else:
            loot = 'Brak informacji'
            embed_monster_name = monster_name

        monster_info = self._wiki_monster_info(embed_monster_name)
        if not monster_info and not monster:
            msg = 'Brak jakichkolwiek danych o {}'.format(monster_name)
            await ctx.send(msg)
            return

        embed = discord.Embed(
            title=embed_monster_name,
            url=self.BASE_URL + embed_monster_name.replace(' ', '_'),
            color=4446036,
        )

        embed.set_author(
            name='Bloodstone Wiki', url=self.BASE_URL,
            icon_url='http://bloodstonewiki.pl/resources/assets/wikiblood2.png?5dda8'
        )

        if 'img' in monster_info:
            embed.set_thumbnail(
                url=monster_info['img']
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

        embed.add_field(name='Loot', value=loot)
        await ctx.send(embed=embed)

    @commands.command()
    async def itemhelp(self, ctx, *, contains):
        if ctx.channel.id != self.WIKI_COMMANDS_ALLOW:
            await ctx.message.author.send('Komenda {}{} jest dostępna tylko na kanale <#{}>'.format(
                self.client.command_prefix,
                ctx.command.name,
                self.WIKI_COMMANDS_ALLOW
            ))
            return

        if len(contains) < 2:
            await ctx.send('W celu wyszukiwania proszę o podanie min. 2 znaków')
            return

        pattern = re.compile(contains, re.IGNORECASE)
        items = self.items_col.find(
            {'lowered_name': pattern}
        )
        if not items.count():
            await ctx.send('Brak w bazie danych przedmiotów które zawierają w nazwie **{}**'.format(contains))
            return

        matching_startwith = []
        matching = []
        contains = contains.lower()
        for item in items:
            if contains in item['lowered_name']:
                if item['lowered_name'].startswith(contains):
                    matching_startwith.append(item['org_name'])
                else:
                    matching.append(item['org_name'])

        matching_startwith.sort()
        matching.sort()

        msg = 'Przedmioty które znajduja się w bazie danych i zawieraja w nazwie **{}** to:\n\n{}'.format(
            contains, '\n'.join(matching_startwith + matching)
        )

        if len(msg) > 2000:
            msg = msg[:1900] + '\n\nZbyt długa wiadomość, usunięto **{}** znaków'.format(
                len(msg) - 1900
            )

        await ctx.send(msg)

    @commands.command()
    async def item(self, ctx, *, item_name):
        if ctx.channel.id != self.WIKI_COMMANDS_ALLOW:
            await ctx.message.author.send('Komenda {}{} jest dostępna tylko na kanale <#{}>'.format(
                self.client.command_prefix,
                ctx.command.name,
                self.WIKI_COMMANDS_ALLOW
            ))
            return

        if not item_name or len(item_name) <= 1:
            msg = "Nieprawidłowe użycie komendy.\nPodaj nazwę przedmiotu, np.```!item Fang```"
            await ctx.send(msg)
            return

        item = self.items_col.find_one(
            {'lowered_name': item_name.lower()}
        )

        if item and 'org_name' in item:
            dropped_by = self.get_dropped_by(item)
            embed_item_name = item['org_name']
        else:
            dropped_by = 'Brak informacji'
            embed_item_name = item_name

        item_info = self._wiki_item_info(embed_item_name)
        if not item_info and not item:
            msg = 'Brak jakichkolwiek danych o {}'.format(item_name)
            await ctx.send(msg)
            return

        embed = discord.Embed(
            title=embed_item_name,
            url=self.BASE_URL + embed_item_name.replace(' ', '_'),
            color=4446036,
        )

        embed.set_author(
            name='Bloodstone Wiki', url=self.BASE_URL,
            icon_url='http://bloodstonewiki.pl/resources/assets/wikiblood2.png?5dda8'
        )

        if 'img' in item_info:
            embed.set_thumbnail(
                url=item_info['img']
            )

        embed.add_field(name='Wypada z', value=dropped_by)
        await ctx.send(embed=embed)


def setup(client):
    client.add_cog(Wikipedia(client))
