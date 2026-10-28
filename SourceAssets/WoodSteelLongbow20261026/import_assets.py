"""Import and save only the newly authored longbow packages."""
from pathlib import Path
import json,hashlib,re,sys
import unreal as u
P=Path(__file__).parent;DEST='/Game/Weapons/WoodSteelLongbow20261026'
sys.path.insert(0,str(P))
from linen_materials import build_linen
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt=P/'import-receipt.json'
r=json.loads(receipt.read_text()) if receipt.exists() else {'saved':{},'sources':{},'gameplay_tested':False}
recovered=set()
if any(x.get_name().startswith(DEST+'/') for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserving unsaved longbow packages')
def save(asset,source=None):
    if not asset or not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Asset save failed '+str(asset))
    r['saved'][asset.get_name()]=asset.get_path_name()
    if source:r['sources'][asset.get_name()]=hashlib.sha256(source.read_bytes()).hexdigest()
    receipt.write_text(json.dumps(r,indent=2),encoding='utf-8')
    print('LONGBOW_SAVED '+asset.get_path_name(),flush=True)
def existing(name,folder=DEST):
    if name in r['saved']:return u.load_asset(r['saved'][name])
    if E.does_asset_exist(folder+'/'+name):
        # This first mesh was imported by the previous batch and saved when that
        # editor closed, after save_loaded_asset had returned false. Resume only
        # that known partial import, and require its original source file.
        if name=='SK_WoodSteelLongbow_Original' and folder==DEST:
            mesh=u.load_asset(folder+'/'+name)
            sources=mesh.get_editor_property('asset_import_data').extract_filenames()
            expected=(P/'Export'/(name+'.fbx')).resolve()
            if len(sources)==1 and Path(sources[0]).resolve()==expected:
                recovered.add(name);return mesh
        raise RuntimeError('Existing unowned asset '+folder+'/'+name)
    return None
def texture(index,kind):
    name='T_WoodSteelLongbow_'+kind;t=existing(name,DEST+'/Textures')
    if t:return t
    source=P/'Textures'/('Image_'+str(index)+'.png')
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=DEST+'/Textures';task.destination_name=name
    task.automated=True;task.save=False;A.import_asset_tasks([task]);t=u.load_asset(task.destination_path+'/'+name)
    if not t:raise RuntimeError('Texture import failed '+name)
    t.srgb=kind=='BaseColor';t.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
    if kind=='Normal':t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP;t.set_editor_property('flip_green_channel',True)
    elif kind=='MetalRough':t.compression_settings=u.TextureCompressionSettings.TC_MASKS
    save(t,source);return t
tex={kind:texture(i,kind) for i,kind in enumerate(['BaseColor','MetalRough','Normal'])}
def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def out(n,prop,pin=''):L.connect_material_property(n,pin,prop)
def scalar(m,value):return node(m,u.MaterialExpressionConstant,r=value)
materials={}
for skinned in [True,False]:
    suffix='' if skinned else '_Static'
    for finish in ['PBR','Steel','Leather','Linen','WaxedLinen']:
        name='M_WoodSteelLongbow_'+finish+suffix;m=existing(name)
        if not m:
            m=A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
            if finish=='PBR':
                base=node(m,u.MaterialExpressionTextureSample,texture=tex['BaseColor'])
                orm=node(m,u.MaterialExpressionTextureSample,texture=tex['MetalRough'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
                normal=node(m,u.MaterialExpressionTextureSample,texture=tex['Normal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
                out(base,u.MaterialProperty.MP_BASE_COLOR,'RGB');out(orm,u.MaterialProperty.MP_ROUGHNESS,'G')
                out(orm,u.MaterialProperty.MP_METALLIC,'B');out(normal,u.MaterialProperty.MP_NORMAL,'RGB')
            elif finish in ['Linen','WaxedLinen']:
                build_linen(m,finish=='WaxedLinen')
            else:
                rgb,rough,metal={'Steel':((.16,.17,.18),.43,.9),'Leather':((.045,.022,.009),.78,0),'Linen':((.32,.30,.25),.88,0)}[finish]
                out(node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*rgb,1)),u.MaterialProperty.MP_BASE_COLOR)
                out(scalar(m,rough),u.MaterialProperty.MP_ROUGHNESS);out(scalar(m,metal),u.MaterialProperty.MP_METALLIC)
                if finish in ['Leather','Linen']:
                    normal=node(m,u.MaterialExpressionTextureSample,texture=tex['Normal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
                    out(normal,u.MaterialProperty.MP_NORMAL,'RGB')
            if skinned:L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
            L.recompile_material(m);save(m)
        materials[(finish,skinned)]=m
external='/Game/Weapons/DarkBow20260925/SingleLensOptics20260927/'
def finish_slot(name,skin):
    # Blender appends .001 when the second optical head reuses a material;
    # FBX converts that separator to an underscore. Both heads share that finish.
    canonical=re.sub(r'_\d{3}$','',name)
    if canonical in {'M_BowOptic_BlackSteel','M_BowOptic_DarkBronze','M_BowOptic_Etching','M_BowOptic_Glass2x','M_BowOptic_Glass4x'}:
        name=canonical
    if name.startswith('M_WoodSteelLongbow_'):return materials[(name.removeprefix('M_WoodSteelLongbow_'),skin)]
    if name in ['BracketBowWood','BracketEndgrain']:return materials[('Steel',skin)]
    if name=='BracketWaxedLinen':return materials[('Leather',skin)]
    asset=u.load_asset(external+name)
    if not asset:raise RuntimeError('Optical material missing '+name)
    return asset
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
skeleton=u.load_asset(r['saved']['SK_WoodSteelLongbow_Original_Skeleton']) if 'SK_WoodSteelLongbow_Original_Skeleton' in r['saved'] else None
for row in json.loads((P/'authoring.json').read_text())['assets']:
    name=row['name'];source=P/'Export'/(name+'.fbx');mesh=existing(name)
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if mesh and r['sources'].get(name)==digest:continue
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if row['skeletal'] else u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_as_skeletal=row['skeletal'];opt.import_animations=False
    opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
    if row['skeletal']:
        if skeleton:opt.skeleton=skeleton
        d=opt.skeletal_mesh_import_data
        d.set_editor_property('update_skeleton_reference_pose',False)
        d.set_editor_property('use_t0_as_ref_pose',False)
    else:
        d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
    d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=DEST;task.destination_name=name
    task.automated=True;task.replace_existing=bool(mesh);task.replace_existing_settings=True;task.save=False;task.options=opt
    if name not in recovered:
        A.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name)
    if not mesh:raise RuntimeError('Mesh import failed '+name)
    slots=list(mesh.materials if row['skeletal'] else mesh.static_materials)
    for slot in slots:slot.material_interface=finish_slot(str(slot.material_slot_name),row['skeletal'])
    if row['skeletal']:mesh.materials=slots
    else:mesh.static_materials=slots
    if row['skeletal']:
        skeleton=mesh.skeleton;save(skeleton)
    save(mesh,source)
r['complete']=True;receipt.write_text(json.dumps(r,indent=2),encoding='utf-8')
print('WOOD_STEEL_LONGBOW_IMPORT_COMPLETE '+str(len(r['saved'])))
exec(compile((P/'import_icons.py').read_text(encoding='utf-8'),str(P/'import_icons.py'),'exec'),{'__file__':str(P/'import_icons.py')})
