"""Import only this sword's authored assets in the current UE editor."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
data=json.loads((P/'exports.json').read_text(encoding='utf-8'))
D=data['ue_root'];SRC=P.parent/'Meshy/candidate01/downloads'
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary;L=u.EditorAssetLibrary
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world() is not None:raise RuntimeError('PIE active; finish play before importing the sword.')
receipt_path=P/'import_receipt.json'
receipt=json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {'assets':[],'complete':False,'tested':False}
done={r['asset'] for r in receipt['assets']}
def record():receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def saved(obj,source=''):
    if not L.save_loaded_asset(obj,False):raise RuntimeError('Asset save failed: '+obj.get_path_name())
    if obj.get_path_name() not in done:
        receipt['assets'].append({'asset':obj.get_path_name(),'source':source,'saved':True});done.add(obj.get_path_name());record()
    return obj
def imported(file,name,folder,options=None):
    obj=u.load_asset(folder+'/'+name)
    if obj and obj.get_path_name() in done:return obj
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False
    if options:task.options=options
    A.import_asset_tasks([task]);obj=u.load_asset(folder+'/'+name)
    if not obj or not task.imported_object_paths:raise RuntimeError('Import failed: '+str(file))
    return obj
textures={}
for suffix,key in [('', 'BaseColor'),('_normal','Normal'),('_metallic','Metallic'),('_roughness','Roughness')]:
    tex=imported(SRC/('texture_0'+suffix+'.png'),'T_Highland_'+key,D+'/Textures')
    if tex.get_path_name() not in done:
        tex.set_editor_property('srgb',key=='BaseColor')
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if key=='Normal' else u.TextureCompressionSettings.TC_DEFAULT if key=='BaseColor' else u.TextureCompressionSettings.TC_MASKS)
        if key=='Normal':tex.set_editor_property('flip_green_channel',True)
        saved(tex,str(SRC/('texture_0'+suffix+'.png')))
    textures[key]=tex
def node(mat,cls,**props):
    n=E.create_material_expression(mat,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(a,pin,b,input_name):
    if not E.connect_material_expressions(a,pin,b,input_name):raise RuntimeError('Material connection failed: '+input_name)
def prop(a,pin,target):
    if not E.connect_material_property(a,pin,target):raise RuntimeError('Material output failed: '+str(target))
mat=u.load_asset(D+'/Materials/M_HighlandClaymoreSurface')
if not mat or mat.get_path_name() not in done:
    if not mat:mat=A.create_asset('M_HighlandClaymoreSurface',D+'/Materials',u.Material,u.MaterialFactoryNew())
    tex=node(mat,u.MaterialExpressionTextureSample,texture=textures['BaseColor'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    gold=node(mat,u.MaterialExpressionScalarParameter,parameter_name='NativeGold',default_value=0.)
    time=node(mat,u.MaterialExpressionTime)
    inputs=[]
    for name in ['Tex','Gold','Clock']:
        value=u.CustomInput();value.set_editor_property('input_name',name);inputs.append(value)
    common='float mask=saturate((min(Tex.g,Tex.b)-Tex.r-0.045)*14.0)*saturate((Tex.b-0.12)*8.0); float3 warm=float3(1.0,0.48,0.075); '
    base=node(mat,u.MaterialExpressionCustom,description='Native UV ink tint',inputs=inputs,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,code=common+'return lerp(Tex,warm*max(0.20,dot(Tex,float3(0.2126,0.7152,0.0722))),mask*Gold);')
    glow=node(mat,u.MaterialExpressionCustom,description='Native blue ink or golden breathing',inputs=inputs,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,code=common+'float pulse=0.85+0.15*sin(Clock*2.0944); return lerp(float3(0.10,0.58,1.0),warm,Gold)*mask*pulse*lerp(1.1,3.0,Gold);')
    for target in [base,glow]:wire(tex,'RGB',target,'Tex');wire(gold,'',target,'Gold');wire(time,'',target,'Clock')
    prop(base,'',u.MaterialProperty.MP_BASE_COLOR);prop(glow,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    for key,target in [('Normal',u.MaterialProperty.MP_NORMAL),('Metallic',u.MaterialProperty.MP_METALLIC),('Roughness',u.MaterialProperty.MP_ROUGHNESS)]:
        sample=node(mat,u.MaterialExpressionTextureSample,texture=textures[key],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        prop(sample,'RGB' if key=='Normal' else 'R',target)
    E.layout_material_expressions(mat);E.recompile_material(mat);saved(mat)
mount=u.load_asset(D+'/Materials/M_HighlandMountMetal')
if not mount:
    mount=A.create_asset('M_HighlandMountMetal',D+'/Materials',u.Material,u.MaterialFactoryNew())
    color=node(mount,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.18,.13,.075,1));prop(color,'',u.MaterialProperty.MP_BASE_COLOR)
    for value,target in [(.85,u.MaterialProperty.MP_METALLIC),(.36,u.MaterialProperty.MP_ROUGHNESS)]:prop(node(mount,u.MaterialExpressionConstant,r=value),'',target)
    E.recompile_material(mount);saved(mount)
u.SystemLibrary.execute_console_command(editor.get_editor_world(),'Interchange.FeatureFlags.Import.FBX 0')
names=[data['world_mesh']]+[r['mesh'] for r in data['parts']]+[r['mesh'] for r in data['adapters'].values()]
static=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
for name in names:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    cfg=opt.static_mesh_import_data;cfg.combine_meshes=True;cfg.auto_generate_collision=False;cfg.generate_lightmap_u_vs=False
    cfg.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;cfg.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    mesh=imported(P/'Export'/(name+'.fbx'),name,D+'/Meshes',opt)
    if mesh.get_path_name() in done:continue
    for i in range(len(mesh.static_materials)):mesh.set_material(i,mount if name.startswith('SM_HighlandMount_') else mat)
    settings=static.get_lod_build_settings(mesh,0);settings.recompute_normals=False;settings.recompute_tangents=False;settings.use_full_precision_u_vs=True
    static.set_lod_build_settings(mesh,0,settings);saved(mesh,str(P/'Export'/(name+'.fbx')))
receipt['complete']=True;receipt['arms_mesh']=data['arms_mesh'];receipt['animation_folder']=data['animation_folder'];record()
print('HIGHLAND_ASSETS_IMPORTED '+str(receipt_path))
