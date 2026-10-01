"""Final tiny-face cleanup of the already-authored grip shell; no re-modeling."""
import bpy,bmesh,json,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
O=Path(__file__).parent;sys.path.insert(0,str(O));import geometry as G
from shell_cleanup import close_slivers
bpy.ops.wm.open_mainfile(filepath=str(O/'A762_ReceiverGrip08.blend'))
bpy.context.preferences.filepaths.save_version=0
parts=[ob for ob in bpy.context.scene.objects if ob.type=='MESH'];OUT=O/'Exports'
for ob in parts:
    if 'ContinuousGrip08' not in ob.name:continue
    me=ob.data;attr=me.attributes.new('FinalNormals','FLOAT_VECTOR','CORNER')
    attr.data.foreach_set('vector',np.array([tuple(n.vector) for n in me.corner_normals],np.float32).ravel())
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.dissolve_degenerate(bm,dist=3e-7,edges=list(bm.edges))
    todo=set(bm.verts);components=[]
    while todo:
        component={todo.pop()};stack=list(component)
        while stack:
            vertex=stack.pop()
            for edge in vertex.link_edges:
                other=edge.other_vert(vertex)
                if other in todo:todo.remove(other);component.add(other);stack.append(other)
        components.append(component)
    if components:
        keep=max(components,key=len);remove=[v for v in bm.verts if v not in keep]
        if remove:bmesh.ops.delete(bm,geom=remove,context='VERTS')
    wire=[e for e in bm.edges if not e.link_faces]
    if wire:bmesh.ops.delete(bm,geom=wire,context='EDGES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    close_slivers(bm)
    print('CLEAN_SHELL',ob.name,'boundary',sum(e.is_boundary for e in bm.edges),'nonmanifold',sum(not e.is_manifold for e in bm.edges),flush=True)
    bm.to_mesh(me);bm.free();me.normals_split_custom_set([d.vector.normalized() for d in me.attributes['FinalNormals'].data])
    me.attributes.remove(me.attributes['FinalNormals'])
def active(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
plan=json.loads((O/'authoring.json').read_text());h=G.read('Body')[0]
source=(O/'author.py').read_text().split('# Export indexed buffers with all surviving UV channels and corner normals.')[1]
exec(compile(source,str(O/'author.py')+' export','exec'))
