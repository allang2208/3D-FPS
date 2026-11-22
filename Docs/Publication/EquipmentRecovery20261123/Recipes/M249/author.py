from pathlib import Path
import unreal as u,json,gzip,hashlib,runpy,traceback,zipfile,shutil
H=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
W=Path(__file__).resolve().parent
assert H==W/'Host'
R=Path('D:/FPS3D/FPSGAME');S=R/'SourceAssets/M249Orpind20261107';D=H/'SourceAssets'/S.name
def read(p):return json.loads(p.read_bytes().decode('utf-8-sig'))
def file(k):return H/'Content'/(k[6:].split('.')[0]+'.uasset')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def record(k,n,extra=None):
 obj=dict(stage=n,sha256=sha(file(k)))
 if extra:obj.update(extra)
 ledger[k]=obj
 (W/'authored.json').write_text(json.dumps(ledger,indent=2))
def run(p):return runpy.run_path(str(p),run_name='__main__')
def seed(z,rel):
 assert file('/Game/'+rel.removeprefix('Content/').removesuffix('.uasset')).resolve().is_relative_to(H/'Content')
 with zipfile.ZipFile(S/z) as arc:(H/rel).write_bytes(arc.read(rel))
def native(stage,recipe,paths,data_dir,seedzip):
 src=(S/recipe).read_text(encoding='utf-8-sig')
 if stage=='Repair08':
  code=src[src.index("mesh=u.load_asset"):src.index('saved.append(clip.get_path_name())')]
 elif stage=='Repair11':
  code=src[src.index("mesh=u.load_asset"):src.index('receipt=dict(saved_packages')]
 else:
  code=src[src.index('for data in motions:'):src.index('for family',src.index('for data in motions:'))]
 for k in paths:seed(seedzip,'Content/'+k[6:]+'.uasset')
 env=dict(u=u,json=json,gzip=gzip,r=S/data_dir,mesh=None,load=u.load_asset,E=u.EditorAssetLibrary,owned=paths,clip_path=paths[0],report={'animations':[]},motions=[json.load(gzip.open(p)) for p in sorted((S/data_dir/'Motion').glob('*.json.gz'))],save=lambda a:save(a))
 exec(compile(code,str(S/recipe),'exec'),env)
 for k in paths:record(k,stage)
def save(a):
 if not u.EditorAssetLibrary.save_loaded_asset(a,False):raise RuntimeError(a.get_path_name())
def profiles():
 for name,k,n,f in [('handguard','/Game/Weapons/LMGStabilityGrip20261111/DA_M249_Handguard','Wrist39','handguard'),('bipod','/Game/Weapons/M249/Bipod/DA_M249_Bipod','Wrist34','bipod')]:
  if name=='bipod':seed('Wrist34/before.zip','Content/'+k[6:]+'.uasset')
  payload=gzip.decompress((S/n/(f+'.json.gz')).read_bytes()).decode()
  a=u.load_asset(k)
  if not a.set_shared_clips_from_json(payload):raise RuntimeError(k)
  save(a);record(k,n,{'clips':len(json.loads(payload)['clips'])})
def mount():
 n='GripMount40'
 # Two inputs are the exact post-40 packages from the subsequent pin operation.
 saved={k:v for k,v in read(S/n/'saved.json').items() if k in read(S/'BipodPin41/inputs.json') and sha(file(k))==v}
 (D/n/'saved.json').write_text(json.dumps(saved))
 run(D/n/'install.py')
 for k in read(D/n/'saved.json'):record(k,n)
def pin():
 n='BipodPin41';run(D/n/'install.py')
 for k in read(D/n/'saved.json'):record(k,n)
def rear():
 n='RearGrip44';p=D/n/'install.py'
 env={'__file__':str(p)};exec(compile(p.read_text('utf-8-sig').rsplit('\npublish()',1)[0],str(p),'exec'),env)
 before=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX');u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
 try:
  for k,original in read(S/n/'saved.json').items():
   key=k.rsplit('SM_M249_',1)[1];fbx=D/n/'Exports'/('SM_M249_'+key+'.fbx')
   if sha(fbx)!=original['fbx']:raise RuntimeError('FBX '+k)
   row=env['replace'](k,key,fbx)
   for field in ('surface','source_triangles','sections','fbx'):
    if row[field]!=original[field]:raise RuntimeError(k+' '+field)
   record(k,n,row)
 finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(before))
def icons():
 ref=read(S/'BipodIcon42/deployment.json')
 master=S/'BipodIcon42'/ref['master'];assert sha(master)==ref['master_sha256']
 keys={'/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms/'+s:master for s in ref['pngs']}
 k='/Game/ColdSteelData/Icons/ue_m249_no_bipod';p=R/'Content/ColdSteelData/Icons/ue_m249_no_bipod.png'
 assert sha(p)==read(R/'Docs/Publication/Conversation20261112/Evidence/local-assets.json')['Content/ColdSteelData/Icons/ue_m249_no_bipod.png']
 keys[k]=p
 keys['/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms/ue_m249_underbarrel_false']=R/'SourceAssets/LMGStabilityGrip20261111/Icons/ue_m249_underbarrel_false.png'
 for k,p in keys.items():
  q=file(k).with_suffix('.png');shutil.copy2(p,q)
  t=u.AssetImportTask();t.filename=str(q);t.destination_path,t.destination_name=k.rsplit('/',1);t.replace_existing=True;t.automated=True;t.save=False
  u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
  if not t.imported_object_paths:raise RuntimeError(k)
  a=u.load_asset(k);a.lod_group=u.TextureGroup.TEXTUREGROUP_UI;a.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;a.srgb=True;a.never_stream=True;a.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
  if 'FramedFirearms' not in k:a.set_editor_property('max_texture_size',0)
  save(a);record(k,'LMGStabilityGrip' if k.endswith('underbarrel_false') else 'BipodIcon42' if 'FramedFirearms' in k else 'Conversation20261112',{'png':sha(q)})
def attempt(n,func):
 try:func()
 except Exception: errors[n]=traceback.format_exc();u.log_error(errors[n])
 (W/'author-errors.json').write_text(json.dumps(errors,indent=2))
ledger={};errors={}
prefix='/Game/Weapons/M249/'
attempt('box',lambda:native('ReloadAudit21','ReloadAudit21/install.py',[prefix+'Animations/A_M249_'+i for i in ('reload','reload_empty')],'ReloadAudit21','ReloadAudit21/Before.zip'))
attempt('side',lambda:native('ReturnReview24','ReturnReview24/install.py',[prefix+'SideMagazine20261108/Animations/A_M249_'+i for i in ('side_reload','side_reload_empty')],'ReturnReview24','ReturnReview24/Before.zip'))
attempt('melee',lambda:native('Repair08','Repair08/import.py',[prefix+'Animations/A_M249_quick_melee'],'Repair08','Repair08/before.zip'))
attempt('deploy',lambda:native('Repair11','Repair09/import.py',[prefix+'Bipod/A_M249_Bipod'],'Repair11','Repair11/before.zip'))
attempt('profiles',profiles);attempt('mount',mount);attempt('pin',pin);attempt('rear',rear);attempt('icons',icons)
print('M249_RECOVERY_DONE',len(ledger),list(errors),flush=True)
