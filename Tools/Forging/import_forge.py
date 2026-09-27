"""Import/save original forge tools, reusing the project's aged PBR library."""
import unreal as u,sys,json,datetime
from pathlib import Path
ROOT=Path(u.Paths.project_dir());SRC=ROOT/'SourceAssets/ForgeInteraction20260927';DEST='/Game/Props/ForgeInteraction20260927'
sys.path.insert(0,str(ROOT/'Tools/Fluids'))
sys.path.insert(0,str(ROOT/'Tools/Forging'))
from forge_materials import build_material, build_effects
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
saved=[]
dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
# The first graph import created these two new packages before reporting a pin error.
# Resume our unsaved, never-published packages; preserve any saved asset edited in UE.
owned_new={DEST+'/M_ForgeHotSteel',DEST+'/M_ForgeGuide'}
def own_unpublished(p):return p in owned_new and not (ROOT/'Content'/(p.removeprefix('/Game/')+'.uasset')).exists()
if any(p.startswith(DEST) and not own_unpublished(p) for p in dirty):raise RuntimeError('Unsaved forge target assets; preserving editor work')
def save(a):
    if not a:raise RuntimeError('Missing forge dependency')
    if isinstance(a,u.Material):L.recompile_material(a)
    if not E.save_loaded_asset(a,False):raise RuntimeError('Could not save '+a.get_path_name())
    saved.append(a.get_path_name());return a
def material(name,hot=False):
    return save(build_material(name,hot))
mats={'AgedSteel':u.load_asset('/Game/Props/CastingStation20260926/AnvilReferenceV3/Materials/M_AnvilReferenceSteel'),
      'StruckFace':u.load_asset('/Game/Props/CastingStation20260926/AnvilReferenceV3/Materials/M_AnvilReferenceSteel'),
      'AshHandle':u.load_asset('/Game/UnrealNormandy/MaterialInstances/MI_Wood_00A'),
      'HotBlank':material('M_ForgeHotSteel',True),'Guide':material('M_ForgeGuide')}
if any(v is None for v in mats.values()):raise RuntimeError('Existing aged metal/wood library unavailable')
for effect in build_effects():save(effect)
for path in sorted(SRC.glob('SM_*.fbx')):
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False
    d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
    d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True
    d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    t=u.AssetImportTask();t.filename=str(path);t.destination_path=DEST;t.destination_name=path.stem
    t.automated=True;t.replace_existing=True;t.save=False;t.options=opt;t.factory=u.FbxFactory();A.import_asset_tasks([t])
    mesh=u.load_asset(DEST+'/'+path.stem)
    if mesh is None:raise RuntimeError('Import failed '+path.stem)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,mats[str(slot.get_editor_property('material_slot_name')).split('.')[0]])
    save(mesh)
audio=u.AssetImportTask();audio.filename=str(SRC/'ForgeHammerImpact.wav');audio.destination_path=DEST;audio.destination_name='SW_ForgeHammerImpact';audio.automated=True;audio.replace_existing=True;audio.save=True
A.import_asset_tasks([audio]);save(u.load_asset(DEST+'/SW_ForgeHammerImpact'))
receipt={'saved':saved,'runtime_tested':False,'rendered':False,'source':str(SRC)}
(SRC/('import-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')).write_text(json.dumps(receipt,indent=2),encoding='utf8')
print('FORGE_SAVED '+json.dumps(receipt),flush=True)
