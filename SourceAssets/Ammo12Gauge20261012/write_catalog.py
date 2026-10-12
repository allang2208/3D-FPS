"""Author the three game ammunition definitions without rewriting other rows."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'Content/ColdSteelData'
VARIANTS = [
    dict(id='ammo_12g', name='00 鹿弹', icon='buckshot', rarity='common',
         tier_name='绿阶', tier_color='#4CAA70', damage=1.0, count=8, reach=1.0, armor=0.0, pierce=0,
         model='Federal LE133 00',
         description='参考 LE133 00 的 12 号鹿弹。每发 8 颗弹丸，保留标准整发伤害与射程，无额外目标穿透和护甲穿透，适合近距离。'),
    dict(id='ammo_12g_flechette', name='箭型弹', icon='flechette', rarity='rare',
         tier_name='蓝阶', tier_color='#4C8FD8', damage=0.9, count=8, reach=1.0, armor=0.0, pierce=1,
         model='Sabot Designs 12 GA Flechette',
         description='参考 Sabot Designs 12 GA Flechette 的游戏箭型弹。每发 8 枚，整发伤害为鹿弹的 90%，每枚可额外穿透 1 个目标；射程不变，不赋予穿墙或护甲穿透。弹丸数量与效果为游戏设定。'),
    dict(id='ammo_12g_slug', name='独头弹', icon='slug', rarity='rare',
         tier_name='蓝阶', tier_color='#4C8FD8', damage=0.75, count=1, reach=2.0, armor=0.1, pierce=0,
         model='Federal F127 RS',
         description='参考 F127 RS 的 12 号独头弹。每发 1 颗，伤害为标准散弹整发全部弹丸总伤害的 75%，射程翻倍，无视 10% 物理护甲；不额外穿透目标。'),
]

def add_rows(path, rows, array_key=None):
    # Touch only requested identities, preserving unrelated formatting/parallel work.
    text = path.read_text(encoding='utf-8-sig')
    source = json.loads(text)
    entries = source[array_key] if array_key else source
    for row in rows:
        identity = row['id']
        old = next((r for r in entries if r['id'] == identity), None) if array_key else entries.get(identity)
        value = dict(old or {})
        value.update(row)
        encoded = json.dumps(value, ensure_ascii=False, indent=2)
        if old is not None:
            # Locate the full JSON object enclosing this exact identity.
            key = json.dumps(identity)
            pos = text.index('"id": ' + key)
            start = text.rfind('{', 0, pos)
            _, length = json.JSONDecoder().raw_decode(text[start:])
            indent = ' ' * (4 if array_key else 2)
            replacement = encoded.replace('\n', '\n' + indent)
            text = text[:start] + replacement + text[start + length:]
        else:
            end = text.rfind(']' if array_key else '}')
            prefix = text[:end].rstrip()
            indent = ' ' * (4 if array_key else 2)
            replacement = encoded.replace('\n', '\n' + indent)
            entry = replacement if array_key else json.dumps(identity) + ': ' + replacement
            text = prefix + ',\n' + indent + entry + '\n' + ('  ' if array_key else '') + text[end:]
        if array_key:
            if old is None: entries.append(value)
        else: entries[identity] = value
    path.write_text(text, encoding='utf-8', newline='\r\n')

ammo, items, recipes = [], [], []
for index, v in enumerate(VARIANTS):
    icon = f'Icons/Ammo12Gauge20261012/{v["icon"]}.png'
    ammo.append(dict(id=v['id'], group='ammo_12g', group_name='12 号', name=v['name'],
                     tier_name=v['tier_name'], tier_color=v['tier_color'], description=v['description'],
                     reference_model=v['model'], icon=icon, order=100+index, enabled=True,
                     allow_infinite_reserve=index==0, damage_multiplier=v['damage'],
                     physical_armor_penetration=v['armor'], projectile_count=v['count'],
                     range_multiplier=v['reach'], target_penetration=v['pierce']))
    items.append(dict(id=v['id'], name='12 号'+v['name'], category='ammo', type='弹药',
                      stack_max=60, maxStack=60, grid_w=1, grid_h=1, rarity=v['rarity'],
                      world_mesh='/Game/Items/Ammo12Gauge20261012/Meshes/SM_12G_'+['Buckshot','Flechette','Slug'][index]+'_Box.SM_12G_'+['Buckshot','Flechette','Slug'][index]+'_Box',
                      icon=icon, ue_icon=icon, desc=v['description']))
    # Abstract inventory crafting units only, matching the existing game economy.
    recipes.append(dict(id='craft_'+v['id'],
                        inputs=[dict(item='copperIngot',count=1),
                                dict(item='ironIngot' if index==1 else 'leadOre',count=1),
                                dict(item='sulfurOre',count=1)],
                        output=dict(item=v['id'],count=12 if index==0 else 8)))
add_rows(DATA/'ammo_types.json', ammo, 'types')
add_rows(DATA/'items.json', items)
add_rows(DATA/'ammo-crafting-recipes.json', recipes, 'recipes')
print('Saved 3 shotgun ammo types, item definitions and workbench recipes.')
