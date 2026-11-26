"""Save actual combat-shirt assets in the existing isolated background host."""
import json,hashlib,importlib.util,gc,ast,os
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR2'
DEST='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR2'
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
    for name in ['CombatRipstop','CombatCarrier','CombatStretch','CombatCuff','CombatLining','CombatThread']:
        textures={}
        for channel in ['BaseColor','NormalGL','ORM']:
            file=R/'Textures'/(name+'_'+channel+'.png');path=DEST+'/Textures/'+file.stem
            texture=u.load_asset(path)
            if not texture or E.get_metadata_tag(texture,'CombatTextureSHA')!=sha(file):
                task=u.AssetImportTask();task.filename=str(file);task.destination_path=DEST+'/Textures';task.destination_name=file.stem;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);texture=load(path)
                normal=channel=='NormalGL';colour=channel=='BaseColor'
                for key,value in dict(srgb=colour,compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_DEFAULT if colour else u.TextureCompressionSettings.TC_MASKS,flip_green_channel=normal,never_stream=False,compression_no_alpha=True,address_x=u.TextureAddress.TA_WRAP,address_y=u.TextureAddress.TA_WRAP,max_texture_size=1024).items():texture.set_editor_property(key,value)
                E.set_metadata_tag(texture,'CombatTextureSHA',sha(file));save(texture)
            textures[channel]=texture
        path=DEST+'/Materials/M_'+name;mat=u.load_asset(path)
        signature=hashlib.sha256(('combat2-physical-fields-v3:'+''.join(sha(R/'Textures'/(name+'_'+c+'.png')) for c in ['BaseColor','NormalGL','ORM'])).encode()).hexdigest()
        if mat and E.get_metadata_tag(mat,'CombatMaterialSHA')==signature:
            receipt['materials'][name]=mat.get_path_name();continue
        mat=mat or A.create_asset('M_'+name,DEST+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(mat);L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);mat.set_editor_property('two_sided',False)
        for channel,texture in textures.items():
            expression=node(mat,u.MaterialExpressionTextureSampleParameter2D,parameter_name=channel,texture=texture,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='NormalGL' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
            if channel=='BaseColor':L.connect_material_property(expression,'RGB',u.MaterialProperty.MP_BASE_COLOR)
            elif channel=='NormalGL':L.connect_material_property(expression,'RGB',u.MaterialProperty.MP_NORMAL)
            else:
                for pin,prop in [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]:L.connect_material_property(expression,pin,prop)
        L.connect_material_property(node(mat,u.MaterialExpressionConstant,r=.26),'',u.MaterialProperty.MP_SPECULAR)
        errors=L.recompile_material(mat)
        if errors:raise RuntimeError('Textile material compilation '+str(errors))
        E.set_metadata_tag(mat,'CombatMaterialSHA',signature);save(mat);receipt['materials'][name]=mat.get_path_name();record()
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,str(P/file));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
io=module('ts01_combat_io','Tools/ChainmailPants/save_assets.py');io.DEST=DEST
material();manifest=read(Path(os.environ.get('TS01_SHIRT_SAVE_PLAN',str(R/'authored.json'))));receipt['completed']=False;batch_count=0;batch_limit=int(os.environ.get('TS01_COMBAT_BATCH_SIZE','6'))
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
    batch_count+=1
    if batch_count>=batch_limit:break
receipt['completed']=all(receipt['wear'].get(row['asset'],{}).get('sha256')==sha(row['file']) for row in manifest['rows']);record();print('TS01_COMBAT_SAVE_BATCH',len(receipt['wear']),flush=True)
