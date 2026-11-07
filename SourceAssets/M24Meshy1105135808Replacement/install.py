"""Install both variants at their existing asset paths through the editor mutex."""
import json,shutil,uuid
from pathlib import Path
import unreal as u
root=Path(__file__).resolve().parent
project=root.parents[1]; exports=root/'Exports'
base='/Game/Weapons/M24/CarbonSpine20261104'
new=base+'/Meshy1105135808'
ui='/Game/ColdSteelData/AttachmentIcons20260913'
icon='ue_m24_stock_m24_carbon_spine_stock'
fit=json.loads((root/'fit.json').read_text());source=json.loads((root/'source.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
if Path(u.Paths.project_dir()).resolve()!=project:raise RuntimeError('Wrong UE host')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; preserve user play session')
targets={k:base+'/Meshes/'+Path(e['file']).stem for k,e in fit.items()}
iconpaths=[ui+'/'+icon,ui+'/FramedFirearms/'+icon]
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in dirty or any(q.startswith(new+'/') for q in dirty) for p in [*targets.values(),*iconpaths]):
    raise RuntimeError('An asset in this replacement already has unsaved edits')
def disk(path):
    return project/'Content'/(path.removeprefix('/Game/')+'.uasset')
def preserve(p):
    backup=root/'Before'/p.relative_to(project/'Content')
    if not backup.exists():
        backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,backup)
for path in [*targets.values(),*iconpaths]:
    preserve(disk(path))
for path in iconpaths:preserve(disk(path).with_suffix('.png'))
edition=source['source']
def existing(path):
    if not E.does_asset_exist(path):return None
    o=u.load_asset(path)
    if E.get_metadata_tag(o,'MeshySource')!=edition:raise RuntimeError('Occupied output '+path)
    return o
def save(o):
    if not E.save_loaded_asset(o,False):raise RuntimeError('Cannot save '+o.get_path_name())
def import_asset(file,folder,name,option=None,replace=False):
    t=u.AssetImportTask();t.filename=str(file);t.destination_name=name;t.destination_path=folder
    t.automated=True;t.replace_existing=replace;t.replace_existing_settings=replace;t.save=False
    if option:t.options=option;t.factory=u.FbxFactory()
    else:t.factory=u.TextureFactory()
    A.import_asset_tasks([t])
    items=t.get_objects()
    if len(items)!=1 or items[0].get_name()!=name:raise RuntimeError('Import '+str(file)+' returned '+str(t.imported_object_paths))
    return items[0]
textures={}
for k,t in source['textures'].items():
    file=exports/t['file'];name=file.stem
    tex=existing(new+'/'+name)
    if not tex:
        tex=import_asset(file,new,name)
        tex.compression_settings={'BaseColor':u.TextureCompressionSettings.TC_DEFAULT,'MetalRough':u.TextureCompressionSettings.TC_MASKS,'NormalDX':u.TextureCompressionSettings.TC_NORMALMAP}[k]
        tex.srgb=k=='BaseColor';tex.never_stream=False
        tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if k=='NormalDX' else u.TextureGroup.TEXTUREGROUP_WEAPON
        if k=='NormalDX':tex.set_editor_property('flip_green_channel',False)
        E.set_metadata_tag(tex,'MeshySource',edition);save(tex)
    textures[k]=tex
