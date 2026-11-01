import unreal as u,json,ast,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text());exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'packed','exec'))
snapshot=json.loads((O/'ue_before.json').read_text());patch=json.loads((O/'flow_patch.json').read_text());report={'saved_assets':[],'preserved_clips':{},'runtime_tested':False}
for family,name in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items():
 p=u.load_asset('/Game/Weapons/M24/MotionPolish20261027/'+name);current=packed(p,family);expected=json.loads((O/(family+'_profile.json')).read_text());assert current==expected,'Saved profile differs from import receipt'
 changed={v['base'] for k,v in patch.items() if k.startswith(family+'/')};old=snapshot['profiles'][family];retained=[]
 for c in current['clips']:
  if c['base'] not in changed:
   assert c==next(v for v in old if v['base']==c['base']),'Unrelated clip changed: '+c['base'];retained.append(c['base'])
 path=Path(u.Paths.project_content_dir())/'Weapons/M24/MotionPolish20261027'/(name+'.uasset')
 report['saved_assets'].append({'path':p.get_path_name(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()});report['preserved_clips'][family]=retained
mesh=Path(u.Paths.project_content_dir())/'Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9.uasset'
receipt=json.loads((O/'read_receipt.json').read_text());assert hashlib.sha256(mesh.read_bytes()).hexdigest()==receipt['mesh']['sha256'],'Mesh changed during animation work'
report['mesh_unchanged']=True;report['dirty_profiles']=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().endswith(('DA_M24_SupportGrip','DA_M24_Mag10'))];assert not report['dirty_profiles']
(O/'readback_receipt.json').write_text(json.dumps(report,indent=2));print('M24_FLOW_SAVED_READBACK',json.dumps({'saved_assets':report['saved_assets'],'preserved_clip_counts':{k:len(v) for k,v in report['preserved_clips'].items()},'mesh_unchanged':True}),flush=True)
