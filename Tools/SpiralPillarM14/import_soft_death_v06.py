"""Save M14 soft death, its continuous morph mesh and matching flattened corpse hulls."""
from pathlib import Path
import json, shutil, traceback
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV06'
DEST='/Game/Monsters/SpiralPillarM14'
LIB=u.EditorAssetLibrary
REPORT=ROOT/'Records/ue_revision.json'
report={'complete':False,'saved':[],'tested':False,'rendered':False}

def record():REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def save(asset):
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());record()

def import_fbx(filename,name,folder,skeleton,animation=False):
    path=folder+'/'+name
    if LIB.does_asset_exist(path):return u.load_asset(path)
    task=u.AssetImportTask();task.filename=str(filename);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.save=False;task.factory=u.FbxFactory()
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.import_as_skeletal=True;options.skeleton=skeleton
    options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION if animation else u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_mesh=not animation;options.import_animations=animation
    options.import_materials=False;options.import_textures=False;options.create_physics_asset=False
    data=options.anim_sequence_import_data if animation else options.skeletal_mesh_import_data
    data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    if animation:
        data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',30)
        data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    else:
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        data.set_editor_property('import_morph_targets',True)
        data.set_editor_property('update_skeleton_reference_pose',False)
        data.set_editor_property('use_t0_as_ref_pose',False)
    task.options=options;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Import did not create '+path)
    return asset

def main():
    original=PROJECT/'Content/Monsters/SpiralPillarM14/BP_SpiralPillarM14.uasset'
    backup=ROOT/'Before/BP_SpiralPillarM14.uasset';backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(original,backup)
    bp=u.load_asset(DEST+'/BP_SpiralPillarM14');u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=u.get_default_object(bp.generated_class());previous_mesh=cdo.get_editor_property('visual_mesh')
    alive_physics=previous_mesh.physics_asset
    report['previous_mesh']=previous_mesh.get_path_name()
    report['previous_death']=cdo.get_editor_property('death_clip').get_path_name()
    report['preserved']={name:cdo.get_editor_property(name).get_path_name()
        for name in ('bite_clip','spit_clip','sweep_positive_clip','sweep_negative_clip','move_clip')}
    report['preserved'].update({name:float(cdo.get_editor_property(name))
        for name in ('bite_trigger_range','mouth_reach','walk_speed','animation_walk_speed')})
    path=DEST+'/SK_M14_SoftDeath_v06'
    mesh=u.load_asset(path) if LIB.does_asset_exist(path) else LIB.duplicate_asset(previous_mesh.get_path_name(),path)
    if not u.SpiralPillarM14.build_soft_death_morphs(mesh):
        raise RuntimeError('Could not write continuous morph source data')
    save(mesh)
    report['mesh_authoring']='Original UE mesh duplicated; editable morph source deltas from the Blender spatial field'
    old_fbx=u.SystemLibrary.get_console_variable_bool_value('Interchange.FeatureFlags.Import.FBX')
    try:
        u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
        clip=import_fbx(ROOT/'Exports/A_M14_Death_v06.fbx','A_M14_Death_v06',DEST+'/Animations',previous_mesh.skeleton,True)
    finally:
        u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+('1' if old_fbx else '0'))
    # Bind the actual imported names. Blender FBX can prefix them with its node.
    imported=[target.get_name() for target in mesh.get_editor_property('morph_targets')]
    morphs=[]
    for requested in ('M14_DeathSag','M14_DeathFold','M14_DeathSpread'):
        matches=[name for name in imported if name==requested or name.endswith('_'+requested)]
        if len(matches)!=1:raise RuntimeError('Cannot bind requested morph '+requested+': '+str(imported))
        morphs.append(matches[0])
    materials={family:u.load_asset(DEST+'/Materials/M_M14_'+family) for family in ('Body','Mouth','Membrane','Metal')}
    for material in materials.values():
        material.set_editor_property('used_with_morph_targets',True)
        errors=u.MaterialEditingLibrary.recompile_material(material)
        if errors:raise RuntimeError(str(errors))
        save(material)
    # Duplication keeps the original section/slot/material assignments intact.
    mesh.set_editor_property('physics_asset',alive_physics)
    save(mesh);save(mesh.skeleton)
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('loop',False);clip.set_preview_skeletal_mesh(mesh);save(clip)
    path=DEST+'/PA_M14_SoftCorpse_v06'
    corpse=u.load_asset(path) if LIB.does_asset_exist(path) else LIB.duplicate_asset(cdo.get_editor_property('corpse_physics_asset').get_path_name(),path)
    hulls=json.loads((ROOT/'Exports/soft_corpse_hulls.json').read_text(encoding='utf8'))['hulls']
    points=[u.Vector(*point) for hull in hulls for point in hull]
    if not u.SpiralPillarM14.build_soft_corpse_physics(mesh,corpse,points,[len(hull) for hull in hulls]):
        raise RuntimeError('Could not author flattened corpse collision')
    save(corpse)
    cdo.set_editor_property('visual_mesh',mesh);cdo.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
    cdo.set_editor_property('death_clip',clip);cdo.set_editor_property('corpse_physics_asset',corpse)
    cdo.set_editor_property('soft_death_morph_targets',[u.Name(name) for name in morphs])
    cdo.set_editor_property('death_physics_fraction',.9)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(complete=True,mesh=mesh.get_path_name(),morphs=morphs,death_animation=clip.get_path_name(),
        corpse_physics=corpse.get_path_name(),death_seconds=3.6,fully_spread_seconds=2.7,handoff_seconds=3.24,
        animated_bone_scale='unit',physics_bodies=1,physics_hulls=len(hulls),user_testing_pending=True)
    record();print('M14_V06_SOFT_DEATH_SAVED')

try:main()
except Exception:
    report['error']=traceback.format_exc();record();raise
