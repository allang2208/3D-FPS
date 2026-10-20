"""Publish only the two sniper definitions and their requested special muzzle."""
import json,re,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];backup=Path('D:/FPS3D/FPSGAME_Backups/SniperSuppressor20261019');backup.mkdir(parents=True,exist_ok=True)
if not json.loads((O/'assets_receipt.json').read_text())['complete']:raise RuntimeError('Save the actual assets before exposing the option')
decoder=json.JSONDecoder()
option={'id':'sniper_heavy_suppressor','name':'大口径狙击消音器',
 'description':'狙击枪专用长筒消音器，采用哑黑金属外壳、圆润端缘和紧凑尾环，抑制枪声与枪口火光。',
 'effects':[{'text':'子弹速度降低25%','benefit':-1},{'text':'后坐力降低40%','benefit':1},{'text':'枪械稳定性提高30%','benefit':1}],
 'special_effects':['首发命中直接击杀目标时，不会引起其他怪物警觉；未击杀目标仍会发出警报。'],
 'stats':{'bullet_speed_mult':.75,'recoil_mult':.60,'stability_mult':1.30}}
receipt={'complete':False,'runtime_tested':False,'option':option,'sniper_critical_bonus':1.0,'files':{}}
def write(path,before,after):
 sha=hashlib.sha256(before.encode()).hexdigest();dest=backup/(path.stem+'_'+sha[:12]+'.json')
 if not dest.exists():dest.write_text(before,encoding='utf-8')
 if path.read_text(encoding='utf-8-sig')!=before:raise RuntimeError('Catalog changed during authoring; preserve current '+str(path))
 path.write_text(after,encoding='utf-8');receipt['files'][path.name]={'before_sha256':sha,'after_sha256':hashlib.sha256(after.encode()).hexdigest(),'backup':str(dest)}
path=P/'Content/ColdSteelData/gunsmith.json';before=path.read_text(encoding='utf-8-sig');pos=before.index('[',before.index('"weapons"'))+1;edits=[]
while True:
 while before[pos].isspace() or before[pos]==',':pos+=1
 if before[pos]==']':break
 row,end=decoder.raw_decode(before,pos)
 if row['id'] in ('ue_svd','ue_svch'):
  options=row['options']['muzzle'];options[:]=[p for p in options if p['id']!=option['id']];options.append(option)
  traits=row.setdefault('traits',[])
  traits[:]=[t for t in traits if '暴击伤害' not in t.get('text','') and '狙击枪暴击加成' not in t.get('text','')]
  traits.append({'icon':'special','text':'狙击枪暴击加成与暴击技能加成相加后单次结算。'})
  indent=re.search(r'[^\S\n]*$',before[:pos]).group();edits.append((pos,end,json.dumps(row,ensure_ascii=False,indent=2).replace('\n','\n'+indent)))
 pos=end
if len(edits)!=2:raise RuntimeError('Both supported sniper entries are required')
after=before
for start,end,text in reversed(edits):after=after[:start]+text+after[end:]
write(path,before,after)
path=P/'Content/ColdSteelData/items.json';before=path.read_text(encoding='utf-8-sig');edits=[]
for key in ('ue_svd','ue_svch'):
 match=re.search(r'^([ \t]*)"'+key+r'"\s*:\s*',before,re.M)
 if not match:raise RuntimeError('Missing sniper definition '+key)
 start=match.end();row,end=decoder.raw_decode(before,start);row.update(weaponType='sniper',weaponTypeTag='狙击步枪',critDamageBonus=1.0)
 if key=='ue_svd':row['desc']=row['desc'].replace('命中要害的暴击伤害另加一半','暴击伤害更高')
 else:row['desc']='采用长护木、顶部全长导轨和可调枪托的半自动狙击步枪，使用 7.62×54R 有底缘弹与可拆卸弹匣。机械瞄具便于迅速瞄准，也能安装通用光学瞄具。单发威力与远距离命中能力突出，适合稳住枪身后逐发射击。'
 indent=match.group(1);edits.append((start,end,json.dumps(row,ensure_ascii=False,indent=2).replace('\n','\n'+indent)))
after=before
for start,end,text in sorted(edits,reverse=True):after=after[:start]+text+after[end:]
write(path,before,after);receipt['complete']=True
(O/'catalog_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8');print('SNIPER_SUPPRESSOR_CATALOG_SAVED',flush=True)
