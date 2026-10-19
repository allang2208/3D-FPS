"""Save scoped ST6 lower gear and tailored capris in separate native packages."""
import importlib.util,json,hashlib
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6LowerSet20261018'
DEST='/Game/Characters/ModularOutfit20260924/ST6LowerSet20261018'
spec=importlib.util.spec_from_file_location('st6_lower_mesh_io',str(P/'Tools/ChainmailPants/save_assets.py'));io=importlib.util.module_from_spec(spec);spec.loader.exec_module(io);io.DEST=DEST
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;G=u.GeometryScript_AssetUtils;T=u.GeometryScript_MeshTransforms
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
receipt_path=R/'saved_assets.json';receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {'saved':[],'meshes':{},'runtime_tested':False}
level=u.get_editor_subsystem(u.LevelEditorSubsystem) if '-run=' not in u.SystemLibrary.get_command_line().lower() else None
in_play=bool(level and level.is_in_play_in_editor())
def record():receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(asset):
    io.save(asset)
    if asset.get_path_name() not in receipt['saved']:receipt['saved'].append(asset.get_path_name())
    record()
def load(path):return io.load(path)
def texture(file):
    name=file.stem;folder=DEST+'/Textures';path=folder+'/'+name;sha=hashlib.sha256(file.read_bytes()).hexdigest();asset=u.load_asset(path)
    if asset and E.get_metadata_tag(asset,'ST6SourceSHA')==sha:return asset
    if asset and in_play:raise RuntimeError('Preserve loaded ST6 texture during PIE: '+path)
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);asset=load(path)
    normal=name.endswith('_Normal');color=name.endswith('_BaseColor')
    asset.set_editor_property('srgb',color);asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_DEFAULT if color else u.TextureCompressionSettings.TC_MASKS)
    asset.set_editor_property('flip_green_channel',normal);asset.set_editor_property('never_stream',False);asset.set_editor_property('max_texture_size',1024);asset.set_editor_property('compression_no_alpha',True)
    asset.set_editor_property('address_x',u.TextureAddress.TA_WRAP);asset.set_editor_property('address_y',u.TextureAddress.TA_WRAP);E.set_metadata_tag(asset,'ST6SourceSHA',sha);save(asset);return asset
def material(name,channels=None,colour=None,rough=.7,metal=0):
    folder=DEST+'/Materials';path=folder+'/'+name;mat=u.load_asset(path)
    if mat and E.get_metadata_tag(mat,'ST6Surface')=='v1':return mat
    if mat and in_play:raise RuntimeError('Preserve loaded ST6 material during PIE: '+path)
    mat=mat or A.create_asset(name,folder,u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(mat);L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    if channels:
        uv=L.create_material_expression(mat,u.MaterialExpressionTextureCoordinate);uv.set_editor_property('u_tiling',4);uv.set_editor_property('v_tiling',4)
        for channel,tex in channels.items():
            node=L.create_material_expression(mat,u.MaterialExpressionTextureSampleParameter2D);node.set_editor_property('parameter_name',channel);node.set_editor_property('texture',tex)
            node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS);io.wire(uv,node,'UVs')
            if channel=='BaseColor':io.output(node,u.MaterialProperty.MP_BASE_COLOR,'RGB')
            elif channel=='Normal':io.output(node,u.MaterialProperty.MP_NORMAL,'RGB')
            else:
                for pin,prop in [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]:io.output(node,prop,pin)
    else:
        c=L.create_material_expression(mat,u.MaterialExpressionConstant3Vector);c.set_editor_property('constant',u.LinearColor(*colour,1));io.output(c,u.MaterialProperty.MP_BASE_COLOR)
        for value,prop in [(rough,u.MaterialProperty.MP_ROUGHNESS),(metal,u.MaterialProperty.MP_METALLIC)]:
            c=L.create_material_expression(mat,u.MaterialExpressionConstant);c.set_editor_property('r',value);io.output(c,prop)
    errors=[str(e) for e in (L.recompile_material(mat) or [])]
    if errors:raise RuntimeError(name+': '+'; '.join(errors))
    E.set_metadata_tag(mat,'ST6Surface','v1');save(mat);return mat
