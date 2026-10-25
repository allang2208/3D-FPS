"""Save four ST6 wardrobe meshes per batch, preserving their native base geometry."""
import json,hashlib,importlib.util,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6LowerDetail20261024';DEST='/Game/Characters/ModularOutfit20260924/ST6LowerDetail20261024'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
io=module('st6_lower_detail_io','Tools/ChainmailPants/save_assets.py');io.DEST=DEST
hem=module('st6_lower_detail_hem','Tools/BlueMageRobe/hem_materials.py');hem.DEST=DEST+'/UnderRobe/Materials'
receipt_path=R/'saved_assets.json';receipt=read(receipt_path) if receipt_path.exists() else dict(completed=False,meshes={},pickups={},icons={},runtime_tested=False)
manifest=read(R/'manifest.json');families=['Gunmetal','Fabric','Rubber','Thread','Khaki','Stretch']
def record():receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing ST6 production input '+path)
    return asset
def save(asset):
    if not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside ST6 detail scope')
    asset.modify()
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
def materials():
    if receipt.get('materials'):return [load(p) for p in receipt['materials']]
    textures={};rows=read(R/'textures.json')['maps'];E.make_directory(DEST+'/Textures');E.make_directory(DEST+'/Materials')
    for row in rows:
        for channel in ('BaseColor','Normal','ORM'):
            name='T_ST6_'+row['name']+'_'+channel;t=u.AssetImportTask();t.filename=str(R/'Textures'/(name+'.png'));t.destination_path=DEST+'/Textures';t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);tex=load(DEST+'/Textures/'+name)
            for key,value in dict(srgb=channel=='BaseColor',compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT,flip_green_channel=channel=='Normal',never_stream=False,max_texture_size=row['resolution'],compression_no_alpha=True,address_x=u.TextureAddress.TA_WRAP,address_y=u.TextureAddress.TA_WRAP).items():tex.set_editor_property(key,value)
            save(tex);textures[row['name']+'_'+channel]=tex
    mats=[]
    for family in families:
        name='M_ST6_'+family;mat=u.load_asset(DEST+'/Materials/'+name) or A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(mat)
        cloth=family in ('Fabric','Stretch','Thread');mat.set_editor_property('use_material_attributes',True);mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_CLOTH if cloth else u.MaterialShadingModel.MSM_DEFAULT_LIT);L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        def node(cls):return L.create_material_expression(mat,cls)
        def wire(a,b,pin,out=''):
            if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('ST6 material pin '+pin)
        def scalar(v):
            n=node(u.MaterialExpressionConstant);n.set_editor_property('r',v);return n
        attrs=node(u.MaterialExpressionMakeMaterialAttributes);uv=node(u.MaterialExpressionTextureCoordinate);uv.set_editor_property('u_tiling',4);uv.set_editor_property('v_tiling',4);samples={}
        for channel in ('BaseColor','Normal','ORM'):
            n=node(u.MaterialExpressionTextureSampleParameter2D);n.set_editor_property('parameter_name',channel);n.set_editor_property('texture',textures[family+'_'+channel]);n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR);wire(uv,n,'UVs');samples[channel]=n
        wire(samples['BaseColor'],attrs,'BaseColor','RGB')
        mult=node(u.MaterialExpressionMultiply);wire(samples['Normal'],mult,'A','RGB');scale=node(u.MaterialExpressionConstant3Vector);scale.set_editor_property('constant',u.LinearColor(.8,.8,1,1));wire(scale,mult,'B');normal=node(u.MaterialExpressionNormalize);wire(mult,normal,'VectorInput');wire(normal,attrs,'Normal')
        for channel,pin in [('R','AmbientOcclusion'),('G','Roughness'),('B','Metallic')]:wire(samples['ORM'],attrs,pin,channel)
        if cloth:
            fuzz=node(u.MaterialExpressionMultiply);wire(samples['BaseColor'],fuzz,'A','RGB');wire(scalar(.25),fuzz,'B');wire(fuzz,attrs,'SubsurfaceColor');wire(scalar(.15),attrs,'ClearCoat')
        wire(scalar(.3 if cloth else .4),attrs,'Specular')
        if not L.connect_material_property(attrs,'',u.MaterialProperty.MP_MATERIAL_ATTRIBUTES):raise RuntimeError('ST6 material output')
        errors=L.recompile_material(mat)
        if errors:raise RuntimeError('ST6 shader compile '+str(errors))
        save(mat);mats.append(mat)
    receipt['materials']=[m.get_path_name() for m in mats];receipt['textures']={k:v.get_path_name() for k,v in textures.items()};record();return mats

