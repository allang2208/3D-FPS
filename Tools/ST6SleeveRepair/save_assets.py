"""Save the repaired native sleeve family to isolated packages, then publish."""
import json,hashlib,gc,sys,runpy
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6SleeveRepair20261018';DEST='/Game/Characters/ModularOutfit20260924/ST6SleeveRepair20261018'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
receipt_path=R/'saved_assets.json';receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else dict(saved={},runtime_tested=False)
def record():receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing production input '+path)
    return asset
def save(asset):
    if not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside sleeve repair scope')
    asset.modify()
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
def wire(a,b,pin,out=''):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot connect material')
def make_material(name,cuff=False,lining=False):
    path=DEST+'/Materials/'+name;mat=u.load_asset(path)
    if mat and E.get_metadata_tag(mat,'ST6NativeSleeveSurface')=='v1':return mat
    mat=mat or A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(mat);mat.set_editor_property('two_sided',False);L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    uv=L.create_material_expression(mat,u.MaterialExpressionTextureCoordinate)
    inputs={'UV':uv}
    for key in ('BaseColor','Normal','ORM'):
        t=L.create_material_expression(mat,u.MaterialExpressionTextureObjectParameter);t.set_editor_property('parameter_name',key);t.set_editor_property('texture',load('/Game/Characters/ModularOutfit20260924/ST6LowerSet20261018/Textures/T_ST6_Fabric_'+key));t.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if key=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS);inputs[key]=t
    code='''float3 color=Texture2DSample(BaseColor,BaseColorSampler,UV*4).rgb;
float2 xy=Texture2DSample(Normal,NormalSampler,UV*4).rg*2-1;
float3 orm=Texture2DSample(ORM,ORMSampler,UV*4).rgb;
float seam=0,stitch=0,dy=0;
'''
    if cuff:code+='''float y=UV.y*25; float x=UV.x*25;
float d1=y-1.28,d2=y-3.52;float s1=exp(-d1*d1/.0081),s2=exp(-d2*d2/.0081);seam=s1+s2;
float edge=exp(-pow((y-1.53)/.035,2))+exp(-pow((y-3.27)/.035,2));
float aa=max(fwidth(x*3.5),.03);stitch=edge*(1-smoothstep(.28-aa,.28+aa,abs(frac(x*3.5)-.5)));
dy=.018*(-2*d1/.0081*s1-2*d2/.0081*s2);
'''
    code+=f'''color*= {'.60' if lining else '.90' if cuff else '1.0'};
color=color*(1-.10*seam)+.008*stitch;
OutNormal=normalize(float3(xy*.6+float2(0,dy),sqrt(saturate(1-dot(xy*.6,xy*.6)))));
OutRoughness=clamp(orm.g+{'.06' if lining else '.02'},.72,.9);OutAO=orm.r*(1-.08*seam);return color;'''
    custom=L.create_material_expression(mat,u.MaterialExpressionCustom);custom.set_editor_property('code',code);custom.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3);pins=[]
    for key in inputs:pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    custom.set_editor_property('inputs',pins);outputs=[]
    for key,kind in [('OutNormal',u.CustomMaterialOutputType.CMOT_FLOAT3),('OutRoughness',u.CustomMaterialOutputType.CMOT_FLOAT1),('OutAO',u.CustomMaterialOutputType.CMOT_FLOAT1)]:out=u.CustomOutput();out.set_editor_property('output_name',key);out.set_editor_property('output_type',kind);outputs.append(out)
    custom.set_editor_property('additional_outputs',outputs)
    for key,value in inputs.items():wire(value,custom,key)
    for pin,prop in [('',u.MaterialProperty.MP_BASE_COLOR),('OutNormal',u.MaterialProperty.MP_NORMAL),('OutRoughness',u.MaterialProperty.MP_ROUGHNESS),('OutAO',u.MaterialProperty.MP_AMBIENT_OCCLUSION)]:
        if not L.connect_material_property(custom,pin,prop):raise RuntimeError('Material output failure')
    spec=L.create_material_expression(mat,u.MaterialExpressionConstant);spec.set_editor_property('r',.25);L.connect_material_property(spec,'',u.MaterialProperty.MP_SPECULAR)
    errors=[str(e) for e in (L.recompile_material(mat) or [])]
    if errors:raise RuntimeError('ST6 material compile: '+'; '.join(errors))
    E.set_metadata_tag(mat,'ST6NativeSleeveSurface','v1');save(mat);return mat
