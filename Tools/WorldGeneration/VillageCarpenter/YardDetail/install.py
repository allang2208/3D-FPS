"""Import this batch's meshes and refit only the saved repaired carpenter assembly."""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
import unreal as u

here=Path(__file__).resolve().parent
root=here.parents[3]
tree=here.parent.parent
sys.path[:0]=[str(here.parent),str(here.parent/'Props'),str(tree/'VillageBlacksmith'),str(tree/'AbandonedVillage')]
from YardDetail.layout import PACKAGE, LEVEL, TAG, place_detail
from author_shop import require
from shop_pendants import component,remove_components
import import_props as surfaces

source=root/'SourceAssets/HillsVillageCarpenter/YardDetail'
run=Path(os.environ['CARPENTER_YARD_RUN'])
batch=run.parent
content=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir()))
map_file=content/(LEVEL.removeprefix('/Game/')+'.umap')
assets=u.EditorAssetLibrary
mesh_ed=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
owner='CarpenterYardDetailR1'
plan=json.loads((root/'SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf-8'))
house=next(h for h in plan['houses'] if h[0]==plan['carpenter']['house'])
rows=json.loads((source/'models.json').read_text(encoding='utf-8'))
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def save_json(path,data):
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
def content_file(package):
    return content/(package.removeprefix('/Game/')+'.uasset')

peel_path=surfaces.DEST+'/Surfaces/M_CarpenterPlaneFiber'
if assets.does_asset_exist(peel_path):
    peel=require(peel_path)
else:
    peel=surfaces.material('PlaneFiber',surfaces.RURAL+'WoodSurface_00A_','normandy',
                           (.84,.78,.58),(.18,.119,.052),rough_scale=.47,rough_bias=.38)
mats={
    'Sawn':require(surfaces.DEST+'/Surfaces/M_CarpenterSawn'),
    'Endgrain':require(surfaces.DEST+'/Surfaces/M_CarpenterCut'),
    'Oak':require('/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Oak'),
    'Bark':require(surfaces.DEST+'/Surfaces/M_CarpenterBark'),
    'Peel':peel,
}
published=[peel_path]
mesh_rows=[]
for row in rows:
    package=PACKAGE+row['key']
    fbx=source/row['file']
    revision=sha(fbx)
    if assets.does_asset_exist(package):
        mesh=require(package)
        if assets.get_metadata_tag(mesh,'YardSourceSHA256')!=revision:
            raise RuntimeError('Existing mesh differs from the authored batch: '+package)
    else:
        task=u.AssetImportTask()
        task.filename=str(fbx)
        task.destination_name=row['name']
        task.destination_path=PACKAGE.rsplit('/',1)[0]
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
        mesh=require(package)
        for index,slot in enumerate(mesh.static_materials):
            mesh.set_material(index,mats[str(slot.material_slot_name)])
        boxes=[]
        for center,extent in row['boxes']:
            box=u.KBoxElem()
            box.set_editor_property('center',u.Vector(*center))
            for field,size in zip(('x','y','z'),extent): box.set_editor_property(field,size)
            boxes.append(box)
        body=mesh.get_editor_property('body_setup')
        aggregate=body.get_editor_property('agg_geom')
        aggregate.set_editor_property('box_elems',boxes)
        aggregate.set_editor_property('convex_elems',[])
        body.set_editor_property('agg_geom',aggregate)
        body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
        mesh_ed.set_lod_screen_sizes(mesh,[1.,.30,.095] if boxes else [1.,.14,.045])
        assets.set_metadata_tag(mesh,'YardDetailOwner',owner)
        assets.set_metadata_tag(mesh,'YardSourceSHA256',revision)
        if not assets.save_loaded_asset(mesh,False):raise RuntimeError('Cannot write '+package)
    published.append(package)
    mesh_rows.append(dict(package=package,source_sha256=revision,lods=mesh_ed.get_lod_count(mesh),
                          triangles=row['triangles'],simple_boxes=len(row['boxes'])))
save_json(run/'assets-saved.json',mesh_rows)
file_stamp=map_file.stat().st_mtime_ns
original_sha=sha(map_file)
world=u.EditorLoadingAndSavingUtils.load_map(LEVEL)
if not world: raise RuntimeError('Current village level unavailable')
sub=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
actor=next(a for a in sub.get_all_level_actors() if a.get_actor_label()=='Village_Carpenter_Repaired'
           and 'VillageCarpenter.Assembly' in map(str,a.tags))
legacy={surfaces.DEST+'/SM_Carpenter'+key for key in ('DryingRack','LogStack','Shavings')}
old=[]
seen=set()
for c in actor.get_components_by_class(u.StaticMeshComponent):
    tags=set(map(str,c.component_tags))
    mesh=c.static_mesh
    if 'VillageCarpenter.Repaired' not in tags or not mesh:continue
    path=mesh.get_path_name().split('.')[0]
    if path in legacy or TAG in tags:
        old.append(c)
        seen.add(path)
if not (legacy<=seen or {r['package'] for r in mesh_rows}<=seen):
    raise RuntimeError('The saved repaired assembly has changed; protect its existing dressing.')
actor.modify()
remove_components(actor,old)
def add(state,path,transform,profile,extra):
    c=component(actor,u.StaticMeshComponent)
    c.set_mobility(u.ComponentMobility.STATIC)
    c.set_static_mesh(require(path))
    c.set_world_transform(transform,False,True)
    tags=['VillageCarpenter.'+state,*extra]
    if profile=='NoCollision':
        tags.append('VillageCarpenter.NoCollision')
        c.set_cull_distance(2200.)
    c.component_tags=tags
    c.set_collision_profile_name(profile)
    c.set_editor_property('generate_overlap_events',False)
    c.set_editor_property('receives_decals',False)
    c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    c.set_visibility(False)
    c.set_hidden_in_game(True)
place_detail(house,add)
backup=run/'Before'/map_file.name
backup.parent.mkdir(exist_ok=True)
if file_stamp!=map_file.stat().st_mtime_ns or original_sha!=sha(map_file):raise RuntimeError('Village changed while authoring')
shutil.copy2(map_file,backup)
if file_stamp!=map_file.stat().st_mtime_ns or not u.EditorLoadingAndSavingUtils.save_map(world,LEVEL):
    raise RuntimeError('Could not save village')
saved=run/'Saved'
saved.mkdir(exist_ok=True)
shutil.copy2(map_file,saved/map_file.name)
for path in published:
    asset=content_file(path)
    target=saved/path.removeprefix('/Game/')
    target=target.with_suffix('.uasset')
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(asset,target)
receipt=dict(level=LEVEL,assembly=actor.get_actor_label(),revision=owner,map_before=original_sha,
             map_after=sha(map_file),snapshot=str(saved),backup=str(backup),material=peel_path,meshes=mesh_rows)
save_json(run/'install.json',receipt)
save_json(batch/'staged.json',receipt)