def detail_mesh(d,base):
    _,bones=B.get_all_bones_info(base);names={str(b.name):b.index for b in bones};remap={b['index']:names[b['name']] for b in d['bones']}
    positions=[];normals=[];uv=[];weights=[];faces=[];lookup={}
    for fi,face in enumerate(d['triangles']):
        row=[]
        for ci,vi in enumerate(face):
            n=d['normals'][fi][ci];t=d['uv'][fi][ci];key=(vi,*[round(x,7) for x in n+t])
            if key not in lookup:
                lookup[key]=len(positions);positions.append(u.Vector(*d['positions'][vi]));normals.append(u.Vector(*n));uv.append(u.Vector2D(*t));weights.append([[remap[bi],w] for bi,w in d['weights'][vi]])
            row.append(lookup[key])
        faces.append(u.IntVector(*row))
    dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=positions,normals=normals,uv0=uv,triangles=faces),0,True)
    B.copy_bones_from_mesh(base,dm);B.mesh_create_bone_weights(dm)
    for vi,ws in enumerate(weights):B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=bi,weight=w) for bi,w in ws])
    for ti,slot in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,ti,slot,True)
    return dm,weights

def lods(asset):
    path=asset.get_path_name().split('.')[0];folder,name=path.rsplit('/',1);factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings)
    policy=u.load_asset(path+'_LODPolicy') or A.create_asset(name+'_LODPolicy',folder,u.SkeletalMeshLODSettings,factory);groups=[]
    for ratio,screen in [(1.,1.),(.5,.18),(.22,.075)]:
        group=u.SkeletalMeshLODGroupSettings();s=group.get_editor_property('reduction_settings')
        for key,value in dict(num_of_triangles_percentage=ratio,num_of_vert_percentage=ratio,max_bones_per_vertex=8,lock_edges=False,enforce_bone_boundaries=True,merge_coincident_vert_bones=False,welding_threshold=0.,recalc_normals=False).items():s.set_editor_property(key,value)
        group.set_editor_property('reduction_settings',s);group.set_editor_property('screen_size',u.PerPlatformFloat(default=screen));groups.append(group)
    policy.set_editor_property('lod_groups',groups);save(policy);asset.set_editor_property('lod_settings',policy)
    models=list(asset.get_editor_property('source_models'))
    for index,model in enumerate(models):model.set_editor_property('reduction_settings',groups[min(index,2)].get_editor_property('reduction_settings'))
    asset.set_editor_property('source_models',models)
    if not S.regenerate_lod(asset,3,True,False):raise RuntimeError('ST6 LOD build failed '+path)

hem_cache={}
def retained_hem_surface(old,family):
    original=old.get_path_name()
    if original in hem_cache:return hem_cache[original]
    suffix=hashlib.sha256(original.encode()).hexdigest()[:10];path=DEST+'/UnderRobe/Materials/M_ST6_'+family+'_RetainedHem_'+suffix
    mat=u.load_asset(path)
    if mat and E.get_metadata_tag(mat,'ST6RetainedHem')=='20261024':hem_cache[original]=mat;return mat
    E.make_directory(path.rsplit('/',1)[0]);mat=mat or E.duplicate_asset(original,path)
    if not isinstance(mat,u.Material) or mat.get_editor_property('use_material_attributes'):
        raise RuntimeError('ST6 retained hem requires its existing direct-output master: '+original)
    # Keep the existing WPO and opacity graphs exactly as authored. Replace
    # only the physical surface outputs; no new hem pins or envelopes.
    uv=L.create_material_expression(mat,u.MaterialExpressionTextureCoordinate);uv.set_editor_property('u_tiling',4);uv.set_editor_property('v_tiling',4)
    for channel in ('BaseColor','Normal','ORM'):
        tex=load(receipt['textures'][family+'_'+channel]);n=L.create_material_expression(mat,u.MaterialExpressionTextureSampleParameter2D);n.set_editor_property('parameter_name','Detail_'+channel);n.set_editor_property('texture',tex)
        n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR);io.wire(uv,n,'UVs')
        if channel=='BaseColor':io.output(n,u.MaterialProperty.MP_BASE_COLOR,'RGB')
        elif channel=='Normal':io.output(n,u.MaterialProperty.MP_NORMAL,'RGB')
        else:
            for pin,prop in [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]:io.output(n,prop,pin)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('ST6 retained hem shader '+str(errors))
    E.set_metadata_tag(mat,'ST6RetainedHem','20261024');save(mat);hem_cache[original]=mat;return mat

