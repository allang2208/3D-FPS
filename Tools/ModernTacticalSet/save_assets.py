"""Save isolated TS01 materials, native wearable meshes, drops and UI assets."""
import json,hashlib,importlib.util,gc,os
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');SROOT=P/'SourceAssets/ModernTacticalSet20261113';R=SROOT/'Integration';DEST='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils;L=u.MaterialEditingLibrary
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,str(P/file));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
io=module('ts01_skeletal_io','Tools/ChainmailPants/save_assets.py');io.DEST=DEST
static_io=module('ts01_static_io','Tools/FieldHat/save_icon.py')
receipt=read(R/'saved_assets.json') if (R/'saved_assets.json').exists() else dict(completed=False,materials={},wear={},displays={},icons={})
def record():(R/'saved_assets.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(asset):
    if not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside TS01 asset scope')
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing '+path)
    return a
def texture(file,ui=False):
    folder=DEST+('/Icons' if ui else '/Textures');path=folder+'/'+file.stem;fingerprint=sha(file);asset=u.load_asset(path)
    if asset and E.get_metadata_tag(asset,'TS01SourceSHA')==fingerprint:return asset
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=file.stem;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);asset=load(path)
    normal=file.stem.endswith('_NormalGL');color=file.stem.endswith('_BaseColor') or ui
    props=dict(srgb=color,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON if ui else u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_DEFAULT if color else u.TextureCompressionSettings.TC_MASKS)
    if ui:props.update(lod_group=u.TextureGroup.TEXTUREGROUP_UI,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    else:props.update(flip_green_channel=normal,never_stream=False,compression_no_alpha=True,address_x=u.TextureAddress.TA_WRAP,address_y=u.TextureAddress.TA_WRAP,max_texture_size=1024)
    for k,v in props.items():asset.set_editor_property(k,v)
    E.set_metadata_tag(asset,'TS01SourceSHA',fingerprint);save(asset);return asset
def surface(name):
    path=DEST+'/Materials/M_'+name;mat=u.load_asset(path);files={c:SROOT/'Textures'/(name+'_'+c+'.png') for c in ['BaseColor','NormalGL','ORM']};fingerprint=hashlib.sha256(('ts01-pbr-v1'+''.join(sha(f) for f in files.values())).encode()).hexdigest()
    if mat and E.get_metadata_tag(mat,'TS01SurfaceSHA')==fingerprint:return mat
    tex={c:texture(f) for c,f in files.items()};mat=mat or A.create_asset('M_'+name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    for expr in list(L.get_material_expressions(mat)):L.delete_material_expression(mat,expr)
    L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    for c,t in tex.items():
        node=L.create_material_expression(mat,u.MaterialExpressionTextureSampleParameter2D);node.set_editor_property('parameter_name',c);node.set_editor_property('texture',t);node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR if c=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if c=='NormalGL' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        if c=='BaseColor':L.connect_material_property(node,'RGB',u.MaterialProperty.MP_BASE_COLOR)
        elif c=='NormalGL':L.connect_material_property(node,'RGB',u.MaterialProperty.MP_NORMAL)
        else:
            for pin,prop in [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]:L.connect_material_property(node,pin,prop)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Material compilation '+name+': '+str(errors))
    E.set_metadata_tag(mat,'TS01SurfaceSHA',fingerprint);save(mat);return mat
materials={}
def get_mats(slots):
    out=[]
    for name in slots:
        if name not in materials:
            if name.startswith('NATIVE:'):mat=load(name[7:])
            else:mat=surface(name.removeprefix('TS01_'));receipt['materials'][name]=mat.get_path_name();record()
            materials[name]=mat
        out.append(materials[name])
    return out
manifest=read(R/'derived.json');prepared=read(R/'prepared.json');receipt['completed']=False
if not manifest['completed']:raise RuntimeError('Derivatives unfinished')
for master in prepared['rows']:
    get_mats(master['material_slots'])
def skeletal(row):
    key=row['kind']+'/'+row['rig'];fingerprint=sha(row['file']);old=receipt['wear'].get(key,{})
    if old.get('sha256')==fingerprint:return
    d=read(row['file']);mats=get_mats(d['material_slots']);source=load(d['source']);native,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Native skeleton read '+key)
    dm=io.dynamic(d,native);name='SK_TS01_'+row['rig']+'_'+row['kind'];folder=DEST+'/Wear/'+row['rig'];asset=u.load_asset(folder+'/'+name) or A.duplicate_asset(name,folder,source)
    opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,new_material_slot_names=[str(i)+'_'+s.replace(':','_').split('/')[-1] for i,s in enumerate(d['material_slots'])],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    # Set the template's production options before replacing its geometry. Each
    # property notification can rebuild a skeletal mesh; doing this afterwards
    # repeatedly rebuilds the large authored garment for the same final result.
    asset.set_editor_property('physics_asset',None)
    build=S.get_lod_build_settings(asset,0);build.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(asset,0,build)
    u.FPSModularOutfitComponent.configure_outfit_lods(asset)
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings);policy=u.load_asset(folder+'/'+name+'_LODPolicy') or A.create_asset(name+'_LODPolicy',folder,u.SkeletalMeshLODSettings,factory);groups=[]
    for ratio,screen in [(1.,1.),(.50,.18),(.25,.065)]:
        group=u.SkeletalMeshLODGroupSettings();reduction=group.get_editor_property('reduction_settings')
        for k,v in dict(num_of_triangles_percentage=ratio,max_bones_per_vertex=8,lock_edges=False,enforce_bone_boundaries=False,merge_coincident_vert_bones=False,welding_threshold=0.,recalc_normals=False).items():reduction.set_editor_property(k,v)
        group.set_editor_property('reduction_settings',reduction);group.set_editor_property('screen_size',u.PerPlatformFloat(default=screen));groups.append(group)
    policy.set_editor_property('lod_groups',groups);asset.set_editor_property('lod_settings',policy)
    models=list(asset.get_editor_property('source_models'))
    for i,model in enumerate(models):model.set_editor_property('reduction_settings',groups[min(i,2)].get_editor_property('reduction_settings'))
    asset.set_editor_property('source_models',models);save(policy)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,opts,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Write mesh '+key)
    if not S.regenerate_lod(asset,3,True,False):raise RuntimeError('LOD production failed '+key)
    E.set_metadata_tag(asset,'TS01SourceSHA',fingerprint);E.set_metadata_tag(asset,'TS01Master','ModernTacticalSet20261113');save(asset)
    receipt['wear'][key]=dict(asset=asset.get_path_name(),sha256=fingerprint,lod_count=3);record();print('TS01_WEAR_SAVED',key,flush=True)
    del d,dm,native,source,asset;gc.collect();u.SystemLibrary.collect_garbage()
def static(d,path):
    dm=static_io.dynamic(d);mats=get_mats(d['material_slots']);result=io.static(dm,path,mats);del dm;gc.collect();return result
batch_limit=int(os.environ.get('TS01_SAVE_BATCH_SIZE','999'));count=0
for row in manifest['records']:
    if row['kind']=='helmet':continue
    key=row['kind']+'/'+row['rig']
    if receipt['wear'].get(key,{}).get('sha256')==sha(row['file']):continue
    skeletal(row);count+=1
    if count>=batch_limit:
        print('TS01_SAVE_BATCH_COMPLETE',count,flush=True);raise SystemExit(0)
for row in manifest['records']:
    if row['kind']!='helmet':continue
    key='helmet/'+row['rig'];fingerprint=sha(row['file'])
    if receipt['wear'].get(key,{}).get('sha256')==fingerprint:continue
    d=read(row['file']);asset=static(d,DEST+'/Wear/'+row['rig']+'/SM_TS01_Helmet_'+row['rig']);receipt['wear'][key]=dict(asset=asset,sha256=fingerprint,lod_count=3);record();del d;u.SystemLibrary.collect_garbage()
for row in prepared['rows']:
    if not row['key']:continue
    kind=row['kind'];key=row['key'];fingerprint=sha(row['file']);d=read(row['file'])
    if receipt['displays'].get(kind,{}).get('sha256')!=fingerprint:
        # Empty garment/drop meshes keep skin patches out of inventory and world drops.
        for axis in range(3):
            offset=(min(p[axis] for p in d['positions'])+max(p[axis] for p in d['positions']))*.5
            for p in d['positions']:p[axis]-=offset
        revision='_R3' if kind=='boots' else ''
        pickup=static(d,DEST+'/Pickups/SM_TS01_'+kind+revision)
        display=read(row['icon']['display']);icon_mesh=static(display,DEST+'/Icons/SM_TS01_'+kind+'_Display'+revision)
        receipt['displays'][kind]=dict(pickup=pickup,icon_mesh=icon_mesh,sha256=fingerprint);record()
    tex=texture(Path(row['icon']['png']),True);receipt['icons'][kind]=dict(asset=tex.get_path_name(),sha256=sha(row['icon']['png']));record();del d;gc.collect();u.SystemLibrary.collect_garbage()
receipt['completed']=True;record();print('TS01_ALL_ASSETS_SAVED',flush=True)
