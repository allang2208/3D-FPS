"""Update historical display paths retained in existing inventory/network snapshots."""
import hashlib,shutil,sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).parent));from boot_paths import *
R=R/'Audit';R.mkdir(exist_ok=True);source=read(R.parent/'saved_assets.json');original=read(OLD/'saved_assets.json');previous=read(PREVIOUS/'saved_assets.json')
E=u.EditorAssetLibrary;G=u.GeometryScript_AssetUtils;A=u.AssetToolsHelpers.get_asset_tools();S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    ed=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if ed and ed.is_in_play_in_editor():raise RuntimeError('End PIE before updating old display packages')
receipt=read(R/'legacy_displays.json') if (R/'legacy_displays.json').exists() else dict(saved={},backups={},runtime_tested=False)
def record():write(R/'legacy_displays.json',receipt)
def backup(asset):
    path=asset.get_path_name();disk=P/'Content'/(path.split('.')[0][6:]+'.uasset');dest=R/'Before'/disk.relative_to(P)
    if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(disk,dest)
    receipt['backups'][path]=dict(file=str(dest),sha256=hashlib.sha256(dest.read_bytes()).hexdigest());record()
def save(a):
    a.modify()
    if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
for kind in ('icon','pickup'):
    current=u.load_asset(source['displays'][kind]);assert current
    for path in (original['boots_'+kind],previous['displays'][kind]):
        target=u.load_asset(path);assert target;backup(target)
        dm,status=G.copy_mesh_from_static_mesh(current,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD());assert status==u.GeometryScriptOutcomePins.SUCCESS
        slots=current.static_materials;opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=[str(s.material_slot_name) for s in slots],enable_recompute_normals=False,enable_recompute_tangents=True)
        _,status=G.copy_mesh_to_static_mesh(dm,target,opts,u.GeometryScriptMeshWriteLOD());assert status==u.GeometryScriptOutcomePins.SUCCESS
        options=u.StaticMeshReductionOptions();options.auto_compute_lod_screen_size=False;rows=[]
        for ratio,screen in ((1.,1.),(.55,.18),(.3,.07)):
            row=u.StaticMeshReductionSettings();row.percent_triangles=ratio;row.screen_size=screen;rows.append(row)
        options.reduction_settings=rows;S.set_lods(target,options);E.set_metadata_tag(target,'LeatherBootsPresentationRevision','TailoredV2');save(target)
        check,status=G.copy_mesh_from_static_mesh(target,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD());assert status==u.GeometryScriptOutcomePins.SUCCESS and check.get_triangle_count()==dm.get_triangle_count()
        assert [s.material_interface.get_path_name() for s in target.static_materials]==[s.material_interface.get_path_name() for s in current.static_materials]
        receipt['saved'][path]=dict(source=current.get_path_name(),triangles=dm.get_triangle_count(),lod_count=S.get_lod_count(target));record()
for relative in ('Icons/ue_leather_boots.png','Icons/LeatherBootsUpgrade20261022/ue_leather_boots.png'):
    path=P/'Content/ColdSteelData'/relative;dest=R/'Before'/path.relative_to(P)
    if path.exists() and not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    shutil.copyfile(R.parent/'ue_leather_boots.png',path)
    # Refresh an existing Texture2D counterpart only; PNG-only historical paths
    # remain PNGs. Both resolve to the current authored icon without touching saves.
    texpath='/Game/ColdSteelData/'+relative.removesuffix('.png');tex=u.load_asset(texpath)
    if tex:
        backup(tex);task=u.AssetImportTask();task.filename=str(path);task.destination_path=texpath.rsplit('/',1)[0];task.destination_name=texpath.rsplit('/',1)[1];task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);tex=u.load_asset(texpath)
        tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON);tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);save(tex)
    receipt.setdefault('icons',[])
    if relative not in receipt['icons']:receipt['icons'].append(relative)
receipt['completed']=True;record();print('LEATHER_BOOTS_LEGACY_DISPLAYS_REPAIRED',len(receipt['saved']),flush=True)
