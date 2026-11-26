"""Blender authoring step. Preserve the original PBR UVs while reducing the imported scan."""
from pathlib import Path
import hashlib
import json
import os
import runpy
import sys
import bpy

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/"SourceAssets/HillsVillageHighWall20261120/Design01/Meshy"
CACHE=Path(os.environ.get("HIGH_VILLAGE_CACHE","F:/FPSGAMEData/Caches/Authoring/HighVillageDefense/Reduced"))
CACHE.mkdir(parents=True,exist_ok=True)
roles={"A_HighWall":65000,"B_WestArch":50000,"C_WestGrille":75000}
for key,budget in roles.items():
    source=SOURCE/key/"model.glb"
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    target=CACHE/f"{key}-{digest[:12]}-{budget}.glb"
    if target.exists():continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    total=sum(len(o.data.polygons) for o in meshes)
    for obj in meshes:
        bpy.context.view_layer.objects.active=obj
        mod=obj.modifiers.new("Keep stone silhouette and ironwork","DECIMATE")
        mod.ratio=min(1.,budget/max(total,1))
        mod.use_collapse_triangulate=True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    partial=target.with_name(target.stem+".partial.glb")
    bpy.ops.export_scene.gltf(filepath=str(partial),export_format="GLB",export_animations=False,
        export_cameras=False,export_lights=False,export_image_format="AUTO")
    partial.replace(target)
    print("HIGH_VILLAGE_REDUCED",key,total,budget,flush=True)

runpy.run_path(str(Path(__file__).with_name("bake_wall_normal.py")), run_name="__main__")
