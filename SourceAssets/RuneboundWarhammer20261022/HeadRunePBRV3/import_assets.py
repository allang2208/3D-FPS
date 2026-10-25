"""Save six rune-bearing head revisions, PBR maps and yellow lightning material."""
import ast,json,re
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
D='/Game/Weapons/RuneboundWarhammer20261022/HeadRunePBRV3'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
TAG='RuneboundHeadSurfaceOwner';OWNER='HeadRunePBRV3_20261024'
receipt={'complete':False,'assets':[],'heads':[],'tested':False,'rendered':False}
# Existing project Substrate authoring functions; no old installation body.
source=P.parent/'RuneAndBellRefinement20261024/install_assets.py'
tree=ast.parse(source.read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'<project_material_authoring>','exec'))
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Use the main project authoring host')
catalog=json.loads((ROOT/'Content/ColdSteelData/runebound-warhammer-modules.json').read_text('utf-8-sig'))

def texture(file,normal=False,color=False,size=4096):
    file=Path(file);name=file.stem;tex=existing(name)
    if not tex:
        task=u.AssetImportTask();task.filename=str(file);task.destination_path=D;task.destination_name=name
        task.automated=True;task.save=False;A.import_asset_tasks([task]);tex=u.load_asset(D+'/'+name)
    if not tex:raise RuntimeError('Texture import failed '+str(file))
    tex.set_editor_property('srgb',color)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_DEFAULT if color else u.TextureCompressionSettings.TC_MASKS)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON);tex.set_editor_property('max_texture_size',size)
    tex.set_editor_property('never_stream',False)
    if normal:tex.set_editor_property('flip_green_channel',True)
    return save(tex)
def sample(m,tex,index=0,normal=False,color=False):
    out=node(m,u.MaterialExpressionTextureSample,texture=tex,
        sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_COLOR if color else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    if index:wire(node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=index),out,'UVs')
    return out
def rune_emission(m,mask,gold=False):
    tint,glow=energy_parameters(m,3.,5.,.12)
    tint.set_editor_property('default_value',u.LinearColor(1.,.64,.06,1.) if gold else u.LinearColor(.015,.27,1.,1.))
    return binary(m,u.MaterialExpressionMultiply,mask,glow)