name='M_M24_Meshy1105135808';mat=existing(new+'/'+name)
if not mat:
    mat=A.create_asset(name,new,u.Material,u.MaterialFactoryNew());mat.set_editor_property('two_sided',True)
    def sample(k,types,y):
        n=L.create_material_expression(mat,u.MaterialExpressionTextureSample,-420,y)
        n.set_editor_property('texture',textures[k]);n.set_editor_property('sampler_type',types);return n
    def prop(node,pin,typ):
        if not L.connect_material_property(node,pin,typ):raise RuntimeError('Could not bind '+str(typ))
    color=sample('BaseColor',u.MaterialSamplerType.SAMPLERTYPE_COLOR,0)
    mr=sample('MetalRough',u.MaterialSamplerType.SAMPLERTYPE_MASKS,290)
    normal=sample('NormalDX',u.MaterialSamplerType.SAMPLERTYPE_NORMAL,580)
    prop(color,'RGB',u.MaterialProperty.MP_BASE_COLOR);prop(mr,'G',u.MaterialProperty.MP_ROUGHNESS)
    prop(mr,'B',u.MaterialProperty.MP_METALLIC);prop(normal,'RGB',u.MaterialProperty.MP_NORMAL)
    L.recompile_material(mat);E.set_metadata_tag(mat,'MeshySource',edition);save(mat)
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.override_full_name=True
imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False
imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
flag='Interchange.FeatureFlags.Import.FBX'
orig=u.SystemLibrary.get_console_variable_int_value(flag)
# Temp packages carry the FBX geometry until every destination LOD is prepared.
temp='/Temp/M24Meshy5808_'+uuid.uuid4().hex[:12]
prepared={};destinations={k:u.load_asset(p) for k,p in targets.items()}
try:
    u.SystemLibrary.execute_console_command(None,flag+' 0')
    for k,info in fit.items():
        file=exports/info['file'];m=import_asset(file,temp,file.stem,opt)
        slots={'CS_Receiver':u.load_asset(info['receiver_mat']),'CS_Meshy':mat}
        labels=[str(s.material_slot_name) for s in m.static_materials]
        if set(labels)!=set(slots) or not all(slots.values()):raise RuntimeError('Incoming material slots '+str(labels))
        for i,label in enumerate(labels):m.set_material(i,slots[label])
        bs=sub.get_lod_build_settings(m,0);bs.recompute_normals=False;bs.recompute_tangents=False
        bs.use_full_precision_u_vs=True;bs.use_high_precision_tangent_basis=True
        u.ASH12AttachmentAssetTools.disable_runtime_fast_build(m);sub.set_lod_build_settings(m,0,bs)
        lod=u.StaticMeshReductionOptions();lod.auto_compute_lod_screen_size=False
        lod.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=p,screen_size=s) for p,s in ((1.,1.),(.5,.18),(.2,.075))]
        if sub.set_lods(m,lod)!=3 or not u.M24ChassisAssetTools.bake_stock_tangent_basis(m):
            raise RuntimeError('Unable to build M24 LODs and tangent frames: '+k)
        prepared[k]=m
finally:
    u.SystemLibrary.execute_console_command(None,flag+' '+str(orig))
icons=[]
for path in iconpaths:
    file=disk(path).with_suffix('.png')
    variant='FramedFirearms' if '/FramedFirearms/' in path else ''
    shutil.copy2(exports/'Icons'/variant/file.name,file)
    tex=import_asset(file,path.rsplit('/',1)[0],icon,replace=True)
    tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.srgb=True;tex.never_stream=True
    icons.append(tex)
report={'source':edition,'source_sha256':source['sha256'],'meshes':{},'icons':iconpaths,'material':mat.get_path_name(),'textures':{k:t.get_path_name() for k,t in textures.items()},'gameplay_tested':False}
for k,incoming in prepared.items():
    dest=destinations[k]
    dest.set_editor_property('static_materials',list(incoming.static_materials))
    for l in range(3):
        if sub.set_lod_from_static_mesh(dest,l,incoming,l,True)!=l:raise RuntimeError('LOD transfer '+k+' '+str(l))
    dest.get_editor_property('asset_import_data').scripted_add_filename(str(exports/fit[k]['file']),0,'')
    E.set_metadata_tag(dest,'MeshySource',edition);E.set_metadata_tag(dest,'Source',str(root/'M24_Meshy_Fitted.blend'))
    E.set_metadata_tag(dest,'M24CarbonSpineEdition','Meshy1105135808')
    report['meshes'][k]={'path':dest.get_path_name(),'lod_triangles':[dest.get_num_triangles(i) for i in range(3)],'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in dest.static_materials}}
# Preserve the original stable object identities for loaded actors and old saved loadouts.
packages=[o.get_outermost() for o in [*destinations.values(),*icons]]
if not u.EditorLoadingAndSavingUtils.save_packages(packages,False):raise RuntimeError('Could not save all replacement assets')
(root/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_MESHY_5808_SAVED',list(targets.values()))
