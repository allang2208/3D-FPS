"""Save nun-only PBR and native-bound boot geometry into the active asset.

Use BOOT_STAGE='materials' or 'geometry' for short serialized editor batches.
No gameplay, viewport capture or acceptance testing is started here.
"""
from pathlib import Path
import json,hashlib,shutil
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChapelNun20261115/BootFinishR8';DEST='/Game/Characters/ChapelNun20261115/BootFinishR8'
BOOT='/Game/Characters/ChapelNun20261115/RefinementR4/Meshes/SK_Nun_Boots'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('PIE is running; finish gameplay before saving the boot asset')
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
recipe=read(R/'Inputs/recipe.json');receipt_path=R/'saved_assets.json'
receipt=read(receipt_path) if receipt_path.exists() else {'completed':False,'textures':{},'materials':{},'runtime_tested':False,'preview_rendered':False}
def record():receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj
def save(obj):
    if not obj.get_path_name().startswith((DEST+'/',BOOT+'.')):raise RuntimeError('Outside nun boot scope')
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Could not save '+obj.get_path_name())
    return obj
def node(mat,cls,**props):
    n=L.create_material_expression(mat,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(a,b,pin,out=''):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Shader connection '+pin)
def output(a,prop,out=''):
    if not L.connect_material_property(a,out,prop):raise RuntimeError('Shader output '+str(prop))
def constant(m,value):return node(m,u.MaterialExpressionConstant,r=value)
def color(m,value):return node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*value,1))
def custom(m,code,kind,inputs):
    n=node(m,u.MaterialExpressionCustom,code=code,output_type=kind);pins=[]
    for key in inputs:p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
    n.set_editor_property('inputs',pins)
    for key,(source,pin) in inputs.items():wire(source,n,key,pin)
    return n

FIELD='''float x=abs(P.x)-13.58361,y=P.y+.32070,z=P.z;
float v=x*.1689+y*.98563,u=x*.98563-y*.1689;
float toe=smoothstep(12.,22.,v)*(1-smoothstep(3.5,9.,z));
float heel=(1-smoothstep(-4.,0.,v))*smoothstep(1.,3.,z)*(1-smoothstep(7.,12.,z));
float dust=(1-smoothstep(.0,5.,z))*(.70+.18*sin(u*1.11+v*.51)+.12*sin(v*2.11-u*.8));
float flex=(exp(-pow((v-6.1-.047*u*u-.10*u)/.55,2.))+ .7*exp(-pow((v-8.8+.025*u*u-.10*u)/.65,2.)) + .4*exp(-pow((v-11.1-.037*u*u-.10*u)/.75,2.)))*smoothstep(2.2,4.3,z)*(1-smoothstep(11.8,15.,z))*(1-smoothstep(3.,5.8,abs(u)));
return float4(saturate(toe*.8+heel*.5),saturate(dust),saturate(heel),saturate(flex));'''

