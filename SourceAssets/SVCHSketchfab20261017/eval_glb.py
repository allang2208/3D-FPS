import bpy, json
import numpy as np
from mathutils import Vector
src=r"D:\FPS3D\FPSGAME\SourceAssets\SVCHSketchfab20261017\download\svch.glb"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
dg=bpy.context.evaluated_depsgraph_get()
rows=[]
for o in list(bpy.context.scene.objects):
    if o.type!='MESH': continue
    if not o.vertex_groups: continue
    ev=o.evaluated_get(dg)
    me=ev.to_mesh()
    mw=o.matrix_world
    names={g.index:g.name for g in o.vertex_groups}
    # dominant group per vertex from ORIGINAL mesh
    orig=o.data
    dom=[]
    for v in orig.vertices:
        best=max(v.groups,key=lambda g:g.weight,default=None)
        dom.append(names[best.group] if best else '')
    P=np.array([[*(mw@ev.matrix_world.inverted()@ (o.matrix_world@v.co))] for v in me.vertices])
    print("OBJ",o.name,len(me.vertices),len(me.polygons),"mats",[m.name if m else None for m in me.materials])
    rows.append(dict(obj=o.name, verts=len(me.vertices), polys=len(me.polygons),
                     mats=[m.name if m else None for m in me.materials],
                     dom=dom, P=P.tolist()))
    ev.to_mesh_clear()
json.dump(rows, open(r"D:\FPS3D\FPSGAME\SourceAssets\SVCHSketchfab20261017\glb_eval.json","w"))
print("EVAL_DONE")