def mats():
    E.make_directory(DEST+'/Materials');E.make_directory(DEST+'/Textures');surfaces={}
    for name in ('Fabric','Rubber','Khaki','Stretch'):
        channels={channel:texture(R/'Textures'/f'T_ST6_{name}_{channel}.png') for channel in ('BaseColor','Normal','ORM')}
        surfaces[name]=material('M_ST6_'+name,channels)
    return [material('M_ST6_Gunmetal',colour=(.045,.052,.055),rough=.5,metal=1),surfaces['Fabric'],surfaces['Rubber'],material('M_ST6_Thread',colour=(.12,.10,.067),rough=.82),surfaces['Khaki'],surfaces['Stretch'],load('/Game/AsianMale_Jason/Material/MI_Body_Baked')]
native_cache={}
def native(data):
    if data['source'] not in native_cache:
        source=load(data['source']);dm,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read native bind')
        native_cache[data['source']]=(source,dm)
    return native_cache[data['source']]
def skeletal(file,name,materials,slots):
    raw=file.read_bytes();sha=hashlib.sha256(raw).hexdigest();data=json.loads(raw);path=DEST+'/'+name;asset=u.load_asset(path)
    if asset and E.get_metadata_tag(asset,'ST6SourceSHA')==sha:
        receipt['meshes'][name]=asset.get_path_name();record();return asset
    if asset and in_play:raise RuntimeError('Preserve loaded clothing during PIE: '+path)
    source,ref=native(data);dm=io.dynamic(data,ref);asset=asset or A.duplicate_asset(name,DEST,source)
    opt=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=materials,new_material_slot_names=slots,enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,opt,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write '+name)
    build=S.get_lod_build_settings(asset,0);build.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(asset,0,build)
    u.FPSModularOutfitComponent.configure_outfit_lods(asset)
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings)
    policy=u.load_asset(DEST+'/'+name+'_LODPolicy') or A.create_asset(name+'_LODPolicy',DEST,u.SkeletalMeshLODSettings,factory)
    groups=[]
    for ratio,screen in [(1.,1.),(.65,.18),(.4,.075)]:
        group=u.SkeletalMeshLODGroupSettings();settings=group.get_editor_property('reduction_settings')
        for key,value in dict(num_of_triangles_percentage=ratio,max_bones_per_vertex=8,lock_edges=True,enforce_bone_boundaries=True,merge_coincident_vert_bones=False,welding_threshold=0.,recalc_normals=False).items():settings.set_editor_property(key,value)
        group.set_editor_property('reduction_settings',settings);group.set_editor_property('screen_size',u.PerPlatformFloat(default=screen));groups.append(group)
    policy.set_editor_property('lod_groups',groups);asset.set_editor_property('lod_settings',policy)
    models=list(asset.get_editor_property('source_models'))
    for i,model in enumerate(models):model.set_editor_property('reduction_settings',groups[min(i,2)].get_editor_property('reduction_settings'))
    asset.set_editor_property('source_models',models);save(policy)
    if not S.regenerate_lod(asset,3,True,False):raise RuntimeError('LOD build failed '+name)
    asset.set_editor_property('physics_asset',None);E.set_metadata_tag(asset,'ST6SourceSHA',sha);E.set_metadata_tag(asset,'SourceContract',data['contract']);save(asset)
    receipt['meshes'][name]=asset.get_path_name();receipt.setdefault('source_sha256',{})[str(file)]=sha;record();print('ST6_LOWER_SKELETAL_SAVED',name,flush=True);return asset
