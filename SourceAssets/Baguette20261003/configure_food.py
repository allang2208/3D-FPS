"""Publish only the baguette definition and its authored eased food motion."""
import json
import runpy
import sys
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME/Content/ColdSteelData')
publisher = Path(__file__).resolve().parents[1] / 'FoodGrip20261003/publish_food_motion.py'
publishing = runpy.run_path(str(publisher))
duration = publishing['food_motion']('baguette_bread')['times']['duration']
path = ROOT / 'items.json'
items = json.loads(path.read_text(encoding='utf-8-sig'))
items['baguette_bread'] = {
    'id': 'baguette_bread', 'name': '法棍面包', 'category': 'consumable', 'type': '食物',
    'desc': '表皮酥脆、内部松软的细长面包，可握住中部直接食用。随身携带能在探索途中充饥，细长外形会占用较多背包空间。',
    'rarity': 'common', 'level': 1, 'price': 35, 'grid_w': 1, 'grid_h': 3,
    'stack': 1, 'stack_max': 1, 'maxStack': 1, 'maxUses': 1,
    'useEffect': {'hunger': 60, 'hydration': -30}, 'useCooldown': 0, 'useDuration': duration,
    'stats': [{'name': '恢复饥饿度', 'value': '+60'}, {'name': '消耗水分', 'value': '-30'}, {'name': '食用方式', 'value': '单次使用'}],
    'icon': '', 'icon_fallback': '🥖', 'ue_icon': 'Icons/baguette_bread.png',
    'world_mesh': '/Game/Items/Consumables/Baguette20261003/SM_Baguette.SM_Baguette',
}
if '--motion-only' not in sys.argv:
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
publishing['publish'](('baguette_bread',))
print(('BAGUETTE_MOTION_SAVED progressive_camera_approach duration=' if '--motion-only' in sys.argv
      else 'BAGUETTE_CATALOG_SAVED grid=1x3 hunger=60 hydration=-30 duration=') + str(duration))
