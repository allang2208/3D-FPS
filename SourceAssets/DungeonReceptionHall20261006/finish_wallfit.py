"""Save final placement adjustments on this task's just-published map only."""
import unreal as u
from pathlib import Path
import json,hashlib
from collections import defaultdict
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
CFG=json.loads((ROOT/'Config/layout.json').read_text('utf8'));OLD=json.loads((ROOT/'Snapshots/layout-before-wallfit.json').read_text('utf8'))
disk=PROJECT/'Content/GameMaps/Design/L_ReceptionHall_Subject.umap';snapshot=ROOT/'Snapshots/L_ReceptionHall_Subject.before-wallfit.umap'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Preserve active PIE')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map edits')
if hashlib.sha256(disk.read_bytes()).digest()!=hashlib.sha256(snapshot.read_bytes()).digest():raise RuntimeError('Subject changed since this task saved it; preserve newer map')
world=u.EditorLoadingAndSavingUtils.load_map(CFG['map']);AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
actors={a.get_actor_label():a for a in AA.get_all_level_actors()};by_id={p['id']:p for p in OLD['parts']};groups=defaultdict(list);moved=[]
for p in CFG['parts']:groups[(p['mesh'],p['collision'])].append(p)
def vec(p):return u.Vector(p[0]*100,-p[1]*100,p[2]*100)
for (mesh,collision),parts in groups.items():
    cluster=actors.get('Reception_Instances_'+mesh.rsplit('/',1)[1])
    comp=cluster.get_component_by_class(u.InstancedStaticMeshComponent) if cluster else None
    for index,p in enumerate(parts):
        if p['position_m']==by_id[p['id']]['position_m']:continue
        if comp:
            comp.modify();t=u.Transform(location=vec(p['position_m']),rotation=u.Rotator(pitch=0,yaw=-p['yaw_deg'],roll=0),scale=u.Vector(*p['scale']))
            if not comp.update_instance_transform(index,t,True,True,True):raise RuntimeError('Unable to move instance '+p['id'])
        else:
            a=actors['Reception_'+p['id']];a.modify();a.set_actor_location(vec(p['position_m']),False,True)
        moved.append(p['id'])
for kind in ('WallClock','ClockHands'):
    a=actors['Reception_SM_Reception_'+kind];a.modify();a.set_actor_location(vec([0,.12,0]),False,True);moved.append(kind)
u.EditorAssetLibrary.set_metadata_tag(world,'ReceptionHall20261006.WallFit','20261006-final')
if not u.EditorLoadingAndSavingUtils.save_map(world,CFG['map']):raise RuntimeError('Unable to save final layout')
receipt=json.loads((ROOT/'Receipts/install.json').read_text('utf8'));receipt['wall_fit']=dict(saved=True,moved=moved,tests_run=False)
(ROOT/'Receipts/install.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
(ROOT/'Receipts/wallfit.json').write_text(json.dumps(dict(stage='map_saved',moved=moved,tests_run=False),ensure_ascii=False,indent=2),encoding='utf8')
print('RECEPTION_FINAL_WALL_FIT_SAVED',len(moved))
