import bpy,json
from pathlib import Path
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'SkeletonSniperStock_SVD_Editable.blend'),load_ui=False,use_scripts=False)
result={}
for ob in bpy.data.objects:
    if ob.type!='MESH':continue
    me=ob.data;me.calc_tangents();uv=me.uv_layers.active.data;rows=[]
    for f in me.polygons:
        if any(me.loops[i].tangent.length<.0001 for i in f.loop_indices):
            a,b,c=[uv[i].uv.copy() for i in f.loop_indices];v=b-a;w=c-a
            rows.append(dict(face=f.index,area=f.area,uv_area=abs(v.x*w.y-v.y*w.x),normal=list(f.normal)))
    result[ob.name]=rows
(O/'svd_degenerate_faces.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result),flush=True)
