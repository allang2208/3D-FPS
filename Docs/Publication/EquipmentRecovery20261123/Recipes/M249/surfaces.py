from shared import *
import subprocess,_winapi,time
H=W/'SurfaceHost';D=H/'SourceAssets'/S.name
def link(p,q):
 if not q.exists():q.parent.mkdir(parents=True,exist_ok=True);_winapi.CreateJunction(str(p),str(q))
def private(p):return p.resolve().is_relative_to(H.resolve()) and '/Content/Weapons/M249/' in p.as_posix()
def displace(p,stage):
 if not p.is_file():return
 assert private(p)
 dst=W/'PriorIsolated'/stage/p.relative_to(H)
 dst.parent.mkdir(parents=True,exist_ok=True)
 if not dst.exists():p.replace(dst)
 else:raise RuntimeError(str(dst))
def setup():
 H.mkdir(exist_ok=True);shutil.copy2(R/'FPSGAME.uproject',H/'FPSGAME.uproject')
 for n in ('Binaries','Shaders','Plugins'):link(W/'Host'/n,H/n)
 shutil.copytree(R/'Config',H/'Config',dirs_exist_ok=True)
 for rel,own in [('Content','Weapons'),('Content/Weapons','M249')]:
  q=H/rel;q.mkdir(exist_ok=True,parents=True)
  for p in (R/rel).iterdir():
   if p.name==own:continue
   if p.is_dir():link(p,q/p.name)
   else:shutil.copy2(p,q/p.name)
 shutil.copytree(C/'Weapons/M249',H/'Content/Weapons/M249',dirs_exist_ok=True)
def inputs(stage):
 p=S/stage;q=D/stage;q.mkdir(parents=True,exist_ok=True)
 for f in p.iterdir():
  if f.is_dir() and f.name in ('Exports','Input'):link(f,q/f.name)
  elif f.is_file() and (f.suffix in ('.fbx','.json','.py','.gz','.wav')) and f.name!='install_receipt.json':shutil.copy2(f,q/f.name)
 if stage=='Repair16':shutil.copy2(S/'Repair13/install_receipt.json',D/'Repair13/install_receipt.json')
 orig=read(p/'install_receipt.json'); products=orig.get('asset_hashes',orig['saved'])
 before=set()
 if stage!='Repair13':
  with zipfile.ZipFile(next(p.glob('*.zip'))) as z:
   for member in z.namelist():
    rel=member if member.startswith('Content/') else 'Content/'+member
    if not rel.startswith('Content/Weapons/M249/') or not rel.endswith('.uasset'):continue
    dest=H/rel;assert private(dest);dest.write_bytes(z.read(member));before.add(rel)
 for k in products:
  rel=game(k)
  if rel not in before:displace(H/rel,stage)
 t=(p/'install.py').read_text('utf-8-sig')
 if stage=='Repair12':
  # Historical M24 reference meshes have since been saved by their owners. The archived M249 optics from R16 provide the final mesh input.
  t=t.replace("for path,sha in inputs['hashes'].items():","for path,sha in inputs['hashes'].items():\n    if not path.startswith('/Game/Weapons/M249/'):continue")
  t=t[:t.index('feed_finish={}')]+"R['complete']=True;record()\n"
 if stage=='Repair13':
  # Latest pose and geometry are authored from later exact checkpoints. Only generate the independent IR13 material creation and audio stages here.
  t=t.replace("for src,sha in inputs['hashes'].items():","for src,sha in inputs['hashes'].items():\n    if src.startswith('/Game/Weapons/M249/') and not ('/Materials/' in src or '/Audio/' in src):continue")
  start=t.index("cv='Interchange.FeatureFlags.Import.FBX'");end=t.index("dst=D+'/Audio/S_M249_Suppressed';",start)
  t=t[:start]+"for part in recipe['parts'].values():\n    for source in part['materials'].values():material(source)\n"+t[end:]
 if stage=='Finish29':
  pass
 (q/'replay.py').write_text(t,encoding='utf-8')
def execute(stage):
 q=D/stage;driver=W/('surface_'+stage+'.py')
 driver.write_text("import runpy\nfrom pathlib import Path\nroot=Path("+repr(str(q))+")\nrunpy.run_path(str(root/'replay.py'),run_name='__main__')\n"+("runpy.run_path(str(root/'finalize_surfaces.py'),run_name='__main__')\n" if stage=='Repair16' else ''),encoding='utf-8')
 exe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
 with (W/(stage+'-console.log')).open('wb') as output:
  p=subprocess.run([exe,str(H/'FPSGAME.uproject'),'-run=pythonscript','-script='+str(driver),'-unattended','-nullrhi','-nosound','-nop4','-NoLiveCoding','-NoSplash','-NoAssetRegistryCache','-abslog='+str(W/(stage+'.log'))],cwd=H,stdout=output,stderr=subprocess.STDOUT)
 receipt=q/'install_receipt.json';d=read(receipt) if receipt.exists() else {};complete=d.get('complete',False) and (stage!='Repair16' or d.get('surface_revision')==2)
 snapshot=W/(stage+'-authored.json');write(snapshot,d)
 inv=read(W/'inventory.json');out={}
 for k,h in d.get('asset_hashes',d.get('saved',{})).items():
  rel=game(k); ver=inv.get(rel,{}).get('version','')
  if not (ver.startswith(stage+'/') or (ver.startswith('Repair20/inputs') and k in read(S/stage/'install_receipt.json').get('asset_hashes',read(S/stage/'install_receipt.json')['saved']))):continue
  # Use a completed author pass; partial packages stay isolated for retry.
  if not complete:continue
  src=H/rel
  if sha(src)!=h:raise RuntimeError(k)
  dest=W/'SurfaceOutputs'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);out[k]=dict(stage=stage,sha256=h)
 write(stage+'-outputs.json',out)
 print(stage,'engine',p.returncode,'complete',complete,'approved scope saved',len(out),flush=True)
if __name__=='__main__':
 stages=sys.argv[1:] or ['Repair12','Repair13','Repair16','Finish29']
 if not H.exists():setup()
 for stage in stages:
  inputs(stage);execute(stage)
