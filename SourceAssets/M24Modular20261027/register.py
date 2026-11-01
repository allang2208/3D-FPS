"""Register only M24-owned catalog rows and current imported hand sections."""
import json,copy,shutil,runpy
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[1]
src=json.loads((O/'authoring.json').read_text());reg=src['registration_ue_cm']
header='#pragma once\n#include "CoreMinimal.h"\n\n// Generated from M24Modular20261027/authoring.json; static export centimetres.\nnamespace M24AttachmentCoordinates\n{\n'
for name,values in [('SightRear',reg['WPN_RearSight']),('SightFront',reg['WPN_FrontSight']),('Magazine',reg['WPN_SOCKET_Magazine']),('BareMuzzle',src['bare_muzzle_ue_cm'])]:
    header+='inline const FVector '+name+'('+','.join(f'{v:.10f}' for v in values)+');\n'
(P/'Source/FPSGAME/Weapons/M24AttachmentCoordinates.h').write_text(header+'}\n',encoding='utf-8')
if not (O/'import_receipt.json').exists():raise RuntimeError('Asset import must complete before catalog installation')
receipt=json.loads((O/'import_receipt.json').read_text())
if not receipt['complete']:raise RuntimeError('Asset import incomplete')
def edit(name,modify):
    path=P/'Content/ColdSteelData'/name;original=path.read_bytes();data=json.loads(original)
    backup=O/('before_'+name)
    if not backup.exists():backup.write_bytes(original)
    modify(data)
    if path.read_bytes()!=original:raise RuntimeError('Concurrent modification: '+name)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def option(id,name,desc,special=[]):return dict(id=id,name=name,description=desc,effects=[],stats={},special_effects=special)
def catalog(data):
    row=next(x for x in data['weapons'] if x['id']=='ue_m24')
    row['allowed']=['optic','muzzle','stock'];row['inherit_common_options']=False
    row['default_parts']={'optic':'m24_custom_scope_6x','muzzle':'none','stock':'m24_cheekrest'}
    row['options']={
      'optic':[option('m24_custom_scope_6x','M24 定制六倍瞄准镜','长镜筒、双环安装座与独立调节鼓组成完整瞄具总成。',['光学瞄准｜瞄准时使用固定六倍放大与中心分划。']),
               option('none','M24 觇孔机械瞄具','取下光学瞄准镜，使用侧置调节座、觇孔照门与护筒准星组成的机械瞄具总成。',['机械瞄准｜使用觇孔照门与前准星，不提供光学放大。'])],
      'muzzle':[],
      'stock':[option('m24_cheekrest','M24 原装贴腮板','贴合后托上缘的独立弧形贴腮板。'),
               option('none','拆下贴腮板','保留原装枪托，移除上方贴腮板。')]}
    runpy.run_path(str(O.parent/'M24SniperSuppressor20261029/catalog.py'))['apply'](row)
    runpy.run_path(str(O.parent/'M24Bipod20261029/catalog.py'))['apply'](row)
    runpy.run_path(str(O.parent/'M24CarbonBolt20261029/catalog.py'))['apply_catalog'](data)
    runpy.run_path(str(O.parent/'M24RearGrip20261029/catalog.py'))['apply_catalog'](data)
    runpy.run_path(str(O.parent/'M24AdvancedAction20261029/catalog.py'))['apply_catalog'](data)
    # Update assembly information without dropping the innate critical passive.
    row['traits'][1]={'icon':'mechanic','text':'瞄准镜、狙击枪消音器和贴腮板可独立拆装；新枪默认使用裸枪口。'}
edit('gunsmith.json',catalog)
def outfits(data):
    # The profile map is keyed by exact mesh path; keep every older entry intact.
    old='/Game/Weapons/M24/Gameplay20261026/SK_M24_V9.SK_M24_V9'
    def descend(node):
        if isinstance(node,dict):
            if old in node:
                profile=copy.deepcopy(node[old]);profile['hide_source_materials']=receipt['arm_materials']
                node[receipt['mesh']]=profile
                return True
            for value in node.values():
                if descend(value):return True
        return False
    if not descend(data):raise RuntimeError('Current M24 outfit profile is missing')
edit('modular_outfits.json',outfits)
(O/'data_receipt.json').write_text(json.dumps({'complete':True,'files':['gunsmith.json','modular_outfits.json'],'tested':False},indent=2),encoding='utf-8')
print('M24_MODULAR_CATALOG_SAVED')
