"""Append the three saved bow bodies to the current shared catalog."""
from pathlib import Path
import json,shutil,hashlib
P=Path(__file__).parent;ROOT=P.parents[1];DATA=ROOT/'Content/ColdSteelData'
BACK=ROOT/'Saved/BowBodyVariants20260926/Before';BACK.mkdir(parents=True,exist_ok=True)
assets=json.loads((P/'import-receipt.json').read_text())['saved']
rows=json.loads((P/'authoring.json').read_text())['assets']
plans={v['id']:v for v in json.loads((P.parent/'BowBodyConcepts20260926/proposed-stats.json').read_text(encoding='utf-8-sig'))['variants']}
descriptions={
 'swift_limb':('轻薄的木质弓臂回弹利落，便于快速拉放；较轻的拉力降低了单箭威力。','蜜金色窄薄弓臂，红褐薄层和平滑反曲弓梢。'),
 'heavy_limb':('厚实弓胎与深色背衬提供更强拉力，适合预先蓄力出箭；长时间保持会更快力竭。','深栗木宽厚弓臂，饱满截面和自然嵌合的深色背衬。'),
 'steady_limb':('宽扁层压弓臂便于稳定控弓，适合保持瞄准等待时机；拉弓与举弓节奏略慢。','浅白蜡木宽扁弓臂，深胡桃夹芯与细长层压线。')}
path=DATA/'bow-gunsmith.json';catalog=json.loads(path.read_text(encoding='utf-8-sig'))
riser=next(c for c in catalog['columns'] if c['key']=='riser');changes=[]
for row in rows:
 plan=plans[row['id']];icon='bow_dark_riser_'+row['id']
 for required in [row['mesh'],row['material'],icon]:
  if required not in assets:raise RuntimeError('Asset has not been saved '+required)
 description,appearance=descriptions[row['id']]
 option=dict(id=row['id'],name=plan['name']+'弓体',description=description,appearance=appearance,
  visual=dict(bow_part_riser_mesh=assets[row['mesh']],bow_part_riser_material='',bow_part_riser_scale=1.0),stats=plan['stats'])
 index=next((i for i,o in enumerate(riser['options']) if o['id']==row['id']),None)
 if index is None:riser['options'].append(option)
 else:riser['options'][index]=option
 dest=DATA/'AttachmentIcons20260913'/(icon+'.png');source=P/'Icons'/(icon+'.png')
 if dest.exists() and not (BACK/dest.name).exists():shutil.copy2(dest,BACK/dest.name)
 shutil.copy2(source,dest);changes.append(dict(id=row['id'],mesh=assets[row['mesh']],icon=str(dest),icon_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),stats=plan['stats']))
if not (BACK/path.name).exists():shutil.copy2(path,BACK/path.name)
path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
config=ROOT/'Config/DefaultGame.ini';text=config.read_text(encoding='utf-8-sig')
line='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/DarkBow20260925/BodyVariantsV14")'
if line not in text:
 if not (BACK/config.name).exists():shutil.copy2(config,BACK/config.name)
 section='[/Script/UnrealEd.ProjectPackagingSettings]'
 if section not in text:raise RuntimeError('Packaging section missing')
 text=text.replace(section,section+'\n'+line,1);config.write_text(text,encoding='utf8')
(P/'install-receipt.json').write_text(json.dumps(dict(variants=changes,slot='riser',base_bow_changed=False,native_code_changed=False,gameplay_tested=False),ensure_ascii=False,indent=2),encoding='utf8')
print('BOW_THREE_VARIANTS_INSTALLED',flush=True)
