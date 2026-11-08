"""Import and save only this task's two meshes, PBR materials and shared icon."""
import ast,json,re
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
D='/Game/Weapons/CommonHammerSeats20261107/ConicalSeatV1'
TAG='ConicalSeatOwner';OWNER='ConicalHammerSeat20261107_BuildV1'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
receipt={'complete':False,'assets':[],'parts':{},'visual_tested':False,'runtime_registered':False,'editor_ui_started':False}
helpers=ROOT/'SourceAssets/RuneboundWarhammer20261022/RuneAndBellRefinement20261024/install_assets.py'
names={'record','save','existing','node','wire','constant','vector','binary','material','surface'}
tree=ast.parse(helpers.read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'<saved substrate material helpers>','exec'))
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong authoring project')
record()

def imp(path,name,options=None):
    asset=existing(name)
    if not asset:
        task=u.AssetImportTask();task.filename=str(path);task.destination_path=D;task.destination_name=name
        task.automated=True;task.save=False
        if options:task.options=options
        A.import_asset_tasks([task]);asset=u.load_asset(D+'/'+name)
    if not asset:raise RuntimeError('Import failed '+name)
    return asset

materials={}
for variant in ('Steel','Runebound'):
    textures={}
    for suffix in ('BaseColor','ORM','Normal'):
        name='T_ConicalSeat_'+variant+'_'+suffix;tex=imp(P/'Textures'/(name+'.png'),name)
        tex.set_editor_property('srgb',suffix=='BaseColor');tex.set_editor_property('max_texture_size',4096)
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if suffix=='Normal' else u.TextureCompressionSettings.TC_MASKS if suffix=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
        tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON);tex.set_editor_property('never_stream',False)
        if suffix=='Normal':tex.set_editor_property('flip_green_channel',True)
        textures[suffix]=save(tex)
    name='M_ConicalSeat_'+variant+'_Surface';mat=material(name)
    mat.set_editor_property('used_with_nanite',False)
    color=node(mat,u.MaterialExpressionTextureSample,texture=textures['BaseColor'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    orm=node(mat,u.MaterialExpressionTextureSample,texture=textures['ORM'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    normal=node(mat,u.MaterialExpressionTextureSample,texture=textures['Normal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    L.connect_material_property(orm,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    materials[name]=surface(mat,{'basecolor':color,'roughness':(orm,'G'),'metallic':(orm,'B'),'normal':normal})

u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False
opt.static_mesh_import_data.generate_lightmap_u_vs=False
opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
prod=json.loads((P/'production_receipt.json').read_text('utf-8'))
for part in prod['parts']:
    mesh=imp(Path(part['fbx']),part['mesh'],opt);bindings={}
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        raw=str(slot.material_slot_name);key=re.sub(r'(?:[._]\d{3})+$','',raw)
        mesh.set_material(i,materials[key]);bindings[raw]=materials[key].get_path_name()
    nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=False;mesh.set_editor_property('nanite_settings',nanite)
    save(mesh)
    receipt['parts'][part['variant']]={'mesh':mesh.get_path_name(),'materials':bindings,'location_cm':[0,0,0],'forward_axis':'+Z'};record()

name='head_mount_conical_seat';icon=imp(P.parent/'IconV2'/(name+'.png'),name)
icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);icon.set_editor_property('srgb',True)
icon.set_editor_property('never_stream',True);icon.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
save(icon)
receipt.update(complete=True,icon=icon.get_path_name(),normal_import='tangent normal map, flipped green for DirectX',texture_resolution=4096)
record();print('CONICAL_SEAT_UE_ASSETS_SAVED')
