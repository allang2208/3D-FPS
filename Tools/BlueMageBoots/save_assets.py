"""Save scoped approved V1 mage boots in separate native packages."""
import importlib.util,json,hashlib,gc,sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).parent))
from common import P,R,DEST,KEY,FAMILY,SLOTS,VARIANTS,read,write,module

spec=importlib.util.spec_from_file_location('st6_lower_mesh_io',str(P/'Tools/ChainmailPants/save_assets.py'));io=importlib.util.module_from_spec(spec);spec.loader.exec_module(io);io.DEST=DEST
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;G=u.GeometryScript_AssetUtils;T=u.GeometryScript_MeshTransforms
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
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
    if asset and E.get_metadata_tag(asset,'MageBootsSourceSHA')==sha:return asset
    if asset and in_play:raise RuntimeError('Preserve loaded mage-boot texture during PIE: '+path)
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);asset=load(path)
    normal=name.endswith('_Normal');color=name.endswith('_BaseColor')
    asset.set_editor_property('srgb',color);asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_DEFAULT if color else u.TextureCompressionSettings.TC_MASKS)
    asset.set_editor_property('flip_green_channel',normal);asset.set_editor_property('never_stream',False);asset.set_editor_property('max_texture_size',2048);asset.set_editor_property('compression_no_alpha',True)
    asset.set_editor_property('address_x',u.TextureAddress.TA_WRAP);asset.set_editor_property('address_y',u.TextureAddress.TA_WRAP);E.set_metadata_tag(asset,'MageBootsSourceSHA',sha);save(asset);return asset
def material(name,channels=None,colour=None,rough=.7,metal=0):
    folder=DEST+'/Materials';path=folder+'/'+name;mat=u.load_asset(path)
    if mat and E.get_metadata_tag(mat,'MageBootsSurface')=='mage-boot-v1':return mat
    if mat and in_play:raise RuntimeError('Preserve loaded mage-boot material during PIE: '+path)
    mat=mat or A.create_asset(name,folder,u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(mat);L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    if channels:
        uv=L.create_material_expression(mat,u.MaterialExpressionTextureCoordinate);uv.set_editor_property('u_tiling',6.25);uv.set_editor_property('v_tiling',6.25)
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
    E.set_metadata_tag(mat,'MageBootsSurface','mage-boot-v1');save(mat);return mat
def mats():
    E.make_directory(DEST+'/Materials');E.make_directory(DEST+'/Textures');surfaces={}
    for name in ('Leather','Cobalt','Lining','Rubber'):
        channels={channel:texture(R/'Textures'/f'T_MageBoots_{name}_{channel}.png') for channel in ('BaseColor','Normal','ORM')}
        texture(R/'Textures'/f'T_MageBoots_{name}_Height.png')
        surfaces[name]=material('M_MageBoots_'+name,channels)
    return [surfaces['Leather'],surfaces['Cobalt'],material('M_MageBoots_SilverEmbroidery',colour=(.46,.49,.55),rough=.38,metal=.85),material('M_MageBoots_DarkThread',colour=(.018,.02,.024),rough=.84),surfaces['Lining'],surfaces['Rubber'],material('M_MageBoots_Sapphire',colour=(.009,.05,.28),rough=.14,metal=.25)]
native_cache={}
def native(data):
    if data['source'] not in native_cache:
        source=load(data['source']);dm,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read native bind')
        native_cache[data['source']]=(source,dm)
    return native_cache[data['source']]
def skeletal(file,name,materials,slots):
    raw=file.read_bytes();sha=hashlib.sha256(raw).hexdigest();data=json.loads(raw);path=DEST+'/'+name;asset=u.load_asset(path)
    if asset and E.get_metadata_tag(asset,'MageBootsSourceSHA')==sha:
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
    asset.set_editor_property('physics_asset',None);E.set_metadata_tag(asset,'MageBootsSourceSHA',sha);E.set_metadata_tag(asset,'SourceContract',data['contract']);E.set_metadata_tag(asset,'EquipmentDefinition',KEY);save(asset)
    receipt['meshes'][name]=asset.get_path_name();receipt.setdefault('source_sha256',{})[str(file)]=sha;record();print('MAGE_BOOTS_SKELETAL_SAVED',name,flush=True);return asset

def static_source(file,path,materials,pickup=False):
    raw=file.read_bytes();sha=hashlib.sha256(raw).hexdigest();existing=u.load_asset(path)
    if existing and E.get_metadata_tag(existing,'MageBootsSourceSHA')==sha:return existing.get_path_name()
    if existing and in_play:raise RuntimeError('Preserve loaded mage-boot display during PIE')
    data=json.loads(raw);iconio=module('mage_boots_static_io','Tools/BlueMageSetIcons/save_icons.py');dm=iconio.dynamic(data)
    if pickup:
        center=[(min(p[i] for p in data['positions'])+max(p[i] for p in data['positions']))*.5 for i in range(3)];T.translate_mesh(dm,u.Vector(*[-v for v in center]))
    result=io.static(dm,path,materials);asset=load(result);E.set_metadata_tag(asset,'MageBootsSourceSHA',sha);E.set_metadata_tag(asset,'EquipmentDefinition',KEY);save(asset)
    receipt.setdefault('source_sha256',{})[str(file)]=sha;record();return result

def icon_texture():
    file=R/(KEY+'.png');sha=hashlib.sha256(file.read_bytes()).hexdigest();folder=DEST+'/Icons';path=folder+'/T_BlueMageBoots_Icon';asset=u.load_asset(path)
    if asset and E.get_metadata_tag(asset,'MageBootsSourceSHA')==sha:return asset.get_path_name()
    if asset and in_play:raise RuntimeError('Preserve loaded mage-boot icon during PIE')
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=folder;t.destination_name='T_BlueMageBoots_Icon';t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);asset=load(path)
    for key,value in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,srgb=True).items():asset.set_editor_property(key,value)
    E.set_metadata_tag(asset,'MageBootsSourceSHA',sha);save(asset);receipt.setdefault('source_sha256',{})[str(file)]=sha;return asset.get_path_name()

def main():
    E.make_directory(DEST);materials=mats();receipt['materials']=[m.get_path_name() for m in materials];record()
    for name in VARIANTS:
        skeletal(R/'Authored'/(name+'.json'),'SK_'+name,materials,SLOTS)
        gc.collect();u.SystemLibrary.collect_garbage()
    receipt['pickup']=static_source(R/'Authored/Jason_BlueMageBoots_Garment.json',DEST+'/Pickups/SM_BlueMageBoots',materials,True);record()
    receipt['icon']=static_source(P/'SourceAssets/BlueMageSetIcons20261019'/(KEY+'-display.json'),DEST+'/Icons/SM_BlueMageBoots_Display',materials);record()
    receipt['icon_texture']=icon_texture();receipt['completed']=True;record();print('MAGE_BOOTS_ASSETS_COMPLETE',flush=True)
if __name__=='__main__':main()
