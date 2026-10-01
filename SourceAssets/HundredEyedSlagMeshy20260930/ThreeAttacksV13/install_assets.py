"""Save three idle-casting clips and the exposure-compensated red eye sprite."""
import json, sys, shutil
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent;PROJECT=OUT.parents[2]
BASE='/Game/Monsters/HundredEyedSlag';REV='ThreeAttacksV13'
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools()
contracts=json.loads((OUT/'animation_contract.json').read_text())['actions']
paths=[BASE+'/ThreeAttacksV13/Animations/A_HundredEyedSlag_'+c['name'] for c in contracts]
material_path=BASE+'/ThreeAttacksV13/Materials/M_EyeChargeRed'
skeleton_path=BASE+'/V1/SK_HundredEyedSlag_V1_Skeleton'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if u.EditorLevelLibrary.get_game_world() is not None:raise RuntimeError('End related PIE before asset saving')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(paths+[material_path,skeleton_path]):raise RuntimeError('Unsaved target assets preserved')
for path in paths+[material_path]:
    if LIB.does_asset_exist(path) and LIB.get_metadata_tag(u.load_asset(path),'HundredEyedSlag.Revision')!=REV:
        raise RuntimeError('Unowned destination preserved: '+path)
    source=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    backup=OUT/'Before'/(path.removeprefix('/Game/')+'.uasset')
    if source.exists() and not backup.exists():
        backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
material=u.load_asset(material_path) if LIB.does_asset_exist(material_path) else TOOLS.create_asset(
    'M_EyeChargeRed',material_path.rsplit('/',1)[0],u.Material,u.MaterialFactoryNew())
editing=u.MaterialEditingLibrary
for e in list(editing.get_material_expressions(material)):editing.delete_material_expression(material,e)
material.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
material.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
material.set_editor_property('two_sided',True)
material.set_editor_property('disable_depth_test',False)
uv=editing.create_material_expression(material,u.MaterialExpressionTextureCoordinate,-620,260)
mask=editing.create_material_expression(material,u.MaterialExpressionCustom,-400,260)
mask.set_editor_property('code','float2 p=UV-.5;float r=length(p);float core=exp(-r*r*92);float halo=exp(-r*r*24)*.38;return saturate(core+halo)*smoothstep(.5,.36,r);')
mask.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
input_uv=u.CustomInput();input_uv.set_editor_property('input_name','UV');mask.set_editor_property('inputs',[input_uv])
if not editing.connect_material_expressions(uv,'',mask,'UV'):raise RuntimeError('Sprite UV connection failed')
tint=editing.create_material_expression(material,u.MaterialExpressionVectorParameter,-620,-40)
tint.set_editor_property('parameter_name','Tint');tint.set_editor_property('default_value',u.LinearColor(1,.006,.002,1))
intensity=editing.create_material_expression(material,u.MaterialExpressionScalarParameter,-620,80)
intensity.set_editor_property('parameter_name','Intensity');intensity.set_editor_property('default_value',16.)
emissive=editing.create_material_expression(material,u.MaterialExpressionMultiply,-400,-40)
editing.connect_material_expressions(tint,'',emissive,'A');editing.connect_material_expressions(intensity,'',emissive,'B')
exposure=editing.create_material_expression(material,u.MaterialExpressionEyeAdaptationInverse,-160,-40)
exposure_input=str(editing.get_material_expression_input_names(exposure)[0])
if not editing.connect_material_expressions(emissive,'',exposure,exposure_input):raise RuntimeError('Exposure compensation connection failed')
editing.connect_material_property(exposure,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
opacity=editing.create_material_expression(material,u.MaterialExpressionScalarParameter,-620,440)
opacity.set_editor_property('parameter_name','Opacity');opacity.set_editor_property('default_value',.9)
multiply=editing.create_material_expression(material,u.MaterialExpressionMultiply,-160,280)
editing.connect_material_expressions(mask,'',multiply,'A');editing.connect_material_expressions(opacity,'',multiply,'B')
depth=editing.create_material_expression(material,u.MaterialExpressionDepthFade,30,280)
depth.set_editor_property('fade_distance_default',2.)
if not editing.connect_material_expressions(multiply,'',depth,'Opacity'):raise RuntimeError('Sprite fade connection failed')
editing.connect_material_property(depth,'',u.MaterialProperty.MP_OPACITY)
editing.set_material_usage(material,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
errors=editing.recompile_material(material)
if errors:raise RuntimeError('Eye charge material compilation failed: '+str(errors))
LIB.set_metadata_tag(material,'HundredEyedSlag.Revision',REV)
if not LIB.save_loaded_asset(material,False):raise RuntimeError('Red eye sprite material save failed')
print('SLAG_V13_RED_EYE_SPRITE_MATERIAL_SAVED',flush=True)
skeleton=u.load_asset(skeleton_path)
mesh=u.load_asset(BASE+'/ArticulationV12/SK_HundredEyedSlag_V12')
if skeleton is None or mesh is None:raise RuntimeError('Saved V12 mesh and common skeleton required')
sys.path.insert(0,str(PROJECT/'Tools/InfectedDog'))
from meshy_animation_units import match_bind_root_scale
variable='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(variable)
u.SystemLibrary.execute_console_command(None,variable+' 0')
saved=[]
try:
    for c,path in zip(contracts,paths):
        op=u.FbxImportUI();op.automated_import_should_detect_type=False;op.override_full_name=True
        op.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;op.import_as_skeletal=True
        op.import_mesh=False;op.import_animations=True;op.import_materials=False;op.import_textures=False;op.skeleton=skeleton
        op.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        op.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
        task=u.AssetImportTask();task.filename=str(OUT/'Delivery'/c['file'])
        task.destination_path,task.destination_name=path.rsplit('/',1)
        task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True;task.options=op
        TOOLS.import_asset_tasks([task]);clip=u.load_asset(path)
        if clip is None or path not in [p.split('.')[0] for p in task.imported_object_paths]:raise RuntimeError('Clip import failed: '+path)
        units=match_bind_root_scale(clip,mesh);clip.set_preview_skeletal_mesh(mesh)
        LIB.set_metadata_tag(clip,'HundredEyedSlag.Revision',REV)
        if not LIB.save_loaded_asset(clip,False):raise RuntimeError('Clip save failed: '+path)
        saved.append(dict(role=c['name'],path=clip.get_path_name(),seconds=clip.get_play_length(),saved=True,units=units))
        print('SLAG_V13_IDLE_LASER_CLIP_SAVED '+c['name'],flush=True)
finally:u.SystemLibrary.execute_console_command(None,variable+' '+str(old))
receipt=dict(revision=REV,animation_assets_saved=len(saved),assets=saved,material_saved=True,
    material_path=material.get_path_name(),mesh_saved=False,skeleton_saved=False,native_runtime_build_pending=True,
    execution_mode='background_commandlet' if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower() else 'existing_editor_bridge',
    tested=False,preview_rendered=False)
(OUT/'animation_installation.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
(OUT/'ready_assets.json').write_text(json.dumps(dict(revision=REV,animations_saved=3,material_saved=True,
    native_build_pending=True),indent=2),encoding='utf-8')
print('SLAG_V13_THREE_IDLE_LASER_CLIPS_AND_MATERIAL_SAVED',flush=True)
