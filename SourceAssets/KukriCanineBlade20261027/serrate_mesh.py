"""Locally split the existing blade at tooth stations, keeping its mount/UVs."""
import bpy, math, bisect
from mathutils import Vector, Matrix

START=.086
PITCH=.012
TEETH=12
DEPTH=.0038
END=START+PITCH*TEETH

def serrate(blade):
    source=blade.data
    source.calc_loop_triangles()
    names=list(source.color_attributes.keys())
    corners=[]
    for i,loop in enumerate(source.loops):
        corners.append((source.vertices[loop.vertex_index].co.copy(),source.uv_layers.active.data[i].uv.copy(),
                        Vector(source.corner_normals[i].vector),
                        [Vector(source.color_attributes[name].data[i].color) for name in names]))
    stations=sorted(set(START+PITCH*(tooth+part) for tooth in range(TEETH) for part in (0,.45,.60,1)))
    field_index=names.index('SurfaceField')
    def lerp(a,b,t):
        return (a[0].lerp(b[0],t),a[1].lerp(b[1],t),a[2].lerp(b[2],t).normalized(),
                [x.lerp(y,t) for x,y in zip(a[3],b[3])])
    def half(poly,z,above):
        result=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            da=a[0].z-z;db=b[0].z-z
            ina=da>=-1e-10 if above else da<=1e-10
            inb=db>=-1e-10 if above else db<=1e-10
            if ina:result.append(a)
            if ina!=inb and abs(da-db)>1e-12:result.append(lerp(a,b,da/(da-db)))
        return result
    def tooth_depth(z):
        if z<=START or z>=END:return 0.
        phase=(z-START)/PITCH%1.
        if phase<.45:return DEPTH*phase/.45
        if phase<.60:return DEPTH*(1-.05*(phase-.45)/.15)
        return DEPTH*.95*(1-phase)/.40
    def deform(c):
        p=c[0].copy();q=c[3][field_index][3]
        t=max(0,min(1,(q-.52)/.43))
        p.x-=tooth_depth(p.z)*t*t*(3-2*t)
        return p
    vertices=[];faces=[];data=[];lookup={}
    def vertex(p):
        key=tuple(round(v,11) for v in p)
        if key not in lookup:lookup[key]=len(vertices);vertices.append(p)
        return lookup[key]
    for triangle in source.loop_triangles:
        pieces=[[corners[i] for i in triangle.loops]]
        lo=min(c[0].z for c in pieces[0]);hi=max(c[0].z for c in pieces[0])
        for station in stations[bisect.bisect_right(stations,lo+1e-10):bisect.bisect_left(stations,hi-1e-10)]:
            split=[]
            for poly in pieces:
                if min(c[0].z for c in poly)<station-1e-10 and max(c[0].z for c in poly)>station+1e-10:
                    split.extend([half(poly,station,False),half(poly,station,True)])
                else:split.append(poly)
            pieces=split
        for poly in pieces:
            for i in range(1,len(poly)-1):
                tri=[poly[0],poly[i],poly[i+1]];new=[deform(c) for c in tri]
                if (new[1]-new[0]).cross(new[2]-new[0]).length_squared<1e-22:continue
                old_a,old_b=tri[1][0]-tri[0][0],tri[2][0]-tri[0][0]
                new_a,new_b=new[1]-new[0],new[2]-new[0]
                old_basis=Matrix((old_a,old_b,old_a.cross(old_b).normalized())).transposed()
                new_basis=Matrix((new_a,new_b,new_a.cross(new_b).normalized())).transposed()
                normal_matrix=(new_basis@old_basis.inverted_safe()).inverted_safe().transposed()
                faces.append(tuple(vertex(p) for p in new))
                data.extend((c[1],(normal_matrix@c[2]).normalized(),c[3]) for c in tri)
    mesh=bpy.data.meshes.new('SM_Kukri_Blade_Canine');mesh.from_pydata(vertices,[],faces);mesh.update()
    uv=mesh.uv_layers.new(name=source.uv_layers.active.name)
    attrs=[mesh.color_attributes.new(name=name,type='FLOAT_COLOR',domain='CORNER') for name in names]
    for i,(coords,normal,colors) in enumerate(data):
        uv.data[i].uv=coords
        for attr,color in zip(attrs,colors):attr.data[i].color=color
    for poly in mesh.polygons:poly.use_smooth=True
    mesh.normals_split_custom_set([c[1] for c in data])
    blade.data=mesh
    return {'teeth':TEETH,'depth_cm':DEPTH*100,'pitch_cm':PITCH*100,
            'start_cm':START*100,'end_cm':END*100,'vertices':len(vertices),'triangles':len(faces)}
