import bpy,bmesh
from pathlib import Path
root=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(root/'handbrain_detailed_v01.blend'))
for o in bpy.context.scene.objects:
    if o.type!='MESH' or len(o.data.polygons)<1000: continue
    before=len(o.data.vertices)
    bm=bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=0.00001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(o.data)
    bm.free()
    o.data.normals_split_custom_set([(0,0,0)]*len(o.data.loops))
    for p in o.data.polygons: p.use_smooth=True
    print('Welded',before,len(o.data.vertices))
bpy.context.scene.render.filepath=str(root/'render_smoothing_test.png')
bpy.ops.render.render(write_still=True)
