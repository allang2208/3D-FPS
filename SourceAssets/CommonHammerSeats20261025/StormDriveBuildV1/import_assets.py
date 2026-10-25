"""Import and save both fitted Storm Drive seats, 4K PBR and the framed icon."""
import ast,json,re
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
COMMON='/Game/Weapons/CommonHammerSeats20261025/StormDriveV1';D=COMMON
RUNE='/Game/Weapons/RuneboundWarhammer20261022/StormDriveV1'
TAG='StormDriveOwner';OWNER='StormDriveBuildV1_20261025'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
receipt={'complete':False,'assets':[],'parts':{},'gpu_compilation':{},'visual_tested':False,'audio_auditioned':False}
helpers=ROOT/'SourceAssets/RuneboundWarhammer20261022/RuneAndBellRefinement20261024/install_assets.py'
tree=ast.parse(helpers.read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'<material_helpers>','exec'))
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
editor_worlds=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor_worlds and editor_worlds.get_game_world():raise RuntimeError('Preserve current PIE; import after play stops')
# The first bridge attempt imported this texture while PIE blocked metadata/save.
# Resume that exact source asset after the user has saved and closed the editor.
interrupted_name='T_StormDrive_Steel_BaseColor'
interrupted=u.load_asset(COMMON+'/'+interrupted_name)
if interrupted and not E.get_metadata_tag(interrupted,TAG):
    sources=interrupted.get_editor_property('asset_import_data').extract_filenames()
    expected=(P/'Textures'/(interrupted_name+'.png')).resolve()
    if not any(Path(source).resolve()==expected for source in sources):
        raise RuntimeError('Interrupted texture has a different source; preserve it')
    save(interrupted)
    receipt['resumed_interrupted_pie_texture']=interrupted.get_path_name()
_material=material
def material(name):
    result=_material(name);result.set_editor_property('used_with_nanite',False);return result
def imp(path,name,options=None):
    asset=existing(name)
    if not asset:
        task=u.AssetImportTask();task.filename=str(path);task.destination_name=name;task.destination_path=D;task.automated=True;task.save=False
        if options:task.options=options
        A.import_asset_tasks([task]);asset=u.load_asset(D+'/'+name)
    if not asset:raise RuntimeError('Import failed '+name)
    return asset
record();materials={}
for variant in ('Steel','Runebound'):
    textures={}
    for suffix in ('BaseColor','ORM','Normal'):
        name='T_StormDrive_'+variant+'_'+suffix;tex=imp(P/'Textures'/(name+'.png'),name)
        tex.set_editor_property('srgb',suffix=='BaseColor');tex.set_editor_property('max_texture_size',4096)
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if suffix=='Normal' else u.TextureCompressionSettings.TC_MASKS if suffix=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
        tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON);tex.set_editor_property('never_stream',False)
        if suffix=='Normal':tex.set_editor_property('flip_green_channel',True)
        textures[suffix]=save(tex)
    name='M_StormDrive_'+variant+'_Surface';m=material(name)
    color=node(m,u.MaterialExpressionTextureSample,texture=textures['BaseColor'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    orm=node(m,u.MaterialExpressionTextureSample,texture=textures['ORM'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    normal=node(m,u.MaterialExpressionTextureSample,texture=textures['Normal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    L.connect_material_property(orm,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    materials[name]=surface(m,{'basecolor':color,'roughness':(orm,'G'),'metallic':(orm,'B'),'normal':normal})

m=material('M_StormDrive_GoldInlay')
time=node(m,u.MaterialExpressionTime)
glow=node(m,u.MaterialExpressionCustom,code='float pulse=.88+.12*sin(Age*4.2); return float3(3.2,1.65,.085)*pulse;',output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
pin=u.CustomInput();pin.set_editor_property('input_name','Age');glow.set_editor_property('inputs',[pin]);wire(time,glow,'Age')
materials['M_StormDrive_GoldInlay']=surface(m,{'basecolor':vector(m,(.22,.11,.012)),'roughness':constant(m,.27),'metallic':constant(m,.35),'emissivecolor':glow})
for name,mat in materials.items():
    stats=L.get_statistics(mat)
    receipt['gpu_compilation'][name]={'vertex_instructions':stats.num_vertex_shader_instructions,'pixel_instructions':stats.num_pixel_shader_instructions};record()
    if stats.num_pixel_shader_instructions<=0:raise RuntimeError('No compiled GPU pixel shader '+name)

u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False
opt.static_mesh_import_data.generate_lightmap_u_vs=False
opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
prod=json.loads((P/'production_receipt.json').read_text('utf-8'))
for part in prod['parts']:
    D=RUNE if part['variant']=='Runebound' else COMMON
    mesh=imp(Path(part['fbx']),part['mesh'],opt);bindings={}
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        raw=str(slot.material_slot_name);key=re.sub(r'(?:[._]\d{3})+$','',raw)
        mesh.set_material(i,materials[key]);bindings[raw]=materials[key].get_path_name()
    nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=False;mesh.set_editor_property('nanite_settings',nanite);save(mesh)
    receipt['parts'][part['variant']]={'mesh':mesh.get_path_name(),'materials':bindings};record()
D=COMMON
icon='head_mount_storm_drive_seat'
tex=imp(P/(icon+'.png'),icon);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',True)
tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);save(tex)
receipt.update(complete=True,icon=tex.get_path_name());record()
print('STORM_DRIVE_ASSETS_COMPILED_AND_SAVED')