def dynamic(d,ref):
    _,bones=B.get_all_bones_info(ref);ids={str(b.name):b.index for b in bones};ps=[];ns=[];uv=[];ws=[];fs=[];lookup={}
    for fi,face in enumerate(d['triangles']):
        tri=[]
        for ci,vi in enumerate(face):
            normal=d['normals'][fi][ci];tex=d['uv'][fi][ci];key=(vi,*[round(x,7) for x in normal+tex])
            if key not in lookup:lookup[key]=len(ps);ps.append(u.Vector(*d['positions'][vi]));ns.append(u.Vector(*normal));uv.append(u.Vector2D(*tex));ws.append(d['weights'][vi])
            tri.append(lookup[key])
        fs.append(u.IntVector(*tri))
    dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=ps,normals=ns,uv0=uv,triangles=fs),0,True)
    if dm.get_triangle_count()!=len(fs):raise RuntimeError('Rejected triangles '+d['profile'])
    B.copy_bones_from_mesh(ref,dm);B.mesh_create_bone_weights(dm)
    for i,bindings in enumerate(ws):
        _,ok=B.set_vertex_bone_weights(dm,i,[u.GeometryScriptBoneWeight(bone_index=ids[n],weight=w) for n,w in bindings.items()])
        if not ok:raise RuntimeError('Missing weight '+d['profile'])
    for i,slot in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,i,slot,True)
    return dm
def write_mesh(row,mats):
    profile=row['profile'];file=R/'Authored'/(profile+'.json');raw=file.read_bytes();sha=hashlib.sha256(raw).hexdigest();path=DEST+'/'+profile+'/SK_'+profile+'_ST6Sleeves'
    asset=u.load_asset(path)
    if asset and receipt['saved'].get(profile,{}).get('author_sha256')==sha and E.get_metadata_tag(asset,'ST6SleeveSHA')==sha:return
    d=json.loads(raw);source=load(d['binding_source']);ref,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Native source read failed '+profile)
    dm=dynamic(d,ref);asset=asset or A.duplicate_asset(path.rsplit('/',1)[1],path.rsplit('/',1)[0],source)
    opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,new_material_slot_names=['ST6_Ripstop','ST6_Cuff','ST6_Lining'],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,opts,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Mesh write failed '+profile)
    u.FPSModularOutfitComponent.configure_outfit_lods(asset);factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings);policy=u.load_asset(path+'_LODPolicy') or A.create_asset(path.rsplit('/',1)[1]+'_LODPolicy',path.rsplit('/',1)[0],u.SkeletalMeshLODSettings,factory);groups=[]
    for screen in (1.,.18,.075):
        group=u.SkeletalMeshLODGroupSettings();settings=group.get_editor_property('reduction_settings')
        for key,value in dict(num_of_triangles_percentage=1.,num_of_vert_percentage=1.,max_bones_per_vertex=8,lock_edges=True,enforce_bone_boundaries=True,merge_coincident_vert_bones=False,welding_threshold=0.,recalc_normals=False).items():settings.set_editor_property(key,value)
        group.set_editor_property('reduction_settings',settings);group.set_editor_property('screen_size',u.PerPlatformFloat(default=screen));groups.append(group)
    policy.set_editor_property('lod_groups',groups);save(policy);asset.set_editor_property('lod_settings',policy);models=list(asset.get_editor_property('source_models'))
    for i,model in enumerate(models):model.set_editor_property('reduction_settings',groups[min(i,2)].get_editor_property('reduction_settings'))
    asset.set_editor_property('source_models',models)
    if not S.regenerate_lod(asset,3,True,False):raise RuntimeError('LOD save failed '+profile)
    asset.set_editor_property('physics_asset',None);E.set_metadata_tag(asset,'ST6SleeveSHA',sha);E.set_metadata_tag(asset,'SourceContract',d['contract']);save(asset)
    receipt['saved'][profile]=dict(asset=asset.get_path_name(),author_sha256=sha,native=d['binding_source'],triangles=len(d['triangles']),lod_count=S.get_lod_count(asset));record();print('ST6_NATIVE_SLEEVE_SAVED',profile,flush=True)
def main():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        level=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if level and level.is_in_play_in_editor():raise RuntimeError('Do not replace clothing during PIE')
    E.make_directory(DEST+'/Materials');mats=[make_material('M_ST6_Ripstop'),make_material('M_ST6_Cuff',cuff=True),make_material('M_ST6_Lining',lining=True)];receipt['materials']=[m.get_path_name() for m in mats];record()
    rows=json.loads((R/'before.json').read_text(encoding='utf-8'))['inventory']
    rows.sort(key=lambda r:(r['profile']!='RuneSword',r['profile']))
    for row in rows:write_mesh(row,mats);gc.collect();u.SystemLibrary.collect_garbage()
    receipt['completed']=True;record();runpy.run_path(str(P/'Tools/ST6SleeveRepair/publish.py'),run_name='__main__');print('ST6_NATIVE_SLEEVES_COMPLETE',flush=True)
if __name__=='__main__':main()
