"""M24 muzzle recipe; retain the existing part ID, mesh, sound and icon bindings."""
import copy

PART_ID = 'm24_factory_suppressor'
OPTIONS = [
    {'id': 'none', 'name': '裸枪口', 'description': '原装枪管前端，不安装枪口配件。',
     'effects': [], 'stats': {}, 'special_effects': []},
    {'id': PART_ID, 'name': '狙击枪消音器', 'description': '哑黑长筒外壳与尾部连接环。',
     'effects': [
         {'text': '后坐力降低30%', 'benefit': 1},
         {'text': '枪械稳定性提高20%', 'benefit': 1},
         {'text': '子弹速度降低10%', 'benefit': -1},
         {'text': '开镜耗时增加10%', 'benefit': -1}],
     'stats': {'recoil_mult': .7, 'stability_mult': 1.2, 'bullet_speed_mult': .9, 'ads_percent': .1},
     'special_effects': ['消音｜降低开火声与枪口火光。']}
]

def apply(row):
    row['options']['muzzle'] = copy.deepcopy(OPTIONS)
    row['default_parts']['muzzle'] = 'none'