def wearable(row,mats):
    detail_raw=(R/'Authored'/row['detail']).read_bytes() if row['detail'] else b''
    sha=hashlib.sha256(detail_raw+json.dumps(receipt['materials']).encode()).hexdigest()
    previous=receipt['meshes'].get(row['source'])
    if previous and previous['detail_sha256']==sha and E.does_asset_exist(row['target']):return False
    source=load(row['source']);path=row['target'].split('.')[0];E.make_directory(path.rsplit('/',1)[0]);asset=u.load_asset(path) or E.duplicate_asset(row['source'],path)
    slots=list(source.get_editor_property('materials'));original_materials=[s.material_interface for s in slots]
    # Preserve the per-section ordinary/hem-masked distinction, including boot
    # meshes that carry both ordinary lower sections and masked upper sections.
    replacements={'/Game/Characters/ModularOutfit20260924/ST6LowerSet20261018/Materials/M_ST6_'+family+'.M_ST6_'+family:mats[i] for i,family in enumerate(families)}
    def surface(old):
        if not old:return old
        current=old;wrapped=False;seen=set()
        while current.get_path_name() not in seen:
            path=current.get_path_name();seen.add(path)
            if path in replacements:
                family=path.rsplit('.',1)[-1].removeprefix('M_ST6_')
                return retained_hem_surface(old,family) if wrapped else replacements[path]
            original=E.get_metadata_tag(current,'RobeHemOriginalMaterial')
            if not original:break
            current=load(original);wrapped=True
        return old
    new_materials=[surface(m) for m in original_materials]
    if row['detail']:
        dm,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read ST6 source '+row['source'])
        u.GeometryScript_MeshRepair.compact_mesh(dm);start=dm.get_vertex_count();extra,weights=detail_mesh(json.loads(detail_raw),dm)
        u.GeometryScript_MeshEdits.append_mesh(dm,extra,u.Transform())
        for vi,ws in enumerate(weights):B.set_vertex_bone_weights(dm,start+vi,[u.GeometryScriptBoneWeight(bone_index=bi,weight=w) for bi,w in ws])
        options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=new_materials,new_material_slot_names=[str(s.material_slot_name) for s in slots],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
        _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot save ST6 detail '+path)
        build=S.get_lod_build_settings(asset,0);build.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(asset,0,build);lods(asset)
        del dm,extra,weights
    else:
        for index,slot in enumerate(slots):slot.set_editor_property('material_interface',new_materials[index])
        asset.set_editor_property('materials',slots)
    E.set_metadata_tag(asset,'ST6DetailSourceSHA',sha);save(asset)
    receipt['meshes'][row['source']]=dict(asset=asset.get_path_name(),detail_sha256=sha,base_geometry_preserved=True,rig=row['rig'],kind=row['kind']);record();print('ST6_LOWER_DETAIL_SAVED',asset.get_path_name(),flush=True)
    return True

def presentations(mats):
    for kind in ('pants','boots'):
        key='ue_st6_tactical_'+kind
        if key not in receipt['pickups']:
            d=read(R/'Authored'/(kind+'_garment.json'));source=load(d['source']);ref,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD());dm=io.dynamic(d,ref)
            center=[(min(p[i] for p in d['positions'])+max(p[i] for p in d['positions']))*.5 for i in range(3)];u.GeometryScript_MeshTransforms.translate_mesh(dm,u.Vector(*[-v for v in center]))
            if kind=='pants':u.GeometryScript_MeshTransforms.rotate_mesh(dm,u.Rotator(pitch=0,yaw=0,roll=-90))
            receipt['pickups'][key]=io.static(dm,DEST+'/Pickups/SM_ST6_'+kind,mats);record();del dm,d,ref
        if key not in receipt['icons']:
            t=u.AssetImportTask();t.filename=str(R/(key+'.png'));t.destination_path=DEST+'/Icons';t.destination_name='T_'+key;t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);tex=load(DEST+'/Icons/T_'+key)
            for name,value in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,srgb=True).items():tex.set_editor_property(name,value)
            save(tex);receipt['icons'][key]=tex.get_path_name();record()
        gc.collect();u.SystemLibrary.collect_garbage()

if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('Preserve active PIE; defer ST6 save')
receipt['completed']=False;record();mats=materials();count=0
for row in manifest['meshes']:
    if wearable(row,mats):count+=1
    gc.collect();u.SystemLibrary.collect_garbage()
    if count>=4:break
receipt['remaining']=sum(row['source'] not in receipt['meshes'] for row in manifest['meshes']);record()
if receipt['remaining']==0:
    presentations(mats);receipt['completed']=True;record()
print('ST6_LOWER_DETAIL_BATCH',count,'remaining',receipt['remaining'],'complete',receipt['completed'],flush=True)
