"""Save the two revised skeletal meshes in new asset packages, reusing the approved materials."""
import hashlib,json,os
from pathlib import Path
import unreal as u
src=Path(__file__).resolve().parent
batch=Path(os.environ['FIT_BATCH'])
family='/Game/Weapons/FrontierCompoundBow'
folder=family+'/LegendaryFrameFitR2'
tools=u.AssetToolsHelpers.get_asset_tools()
skins=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
ske=u.load_asset(family+'/RigContactR2/SK_Frontier_Assembly_Skeleton')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
def import_asset(path,dest,options=None):
    task=u.AssetImportTask();task.filename=str(path);task.destination_name=path.stem;task.destination_path=dest
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True
    if options:task.options=options
    tools.import_asset_tasks([task])
    if not task.imported_object_paths:raise ValueError('No asset '+str(path))
    return u.load_asset(dest+'/'+path.stem)
def save(a):
    if not u.EditorLoadingAndSavingUtils.save_packages([a.get_outermost()],False):raise RuntimeError(a.get_name())
data={}
for kind in ('Eclipse','Aurora'):
    name='SK_Frontier_'+kind
    opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    opts.import_as_skeletal=True;opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False
    opts.import_animations=False;opts.create_physics_asset=False;opts.skeleton=ske
    opts.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    opts.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
    opts.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
    mesh=import_asset(src/'Export'/(name+'.fbx'),folder,opts)
    bindings={'M_Frontier_Surface':u.load_asset(family+'/M_Frontier_Surface'),'M_Frontier_Cord':u.load_asset(family+'/M_Frontier_Cord')}
    finish='M_'+kind+'_Frame';bindings[finish]=u.load_asset(family+'/'+kind+'FrameR1/'+finish)
    slots=list(mesh.materials)
    if mesh.skeleton!=ske or set(bindings)!=set(str(s.material_slot_name) for s in slots) or not all(bindings.values()):
        raise RuntimeError('Unexpected '+kind+' bindings: '+str([str(s.material_slot_name) for s in slots]))
    for s in slots:s.material_interface=bindings[str(s.material_slot_name)]
    mesh.materials=slots
    if not skins.regenerate_lod(mesh,3,False,False):raise RuntimeError('Failed LODs '+kind)
    save(mesh)
    key='bow_frontier_compound_riser_frontier_'+kind.lower()
    ic=import_asset(src/'Export'/(key+'.png'),'/Game/ColdSteelData/AttachmentIcons20260913/FramedBows')
    ic.srgb=True;ic.lod_group=u.TextureGroup.TEXTUREGROUP_UI;ic.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
    ic.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    save(ic)
    data[kind]={'mesh':mesh.get_path_name(),'lods':skins.get_lod_count(mesh),'icon':ic.get_path_name(),
      'fbx_sha256':hashlib.sha256((src/'Export'/(name+'.fbx')).read_bytes()).hexdigest(),
      'png_sha256':hashlib.sha256((src/'Export'/(key+'.png')).read_bytes()).hexdigest(),
      'skeleton':ske.get_path_name(),'materials':{k:v.get_path_name() for k,v in bindings.items()}}
(batch/'imported.json').write_text(json.dumps(data,indent=2),encoding='utf8')
