"""Import the workfloor sources and update only the existing blacksmith in the saved village."""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
import unreal as u

here=Path(__file__).resolve().parent
project=here.parents[3]
sys.path.insert(0,str(here.parent))
from Workfloor import dressing,materials,ember_surface
from author_shop import require

batch=Path(os.environ['SMITH_WORKFLOOR_BATCH'])
source=project/'SourceAssets/HillsVillageBlacksmith20261117/Workfloor'
content=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir()))
level='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
level_file=content/(level.removeprefix('/Game/')+'.umap')
assets=u.EditorAssetLibrary
mesh_editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data):path.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
def copy_package(file,folder,relative):
    target=batch/folder/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(file,target)
    return target

rows=json.loads((source/'models.json').read_text(encoding='utf-8'))
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
palette=materials.build()
live_coals=ember_surface.build_material()
published=[m.get_path_name().split('.')[0] for m in palette.values() if m.get_path_name().startswith(dressing.ROOT+'/')]
published.extend([ember_surface.HEAT,ember_surface.MATERIAL])
models=[]
for row in rows:
    fbx=source/row['file']
    revision=digest(fbx)
    path=dressing.ROOT+'/'+row['name']
    if assets.does_asset_exist(path):
        mesh=require(path)
        if assets.get_metadata_tag(mesh,'SmithFBX')!=revision:
            raise RuntimeError('Existing mesh source differs at '+path)
    else:
        task=u.AssetImportTask()
        task.filename=str(fbx)
        task.destination_name=row['name']
        task.destination_path=dressing.ROOT
        task.automated=True
        opts=u.FbxImportUI()
        opts.import_mesh=True
        opts.import_as_skeletal=False
        opts.import_materials=False
        opts.import_textures=False
        opts.automated_import_should_detect_type=False
        opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=opts.static_mesh_import_data
        data.combine_meshes=True
        data.convert_scene=True
        data.convert_scene_unit=True
        data.transform_vertex_to_absolute=True
        data.import_mesh_lods=True
        data.generate_lightmap_u_vs=False
        data.auto_generate_collision=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task.options=opts
        task.factory=u.FbxFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh=require(path)
        for i,slot in enumerate(mesh.static_materials):
            mesh.set_material(i,palette[str(slot.material_slot_name)])
        boxes=[]
        for center,dimensions in row['boxes']:
            box=u.KBoxElem()
            box.set_editor_property('center',u.Vector(*center))
            for field,size in zip(('x','y','z'),dimensions):box.set_editor_property(field,size)
            boxes.append(box)
        body=mesh.get_editor_property('body_setup')
        agg=body.get_editor_property('agg_geom')
        agg.set_editor_property('box_elems',boxes)
        agg.set_editor_property('convex_elems',[])
        body.set_editor_property('agg_geom',agg)
        body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
        mesh_editor.set_lod_screen_sizes(mesh,[1.,.31,.09])
        assets.set_metadata_tag(mesh,'SmithFBX',revision)
        if not assets.save_loaded_asset(mesh,False):raise RuntimeError('Could not save '+path)
    if path==ember_surface.HEARTH:
        ember_surface.bind(mesh,live_coals)
    published.append(path)
    models.append(dict(mesh=path,source_sha256=revision,lods=mesh_editor.get_lod_count(mesh),triangles=row['triangles']))

layout=json.loads((project/'SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf-8'))
house=next(h for h in layout['houses'] if h[0]==layout['blacksmith']['house'])
before=digest(level_file)
stamp=level_file.stat().st_mtime_ns
world=u.EditorLoadingAndSavingUtils.load_map(level)
if not world:raise RuntimeError('Could not open the village')
actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
station,=[a for a in actors.get_all_level_actors() if a.get_actor_label()==dressing.STATION_LABEL]
changes=dressing.apply(house,station)
if stamp!=level_file.stat().st_mtime_ns or before!=digest(level_file):
    raise RuntimeError('Village was saved while applying this change')
backup=copy_package(level_file,'Before',before+'/'+level_file.name)
if stamp!=level_file.stat().st_mtime_ns or not u.EditorLoadingAndSavingUtils.save_map(world,level):
    raise RuntimeError('Cannot publish village')
copy_package(level_file,'Saved',level.removeprefix('/Game/')+'.umap')
for package in published:
    relative=package.removeprefix('/Game/')+'.uasset'
    copy_package(content/relative,'Saved',relative)
receipt=dict(level=level,map_before=before,map_after=digest(level_file),backup=str(backup),changes=changes,
             models=models,packages=published,source=str(source.resolve()),gameplay_tested=False)
write(batch/'install.json',receipt)
