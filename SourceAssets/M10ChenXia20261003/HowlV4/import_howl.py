"""Save M10's dedicated howl clip/VFX and reuse the actual HandBrain voice reference."""
from pathlib import Path
import json,sys,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[2]
DEST='/Game/Monsters/M10Mawcrawler';REV='M10HowlV4_20261003'
sys.path.insert(0,str(PROJECT/'Tools/InfectedDog'))
from meshy_animation_units import match_bind_root_scale
lib=u.EditorAssetLibrary;tools=u.AssetToolsHelpers.get_asset_tools();mel=u.MaterialEditingLibrary
report={'revision':REV,'saved':[],'runtime_tested':False,'preview_rendered':False}
def receipt():(ROOT/'asset_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def load(path):
    asset=u.load_asset(path)
    if asset is None:raise RuntimeError('Missing '+path)
    return asset
def owned(path):
    if not lib.does_asset_exist(path):return None
    asset=load(path)
    if lib.get_metadata_tag(asset,'M10.HowlRevision')!=REV:raise RuntimeError('Preserving unowned asset '+path)
    return asset
def save(asset):
    lib.set_metadata_tag(asset,'M10.HowlRevision',REV)
    if not lib.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());receipt()
def import_asset(file,folder,name,options):
    path=folder+'/'+name;asset=owned(path)
    if asset is not None:return asset
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.options=options;task.automated=True;task.save=False;task.replace_existing=False
    tools.import_asset_tasks([task]);return load(path)
def node(material,kind,**properties):
    value=mel.create_material_expression(material,kind)
    for key,data in properties.items():value.set_editor_property(key,data)
    return value
def wire(a,b,input_name,output=''):
    if not mel.connect_material_expressions(a,output,b,input_name):raise RuntimeError('Cannot connect '+input_name)

if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if any(p.get_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserving unsaved M10 content')
old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
try:
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    contract=json.loads((ROOT/'howl_contract.json').read_text(encoding='utf-8'))
    mesh=load(DEST+'/SK_M10_Mawcrawler');skeleton=mesh.get_editor_property('skeleton')
    op=u.FbxImportUI();op.automated_import_should_detect_type=False;op.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    op.import_as_skeletal=True;op.import_mesh=False;op.import_animations=True;op.import_materials=False;op.import_textures=False;op.skeleton=skeleton
    data=op.anim_sequence_import_data;data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',30)
    data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME);data.set_editor_property('remove_redundant_keys',False)
    clip=import_asset(contract['animation_file'],DEST+'/Animations/HowlV4','A_M10_Howl_V4',op)
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',False);clip.set_editor_property('rate_scale',1.)
    clip.set_preview_skeletal_mesh(mesh);report['root_unit_adaptation']=match_bind_root_scale(clip,mesh);save(clip)

    op=u.FbxImportUI();op.automated_import_should_detect_type=False;op.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    op.import_as_skeletal=False;op.import_mesh=True;op.import_animations=False;op.import_materials=False;op.import_textures=False
    op.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    op.static_mesh_import_data.set_editor_property('generate_lightmap_u_vs',False)
    wave=import_asset(contract['wave_file'],DEST+'/FX/HowlV4','SM_M10_HowlWave',op)
    material=owned(DEST+'/FX/HowlV4/M_M10_HowlWave')
    if material is None:
        material=tools.create_asset('M_M10_HowlWave',DEST+'/FX/HowlV4',u.Material,u.MaterialFactoryNew())
    mel.delete_all_material_expressions(material)
    material.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('two_sided',True);material.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    uv=node(material,u.MaterialExpressionTextureCoordinate)
    opacity=node(material,u.MaterialExpressionScalarParameter,parameter_name='Opacity',default_value=.6)
    angle=node(material,u.MaterialExpressionScalarParameter,parameter_name='HalfAngle',default_value=60.)
    mask=node(material,u.MaterialExpressionCustom,output_type=u.CustomMaterialOutputType.CMOT_FLOAT1,
        code='float edge=saturate((HalfAngle-abs(UV.x-.5)*180.0)/3.0); float v=saturate(1-abs(UV.y*2-1)); return edge*pow(v,1.5)*(.7+.3*cos(UV.y*18.84956))*Opacity;')
    inputs=[]
    for name in ('UV','Opacity','HalfAngle'):
        pin=u.CustomInput();pin.set_editor_property('input_name',name);inputs.append(pin)
    mask.set_editor_property('inputs',inputs)
    wire(uv,mask,'UV');wire(opacity,mask,'Opacity');wire(angle,mask,'HalfAngle')
    depth=node(material,u.MaterialExpressionDepthFade,fade_distance_default=24.)
    wire(mask,depth,'Opacity');mel.connect_material_property(depth,'',u.MaterialProperty.MP_OPACITY)
    tint=node(material,u.MaterialExpressionVectorParameter,parameter_name='Tint',default_value=u.LinearColor(.35,1.25,1.8,1))
    mel.connect_material_property(tint,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(material);save(material)
    wave.set_material(0,material);save(wave)

    handbrain=load('/Game/Monsters/HandBrain/BP_HandBrain')
    voice=u.get_default_object(handbrain.generated_class()).get_editor_property('howl_sound')
    if voice is None:raise RuntimeError('HandBrain has no saved howl_sound reference')
    bp=load(DEST+'/BP_M10Mawcrawler');u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    for key,value in {'howl_clip':clip,'howl_sound':voice,'howl_wave_mesh':wave,'howl_wave_material':material,
        'howl_range':contract['range_cm'],'howl_angle':contract['angle_degrees'],
        'howl_damage_per_tick':contract['damage_per_tick'],'howl_cooldown':contract['cooldown_seconds']}.items():
        cdo.set_editor_property(key,value)
    save(bp)
    report.update(stage='assets_saved',blueprint=bp.get_path_name(),howl_clip=clip.get_path_name(),sound=voice.get_path_name(),wave=wave.get_path_name(),material=material.get_path_name(),contract=contract)
    receipt();u.log('M10_HOWL_V4_ASSETS_SAVED')
except Exception:
    report.update(stage='production_failed',error=traceback.format_exc());receipt();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
