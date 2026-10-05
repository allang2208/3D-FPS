"""Save the continuous tissue-collapse mesh and 30 m ranged gameplay defaults."""
from pathlib import Path
import unreal as u
import json, shutil, traceback
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV14'
DEST='/Game/Monsters/SpiralPillarM14';E=u.EditorAssetLibrary
report={'complete':False,'saved':[],'tested':False,'rendered':False}
def record():(ROOT/'Records/ue_revision.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());record()
def main():
    backup=ROOT/'Before/BP_SpiralPillarM14.uasset';backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(PROJECT/'Content/Monsters/SpiralPillarM14/BP_SpiralPillarM14.uasset',backup)
    bp=u.load_asset(DEST+'/BP_SpiralPillarM14');cdo=u.get_default_object(bp.generated_class())
    report['preserved']={key:cdo.get_editor_property(key).get_path_name() for key in (
        'move_clip','turn_left_clip','turn_right_clip','bite_clip','spit_clip','whirlwind_clip',
        'trunk_slam_clip','death_clip','corpse_physics_asset','mucus_material','mucus_core_material')}
    data=json.loads((ROOT/'Exports/soft_collapse.json').read_text(encoding='utf8'))
    names=[u.Name(n) for n in data['names']]
    path=DEST+'/SK_M14_SoftCollapse_v14'
    mesh=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(DEST+'/SK_M14_HardwareSeams_v13',path)
    if not u.SpiralPillarM14.apply_soft_death_sequence(mesh,str(ROOT/'Exports/soft_collapse.bin'),names):
        raise RuntimeError('Continuous tissue collapse could not be applied')
    save(mesh)
    cdo.set_editor_property('visual_mesh',mesh);cdo.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
    cdo.set_editor_property('soft_death_morph_targets',names)
    cdo.set_editor_property('soft_death_morph_times',data['times'])
    cdo.set_editor_property('death_physics_fraction',.90)
    settings={key:data[key] for key in ('spit_max_range','spit_travel_range','aggro_radius','leash_radius')}
    for key,value in settings.items():cdo.set_editor_property(key,value)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(complete=True,mesh=mesh.get_path_name(),settings=settings,
                  death_targets=data['names'],death_times=data['times'],death_settled_seconds=3.10,
                  source_pose_blend_seconds=.42,physics_handoff_seconds=3.24,user_testing_pending=True)
    record();print('M14_V14_SOFT_COLLAPSE_SAVED')
try:main()
except Exception:
    report['error']=traceback.format_exc();record();raise
