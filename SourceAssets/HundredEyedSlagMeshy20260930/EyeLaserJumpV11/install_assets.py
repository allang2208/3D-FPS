"""Save four charge-only animation assets; preserve all accepted attacks/skin."""
import json
import shutil
import sys
from pathlib import Path
import unreal as u

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
PROJECT = OUT.parents[2]
BASE = '/Game/Monsters/HundredEyedSlag'
LIB = u.EditorAssetLibrary
contracts = json.loads((OUT/'animation_contract.json').read_text())['actions']
paths = [BASE+'/EyeLaserJumpV11/Animations/A_HundredEyedSlag_'+c['name'] for c in contracts]
skeleton_path = BASE+'/V1/SK_HundredEyedSlag_V1_Skeleton'
if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve(): raise RuntimeError('Wrong project')
if u.EditorLevelLibrary.get_game_world() is not None: raise RuntimeError('End related PIE before animation saving')
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(paths+[skeleton_path]): raise RuntimeError('Unsaved target animation/skeleton preserved')

material_path=BASE+'/EyeLaserJumpV11/Materials/M_EyeLaser'
if material_path in dirty: raise RuntimeError('Unsaved eye laser material preserved')
if LIB.does_asset_exist(material_path):
    material=u.load_asset(material_path)
    if LIB.get_metadata_tag(material,'HundredEyedSlag.EyeLaser')!='V11': raise RuntimeError('Unowned laser material preserved')
else:
    material=u.AssetToolsHelpers.get_asset_tools().create_asset('M_EyeLaser',material_path.rsplit('/',1)[0],u.Material,u.MaterialFactoryNew())
    material.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided',True)
    editing=u.MaterialEditingLibrary
    tint=editing.create_material_expression(material,u.MaterialExpressionVectorParameter,-400,0)
    tint.set_editor_property('parameter_name','Tint');tint.set_editor_property('default_value',u.LinearColor(1,.045,.009,1))
    intensity=editing.create_material_expression(material,u.MaterialExpressionScalarParameter,-400,120)
    intensity.set_editor_property('parameter_name','Intensity');intensity.set_editor_property('default_value',6.)
    multiply=editing.create_material_expression(material,u.MaterialExpressionMultiply,-160,0)
    editing.connect_material_expressions(tint,'',multiply,'A');editing.connect_material_expressions(intensity,'',multiply,'B')
    editing.connect_material_property(multiply,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    opacity=editing.create_material_expression(material,u.MaterialExpressionScalarParameter,-400,280)
    opacity.set_editor_property('parameter_name','Opacity');opacity.set_editor_property('default_value',.32)
    depth=editing.create_material_expression(material,u.MaterialExpressionDepthFade,-150,280)
    depth.set_editor_property('fade_distance_default',8.)
    if not editing.connect_material_expressions(opacity,'',depth,'Opacity'): raise RuntimeError('Laser opacity connection failed')
    editing.connect_material_property(depth,'',u.MaterialProperty.MP_OPACITY)
    LIB.set_metadata_tag(material,'HundredEyedSlag.EyeLaser','V11')
    errors=editing.recompile_material(material)
    if errors: raise RuntimeError('Eye laser material compilation failed: '+str(errors))
if not LIB.save_loaded_asset(material,False): raise RuntimeError('Eye laser material save failed')
print('SLAG_EYE_LASER_MATERIAL_SAVED',flush=True)

for path in paths+[skeleton_path]:
    source = PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    backup = OUT/'Before'/(path.removeprefix('/Game/')+'.uasset')
    if source.exists() and not backup.exists():
        backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
skeleton = u.load_asset(skeleton_path)
mesh = u.load_asset(BASE+'/PolishV2/SK_HundredEyedSlag_V2')
if skeleton is None or mesh is None: raise RuntimeError('Existing skeleton and V8 mesh required')
sys.path.insert(0,str(PROJECT/'Tools/InfectedDog'))
from meshy_animation_units import match_bind_root_scale
variable='Interchange.FeatureFlags.Import.FBX'
old=u.SystemLibrary.get_console_variable_int_value(variable)
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
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        clip=u.load_asset(path)
        if clip is None or path not in [p.split('.')[0] for p in task.imported_object_paths]:
            raise RuntimeError('Charge animation import failed: '+path)
        units=match_bind_root_scale(clip,mesh);clip.set_preview_skeletal_mesh(mesh)
        LIB.set_metadata_tag(clip,'HundredEyedSlag.Revision','EyeLaserJumpV11_20261001')
        if not LIB.save_loaded_asset(clip,False):raise RuntimeError('Charge save failed: '+path)
        saved.append({'role':c['name'],'path':clip.get_path_name(),'seconds':clip.get_play_length(),'units':units,'saved':True})
        print('SLAG_SPECIAL_ANIMATION_SAVED '+c['name'],flush=True)
    dirty_after={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    skeleton_saved=False
    # The existing hierarchy already contains every exported bone. Keep its
    # package read-only: other editors may have this shared skeleton loaded.
    # New animation packages retain their reference to the saved skeleton;
    # importer bookkeeping on that loaded object is not written to disk.
finally:u.SystemLibrary.execute_console_command(None,variable+' '+str(old))
receipt={'revision':'EyeLaserJumpV11','animation_assets_saved':len(saved),'assets':saved,'skeleton_saved':skeleton_saved,
    'mesh_saved':False,'accepted_sweep_and_slam_reimported':False,'native_runtime_build_pending':True,
    'execution_mode':'existing_editor_bridge' if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() else 'background_commandlet',
    'tested':False,'preview_rendered':False}
(OUT/'animation_installation.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
status_path=ROOT/'production_status.json';status=json.loads(status_path.read_text(encoding='utf-8-sig'))
status.update(working_revision='EyeLaserJumpV11',special_animation_installation='EyeLaserJumpV11/animation_installation.json',
    special_animations_saved=8,special_runtime_build_pending=True,native_code_changed=True,native_build_required=True,
    special_attacks_tested=False,preview_rendered=False)
status_path.write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'ready_assets.json').write_text(json.dumps({'revision':'EyeLaserJumpV11','animations_saved':8,'material_saved':True,'native_build_pending':True},indent=2),encoding='utf-8')
print('SLAG_V11_EIGHT_ANIMATIONS_AND_LASER_MATERIAL_SAVED',flush=True)
