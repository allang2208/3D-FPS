"""Save fitted meshes, thermal shaders and the shared UI texture; no game run."""
import json,re
from pathlib import Path
import unreal as u
from runpy import run_path
P=Path(__file__).resolve().parents[3];O=P/'SourceAssets/ThermalScopeRuntime20261007';D='/Game/Weapons/ThermalScope20261006/Runtime'
apply_hk416_finish=run_path(str(P/'SourceAssets/WeaponSurface20260930/HK416/current_bindings.py'))['apply_current_bindings']
auth=json.loads((O/'authoring.json').read_text());A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('An existing Play session owns the assets; preserve it.')
targets={D+'/'+n for n in auth['models']}|{D+'/'+n for n in ('M_ThermalScene','M_ThermalBody','M_ThermalFire','T_ThermalScopeIcon')}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets.intersection(dirty):raise RuntimeError('Unsaved target packages exist; preserve them.')
receipt={'saved':[],'runtime_tested':False,'editor_opened':False,'new_scene_capture':False,'default_zoom':1.5,'zoom_steps':[1.5,3,8]}
def save(ob):
    if not u.EditorLoadingAndSavingUtils.save_packages([ob.get_outermost()],False):raise RuntimeError('Save failed: '+ob.get_path_name())
    receipt['saved'].append(ob.get_path_name());(O/'install-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def node(mat,kind,**values):
    ob=L.create_material_expression(mat,kind)
    for k,v in values.items():ob.set_editor_property(k,v)
    return ob
def prop(ob,key):
    if not L.connect_material_property(ob,'',key):raise RuntimeError('Cannot connect material output')
def material(name):
    mat=u.load_asset(D+'/'+name) if E.does_asset_exist(D+'/'+name) else A.create_asset(name,D,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat);return mat
def custom(mat,code,sources,kind=u.CustomMaterialOutputType.CMOT_FLOAT3):
    n=node(mat,u.MaterialExpressionCustom,code=code,output_type=kind)
    pins=[]
    for name in sources:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    n.set_editor_property('inputs',pins)
    for name,(source,out) in sources.items():
        if not L.connect_material_expressions(source,out,n,name):raise RuntimeError('Cannot connect '+name)
    return n
for name in ('M_ThermalBody','M_ThermalFire'):
    mat=material(name);mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    if name.endswith('Body'):L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    else:
        mat.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED);mat.set_editor_property('opacity_mask_clip_value',.45)
        uv=node(mat,u.MaterialExpressionTextureCoordinate);time=node(mat,u.MaterialExpressionTime)
        mask=custom(mat,'return saturate(.72+.18*sin(UV.x*43+Time*7)+.16*sin(UV.y*37-Time*9)+.12*sin((UV.x+UV.y)*71-Time*5));',{'UV':(uv,''),'Time':(time,'')},u.CustomMaterialOutputType.CMOT_FLOAT1)
        prop(mask,u.MaterialProperty.MP_OPACITY_MASK)
    prop(node(mat,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.1,.1,.1)),u.MaterialProperty.MP_EMISSIVE_COLOR)
    L.recompile_material(mat);save(mat)
mat=material('M_ThermalScene');mat.set_editor_property('material_domain',u.MaterialDomain.MD_POST_PROCESS)
mat.set_editor_property('blendable_location',u.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING);mat.set_editor_property('blendable_priority',20)
sources={}
for key,texture in [('SceneColor',u.SceneTextureId.PPI_POST_PROCESS_INPUT0),('WorldDepth',u.SceneTextureId.PPI_SCENE_DEPTH),('TargetDepth',u.SceneTextureId.PPI_CUSTOM_DEPTH),('TargetClass',u.SceneTextureId.PPI_CUSTOM_STENCIL)]:
    sources[key]=(node(mat,u.MaterialExpressionSceneTexture,scene_texture_id=texture,filtered=False),'Color')
sources['ThermalAlpha']=(node(mat,u.MaterialExpressionScalarParameter,parameter_name='ThermalAlpha',default_value=0.),'')
prop(custom(mat,(Path(__file__).parent/'thermal_scene.hlsl').read_text(),sources),u.MaterialProperty.MP_EMISSIVE_COLOR)
L.recompile_material(mat);save(mat)

original=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX');u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    for name,spec in auth['models'].items():
        options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_animations=False;options.override_full_name=True
        data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task=u.AssetImportTask();task.filename=spec['fbx'];task.destination_path=D;task.destination_name=name;task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.options=options;task.factory=u.FbxFactory();task.save=False
        A.import_asset_tasks([task]);mesh=u.load_asset(D+'/'+name)
        if not task.imported_object_paths or mesh is None:raise RuntimeError('Import failed: '+name)
        slots=list(mesh.static_materials)
        for i,slot in enumerate(slots):
            key=re.sub(r'[._]\d{3}$','',str(slot.material_slot_name))
            mat=u.load_asset('/Game/Weapons/ThermalScope20261006/Materials/M_'+key)
            if mat is None:raise RuntimeError('Missing surface '+key)
            slot.material_interface=mat;slots[i]=slot
        mesh.set_editor_property('static_materials',slots)
        if name.endswith('_HK416'):apply_hk416_finish(mesh)
        for key,pos in spec['sockets'].items():
            socket=mesh.find_socket(key)
            if socket is None:socket=u.StaticMeshSocket(outer=mesh);socket.set_editor_property('socket_name',key);mesh.add_socket(socket)
            socket.set_editor_property('relative_location',u.Vector(*pos))
            if key=='ZoomPivot':socket.set_editor_property('relative_rotation',u.MathLibrary.make_rot_from_xz(u.Vector(*spec['socket_forward']),u.Vector(*spec['socket_up'])))
        E.set_metadata_tag(mesh,'ThermalScopeStage','RuntimeIntegration20261007');E.set_metadata_tag(mesh,'Source',spec['fbx']);save(mesh)
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(original))
task=u.AssetImportTask();task.filename=str(P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/optic_thermal_scope.png');task.destination_path=D;task.destination_name='T_ThermalScopeIcon';task.automated=True;task.replace_existing=True;task.save=False
A.import_asset_tasks([task]);texture=u.load_asset(D+'/T_ThermalScopeIcon')
if texture is None:raise RuntimeError('Thermal icon import failed')
texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON);texture.set_editor_property('never_stream',True);texture.set_editor_property('srgb',True);save(texture)
receipt['complete']=True;(O/'install-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('THERMAL_RUNTIME_SAVED '+str(len(receipt['saved']))+' assets')
