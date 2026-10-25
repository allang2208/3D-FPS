"""Five native jacket meshes per bounded batch, then native FP material variants."""
import gc,sys,importlib.util
import unreal as u
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/WorkwearSet')
from workwear_common import *
import workwear_materials as materials
def module(name,path):
    s=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
io=module('workwear_native_save','Tools/GarmentSleeveRepair/save_assets.py');io.R=R;io.DEST=DEST;io.receipt_path=R/'saved_assets.json';io.receipt=read(io.receipt_path) if io.receipt_path.exists() else dict(saved={},completed=False,runtime_tested=False)
# New jacket LOD0 retains the authored folds; distance LODs get their own budgets.
writer=(P/'Tools/GarmentSleeveRepair/save_assets.py').read_text(encoding='utf-8').split('def write_mesh(row):',1)[1].split('\ndef main():',1)[0]
writer='def write_mesh(row):'+writer.replace('for screen in (1.,.18,.075):','for ratio,screen in ((1.,1.),(.50,.18),(.22,.075)):').replace('num_of_triangles_percentage=1.,num_of_vert_percentage=1.','num_of_triangles_percentage=ratio,num_of_vert_percentage=ratio')
exec(compile(writer,'workwear_native_writer','exec'),io.__dict__)
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('Do not save during PIE')
mats=materials.create();manifest=read(R/'authored.json');female=read(R/'female-authored.json');rows=manifest['records']+female['records'];processed=0
if not manifest['completed'] or not female['completed']:raise RuntimeError('Finish jacket source production first')
for row in rows:
    key=KEY+'/'+row['profile'];digest=sha(row['file'])
    if io.receipt['saved'].get(key,{}).get('author_sha256')==digest:continue
    d=read(row['file']);current=mats+[mats[2]]
    if row['profile']=='Body':current[-1]=u.load_asset(d['binding_source']).materials[4].material_interface
    if row.get('owner'):current+=current
    desc=R/'SaveInputs'/(row['profile']+'.json');write(desc,dict(materials=[m.get_path_name() for m in current],material_slots=d['material_slots']))
    io.write_mesh(dict(profile=row['profile'],item=KEY,file=str(desc)));processed+=1;del d;gc.collect();u.SystemLibrary.collect_garbage()
    if processed>=4:break
body_done=all(io.receipt['saved'].get(KEY+'/'+row['profile'],{}).get('author_sha256')==sha(row['file']) for row in rows)
inputs=read(R/'inputs.json');fp={p:s for p,s in inputs['jason_recipe']['rig_meshes'].items() if p not in ('Body','Jason')}
if body_done:
    for profile,source in fp.items():
        key=KEY+'/'+profile
        if io.receipt['saved'].get(key,{}).get('material_revision')==read(R/'materials.json')['revision']:continue
        path=DEST+'/'+KEY+'/'+profile+'/SK_'+profile+'_'+KEY;asset=u.load_asset(path) or io.A.duplicate_asset(path.rsplit('/',1)[1],path.rsplit('/',1)[0],u.load_asset(source));slots=list(asset.materials)
        for i,mat in enumerate(mats):slots[i].set_editor_property('material_interface',mat)
        asset.set_editor_property('materials',slots);io.save(asset);io.receipt['saved'][key]=dict(asset=asset.get_path_name(),native=source,geometry_unchanged=True,material_revision=read(R/'materials.json')['revision'],lod_count=io.S.get_lod_count(asset));io.record();print('WORKWEAR_FP_SAVED',profile,flush=True);gc.collect();u.SystemLibrary.collect_garbage()
io.receipt['completed']=body_done and all(KEY+'/'+p in io.receipt['saved'] for p in fp);io.receipt['remaining']=sum(KEY+'/'+row['profile'] not in io.receipt['saved'] for row in rows);io.record();print('WORKWEAR_ASSET_BATCH',processed,'remaining',io.receipt['remaining'],flush=True)
