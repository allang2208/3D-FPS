"""Save actual combat-shirt assets in the existing isolated background host."""
import json,hashlib,importlib.util,gc,ast,os
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR1'
DEST='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR1'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;G=u.GeometryScript_AssetUtils
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
receipt=read(R/'saved.json') if (R/'saved.json').exists() else dict(wear={},materials={})
def record():(R/'saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def load(p):
    a=u.load_asset(p)
    if not a:raise RuntimeError('Missing '+p)
    return a
def save(a):
    if not a.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside owned outfit revision')
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def node(mat,cls,**props):
    n=L.create_material_expression(mat,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(a,b,pin,output=''):
    if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Material connection '+pin)
def material():
    folder=DEST+'/Materials';name='M_CombatFabric';mat=u.load_asset(folder+'/'+name) or A.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    code=(R/'fabric.ush').read_text();signature=sha(R/'fabric.ush')
    if E.get_metadata_tag(mat,'CombatFabricSHA')!=signature:
        L.delete_all_material_expressions(mat);mat.set_editor_property('two_sided',False);L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        def interp(cls):n=node(mat,u.MaterialExpressionVertexInterpolator);wire(node(mat,cls),n,'');return n
        tex='/Game/Weapons/Super90/Cransh20261006/Textures/T_S90_sleeve_st6_generalist_'
        inputs=dict(RestPosition=interp(u.MaterialExpressionPreSkinnedPosition),RestNormal=interp(u.MaterialExpressionPreSkinnedNormal),WorldPosition=node(mat,u.MaterialExpressionWorldPosition),SurfaceNormal=node(mat,u.MaterialExpressionVertexNormalWS),Fabric=node(mat,u.MaterialExpressionTextureObjectParameter,parameter_name='OriginalFabric',texture=load(tex+'Base_color'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR),FabricNormal=node(mat,u.MaterialExpressionTextureObjectParameter,parameter_name='OriginalFabricNormal',texture=load(tex+'Normal_OpenGL'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL),Origin=node(mat,u.MaterialExpressionVectorParameter,parameter_name='Origin',default_value=u.LinearColor(0,0,0,1)))
        for key,value in dict(ShoulderHeight=52,TorsoMode=0,CollarTop=151.2,NormalStrength=.38).items():inputs[key]=node(mat,u.MaterialExpressionScalarParameter,parameter_name=key,default_value=value)
        custom=node(mat,u.MaterialExpressionCustom,code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,description='TS01 earth-brown ripstop and dark stretch knit, native rest-space')
        pins=[]
        for key in inputs:pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
        custom.set_editor_property('inputs',pins);outputs=[]
        for key,typ in [('OutNormal',u.CustomMaterialOutputType.CMOT_FLOAT3),('OutRoughness',u.CustomMaterialOutputType.CMOT_FLOAT1),('OutAO',u.CustomMaterialOutputType.CMOT_FLOAT1)]:
            out=u.CustomOutput();out.set_editor_property('output_name',key);out.set_editor_property('output_type',typ);outputs.append(out)
        custom.set_editor_property('additional_outputs',outputs)
        for key,value in inputs.items():wire(value,custom,key)
        for pin,prop in [('',u.MaterialProperty.MP_BASE_COLOR),('OutRoughness',u.MaterialProperty.MP_ROUGHNESS),('OutAO',u.MaterialProperty.MP_AMBIENT_OCCLUSION)]:L.connect_material_property(custom,pin,prop)
        transform=node(mat,u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
        wire(custom,transform,'','OutNormal');L.connect_material_property(transform,'',u.MaterialProperty.MP_NORMAL);L.connect_material_property(node(mat,u.MaterialExpressionConstant,r=.26),'',u.MaterialProperty.MP_SPECULAR)
        errors=L.recompile_material(mat)
        if errors:raise RuntimeError('Combat fabric compilation '+str(errors))
        E.set_metadata_tag(mat,'CombatFabricSHA',signature);save(mat)
    receipt['materials']['fabric']=mat.get_path_name()
    for rig in ['Jason','Kaitlin','Body']:
        if rig=='Body':
            d=read(P/'SourceAssets/ST6Reset20261017/Read/Body.json');bones=d['bones']
        else:
            d=read(R/'Inputs'/f'Body_{rig}.json');bones={b['name']:b for b in d['bones']}
        origin=bones['pelvis']['position'];height=(bones['clavicle_l']['position'][2]+bones['clavicle_r']['position'][2])*.5-origin[2]
        name='MI_CombatTorso_'+rig;mi=u.load_asset(folder+'/'+name) or A.create_asset(name,folder,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());L.set_material_instance_parent(mi,mat)
        L.set_material_instance_vector_parameter_value(mi,'Origin',u.LinearColor(*origin,1))
        for key,value in dict(ShoulderHeight=height,TorsoMode=1,CollarTop={'Jason':151.2,'Kaitlin':143.9,'Body':160.5}[rig]).items():L.set_material_instance_scalar_parameter_value(mi,key,value)
        L.update_material_instance(mi);save(mi);receipt['materials'][rig]=mi.get_path_name()
    record()
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,str(P/file));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
io=module('ts01_combat_io','Tools/ChainmailPants/save_assets.py');io.DEST=DEST
material();manifest=read(Path(os.environ.get('TS01_SHIRT_SAVE_PLAN',str(R/'authored.json'))));receipt['completed']=False
for row in manifest['rows']:
    key=row['asset'];fingerprint=sha(row['file'])
    if receipt['wear'].get(key,{}).get('sha256')==fingerprint:continue
    d=read(row['file']);source=load(d['source']);native,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Native mesh '+key)
    dm=io.dynamic(d,native);folder,name=key.rsplit('/',1);asset=u.load_asset(key) or A.duplicate_asset(name,folder,source);asset.set_editor_property('physics_asset',None)
    build=S.get_lod_build_settings(asset,0);build.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(asset,0,build)
    u.FPSModularOutfitComponent.configure_outfit_lods(asset)
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings);policy=u.load_asset(key+'_LODPolicy') or A.create_asset(name+'_LODPolicy',folder,u.SkeletalMeshLODSettings,factory);groups=[]
    for ratio,screen in [(1.,1.),(1.,.18),(1.,.065)]:
        group=u.SkeletalMeshLODGroupSettings();reduction=group.get_editor_property('reduction_settings')
        for k,v in dict(num_of_triangles_percentage=ratio,num_of_vert_percentage=ratio,max_bones_per_vertex=8,lock_edges=True,enforce_bone_boundaries=True,merge_coincident_vert_bones=False,welding_threshold=0.,recalc_normals=False).items():reduction.set_editor_property(k,v)
        group.set_editor_property('reduction_settings',reduction);group.set_editor_property('screen_size',u.PerPlatformFloat(default=screen));groups.append(group)
    policy.set_editor_property('lod_groups',groups);asset.set_editor_property('lod_settings',policy)
    models=list(asset.get_editor_property('source_models'))
    for i,model in enumerate(models):model.set_editor_property('reduction_settings',groups[min(i,2)].get_editor_property('reduction_settings'))
    asset.set_editor_property('source_models',models);save(policy)
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[load(m) for m in d['materials']],new_material_slot_names=d['material_slots'],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Mesh write '+key)
    if not S.regenerate_lod(asset,3,True,False):raise RuntimeError('LOD production '+key)
    E.set_metadata_tag(asset,'CombatSourceSHA',fingerprint);save(asset);receipt['wear'][key]=dict(asset=asset.get_path_name(),sha256=fingerprint,source=row.get('source'),rig=row['rig'],lod_count=3);record();print('TS01_COMBAT_SAVED',len(receipt['wear']),key,flush=True)
    del d,dm,native,source,asset;gc.collect();u.SystemLibrary.collect_garbage()
receipt['completed']=len(receipt['wear'])==62;record();print('TS01_COMBAT_SAVE_BATCH',len(receipt['wear']),flush=True)