def materials():
    for family in ('NunBootLeather','NunBootRubber','NunBootWelt'):
        for channel in ('BaseColor','Normal','ORM'):
            key=family+'_'+channel
            if key in receipt['textures']:continue
            task=u.AssetImportTask();task.filename=str(R/'Textures'/(key+'.png'));task.destination_path=DEST+'/Textures';task.destination_name='T_'+key
            task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True
            A.import_asset_tasks([task]);tex=load(task.destination_path+'/'+task.destination_name)
            for k,v in dict(srgb=channel=='BaseColor',compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT,flip_green_channel=channel=='Normal',never_stream=False,address_x=u.TextureAddress.TA_WRAP,address_y=u.TextureAddress.TA_WRAP,mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE).items():tex.set_editor_property(k,v)
            tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP if channel=='Normal' else u.TextureGroup.TEXTUREGROUP_CHARACTER_SPECULAR if channel=='ORM' else u.TextureGroup.TEXTUREGROUP_CHARACTER)
            save(tex);receipt['textures'][key]=tex.get_path_name();record()
    names=['AgedIron','LeatherUpper','RubberSole','WaxedThread','LeatherReinforcement','LayeredWelt','LeatherLining']
    for index,name in enumerate(names):
        if name in receipt['materials']:continue
        path=DEST+'/Materials/M_NunBoot_'+name
        mat=u.load_asset(path) or E.duplicate_asset(recipe['materials'][index]['asset'],path)
        if not mat:raise RuntimeError('Material duplication '+name)
        # Retain the production hem mask/WPO graph and its parameter names.
        L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        rest=node(mat,u.MaterialExpressionPreSkinnedPosition);interp=node(mat,u.MaterialExpressionVertexInterpolator)
        wire(rest,interp,str(L.get_material_expression_input_names(interp)[0]))
        field=custom(mat,FIELD,u.CustomMaterialOutputType.CMOT_FLOAT4,{'P':(interp,'')})
        if index in (1,2,4,5,6):
            family='NunBootRubber' if index==2 else 'NunBootWelt' if index==5 else 'NunBootLeather'
            samples={}
            for channel in ('BaseColor','Normal','ORM'):
                samples[channel]=node(mat,u.MaterialExpressionTextureSample,texture=load(receipt['textures'][family+'_'+channel]),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            tint=.82 if index==4 else .065 if index==6 else 1.
            bc=f'float3 c=C*{tint}; c*=1.-.13*F.x-.045*F.w;return lerp(c,float3(.09,.072,.052),F.y*'+('.18);' if index in (2,5) else '.12);')
            if index==6:bc='return C*.065;'
            rough='return clamp(R-.10*F.x+.10*F.y+.025*F.w,.30,.80);'
            if index==2:rough='return clamp(R-.04*F.x+.08*F.y,.66,.90);'
            elif index==5:rough='return clamp(R-.08*F.x+.09*F.y,.43,.82);'
            elif index==6:rough='return .87;'
            base=custom(mat,bc,u.CustomMaterialOutputType.CMOT_FLOAT3,{'C':(samples['BaseColor'],'RGB'),'F':(field,'')})
            roughness=custom(mat,rough,u.CustomMaterialOutputType.CMOT_FLOAT1,{'R':(samples['ORM'],'G'),'F':(field,'')})
            output(base,u.MaterialProperty.MP_BASE_COLOR);output(roughness,u.MaterialProperty.MP_ROUGHNESS)
            normal=samples['Normal'];normal_pin='RGB'
            if index==6:
                normal=custom(mat,'return normalize(float3(N.xy*.4,N.z));',u.CustomMaterialOutputType.CMOT_FLOAT3,{'N':(normal,'RGB')});normal_pin=''
            output(normal,u.MaterialProperty.MP_NORMAL,normal_pin);output(samples['ORM'],u.MaterialProperty.MP_AMBIENT_OCCLUSION,'R')
            output(constant(mat,0),u.MaterialProperty.MP_METALLIC)
        else:
            uv=node(mat,u.MaterialExpressionTextureCoordinate)
            code='float2 q=UV*float2(260.,11.);float fade=1-smoothstep(.12,.60,max(fwidth(q.x),fwidth(q.y)));return normalize(float3(.035*sin(q.x*6.283185)*fade,.018*sin(q.y*6.283185)*fade,1));' if index==0 else 'float q=(UV.x+UV.y*.45)*190.;float fade=1-smoothstep(.1,.6,fwidth(q));return normalize(float3(.07*sin(q*6.283185)*fade,.025*cos(q*6.283185)*fade,1));'
            normal=custom(mat,code,u.CustomMaterialOutputType.CMOT_FLOAT3,{'UV':(uv,'')});output(normal,u.MaterialProperty.MP_NORMAL)
            output(color(mat,(.105,.112,.119) if index==0 else (.105,.076,.049)),u.MaterialProperty.MP_BASE_COLOR)
            rough=custom(mat,'return .43+.10*F.y-.04*F.x;' if index==0 else 'return .76+.07*F.y;',u.CustomMaterialOutputType.CMOT_FLOAT1,{'F':(field,'')})
            output(rough,u.MaterialProperty.MP_ROUGHNESS);output(constant(mat,1. if index==0 else 0),u.MaterialProperty.MP_METALLIC)
        output(constant(mat,.43 if index in (1,4,5) else .32),u.MaterialProperty.MP_SPECULAR)
        errors=L.recompile_material(mat)
        if errors:raise RuntimeError('Material compilation '+str(errors))
        save(mat);receipt['materials'][name]=mat.get_path_name();record()
    receipt['materials_completed']=True;record();print('NUN_BOOT_R8_MATERIALS_SAVED',flush=True)

def geometry():
    if not receipt.get('materials_completed'):raise RuntimeError('Finish the material batch first')
    disk=P/'Content/Characters/ChapelNun20261115/RefinementR4/Meshes/SK_Nun_Boots.uasset'
    backup=R/'Before/SK_Nun_Boots.uasset'
    if not backup.exists():
        if hashlib.sha256(disk.read_bytes()).hexdigest()!=recipe['asset_sha256']:raise RuntimeError('The active boot changed since capture; preserve the concurrent edit')
        backup.parent.mkdir(exist_ok=True);shutil.copy2(disk,backup)
    d=read(R/'Authored/boots.json');mesh=load(BOOT)
    G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
    ref,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read native reference')
    ps=[];ns=[];uvs=[];ws=[];faces=[];lookup={}
    for fi,t in enumerate(d['triangles']):
        face=[]
        for ci,vi in enumerate(t):
            n=d['normals'][fi][ci];uv=d['uv'][fi][ci];key=(vi,*[round(x,7) for x in n+uv])
            if key not in lookup:
                lookup[key]=len(ps);ps.append(u.Vector(*d['positions'][vi]));ns.append(u.Vector(*n));uvs.append(u.Vector2D(*uv));ws.append(d['weights'][vi])
            face.append(lookup[key])
        faces.append(u.IntVector(*face))
    dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=ps,normals=ns,uv0=uvs,triangles=faces),0,True)
    B.copy_bones_from_mesh(ref,dm);B.mesh_create_bone_weights(dm)
    for i,weights in enumerate(ws):B.set_vertex_bone_weights(dm,i,[u.GeometryScriptBoneWeight(bone_index=int(b),weight=float(w)) for b,w in weights])
    for i,mi in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,i,mi,True)
    names=['AgedIron','LeatherUpper','RubberSole','WaxedThread','LeatherReinforcement','LayeredWelt','LeatherLining']
    mats=[load(receipt['materials'][name]) for name in names]+[load(recipe['materials'][7]['asset'])]
    opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,new_material_slot_names=d['material_slots'],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,mesh,opts,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot save authored geometry')
    sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings)
    policy=u.load_asset(DEST+'/Meshes/DA_NunBootLOD_R8') or A.create_asset('DA_NunBootLOD_R8',DEST+'/Meshes',u.SkeletalMeshLODSettings,factory)
    groups=[]
    for ratio,screen in ((1.,1.),(.45,.18),(.18,.075)):
        group=u.SkeletalMeshLODGroupSettings();red=group.get_editor_property('reduction_settings')
        for key,value in dict(num_of_triangles_percentage=ratio,num_of_vert_percentage=ratio,base_lod=0,max_bones_per_vertex=8,lock_edges=True,enforce_bone_boundaries=True,merge_coincident_vert_bones=True,welding_threshold=0.,recalc_normals=False).items():red.set_editor_property(key,value)
        group.set_editor_property('reduction_settings',red);group.set_editor_property('screen_size',u.PerPlatformFloat(default=screen));groups.append(group)
    policy.set_editor_property('lod_groups',groups);save(policy);mesh.set_editor_property('lod_settings',policy)
    models=list(mesh.get_editor_property('source_models'))
    for i,model in enumerate(models):model.set_editor_property('reduction_settings',groups[min(i,2)].get_editor_property('reduction_settings'))
    mesh.set_editor_property('source_models',models)
    build=sub.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True);sub.set_lod_build_settings(mesh,0,build)
    if not sub.regenerate_lod(mesh,3,True,False):raise RuntimeError('Cannot generate boot distance LODs')
    save(mesh)
    receipt.update(completed=True,asset=mesh.get_path_name(),source_sha256=hashlib.sha256((R/'Authored/boots.json').read_bytes()).hexdigest(),source_triangles=len(d['triangles']),lod_count=sub.get_lod_count(mesh),lod_ratios=[1,.45,.18],hem_contract_preserved=True,stocking_material_preserved=True,normal_flip_green=True,texture_streaming=True,compiled_cpp_required=False)
    record();print('NUN_BOOT_R8_GEOMETRY_SAVED',mesh.get_path_name(),flush=True)

stage=globals().get('BOOT_STAGE','all')
if stage in ('materials','all'):materials()
if stage in ('geometry','all'):geometry()
