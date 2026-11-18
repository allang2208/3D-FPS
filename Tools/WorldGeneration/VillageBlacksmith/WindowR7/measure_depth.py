import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/WindowR7'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(ROOT/'SourceAssets/HillsVillageBlacksmith20261117/DetailR6/SM_H_OldWall_Window_00A.fbx'))
o=next(o for o in bpy.context.scene.objects if o.type=='MESH')
bpy.context.view_layer.objects.active=o;o.select_set(True)
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)

rows=[]
for x in (-55,-50,-45,45,50,55):
 for z in (-20,-7,30,67,90):
  hit,pos,normal,index=o.ray_cast(Vector((x/100,2,z/100)),Vector((0,-1,0)),distance=4)
  if hit:rows.append([x,z,round(-pos.y*100,2)])
print('FRONT_MOUNT_DEPTH',rows)
(OUT/'mount-depth.json').write_text(json.dumps(rows,indent=2))
