"""Import one espresso assembly and save its two existing staff sample maps."""
import json,hashlib,re,shutil,sys
from pathlib import Path
from datetime import datetime
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];OUT=ROOT/'CoffeePolishV7'
if json.loads((ROOT/'Config/room.json').read_text('utf8')).get('production_revision',0)>=1:
    current=ROOT/'Production20261002/Scripts/install_production.py'
    exec(compile(current.read_text('utf8'),str(current),'exec'))
    raise SystemExit(0)
CFG=json.loads((OUT/'Authored/room-coffee.json').read_text('utf8'))
MAN=json.loads((OUT/'Authored/manifest.json').read_text('utf8'));BASE=CFG['ue_base']+'/CoffeePolishV7'
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
RP=OUT/'install.json';report=json.loads(RP.read_text('utf8')) if RP.exists() else dict(meshes={},maps={},materials=[],backups=[])
report.update(tests_run=False,game_run=False,rendered=False,editor_opened=False)

def record():RP.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
sys.path.insert(0,str(ROOT/'Scripts'))
from build_coffee_materials_v7 import build_materials
report['materials']=build_materials(ROOT,BASE);record()
# Reuse the established FBX import/build implementation without its map edits.
v4=ROOT/'Scripts/import_scene_polish_v4.py';v4code=v4.read_text('utf8')
mesh_code=v4code[v4code.index('u.SystemLibrary.execute_console_command'):v4code.index('AA=u.get_editor_subsystem')]
exec(compile(mesh_code,str(v4),'exec'))
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
backup=OUT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
rec=next(r for r in CFG['rooms'] if r['id']=='StaffRecreation')
part=next(p for p in rec['furniture'] if p['id']=='CoffeeMachine')
label='StaffSubject_StaffRecreation_CoffeeMachine';name=MAN['prototypes']['CoffeeMachine']
for target in (CFG['maps']['StaffRecreation'],CFG['sample_map']):
    if report['maps'].get(target,{}).get('stage')=='map_saved':continue
    disk=PROJECT/'Content'/(target.removeprefix('/Game/')+'.umap');dst=backup/disk.name
    shutil.copy2(disk,dst);report['backups'].append(dict(original=str(disk),backup=str(dst)));record()
    world=u.EditorLoadingAndSavingUtils.load_map(target)
    if not world:raise RuntimeError('Cannot load existing staff map '+target)
    actors=[a for a in AA.get_all_level_actors() if a.get_actor_label()==label and 'StaffLiving.Subject' in [str(t) for t in a.tags]]
    if len(actors)!=1:raise RuntimeError('Preserve unexpected coffee assembly count '+str(len(actors)))
    actor=actors[0];component=actor.get_component_by_class(u.StaticMeshComponent)
    if not component:raise RuntimeError('Missing owned coffee component')
    component.set_static_mesh(meshes[name]);component.set_collision_profile_name('NoCollision')
    if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Map save failed '+target)
    report['maps'][target]=dict(stage='map_saved',changed=[label]);record()
    u.log('STAFF_COFFEE_POLISH_V7_MAP_SAVED '+target)
for filename in ('room.json','modules-draft.json'):shutil.copy2(ROOT/'Config'/filename,backup/filename)
# Update only this prototype reference; keep current furniture and container data.
dp=ROOT/'Config/modules-draft.json';draft=json.loads(dp.read_text('utf8'))
module=next(m for m in draft['modules'] if m['id']=='StaffRecreation')
draftpart=next(p for p in module['parts'] if p.get('id')=='CoffeeMachine')
draftpart.update(mesh=items[name]['asset'],materials=[],collision=False)
draft['coffee_polish_revision']=7;dp.write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding='utf8')
cp=ROOT/'Config/room.json';current=json.loads(cp.read_text('utf8'))
for key in ('coffee_polish_revision','revision','current_authored_source'):current[key]=CFG[key]
cp.write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf8')
report.update(stage='samples_saved',current_authored_source=CFG['current_authored_source'],native_changes=False,
    native_build_required=False,random_pool_registered=False,rewards_deferred=True)
record();u.log('STAFF_COFFEE_POLISH_V7_DELIVERY_SAVED')
