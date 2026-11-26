"""Remove collapsed generated triangles while preserving corner UVs/normals."""
import bpy,math,collections
from mathutils import Vector
def clean(ob):
    me=ob.data;me.calc_loop_triangles();uv=me.uv_layers.active
    positions=[v.co.copy() for v in me.vertices];faces=[];tex=[];normals=[];removed=0
    groups=collections.defaultdict(list)
    for index,tri in enumerate(me.loop_triangles):groups[tuple(sorted(tri.vertices))].append(index)
    discard=set()
    for indices in groups.values():
        if len(indices)<2:continue
        directions=[]
        for index in indices:
            a,b,c=[positions[i] for i in me.loop_triangles[index].vertices];directions.append((b-a).cross(c-a))
        # Opposing coincident faces are internal zero-thickness boolean fins.
        discard.update(indices if any(directions[0].dot(n)<0 for n in directions[1:]) else indices[1:])
    for index,tri in enumerate(me.loop_triangles):
        if index in discard:removed+=1;continue
        a,b,c=[positions[i] for i in tri.vertices];cross=(b-a).cross(c-a)
        if cross.length<1e-12:
            removed+=1;continue
        face_normal=cross.normalized();faces.append(tuple(tri.vertices))
        for li in tri.loops:
            tex.append(tuple(uv.data[li].uv))
            n=me.corner_normals[li].vector
            normals.append(tuple(n.normalized() if n.length>1e-8 and all(math.isfinite(x) for x in n) else face_normal))
    if not removed:return
    replacement=bpy.data.meshes.new(me.name+'_NonCollapsed');replacement.from_pydata(positions,[],faces);replacement.update()
    for mat in me.materials:replacement.materials.append(mat)
    layer=replacement.uv_layers.new(name='PhysicalUV')
    for i,t in enumerate(tex):layer.data[i].uv=t
    for face in replacement.polygons:face.use_smooth=True
    replacement.normals_split_custom_set(normals)
    ob.data=replacement;ob['RemovedCollapsedTriangles']=removed;bpy.data.meshes.remove(me)
