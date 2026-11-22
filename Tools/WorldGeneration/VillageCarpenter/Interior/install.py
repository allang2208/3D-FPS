"""Import and save the joinery fittings in the private village authoring host."""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
import unreal as u

here=Path(__file__).resolve().parent
project=here.parents[3]
sys.path[:0]=[str(here.parent),str(here.parent.parent/'VillageBlacksmith'),str(here.parent.parent/'AbandonedVillage')]
from Interior.layout import ROOT,LEVEL,apply
from Interior.water import create_water
from author_shop import require

batch=Path(os.environ['CARPENTER_INTERIOR_BATCH'])
host=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
if host!=batch/'Host':raise RuntimeError('Expected private carpenter authoring host')
source=project/'SourceAssets/HillsVillageCarpenter/InteriorR1'
assets=u.EditorAssetLibrary
mesh_editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
MODELS='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_'
SURF='/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_Carpenter'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
water=create_water(ROOT)
materials={k:require(path) for k,path in {
    'Sawn':SURF+'Sawn','Endgrain':SURF+'Cut','Oak':MODELS+'Oak','Linen':MODELS+'Linen',
    'Iron':SURF+'Iron','Steel':SURF+'Steel','Brass':SURF+'Brass',
    'WetOak':'/Game/WorldGeneration/TemperateHills/VillageBlacksmith/Workfloor/Materials/M_SmithQuenchOak'
}.items()}
materials['Water']=water
packages=[water.get_path_name().split('.')[0]]
model_info=[]
for row in json.loads((source/'models.json').read_text(encoding='utf-8')):
    package=ROOT+'/'+row['name']
    fbx=source/row['file']
    if assets.does_asset_exist(package):
        mesh=require(package)
        if assets.get_metadata_tag(mesh,'CarpenterInteriorSource')!=digest(fbx):
            raise RuntimeError('Different mesh version in private host '+package)
    else:
        task=u.AssetImportTask()
        task.filename=str(fbx)
        task.destination_name=row['name']
        task.destination_path=ROOT
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
        data.import_mesh_lods=len(row['triangles'])>1
        data.generate_lightmap_u_vs=False
        data.auto_generate_collision=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task.options=opts
        task.factory=u.FbxFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh=require(package)
        for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,materials[str(slot.material_slot_name)])
        body=mesh.get_editor_property('body_setup')
        agg=body.get_editor_property('agg_geom')
        boxes=[]
        for center,size,yaw in row['boxes']:
            box=u.KBoxElem()
            box.set_editor_property('center',u.Vector(*center))
            box.set_editor_property('rotation',u.Rotator(yaw=yaw))
            for axis,extent in zip('xyz',size):box.set_editor_property(axis,extent)
            boxes.append(box)
        agg.set_editor_property('box_elems',boxes)
        agg.set_editor_property('convex_elems',[])
        body.set_editor_property('agg_geom',agg)
        body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
        if len(row['triangles'])==3:mesh_editor.set_lod_screen_sizes(mesh,[1.,.24,.075])
        assets.set_metadata_tag(mesh,'CarpenterInteriorSource',digest(fbx))
        if not assets.save_loaded_asset(mesh,False):raise RuntimeError('Cannot save '+package)
    packages.append(package)
    model_info.append(dict(package=package,triangles=row['triangles'],collision_shapes=len(row['boxes'])))

relative=LEVEL.removeprefix('/Game/')+'.umap'
original=host/'Content'/relative
before=digest(original)
backup=batch/'Before'/before/original.name
backup.parent.mkdir(exist_ok=True,parents=True)
shutil.copy2(original,backup)
world=u.EditorLoadingAndSavingUtils.load_map(LEVEL)
if not world:raise RuntimeError('Village unavailable')
placements=apply(project)
if not u.EditorLoadingAndSavingUtils.save_map(world,LEVEL):raise RuntimeError('Could not save workshop furnishings')
for rel in [relative]+[k.removeprefix('/Game/')+'.uasset' for k in packages]:
    dst=batch/'Saved'/rel
    dst.parent.mkdir(exist_ok=True,parents=True)
    shutil.copy2(host/'Content'/rel,dst)
receipt=dict(level=LEVEL,packages=packages,revision='CarpenterInteriorR1',placements=placements,meshes=model_info,
             map_before=before,map_after=digest(original),before=str(backup),source=str(source.resolve()))
(batch/'staged.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False),encoding='utf-8')
