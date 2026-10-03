"""Save continuous original membrane skin and enable bounded bone follow-through.

This replaces the fragmented cloth-display driver; it does not reimport or
delete visible geometry, repaint weights, alter UVs or rebuild animations.
"""
import json
from pathlib import Path
import shutil
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT=ROOT/'CoherentMembraneV34'
REPORT=OUT/'ue_coherent_membrane_delivery_v34.json'
DEST='/Game/Monsters/BlindSupplicantM07'
MESH=DEST+'/SK_M07_BodyMotionV18'
BP=DEST+'/BP_BlindSupplicantM07'
LIB=u.EditorAssetLibrary

if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve()!=PROJECT/'FPSGAME.uproject':
    raise RuntimeError('M07 membrane belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not editor or editor.is_in_play_in_editor():raise RuntimeError('M07_V34_PIE_PRESERVED')
    if any(p.get_path_name() in (MESH,BP) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Unsaved M07 mesh/Blueprint edits preserved.')
OUT.mkdir(parents=True,exist_ok=True)
for asset in (MESH,BP):
    source=PROJECT/'Content'/Path(asset.removeprefix('/Game/')+'.uasset')
    backup=OUT/'Before'/source.name
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(source,backup)
mesh=u.load_asset(MESH)
bp=u.load_asset(BP)
u.BlueprintEditorLibrary.compile_blueprint(bp)
defaults=u.get_default_object(bp.generated_class())
# Resolve the new property before touching either package: an old DLL must
# not detach cloth while leaving the new presentation inaccessible.
previous_mode=defaults.get_editor_property('use_coherent_gill_motion')
report=dict(revision='CoherentMembraneV34',saved=False,assets=[],mesh=MESH,
    source_geometry=str(ROOT/'BodyMotionV18/Proxy/M07_Original_GillContacts_V18.blend'),
    source_motion=str(PROJECT/'Source/FPSGAME/Monsters/M07MembraneMotionNode.cpp'),
    previous_mode=previous_mode,previous_clearance_degrees=defaults.get_editor_property('gill_clearance_angle_degrees'),
    previous_cloth_assets=[c.get_path_name() for c in mesh.get_editor_property('mesh_clothing_assets')],
    retained_actions={p:defaults.get_editor_property(p).get_path_name() for p in (
        'idle_clip','slow_walk_clip','chase_clip','melee_left_clip','melee_right_clip',
        'magic_gather_clip','magic_release_clip','death_clip','wall_listen_clip')},
    retained_directional_deaths=[c.get_path_name() for c in defaults.get_editor_property('directional_death_clips')],
    geometry_modified=False,weights_modified=False,uv_modified=False,reference_pose_modified=False,
    leaf_count=6,secondary_bones=12,secondary_max_bend_degrees=[1.8,1.3,1.3,1.8,1.3,1.3],
    secondary_solver='Analytic critically damped angular springs; common bend plane per leaf; original skin is the only display driver',
    particle_simulation=False,display_capture_mapping=False,new_runtime_ik=False,
    additional_tick=False,performance_measured=False,runtime_tested=False,rendered=False,user_review_pending=True)


def receipt():REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def save(asset):
    name=asset.get_path_name()
    if name.split('.')[0] not in (MESH,BP):raise RuntimeError('V34 save outside scope: '+name)
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('V34 save failed: '+name)
    report['assets'].append(name)
    receipt()


receipt()
report['detach']=json.loads(u.BlindSupplicantAuthoring.remove_gill_cloth_for_reimport(mesh))
if not report['detach'].get('success'):raise RuntimeError('V34 cloth detach failed: '+json.dumps(report['detach']))
LIB.set_metadata_tag(mesh,'MembraneRevision','CoherentMembraneV34: full original display skin, no fragmented cloth capture')
save(mesh)
defaults.set_editor_property('use_coherent_gill_motion',True)
defaults.set_editor_property('enable_gill_bone_clearance',True)
defaults.set_editor_property('gill_clearance_angle_degrees',4.)
LIB.set_metadata_tag(bp,'MembraneRevision','CoherentMembraneV34: bounded leaf bends and continuous skin driver')
save(bp)
report.update(saved=True,stage='Original visible mesh saved with coherent skin driver; existing AI/F6 Blueprint enabled',
    actual_cloth_asset_count=len(mesh.get_editor_property('mesh_clothing_assets')),clearance_degrees=4.,
    coherent_motion_enabled=defaults.get_editor_property('use_coherent_gill_motion'))
receipt()
for filename in ('production_status.json','gameplay_delivery.json'):
    path=ROOT/filename
    record=json.loads(path.read_text(encoding='utf-8-sig'))
    record.update(membrane_revision='CoherentMembraneV34',membrane_delivery=str(REPORT),
        membrane_driver='Original continuous bone skin plus bounded leaf-tip bends',
        membrane_proxy_asset=None,membrane_particle_simulation=False,
        runtime_tested=False,performance_measured=False,user_review_pending=True)
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('M07_V34_COHERENT_MEMBRANE_SAVED '+str(REPORT))
