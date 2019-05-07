from decimal import Decimal, ROUND_UP


def update_drop(item_desc, killed, times_dropped=None, total=None):
    # UPDATE ITEM DROP CHANCE & AVG_DROP

    if not times_dropped:
        times_dropped = item_desc['times_droped']

    if not total:
        total = item_desc['total']

    drop_chance = str(
        Decimal((times_dropped / killed) * 100).quantize(Decimal('.01'), rounding=ROUND_UP)
    ).rstrip('0').rstrip('.')
    avg_drop = str(
        (Decimal(total / killed)).quantize(Decimal('.01'), rounding=ROUND_UP).normalize()
    ).rstrip('0').rstrip('.')
    item_desc.update({
        'drop_chance': str(drop_chance) + '%',
        'avg_drop': str(avg_drop),
    })
