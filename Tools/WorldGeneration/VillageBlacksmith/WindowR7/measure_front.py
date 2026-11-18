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
for z in range(-80,116,5):
    empty=[]
    for x in range(-85,86):
        # UE X,Y,Z -> Blender X,-Y,Z in metres.
        hit,_,_,_=o.ray_cast(Vector((x/100,2,z/100)),Vector((0,-1,0)),distance=1.98)
        if not hit:empty.append(x)
    inside=[x for x in empty if abs(x)<65]
    if inside:rows.append({'z':z,'clear_min_x':min(inside),'clear_max_x':max(inside)})
(OUT/'aperture-front.json').write_text(json.dumps({'mesh':o.name,'bounds_m':[list(v) for v in o.bound_box],'rows':rows},indent=2))
print('APERTURE',rows)
