def clip(poly,axis,limit,positive):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[0][axis]-limit)*(1 if positive else -1);db=(b[0][axis]-limit)*(1 if positive else -1)
        if da>=0:result.append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db);result.append(tuple(x.lerp(y,t) for x,y in zip(a,b)))
    return result

def retain_interfaces(factory,left,right,bottom):
    original=factory.data;original.calc_loop_triangles();normals=[n.vector.copy() for n in original.corner_normals]
    verts=[];faces=[];corners=[]
    # Retain real side contact cheeks and lower joining collar; interpolated UV
    # and split normals remain intact at the author cuts.
    planes=[(0,left+.0027,True),(0,right-.0027,False),(2,bottom+.008,True)]
    for tri in original.loop_triangles:
        remaining=[(original.vertices[original.loops[i].vertex_index].co.copy(),original.uv_layers[0].data[i].uv.copy(),normals[i]) for i in tri.loops]
        pieces=[]
        for axis,limit,inside in planes:
            outside=clip(remaining,axis,limit,not inside)
            if outside:pieces.append(outside)
            remaining=clip(remaining,axis,limit,inside)
            if not remaining:break
        for poly in pieces:
            for i in range(1,len(poly)-1):
                triangle=(poly[0],poly[i],poly[i+1])
                if (triangle[1][0]-triangle[0][0]).cross(triangle[2][0]-triangle[0][0]).length<1e-12:continue
                faces.append(tuple(range(len(verts),len(verts)+3)))
                for item in triangle:verts.append(item[0]);corners.append(item)
    mesh=bpy.data.meshes.new('Retained native mounting surfaces');mesh.from_pydata(verts,[],faces);mesh.update();mesh.materials.append(bronze)
    uv=mesh.uv_layers.new(name='UVMap');stored=mesh.attributes.new('PreservedNormal',type='FLOAT_VECTOR',domain='CORNER')
    for poly in mesh.polygons:
        poly.use_smooth=True
        for index in poly.loop_indices:
            co,tex,n=corners[mesh.loops[index].vertex_index];uv.data[index].uv=tex;stored.data[index].vector=n.normalized()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    new=bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)['faces'];bm.normal_update()
    uv=bm.loops.layers.uv['UVMap'];nlayer=bm.loops.layers.float_vector['PreservedNormal']
    for face in new:
        face.smooth=False
        axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(face.normal[i]))]
        for loop in face.loops:loop[uv].uv=(loop.vert.co[axes[0]]/.12,loop.vert.co[axes[1]]/.12);loop[nlayer]=face.normal
    bmesh.ops.triangulate(bm,faces=new);bm.to_mesh(mesh);bm.free();mesh.update()
    mesh.normals_split_custom_set([tuple(n.vector) for n in mesh.attributes['PreservedNormal'].data])
    obj=bpy.data.objects.new('Preserved_original_interface',mesh);m.BUILD.objects.link(obj);m.PARTS.append(obj)
    return obj
