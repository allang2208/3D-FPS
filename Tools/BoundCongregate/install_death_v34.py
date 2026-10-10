"""Bind an M-88-only unsupported drop profile to the current cooked corpse."""
from pathlib import Path
import json, shutil
import unreal as u
P=Path('D:/FPS3D/FPSGAME');OUT=P/'SourceAssets/BoundCongregateMeshy20261006/DeathV34';OUT.mkdir(exist_ok=True)
BASE='/Game/Monsters/BoundCongregate'
SOURCE=BASE+'/TentacleReachV29/SK_BoundCongregate_TentacleReachV29'
DEST=BASE+'/DeathV34/DA_BoundCongregate_UnsupportedDropV34'
E=u.EditorAssetLibrary
report=dict(complete=False,saved=[],tested=False,rendered=False)
def record():(OUT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    report['saved'].append(a.get_path_name());record()
try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active PIE')
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if SOURCE in dirty or DEST in dirty:raise RuntimeError('Preserve unsaved owned assets')
    live=u.load_asset(SOURCE)
    cdo=u.get_default_object(u.load_asset(BASE+'/BP_BoundCongregate').generated_class())
    if cdo.get_editor_property('visual_mesh')!=live:raise RuntimeError('Active visual changed')
    revision=E.get_metadata_tag(live,'CorpseRevision')
    if revision not in ('M88 V32 continuous anatomical XPBD','M88 V34 unsupported in-place drop'):
        raise RuntimeError('Active corpse revision changed: '+revision)
    previous=u.load_asset(BASE+'/DeathV32/DA_BoundCongregate_CorpseV32')
    data=u.load_asset(DEST) or E.duplicate_asset(previous.get_path_name(),DEST)
    author=json.loads((P/'SourceAssets/BoundCongregateMeshy20261006/DeathV32/authoring.json').read_text(encoding='utf8'))
    # The cooked node array is not Python-visible. Reuse the exact V32
    # authoring layout with its duplicated data asset; no cage rebuild occurs.
    count=int(author['nodes']);body=int(author['body_nodes'])
    if not author['complete'] or sum(r['nodes'] for r in author['regions'])!=count-body:
        raise RuntimeError('Corpse anatomical node layout changed')
    # V32 authors torso nodes first, followed by each complete limb/organ.
    # Include every appendage; none keeps a compressive stance constraint.
    data.set_editor_property('collapse_in_place',True)
    data.set_editor_property('unsupported_nodes',list(range(body,count)))
    E.set_metadata_tag(data,'DeathMotion','All appendages released immediately; gravity drop without horizontal shove')
    save(data)
    source_file=P/'Content/Monsters/BoundCongregate/TentacleReachV29/SK_BoundCongregate_TentacleReachV29.uasset'
    backup=OUT/'before'/source_file.name;backup.parent.mkdir(exist_ok=True)
    if not backup.exists():shutil.copy2(source_file,backup)
    u.M14SoftBodyData.bind_to_living_mesh(live,data)
    E.set_metadata_tag(live,'CorpseRevision','M88 V34 unsupported in-place drop')
    save(live)
    report.update(complete=True,profile=data.get_path_name(),corpse=data.get_editor_property('corpse_mesh').get_path_name(),
        nodes=count,unsupported_nodes=count-body,appendages=[r['region'] for r in author['regions']],
        horizontal_initial_velocity_cm_s=0,initial_foot_anchor_seconds=0,
        authored_forward_side_impulse=False,compressive_appendage_distance_constraints=False,
        retained='live mesh / V33 bite / V28 flurry / 30m tentacle / one-contact escape / garments',
        user_testing_pending=True)
    print('BOUND_DEATH_V34_SAVED '+json.dumps(dict(nodes=count,unsupported_nodes=count-body)),flush=True)
except Exception as e:report['error']=str(e);raise
finally:record()
