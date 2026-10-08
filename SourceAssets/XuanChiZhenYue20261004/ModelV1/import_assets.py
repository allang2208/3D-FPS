"""Create/save this weapon's meshes, Substrate surfaces and cosmetic skin material."""
import json,time
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong host project')
DATA=json.loads((P/'exports.json').read_text());D=DATA['ue_root']
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary;L=u.EditorAssetLibrary
receipt={'assets':[],'complete':False,'game_tested':False}
def save(obj):
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):raise RuntimeError('Save failed '+obj.get_path_name())
    receipt['assets'].append(obj.get_path_name());(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2));return obj
def imported(file,name,folder,options=None):
    obj=u.load_asset(folder+'/'+name)
    if obj:return obj
    task=u.AssetImportTask();task.filename=str(file);task.destination_name=name;task.destination_path=folder;task.automated=True;task.replace_existing=False;task.save=False
    if options:task.options=options
    A.import_asset_tasks([task]);obj=u.load_asset(folder+'/'+name)
    if not obj:raise RuntimeError('Import failed '+str(file))
    return obj
def node(m,cls,**props):
    n=E.create_material_expression(m,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def link(a,pin,b,target):
    if not E.connect_material_expressions(a,pin,b,target):raise RuntimeError('Material link failed '+target)
def out(a,pin,prop):
    if not E.connect_material_property(a,pin,prop):raise RuntimeError('Material output failed '+str(prop))
def custom(m,code,inputs):
    n=node(m,u.MaterialExpressionCustom,code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
    fields=[]
    for name,_,_ in inputs:
        item=u.CustomInput();item.set_editor_property('input_name',name);fields.append(item)
    n.set_editor_property('inputs',fields)
    for name,source,pin in inputs:link(source,pin,n,name)
    return n
def transform(m,source,src,dst):
    n=node(m,u.MaterialExpressionTransform,transform_source_type=src,transform_type=dst);link(source,'',n,'');return n

def correct_fbx_weight_axis(m):
    # UE's FBX importer maps V to 1-V. UV1 stores weights, not texture sampling.
    changed=False
    for n in E.get_material_expressions(m):
        if isinstance(n,u.MaterialExpressionCustom):
            code=n.get_editor_property('code');fixed=code.replace('w=saturate(Skin.y)','w=saturate(1.0-Skin.y)')
            if fixed!=code:n.set_editor_property('code',fixed);changed=True
    if changed:E.recompile_material(m)
textures={}
for family in ['Hilt','Blade']:
    textures[family]={}
    for i,key in enumerate(['BaseColor','ORM','Normal']):
        file=P/'Textures'/('Image_'+str(i)+'.jpg' if family=='Hilt' else 'Blade_'+key+'.png')
        t=imported(file,'T_XuanChi_'+family+'_'+key,D+'/Textures');t.srgb=key=='BaseColor';t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if key=='Normal' else u.TextureCompressionSettings.TC_MASKS if key=='ORM' else u.TextureCompressionSettings.TC_BC7
        t.never_stream=False
        if key=='Normal':t.flip_green_channel=True
        textures[family][key]=save(t)
materials={}
for family in ['Hilt','Blade','Tassel','Mount']:
    name='M_XuanChi_'+family;m=u.load_asset(D+'/Materials/'+name)
    if m:
        if family=='Tassel':correct_fbx_weight_axis(m)
        materials[family]=save(m);continue
    m=A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew());m.set_editor_property('used_with_skeletal_mesh',False);m.set_editor_property('used_with_nanite',family in ['Hilt','Mount']);m.set_editor_property('two_sided',False)
    slab=node(m,u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    if family=='Mount':
        base=node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.25,.16,.065,1));rough=node(m,u.MaterialExpressionConstant,r=.38);metal=node(m,u.MaterialExpressionConstant,r=.95)
        feeds=[(base,'',u.MaterialProperty.MP_BASE_COLOR,'BaseColor'),(rough,'',u.MaterialProperty.MP_ROUGHNESS,'Roughness'),(metal,'',u.MaterialProperty.MP_METALLIC,'Metallic')]
    else:
        tx=textures['Blade' if family=='Blade' else 'Hilt']
        base=node(m,u.MaterialExpressionTextureSample,texture=tx['BaseColor'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        orm=node(m,u.MaterialExpressionTextureSample,texture=tx['ORM'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        normal=node(m,u.MaterialExpressionTextureSample,texture=tx['Normal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        normal_pin='RGB'
        if family=='Tassel':
            m.set_editor_property('tangent_space_normal',False)
            skin=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=1)
            active=node(m,u.MaterialExpressionScalarParameter,parameter_name='TasselActive',default_value=0.)
            bindings=[('Skin',skin,''),('Active',active,'')]
            for i,rest in enumerate(DATA['tassel_guides_cm'][:7]):
                r=node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*rest,0))
                p=node(m,u.MaterialExpressionVectorParameter,parameter_name='TasselP'+str(i),default_value=u.LinearColor(*rest,0))
                q=node(m,u.MaterialExpressionVectorParameter,parameter_name='TasselQ'+str(i),default_value=u.LinearColor(0,0,0,1))
                qa=node(m,u.MaterialExpressionAppendVector);link(q,'RGB',qa,'A');link(q,'A',qa,'B')
                bindings.extend([('R'+str(i),r,''),('P'+str(i),p,'RGB'),('Q'+str(i),qa,'')])
            wp=node(m,u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
            lp=node(m,u.MaterialExpressionTransformPosition,transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL);link(wp,'',lp,'')
            pre='float3 R[7]={R0,R1,R2,R3,R4,R5,R6}; float3 P[7]={P0,P1,P2,P3,P4,P5,P6}; float4 Q[7]={Q0,Q1,Q2,Q3,Q4,Q5,Q6}; int a=clamp((int)floor(Skin.x+0.01),0,6); int b=min(a+1,6); float w=saturate(1.0-Skin.y); '
            code='if(V.z>=0)return float3(0,0,0); '+pre+'float3 va=V-R[a],vb=V-R[b]; float3 pa=va+2*cross(Q[a].xyz,cross(Q[a].xyz,va)+Q[a].w*va)+P[a]; float3 pb=vb+2*cross(Q[b].xyz,cross(Q[b].xyz,vb)+Q[b].w*vb)+P[b]; return (lerp(pa,pb,w)-V)*Active;'
            deform=custom(m,code,bindings+[('V',lp,'')]);world_delta=transform(m,deform,u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,u.MaterialVectorCoordTransform.TRANSFORM_WORLD);out(world_delta,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
            local_n=transform(m,normal,u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,u.MaterialVectorCoordTransform.TRANSFORM_LOCAL)
            code_n='if(Pos.z>=0)return normalize(V); '+pre+'float3 na=V+2*cross(Q[a].xyz,cross(Q[a].xyz,V)+Q[a].w*V); float3 nb=V+2*cross(Q[b].xyz,cross(Q[b].xyz,V)+Q[b].w*V); return normalize(lerp(V,lerp(na,nb,w),Active));'
            turned=custom(m,code_n,bindings+[('V',local_n,''),('Pos',lp,'')]);normal=transform(m,turned,u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,u.MaterialVectorCoordTransform.TRANSFORM_WORLD);normal_pin=''
        feeds=[(base,'RGB',u.MaterialProperty.MP_BASE_COLOR,'BaseColor'),(normal,normal_pin,u.MaterialProperty.MP_NORMAL,'Normal'),(orm,'G',u.MaterialProperty.MP_ROUGHNESS,'Roughness'),(orm,'B',u.MaterialProperty.MP_METALLIC,'Metallic')]
        out(orm,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    for n,pin,prop,target in feeds:link(n,pin,slab,target);out(n,pin,prop)
    out(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL);E.layout_material_expressions(m)
    errors=E.recompile_material(m)
    if errors:raise RuntimeError('Material compile failed '+name+' '+str(errors))
    materials[family]=save(m)
while (P/'author_in_progress').exists():time.sleep(2)
names=[DATA['world_mesh']]+[r['mesh'] for r in DATA['parts']]+[r['mesh'] for r in DATA['adapters'].values()]
for name in names:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    cfg=opt.static_mesh_import_data;cfg.combine_meshes=True;cfg.auto_generate_collision=False;cfg.generate_lightmap_u_vs=False;cfg.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;cfg.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
    nanite_ok=name not in ['SM_XuanChi_Blade','SM_XuanChi_Tassel'];cfg.build_nanite=nanite_ok
    mesh=imported(P/'Export'/(name+'.fbx'),name,D+'/Meshes',opt)
    for i,slot in enumerate(mesh.static_materials):
        family='Blade' if 'Blade' in str(slot.material_slot_name) else 'Mount' if 'Mount' in str(slot.material_slot_name) else 'Hilt'
        if name=='SM_XuanChi_Tassel':family='Tassel'
        mesh.set_material(i,materials[family])
    ns=mesh.get_editor_property('nanite_settings');ns.enabled=nanite_ok;ns.explicit_tangents=True;ns.fallback_relative_error=0.;mesh.set_editor_property('nanite_settings',ns);save(mesh)
# Existing whirlwind presentation consumes the same source material mapping.
mapping_file=ROOT/'Content/ColdSteelData/whirlwind-temporal-materials.json';add={}
for family,source in materials.items():
    path=source.get_path_name().split('.')[0]+'_Whirlwind';m=u.load_asset(path)
    if not m:
        m=L.duplicate_asset(source.get_path_name(),path);temp=node(m,u.MaterialExpressionTemporalResponsivenessOutput);one=node(m,u.MaterialExpressionConstant,r=1.);link(one,'',temp,'');errors=E.recompile_material(m)
        if errors:raise RuntimeError(str(errors))
    elif family=='Tassel':correct_fbx_weight_axis(m)
    save(m);add[source.get_path_name()]=m.get_path_name()
mapping=json.loads(mapping_file.read_text(encoding='utf-8-sig'));mapping.update(add);mapping_file.write_text(json.dumps(mapping,indent=2)+'\n')
receipt.update(complete=True,materials={k:v.get_path_name() for k,v in materials.items()});(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2));print('XUANCHI_ASSETS_SAVED '+str(len(receipt['assets'])))
