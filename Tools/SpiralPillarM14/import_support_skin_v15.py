"""Save the repaired support skin on the live monster, preserving attacks and death."""
from pathlib import Path
import unreal as u
import json, shutil, traceback
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV15'
DEST='/Game/Monsters/SpiralPillarM14';E=u.EditorAssetLibrary
report={'complete':False,'saved':[],'runtime_tested':False,'rendered':False}
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
    report['preserved_settings']={key:cdo.get_editor_property(key) for key in (
        'spit_max_range','spit_travel_range','spit_cooldown','aggro_radius','leash_radius',
        'slam_contact_seconds','slam_trigger_range','slam_body_radius')}
    report['preserved_death_targets']=[str(n) for n in cdo.get_editor_property('soft_death_morph_targets')]
    report['preserved_death_times']=list(cdo.get_editor_property('soft_death_morph_times'))
    path=DEST+'/SK_M14_SupportSkin_v15'
    mesh=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(DEST+'/SK_M14_SoftCollapse_v14',path)
    names=json.loads((ROOT/'Exports/support_bones.json').read_text(encoding='utf8'))
    if not u.SpiralPillarM14.apply_support_skin(mesh,str(ROOT/'Exports/support_skin.bin'),[u.Name(n) for n in names]):
        raise RuntimeError('Support skin could not be applied')
    save(mesh)
    cdo.set_editor_property('visual_mesh',mesh);cdo.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(complete=True,mesh=mesh.get_path_name(),user_testing_pending=True)
    record();print('M14_V15_SUPPORT_SKIN_SAVED')
try:main()
except Exception:
    report['error']=traceback.format_exc();record();raise
