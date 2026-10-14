"""Keep wrapped PBR UVs precise on sub-millimetre equipment bevels."""
import math,bmesh
def face_area(face):
    if len(face.verts)!=3:return face.calc_area()
    a,b,c=[v.co for v in face.verts]
    return (b-a).cross(c-a).length*.5
def finish(mesh):
    # The bevel clamp can leave zero-area corner triangles where tiny plates
    # meet. They carry no surface, but their invalid UV derivatives reach FBX.
    bm=bmesh.new();bm.from_mesh(mesh)
    microscopic={v for e in bm.edges if e.calc_length()<1.e-5 for v in e.verts}
    if microscopic:bmesh.ops.remove_doubles(bm,verts=list(microscopic),dist=1.e-5)
    collapsed=[f for f in bm.faces if face_area(f)<1.e-14]
    if collapsed:bmesh.ops.delete(bm,geom=collapsed,context='FACES_ONLY')
    bm.normal_update()
    bm.to_mesh(mesh);bm.free()
    mesh.update();uv=mesh.uv_layers.active;changed=0
    for face in mesh.polygons:
        if len(face.loop_indices)!=3:continue
        loops=list(face.loop_indices);a,b,c=[uv.data[i].uv.copy() for i in loops]
        area=abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))
        if area>=1.e-6:continue
        points=[mesh.vertices[mesh.loops[i].vertex_index].co for i in loops]
        tangent=(points[1]-points[0]).normalized();normal=(points[1]-points[0]).cross(points[2]-points[0]).normalized();bitangent=normal.cross(tangent)
        coords=[((p-points[0]).dot(tangent),(p-points[0]).dot(bitangent)) for p in points]
        projected=abs(coords[1][0]*coords[2][1]-coords[1][1]*coords[2][0])
        if projected<1.e-16:raise RuntimeError('Degenerate equipment face '+mesh.name+' '+str(face.index)+' '+str([tuple(p) for p in points])+' normal='+str(tuple(normal))+' coords='+str(coords))
        scale=math.sqrt(1.e-5/projected)
        for li,(x,y) in zip(loops,coords):uv.data[li].uv=(.25+x*scale,.25+y*scale)
        changed+=1
    return changed