def displays(file,label,materials,boots=False):
    data=json.loads(file.read_text());_,ref=native(data)
    for kind in ('Icon','Pickup'):
        dm=io.dynamic(data,ref)
        if kind=='Icon':
            if boots:
                remove=[]
                for ti in range(dm.get_triangle_count()):
                    valid,a,b,c=u.GeometryScript_MeshQueries.get_triangle_positions(dm,ti)
                    if valid and a.x+b.x+c.x<0:remove.append(ti)
                u.GeometryScript_MeshEdits.delete_triangles_from_mesh(dm,u.GeometryScript_List.convert_array_to_index_list(remove),False)
                T.rotate_mesh(dm,u.Rotator(pitch=0,yaw=150,roll=0));T.rotate_mesh(dm,u.Rotator(pitch=30,yaw=0,roll=0))
            else:T.rotate_mesh(dm,u.Rotator(pitch=0,yaw=180,roll=0))
        else:
            center=[(min(p[i] for p in data['positions'])+max(p[i] for p in data['positions']))*.5 for i in range(3)];T.translate_mesh(dm,u.Vector(*[-v for v in center]))
            if not boots:T.rotate_mesh(dm,u.Rotator(pitch=0,yaw=0,roll=-90))
        path=DEST+('/Icons/' if kind=='Icon' else '/Pickups/')+'SM_'+label+('_Display' if kind=='Icon' else '')
        receipt['meshes'][label+'_'+kind.lower()]=io.static(dm,path,materials);record()
def icons():
    for key in ('ue_st6_tactical_pants','ue_st6_tactical_boots','ue_smoke_grey_capri'):
        file=R/(key+'.png');folder='/Game/ColdSteelData/Icons/ST6LowerSet20261018';t=u.AssetImportTask();t.filename=str(file);t.destination_path=folder;t.destination_name=key;t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);asset=load(folder+'/'+key)
        asset.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON);asset.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);asset.set_editor_property('srgb',True)
        asset.modify()
        if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save icon '+key)
        receipt.setdefault('icons',{})[key]=asset.get_path_name();record()

def save_capri():
    capri=P/'SourceAssets/SmokeGreyCapri20261004';previous=json.loads((capri/'saved_assets.json').read_text());cm=[load(p) for p in previous['materials']]
    for suffix in ('','_HighBootsFit'):skeletal(capri/('Jason_SmokeGreyCapri'+suffix+'.json'),'SK_Jason_CapriTailored'+suffix,cm,['Gunmetal','Cotton','Unused','Thread','Facing','NativeSkin'])
    displays(capri/'Jason_SmokeGreyCapri_Garment.json','CapriTailored',cm)
    previous.update(pants=receipt['meshes']['SK_Jason_CapriTailored'],pants_high=receipt['meshes']['SK_Jason_CapriTailored_HighBootsFit'],pants_icon=receipt['meshes']['CapriTailored_icon'],pants_pickup=receipt['meshes']['CapriTailored_pickup'])
    (capri/'saved_assets.json').write_text(json.dumps(previous,indent=2),encoding='utf-8')

def main():
    E.make_directory(DEST);materials=mats();receipt['materials']=[m.get_path_name() for m in materials];record()
    slots=['Gunmetal','GrayRipstop','BlackHardShell','Thread','KhakiLeather','BlackStretch','NativeSkin']
    for name in ('Jason_ST6Trousers','Jason_ST6Trousers_ShortBootsFit','Jason_ST6Trousers_HighBootsFit','Jason_ST6Trousers_ST6BootsFit','Jason_ST6Boots'):
        skeletal(R/(name+'.json'),'SK_'+name,materials,slots)
    displays(R/'Jason_ST6Trousers_Garment.json','ST6Trousers',materials)
    displays(R/'Jason_ST6Boots_Garment.json','ST6Boots',materials,True)
    save_capri()
    icons();receipt['completed']=True;record();print('ST6_LOWER_SET_ASSETS_COMPLETE',flush=True)
if __name__=='__main__':main()
