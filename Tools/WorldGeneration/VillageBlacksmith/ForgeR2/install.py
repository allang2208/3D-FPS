"""Build the revised sign parts and side-blast hearth and replace their level assemblies."""
import hashlib,json,os,sys,shutil
from pathlib import Path
import unreal as u

here=Path(__file__).resolve().parent
project=here.parents[3]
sys.path.insert(0,str(here.parent))
from author_shop import require
from ForgeR2 import refit,surfaces

source=project/'SourceAssets/HillsVillageBlacksmith20261117/ForgeR2'
batch=Path(os.environ['SMITH_FORGE_R2_BATCH'])
host=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
if host!=batch/'Host':raise RuntimeError('Private village host required')
content=host/'Content'
level='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
relative=level.removeprefix('/Game/')+'.umap'
mesh_editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
palette=surfaces.palette(source)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def import_model(row):
    path=refit.ROOT+'/'+row['name']
    task=u.AssetImportTask()
    task.filename=str(source/row['file'])
    task.destination_name=row['name']; task.destination_path=refit.ROOT
    task.automated=True;task.replace_existing=True
    opt=u.FbxImportUI()
    opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False
    d=opt.static_mesh_import_data
    if row['name']=='SM_SmithSideBlastFuel':d.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE)
    d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True
    d.import_mesh_lods=True;d.generate_lightmap_u_vs=False;d.auto_generate_collision=False
    d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.options=opt;task.factory=u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh=require(path)
    for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,palette[str(slot.material_slot_name)])
    collision=[]
    for centre,size in row['boxes']:
        box=u.KBoxElem()
        box.set_editor_property('center',u.Vector(*centre))
        for f,value in zip(('x','y','z'),size):box.set_editor_property(f,value)
        collision.append(box)
    body=mesh.get_editor_property('body_setup');aggregate=body.get_editor_property('agg_geom')
    aggregate.set_editor_property('box_elems',collision);aggregate.set_editor_property('convex_elems',[])
    body.set_editor_property('agg_geom',aggregate)
    body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    mesh_editor.set_lod_screen_sizes(mesh,[1.,.34,.10])
    surfaces.save(mesh)
    b=mesh.get_bounding_box()
    return dict(package=path,lods=mesh_editor.get_lod_count(mesh),source_sha256=digest(source/row['file']),
                bounds_cm=[[v.x,v.y,v.z] for v in (b.min,b.max)])

rows=json.loads((source/'models.json').read_text(encoding='utf-8'))
models=[import_model(r) for r in rows]
original=digest(content/relative)
backup=batch/'Before'/original/Path(relative).name
backup.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(content/relative,backup)
world=u.EditorLoadingAndSavingUtils.load_map(level)
if not world:raise RuntimeError('Village map unavailable')
changes=refit.apply(project)
if not u.EditorLoadingAndSavingUtils.save_map(world,level):raise RuntimeError('Could not save village')
packages=surfaces.PACKAGES+[m['package'] for m in models]
files=[pkg.removeprefix('/Game/')+'.uasset' for pkg in packages]+[relative]
for file in files:
    dest=batch/'Saved'/file
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(content/file,dest)
receipt=dict(revision='SmithForgeAndSignR2',level=level,map_before=original,map_after=digest(content/relative),
             before=str(backup),source=str(source.resolve()),packages=packages,models=models,placements=changes)
(batch/'staged.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
