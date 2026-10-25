"""Save the local crown repair using new mesh paths and the retained V1 body PBR."""
import ast,json,re
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
COMMON='/Game/Weapons/CommonHammerSeats20261025/StormDriveV3';D=COMMON
RUNE='/Game/Weapons/RuneboundWarhammer20261022/StormDriveV3'
OLD='/Game/Weapons/CommonHammerSeats20261025/StormDriveV1'
TAG='StormDriveOwner';OWNER='StormDriveRuneV3_20261025'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
receipt={'complete':False,'assets':[],'parts':{},'game_tested':False}
tree=ast.parse((ROOT/'SourceAssets/RuneboundWarhammer20261022/RuneAndBellRefinement20261024/install_assets.py').read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'<retained_material_helpers>','exec'))
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
worlds=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if worlds and worlds.get_game_world():raise RuntimeError('Preserve active PIE; stop play before asset save')
def imp(path,name,options=None):
    asset=existing(name)
    if not asset:
        task=u.AssetImportTask();task.filename=str(path);task.destination_name=name;task.destination_path=D;task.automated=True;task.save=False
        if options:task.options=options
        A.import_asset_tasks([task]);asset=u.load_asset(D+'/'+name)
    if not asset:raise RuntimeError('Import failed '+name)
    return asset
textures={};record()
for suffix in ('BaseColor','ORM','Normal'):
    name='T_StormDrive_RunePlate_'+suffix;tex=imp(P/'Textures'/(name+'.png'),name)
    tex.set_editor_property('srgb',suffix=='BaseColor');tex.set_editor_property('max_texture_size',2048)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if suffix=='Normal' else u.TextureCompressionSettings.TC_MASKS if suffix=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON);tex.set_editor_property('never_stream',False)
    if suffix=='Normal':tex.set_editor_property('flip_green_channel',True)
    textures[suffix]=save(tex)
name='M_StormDrive_RunePlate_V3';mat=material(name);mat.set_editor_property('used_with_nanite',False)
color=node(mat,u.MaterialExpressionTextureSample,texture=textures['BaseColor'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
orm=node(mat,u.MaterialExpressionTextureSample,texture=textures['ORM'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
normal=node(mat,u.MaterialExpressionTextureSample,texture=textures['Normal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
L.connect_material_property(orm,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
mat=surface(mat,{'basecolor':color,'roughness':(orm,'G'),'metallic':(orm,'B'),'normal':normal})
stats=L.get_statistics(mat)
if stats.num_pixel_shader_instructions<=0:raise RuntimeError('Trim material has no compiled pixel shader')
receipt['rune_shader_instructions']=stats.num_pixel_shader_instructions
materials={name:mat}
materials['M_StormDrive_ClosedSilverTrim']=u.load_asset('/Game/Weapons/CommonHammerSeats20261025/StormDriveV2/M_StormDrive_ClosedSilverTrim')
if not materials['M_StormDrive_ClosedSilverTrim']:raise RuntimeError('Missing retained V2 crown material')
for name in ('M_StormDrive_Steel_Surface','M_StormDrive_Runebound_Surface','M_StormDrive_GoldInlay'):
    materials[name]=u.load_asset(OLD+'/'+name)
    if not materials[name]:raise RuntimeError('Missing retained material '+name)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False;opt.static_mesh_import_data.generate_lightmap_u_vs=False
opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
prod=json.loads((P/'repair_receipt.json').read_text('utf-8'))
for part in prod['parts']:
    D=RUNE if part['variant']=='Runebound' else COMMON
    mesh=imp(part['fbx'],part['mesh'],opt);bindings={}
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        raw=str(slot.material_slot_name);key=re.sub(r'(?:[._]\d{3})+$','',raw)
        mesh.set_material(i,materials[key]);bindings[raw]=materials[key].get_path_name()
    nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=False;mesh.set_editor_property('nanite_settings',nanite);save(mesh)
    receipt['parts'][part['variant']]={'mesh':mesh.get_path_name(),'materials':bindings};record()
D=COMMON;name='head_mount_storm_drive_seat'
tex=imp(P/(name+'.png'),name);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',True)
tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);save(tex)
receipt.update(complete=True,icon=tex.get_path_name());record()
print('STORM_DRIVE_FINE_RUNE_V3_SAVED')
