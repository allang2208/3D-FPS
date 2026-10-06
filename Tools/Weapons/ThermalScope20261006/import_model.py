"""Import the model-stage thermal optic assets; do not enable gameplay."""
import json,re
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parents[3];O=P/'SourceAssets/ThermalScope20261006';D='/Game/Weapons/ThermalScope20261006'
auth=json.loads((O/'authoring.json').read_text(encoding='utf-8'));A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
report={'stage':'model_only','saved':[],'models':{},'materials':{},'runtime_integrated':False,'game_tested':False};receipt=O/'import-receipt.json'
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Finish the current Play session before the model import.')
targets={D+'/Models/'+key for key in auth['models']}|{D+'/Materials/M_'+m['name'] for m in auth['materials']}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets.intersection(dirty):raise RuntimeError('Unsaved edits exist in the thermal model destination.')

def node(mat,kind,**values):
    n=L.create_material_expression(mat,kind)
    for key,value in values.items():n.set_editor_property(key,value)
    return n
def prop(n,p):
    if not L.connect_material_property(n,'',p):raise RuntimeError('Material output could not be connected')
def wire(a,b,p):
    if not L.connect_material_expressions(a,'',b,p):raise RuntimeError('Material input could not be connected: '+p)
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Unable to save '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')

materials={}
for spec in auth['materials']:
    key=spec['name'];name='M_'+key;path=D+'/Materials/'+name
    mat=u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat);mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE);mat.set_editor_property('two_sided',False)
    color=node(mat,u.MaterialExpressionVectorParameter,parameter_name='SurfaceTint',default_value=u.LinearColor(*spec['color']))
    if key=='Thermal_Display':
        mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
        # This is the physical off/standby panel. The gameplay feed is a later
        # stage, with its own square ADS presentation and target mask.
        prop(color,u.MaterialProperty.MP_EMISSIVE_COLOR)
        E.set_metadata_tag(mat,'ThermalDisplayStage','Standby model surface; thermal scene feed not connected')
    else:
        mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
        prop(color,u.MaterialProperty.MP_BASE_COLOR)
        prop(node(mat,u.MaterialExpressionScalarParameter,parameter_name='Metallic',default_value=spec['metallic']),u.MaterialProperty.MP_METALLIC)
        dry=node(mat,u.MaterialExpressionScalarParameter,parameter_name='DryRoughness',default_value=spec['roughness'])
        wet_rough=node(mat,u.MaterialExpressionConstant,r=max(.10,spec['roughness']*.65))
        wet=node(mat,u.MaterialExpressionScalarParameter,parameter_name='WeaponWetness',default_value=0.)
        blend=node(mat,u.MaterialExpressionLinearInterpolate);wire(dry,blend,'A');wire(wet_rough,blend,'B');wire(wet,blend,'Alpha');prop(blend,u.MaterialProperty.MP_ROUGHNESS)
        prop(node(mat,u.MaterialExpressionConstant,r=.5),u.MaterialProperty.MP_SPECULAR)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    E.set_metadata_tag(mat,'Source','Original ThermalScope20261006 parametric model');save(mat);materials[key]=mat;report['materials'][key]=mat.get_path_name()

old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    for name,entry in auth['models'].items():
        options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_animations=False;options.override_full_name=True
        data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_name=name;task.destination_path=D+'/Models';task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.options=options;task.factory=u.FbxFactory();task.save=False
        A.import_asset_tasks([task]);mesh=u.load_asset(D+'/Models/'+name)
        if not task.imported_object_paths or mesh is None:raise RuntimeError('No imported model: '+name)
        slots=list(mesh.static_materials)
        for i,slot in enumerate(slots):
            key=re.sub(r'[._]\d{3}$','',str(slot.material_slot_name));slot.material_interface=materials[key];slots[i]=slot
        mesh.set_editor_property('static_materials',slots)
        for key,pos in entry['sockets_ue_cm'].items():
            socket=mesh.find_socket(key)
            if socket is None:socket=u.StaticMeshSocket(outer=mesh);socket.set_editor_property('socket_name',key);mesh.add_socket(socket)
            socket.set_editor_property('relative_location',u.Vector(*pos))
        E.set_metadata_tag(mesh,'ThermalScopeStage','ModelOnly-v1')
        E.set_metadata_tag(mesh,'DefaultMagnification','1.5')
        E.set_metadata_tag(mesh,'MagnificationSteps','1.5,3,8')
        E.set_metadata_tag(mesh,'Source',str(O/'Model/ThermalScope_Editable.blend'))
        save(mesh);report['models'][name]={'asset':mesh.get_path_name(),'triangles_authored':entry['triangles'],'sockets_ue_cm':entry['sockets_ue_cm']}
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
report['status']='five_model_assets_and_eight_materials_saved';receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('THERMAL_SCOPE_MODEL_SAVED '+json.dumps({'models':len(report['models']),'materials':len(report['materials']),'receipt':str(receipt)}))
