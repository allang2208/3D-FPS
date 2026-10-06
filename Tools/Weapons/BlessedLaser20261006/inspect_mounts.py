"""Record each saved fit's legacy shells in its optical frame."""
import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parents[3];O=P/'SourceAssets/BlessedLaser20261006/Model';R=O/'MountRepair';R.mkdir(exist_ok=True)
auth=json.loads((O/'authoring.json').read_text());report={}
for family,e in auth.items():
    bpy.ops.wm.open_mainfile(filepath=str(O/'Fitted'/('BlessedLaser_'+family+'.blend')))
    ob=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    forward=Vector(e['forward_blender']);up=Vector(e['up_blender']);right=up.cross(forward)
    frame=Matrix((forward,right,up));origin=Vector(e['emitter_blender_m'])
    bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if ob.data.materials[f.material_index].name.startswith('Blessed')],context='FACES')
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
    seen=set();rows=[]
    for v in bm.verts:
        if v in seen or not v.link_faces:continue
        stack=[v];seen.add(v);group=[]
        while stack:
            v=stack.pop();group.append(v)
            for edge in v.link_edges:
                other=edge.other_vert(v)
                if other not in seen:seen.add(other);stack.append(other)
        pts=[frame@(ob.matrix_world@v.co-origin)*1000 for v in group]
        rows.append(dict(vertices=len(pts),min=[min(p[i] for p in pts) for i in range(3)],max=[max(p[i] for p in pts) for i in range(3)],materials=list({ob.data.materials[f.material_index].name for v in group for f in v.link_faces})))
    bm.free();report[family]=rows
    print('MOUNT_SHELLS',family,json.dumps(rows),flush=True)
(R/'legacy_shells.json').write_text(json.dumps(report,indent=2))
