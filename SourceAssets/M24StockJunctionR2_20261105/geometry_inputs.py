from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix
def islands(me):
    pos=np.array([v.co[:] for v in me.vertices]); _,rows=np.unique(np.round(pos,6),return_inverse=True,axis=0)
    parent=list(range(rows.max()+1))
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    ed=np.empty((len(me.edges),2),np.int32);me.edges.foreach_get('vertices',ed.ravel())
    for a,b in rows[ed]:parent[root(a)]=root(b)
    groups=np.array([root(i) for i in rows]);return pos,groups
if __name__=='__main__':
    O=Path(__file__).resolve().parent
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(O/'Inputs/action.fbx'),use_custom_normals=True)
    for o in list(bpy.context.scene.objects):
        if o.type!='MESH':continue
        o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4)
        p,g=islands(o.data)
        print(o.name,'bounds',p.min(0),p.max(0))
        for id in np.unique(g):
            q=p[g==id];lo=q.min(0);hi=q.max(0)
            if lo[1]<.047:print('component',id,len(q),lo.round(6),hi.round(6))
    src=O.parent/'M24ActionLayout20261027/M24_ActionLayout_Editable.blend'
    with bpy.data.libraries.load(str(src)) as (a,b):b.objects=['M24_base']
    o=b.objects[0];p,g=islands(o.data);q=p[g==g[0]]
    print('donor object',o.matrix_world,'size',q.min(0),q.max(0))
    for y in (.018,.024,.036,.052,.070,.085,.103,.115):
        v=q[abs(q[:,1]-y)<.005]
        if len(v):print('donor section',y,v.min(0).round(5),v.max(0).round(5))
