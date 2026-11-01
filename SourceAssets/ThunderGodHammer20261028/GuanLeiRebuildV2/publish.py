"""Point only GuanLei's appearance at the new saved asset; retain behavior and save IDs."""
import json,shutil,datetime
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2];D='/Game/Weapons/ThunderGodHammer20261028/GuanLeiRebuildV2'
if not json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))['complete']:raise RuntimeError('Model import incomplete')
if not json.loads((P.parent/'FactoryIconsV2/import_receipt.json').read_text(encoding='utf-8'))['complete']:raise RuntimeError('Icon import incomplete')
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S');backup=P/('BeforePublication-'+stamp);backup.mkdir()
paths=[R/'Content/ColdSteelData/thunder-god-hammer-modules.json',R/'Content/ColdSteelData/thunder-god-hammer-gunsmith.json']
for path in paths:shutil.copy2(path,backup/path.name)
catalog=json.loads(paths[0].read_text(encoding='utf-8-sig'));option=catalog['slots']['head_mount']['guan_lei_seat']
option.update(mesh=D+'/SM_ThunderHammer_GuanLeiSeatV2.SM_ThunderHammer_GuanLeiSeatV2',model_revision='GuanLeiRebuildV2',source_mesh='SM_ThunderHammer_GuanLeiSeatV2',appearance='锻钢整壳 · 北欧雷纹徽章 · 嵌入式导雷槽')
paths[0].write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
book=json.loads(paths[1].read_text(encoding='utf-8-sig'));seat=next(c for c in book['columns'] if c['key']=='head_mount');entry=next(o for o in seat['options'] if o['id']=='guan_lei_seat')
entry['appearance']=option['appearance'];entry['description']='雷神之锤专属。锻钢整壳围绕北欧雷纹徽章，双侧嵌入式导雷槽汇聚雷能，将蓄满的重击化为旋转飞锤。'
paths[1].write_text(json.dumps(book,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'publish_receipt.json').write_text(json.dumps({'complete':True,'mesh':option['mesh'],'option_id':'guan_lei_seat','backup':str(backup),'gameplay_changes':False,'runtime_tested':False},indent=2),encoding='utf-8')
print('GUANLEI_REBUILD_V2_PUBLISHED')
