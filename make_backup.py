from shutil import copyfile
import datetime
import os

today = datetime.datetime.today()

copyfile('loot.json', os.path.join('backup', 'loot_{}_{}_{}.json'.format(today.day, today.month, today.year)))