def pbr(name,folder,prefix,mask=None,gold=False,size=4096):
    maps={k:texture(folder/(prefix+k+'.png'),normal=k=='Normal',color=k=='BaseColor',size=size) for k in ('BaseColor','ORM','Normal')}
    m=material(name);c=sample(m,maps['BaseColor'],color=True);orm=sample(m,maps['ORM']);n=sample(m,maps['Normal'],normal=True)
    inputs={'basecolor':c,'roughness':(orm,'G'),'metallic':(orm,'B'),'normal':n}
    L.connect_material_property(orm,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    if mask:inputs['emissivecolor']=rune_emission(m,sample(m,mask),gold)
    return surface(m,inputs)
def with_native_rune(parent,name,mask,index):
    m=existing(name) or A.duplicate_asset(name,D,parent)
    if not m:raise RuntimeError('Cannot create native head surface '+name)
    # All old nodes/textures stay, including connector UV0 and metallic maps.
    properties={'basecolor':u.MaterialProperty.MP_BASE_COLOR,'roughness':u.MaterialProperty.MP_ROUGHNESS,
        'metallic':u.MaterialProperty.MP_METALLIC,'normal':u.MaterialProperty.MP_NORMAL,'specular':u.MaterialProperty.MP_SPECULAR,
        'emissivecolor':u.MaterialProperty.MP_EMISSIVE_COLOR}
    inputs={}
    for k,prop in properties.items():
        n=L.get_material_property_input_node(m,prop)
        if n:inputs[k]=(n,L.get_material_property_input_node_output_name(m,prop))
    ink=sample(m,mask,index)
    color=inputs.get('basecolor',(vector(m,(.14,.16,.18)),''))
    lerp=node(m,u.MaterialExpressionLinearInterpolate);wire(color[0],lerp,'A',color[1]);wire(vector(m,(.025,.07,.105)),lerp,'B');wire(ink,lerp,'Alpha','R')
    inputs['basecolor']=lerp;emission=rune_emission(m,ink)
    if 'emissivecolor' in inputs:
        add=node(m,u.MaterialExpressionAdd);old,out=inputs['emissivecolor'];wire(old,add,'A',out);wire(emission,add,'B');emission=add
    inputs['emissivecolor']=emission
    m.set_editor_property('used_with_skeletal_mesh',False);m.set_editor_property('used_with_nanite',True)
    return surface(m,inputs)
def import_mesh(option,name,file,materials,previous):
    mesh=existing(name)
    if not mesh:
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
        data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task=u.AssetImportTask();task.filename=str(file);task.destination_path=D;task.destination_name=name
        task.automated=True;task.save=False;task.options=opt;A.import_asset_tasks([task]);mesh=u.load_asset(D+'/'+name)
    if not mesh:raise RuntimeError('Mesh import failed '+name)
    bindings={}
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        raw=str(slot.material_slot_name);key=re.sub(r'(?:[._]\d{3})+$','',raw)
        if key not in materials:raise RuntimeError('Unmapped head material '+raw)
        mesh.set_material(i,materials[key]);bindings[raw]=materials[key].get_path_name()
    old=u.load_asset(previous)
    if old:mesh.set_editor_property('nanite_settings',old.get_editor_property('nanite_settings'))
    save(mesh);receipt['heads'].append({'id':option,'mesh':mesh.get_path_name(),'materials':bindings})
    record()

u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for kind,prefix,option,oldfolder in [('star_oath','StarOath','star_oath_sealing_anvil','StarOathV1'),('final_toll','FinalToll','final_toll_soul_bell','FinalTollV2')]:
    folder=P/kind/'Textures';prod=json.loads((P/kind/'production_receipt.json').read_text('utf-8'))
    mask=texture(folder/('T_'+prefix+'_NativeRune.png'),size=2048)
    bindings={'M_'+prefix+'_PBR_Surface':pbr('M_RuneboundHeadSurface_'+prefix,folder,'T_'+prefix+'_',mask,kind=='final_toll'),
              'M_'+prefix+'_FineInlay_Brass':pbr('M_'+prefix+'_FineInlay_PBRV3',folder,'T_'+prefix+'_Inlay_',size=1024)}
    for key in ('M_'+prefix+'_Rune_Energy',)+(('M_StarOath_Optical_Crystal',) if kind=='star_oath' else ()):
        bindings[key]=u.load_asset('/Game/Weapons/RuneboundWarhammer20261022/'+oldfolder+'/'+key)
    import_mesh(option,prod['model'],prod['fbx'],bindings,catalog['slots']['hammer_heads'][option]['mesh'])

for row in json.loads((P/'common/production_receipt.json').read_text('utf-8'))['parts']:
    option=row['id'];mask=texture(row['rune_texture'],size=2048)
    previous=catalog['slots']['hammer_heads'][option];mesh=u.load_asset(previous['mesh'])
    bindings={}
    for slot in mesh.get_editor_property('static_materials'):
        key=re.sub(r'(?:[._]\d{3})+$','',str(slot.material_slot_name))
        path=previous.get('materials',{}).get(str(slot.material_slot_name)) or previous.get('materials',{}).get(key)
        base=u.load_asset(path) if path else slot.material_interface
        bindings[key]=with_native_rune(base,'M_RuneboundHeadSurface_'+option+'_'+key,mask,row['rune_uv_channel'])
    import_mesh(option,row['mesh'],row['fbx'],bindings,previous['mesh'])

m=material('M_FinalToll_YellowLightning')
m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
strength=node(m,u.MaterialExpressionScalarParameter,parameter_name='Strength',default_value=.65)
glow=binary(m,u.MaterialExpressionMultiply,vector(m,(8.,5.8,.08)),strength)
L.connect_material_property(glow,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
L.recompile_material(m);save(m)
receipt['complete']=True;receipt['factory_head']='Original rune-bearing head retained unchanged'
record();print('HEAD_RUNE_PBR_V3_SAVED '+str(len(receipt['assets']))+' packages')
