"""Save the RSH suppressor and its authored finish through the authoring gate."""
import json
from pathlib import Path
import unreal as u

O=Path(__file__).resolve().parent
D='/Game/Weapons/RSH12/HeavySuppressor20261004'
E=u.EditorAssetLibrary; L=u.MaterialEditingLibrary; A=u.AssetToolsHelpers.get_asset_tools()
auth=json.loads((O/'authoring.json').read_text(encoding='utf8'))
inputs=json.loads((O/'integration_inputs.json').read_text(encoding='utf8'))
receipt=dict(saved=[],materials={},complete=False,runtime_tested=False)
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('PIE blocks RSH suppressor import')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(D) for p in dirty):raise RuntimeError('RSH suppressor packages have unsaved changes')

def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing required input '+path)
    return asset
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    if asset.get_path_name() not in receipt['saved']:receipt['saved'].append(asset.get_path_name())
    record()
def texture(relative,kind):
    filename=O/relative; name=filename.stem
    task=u.AssetImportTask();task.filename=str(filename);task.destination_path=D+'/Textures';task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
    tex=load(task.destination_path+'/'+name);tex.srgb=kind=='color'
    tex.compression_settings={'color':u.TextureCompressionSettings.TC_BC7,'rough':u.TextureCompressionSettings.TC_GRAYSCALE,
        'mask':u.TextureCompressionSettings.TC_MASKS,'normal':u.TextureCompressionSettings.TC_NORMALMAP}[kind]
    tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
    if kind=='normal':tex.set_editor_property('flip_green_channel',False)
    save(tex);return tex

parent=load('/Game/Weapons/WeaponSurface/Presets/MI_WS_CleanSatinSteel')
materials={}
for part,spec in inputs['textures'].items():
    maps={'SourceBaseColor':texture(spec['base_color'],'color'),
          'SourceRoughness':texture(spec['roughness_texture'],'rough'),
          'SurfaceNormal':texture(spec['normal_dx'],'normal'),
          'SurfaceMask':texture(spec['surface_mask'],'mask')}
    name='MI_RSH12_Heavy_'+part;path=D+'/Materials/'+name
    mat=load(path) if E.does_asset_exist(path) else A.create_asset(name,D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    mat.set_editor_property('parent',parent)
    # Author maps already carry the desired clean finish. Add one standard wet
    # layer while preserving their independent UVs, normals, roughness and AO.
    values=dict(SourceColorWeight=1.,Roughness=.5,SourceRoughnessWeight=1.,SourceRoughnessPivot=.5,
        Metallic=1.,MaskUVChannel=0.,GrainRoughness=0.,MottleRoughness=0.,MottleColor=0.,Stipple=0.,
        EdgeWear=0.,EdgeHighlight=0.,CavityDarken=0.,CavityRoughness=0.,HandlingPolish=0.,
        ScratchAmount=0.,AOStrength=1.,WeaponWetness=0.,BeadScale=60.)
    for key,value in values.items():L.set_material_instance_scalar_parameter_value(mat,key,value)
    for key,tex in maps.items():L.set_material_instance_texture_parameter_value(mat,key,tex)
    L.update_material_instance(mat);E.set_metadata_tag(mat,'RSHHeavyFinish','Authored RSH maps on shared WS clean steel; one built-in wet layer')
    save(mat);materials[part]=mat
    receipt['materials'][part]=dict(path=mat.get_path_name(),parent=parent.get_path_name(),textures={k:t.get_path_name() for k,t in maps.items()})

inner_path=D+'/Materials/M_RSH12_Heavy_Inner'
if E.does_asset_exist(inner_path):inner=load(inner_path)
else:
    inner=A.create_asset('M_RSH12_Heavy_Inner',D+'/Materials',u.Material,u.MaterialFactoryNew())
    color=L.create_material_expression(inner,u.MaterialExpressionConstant3Vector);color.constant=u.LinearColor(.005,.0055,.006,1.)
    rough=L.create_material_expression(inner,u.MaterialExpressionConstant);rough.r=.92
    metal=L.create_material_expression(inner,u.MaterialExpressionConstant);metal.r=0.
    for node,prop in ((color,u.MaterialProperty.MP_BASE_COLOR),(rough,u.MaterialProperty.MP_ROUGHNESS),(metal,u.MaterialProperty.MP_METALLIC)):
        if not L.connect_material_property(node,'',prop):raise RuntimeError('Inner material connection failed')
    for key in ('used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing'):inner.set_editor_property(key,False)
    errors=L.recompile_material(inner)
    if errors:raise RuntimeError('Inner material compilation failed '+str(errors))
save(inner);materials['Inner']=inner

flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    task=u.AssetImportTask();task.filename=auth['fbx'];task.destination_path=D;task.destination_name=auth['model']
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.factory=u.FbxFactory()
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;options.import_as_skeletal=False
    options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_animations=False
    data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.vertex_color_import_option=u.VertexColorImportOption.REPLACE;task.options=options
    A.import_asset_tasks([task]);mesh=load(D+'/'+auth['model']);slots=list(mesh.static_materials)
    for i,slot in enumerate(slots):
        part=str(slot.material_slot_name).removeprefix('RSH12Heavy_')
        slot.material_interface=materials[part];slots[i]=slot
    mesh.set_editor_property('static_materials',slots)
    for name,position in {'MountFace':(0.,0.,0.),'Muzzle':(18.,0.,0.),'AimGuide':(28.,0.,0.)}.items():
        socket=mesh.find_socket(name)
        if not socket:
            socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
        socket.set_editor_property('relative_location',u.Vector(*position))
    E.set_metadata_tag(mesh,'ExclusiveWeapon','ue_rsh12')
    E.set_metadata_tag(mesh,'GunsmithOption','rsh12_heavy_suppressor')
    E.set_metadata_tag(mesh,'MountContract','Actual RSH 3_l front annulus; fixed WPN_root; native registration; +X exit 18 cm; .01 root unit conversion')
    save(mesh)
    receipt['mesh']=mesh.get_path_name();receipt['slots']={str(s.material_slot_name):s.material_interface.get_path_name() for s in slots}
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
receipt['complete']=True;record();print('RSH_HEAVY_SUPPRESSOR_IMPORTED',mesh.get_path_name(),flush=True)
