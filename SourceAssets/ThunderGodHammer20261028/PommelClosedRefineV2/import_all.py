from pathlib import Path
import json,runpy,os,shutil,unreal as u
P=Path(__file__).resolve().parent;R=P.parents[2];backup=P/'BeforePublication';backup.mkdir(exist_ok=True)
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
for key in ['lei_xi','zhen_ting']:
 source=R/'Content/ColdSteelData/AttachmentIcons20260913'/('ue_thunder_god_hammer_pommel_'+key+'_pommel.png')
 if source.exists() and not (backup/source.name).exists():shutil.copy2(source,backup/source.name)
for kind in ['LeiXi','ZhenTing']:runpy.run_path(str(P/kind/'import_assets.py'),run_name='__main__')
def publish(path,edit):
 old=path.read_text(encoding='utf-8-sig');data=json.loads(old);edit(data)
 if not (backup/path.name).exists():(backup/path.name).write_text(old,encoding='utf-8')
 if path.read_text(encoding='utf-8-sig')!=old:raise RuntimeError('Concurrent edit: '+str(path))
 temp=path.with_suffix('.pommel_closed_v2.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(temp,path)
def modules(data):
 for kind,key in [('LeiXi','lei_xi'),('ZhenTing','zhen_ting')]:
  receipt=json.loads((P/kind/'import_receipt.json').read_text(encoding='utf-8'));item=data['slots']['pommel'][key+'_pommel']
  item['mesh']=receipt['mesh'];item['model_revision']='PommelClosedRefineV2/'+kind
def catalog(data):
 option=next(o for c in data['columns'] if c['key']=='pommel' for o in c['options'] if o['id']=='zhen_ting_pommel')
 option['special_effects']=[s.replace('沿释放方向额外落下3道雷击；','沿释放方向由近及远额外落下3道雷击，每道间隔0.25秒；').replace('沿释放方向追加3道同款魔法落雷。','沿释放方向由近及远追加3道同款魔法落雷，每道间隔0.25秒。') for s in option.get('special_effects',[])]
publish(R/'Content/ColdSteelData/thunder-god-hammer-modules.json',modules)
publish(R/'Content/ColdSteelData/thunder-god-hammer-gunsmith.json',catalog)
receipt={'complete':True,'catalog_published':True,'models':['LeiXi','ZhenTing'],'runtime_tested':False,'timing_seconds':[.25,.50,.75]}
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('POMMEL_CLOSED_V2_IMPORTED_SAVED_AND_PUBLISHED')
