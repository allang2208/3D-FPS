"""Publish the single-use roll and its existing shared food-use contract."""
import json
import runpy
from pathlib import Path

DATA = Path('D:/FPS3D/FPSGAME/Content/ColdSteelData')
publisher = Path(__file__).resolve().parents[1] / 'FoodGrip20261003/publish_food_motion.py'
publishing = runpy.run_path(str(publisher))
duration = publishing['food_motion']('bread')['times']['duration']
path = DATA / 'items.json'
items = json.loads(path.read_text(encoding='utf-8-sig'))
items['bread'] = {
    'id': 'bread', 'name': '普通面包', 'category': 'consumable', 'type': '食物',
    'desc': '小麦面团烘烤成的日常食物，金黄外皮包着松软内里。个头小巧，适合随身携带，在探索途中直接食用充饥。',
    'rarity': 'common', 'level': 1, 'price': 12,
    'grid_w': 1, 'grid_h': 1,
    'stack': 1, 'stack_max': 1, 'maxStack': 1, 'maxUses': 1,
    'useEffect': {'hunger': 15, 'hydration': -10}, 'useCooldown': 0, 'useDuration': duration,
    'stats': [{'name': '恢复饥饿度', 'value': '+15'}, {'name': '消耗水分', 'value': '-10'}, {'name': '食用方式', 'value': '单次使用'}],
    'icon': '', 'icon_fallback': '面包', 'ue_icon': 'Icons/bread.png',
    'world_mesh': '/Game/Items/Consumables/Bread20261003/SM_Bread.SM_Bread',
}
path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

publishing['publish'](('bread',))
print('BREAD_CATALOG_SAVED grid=1x1 hunger=15 hydration=-10 duration=' + str(duration))
