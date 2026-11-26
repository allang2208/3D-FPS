"""Bake low frequency scan relief into chapel surfaces, retaining structural openings and joint edges."""
import math
import bpy
import bmesh
import numpy as np
from mathutils import Vector

def clip(poly,axis,limit,sign):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[axis]-limit)*sign;db=(b[axis]-limit)*sign
        if da>=0:result.append(a)
        if (da<0)!=(db<0):
            t=da/(da-db)
            result.append((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t))
    return result

def surface_mesh(original,name,source,wood_directions,yard_offsets):
    result=[];vertices=[];mats=[];smooth=[];coords=[];weld={};heights={}
    slots=list(original.materials)
    def add(points,uv,material,round_face=False):
        indices=[]
        for p in points:
            key=tuple(round(c,6) for c in p)+(material if round_face else -1,)
            if key not in weld:
                weld[key]=len(vertices);vertices.append(tuple(p))
            i=weld[key]
            if not indices or indices[-1]!=i:indices.append(i)
        if len(indices)>2 and indices[-1]==indices[0]:indices.pop()
        if len(indices)!=len(points) or len(set(indices))<3:return
        result.append(indices);coords.append(uv);mats.append(material);smooth.append(round_face)
    def scan(slot,u,v):
        if slot not in heights:
            if slot=='Footing':
                # Blender image pixels start at the bottom. scan() indexes a top-down grid.
                im=bpy.data.images.load(str(source.parent/'Footing/StoneSurface02A_Height.png'))
                im.colorspace_settings.name='Non-Color'
                im.scale(256,256)
                pixels=np.empty(256*256*4,dtype='f4')
                im.pixels.foreach_get(pixels)
                heights[slot]=pixels.reshape(256,256,4)[::-1,:,0].copy()
                bpy.data.images.remove(im)
            else:
                heights[slot]=np.load(source/(slot+'_Relief.npy'))
        grid=heights[slot];n=len(grid)
        p=(u%1)*n-.5;q=((-v)%1)*n-.5
        x=math.floor(p);y=math.floor(q);tx=p-x;ty=q-y
        return ((1-ty)*((1-tx)*grid[y%n,x%n]+tx*grid[y%n,(x+1)%n])+
                ty*((1-tx)*grid[(y+1)%n,x%n]+tx*grid[(y+1)%n,(x+1)%n]))
    def envelope(y,z):
        half=4 if name.endswith('Gable') else 2
        top=4.5
        if name=='EastGable':top=8.5-abs(y)
        if name=='WestGable':top=8.5 if abs(y)<=1.50 else 8.5-abs(y)
        dist=min(half-abs(y),z,top-z)
        # Ease into the trim surrounding the true apertures. Keep the reveals and door sweep untouched.
        if name in ('EastGable','WindowBay','WestGable'):
            rad,sill,spring,peak=(.87,0,2.10,2.96) if name=='WestGable' else ((.34,2.68,4.01,4.57) if name=='EastGable' else (.34,1.44,2.77,3.33))
            arch=spring+(peak-spring)*math.sqrt(max(0,1-abs(y)/rad))
            dist=min(dist,max(abs(y)-rad,sill-z,z-arch))
        if name=='WestGable':dist=min(dist,math.hypot(y,z-5.32)-.34,abs(abs(y)-1.50) if z>6.96 else 99)
        t=max(0,min(1,dist/.11))
        return t*t*(3-2*t)
    for f in original.polygons:
        points=[original.vertices[i].co.copy() for i in f.vertices]
        n=f.normal; mat=f.material_index;slot=slots[mat].name
        wall=name in ('SolidBay','WindowBay','WestGable','EastGable') and abs(n.x)>.999
        floor=name in ('FloorBay','SanctuarySteps') and slot=='Flagstone' and n.z>.999
        axis=max(range(3),key=lambda i:abs(n[i]))
        footing=slot=='Footing' and (n.z>.999 or abs(n[axis])>.999 and axis!=2)
        def planar(p):
            if axis==0:return (p.y,p.z)
            if axis==1:return (p.x,p.z)
            return (p.x,p.y)
        if not wall and not floor and not footing:
            if slot=='Timber':
                axis3=wood_directions.get(f.index)
                if axis3 is None:
                    edges=[b-a for a,b in zip(points,points[1:]+points[:1])]
                    axis3=max(edges,key=lambda e:e.length_squared).normalized()
                along=axis3-n*axis3.dot(n)
                if along.length<.001:along=Vector((0,0,1)) if abs(n.z)<.9 else Vector((1,0,0))
                along.normalize();across=along.cross(n).normalized()
                # The source grain follows the image's vertical direction; single beams only use a narrow strip.
                uv=[(p.dot(across)*.50+.157,p.dot(along)*.50+.213) for p in points]
            elif slot.startswith('Yard'):
                offset=yard_offsets[f.index]
                uv=[(a*1.18+offset[0],b*1.18+offset[1]) for a,b in map(planar,points)]
                add(points,uv,mat,True)
                continue
            elif slot=='Footing':
                uv=[(a/.90+.13,b/.90+.41) for a,b in map(planar,points)]
            elif slot in ('Flagstone','Wall','Limewash'):
                uv=[(a*.5+.173,b*.5+.297) for a,b in map(planar,points)]
            else:uv=[planar(p) for p in points]
            add(points,uv,mat)
            continue
        proj=[planar(p) for p in points];step=.035 if footing else (.065 if wall else .048)
        width=2. if wall else 2.
        def get_uv(a,b):
            return (a/.90+.13,b/.90+.41) if footing else (a/width+.173,b/width+.297)
        if footing:
            edges=[(p,q,math.dist(p,q)) for p,q in zip(proj,proj[1:]+proj[:1]) if math.dist(p,q)>1e-6]
        # Split each existing convex shell face on the same global lattice, including thin arched cutouts.
        for i in range(math.floor(min(x for x,y in proj)/step),math.ceil(max(x for x,y in proj)/step)):
            column=clip(clip(proj,0,i*step,1),0,(i+1)*step,-1)
            if len(column)<3:continue
            for j in range(math.floor(min(y for x,y in column)/step),math.ceil(max(y for x,y in column)/step)):
                cell=clip(clip(column,1,j*step,1),1,(j+1)*step,-1)
                clean=[]
                for pt in cell:
                    if not clean or math.dist(clean[-1],pt)>1e-6:clean.append(pt)
                if len(clean)>2 and math.dist(clean[0],clean[-1])<1e-6:clean.pop()
                if len(clean)<3:continue
                if abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(clean,clean[1:]+clean[:1])))<1e-10:continue
                pos=[];uv=[]
                for a,b in clean:
                    u,v=get_uv(a,b);h=scan(slot,u,v);uv.append((u,v))
                    if footing:
                        edge=min(abs((a-p[0])*(q[1]-p[1])-(b-p[1])*(q[0]-p[0]))/length for p,q,length in edges)
                        delta=max(-.010,min(.009,(h-.69)*.064))*min(1.,edge/.035)
                        xyz=list((points[0].x,a,b) if axis==0 else ((a,points[0].y,b) if axis==1 else (a,b,points[0].z)))
                        xyz[axis]+=n[axis]*delta
                        pos.append(xyz)
                    elif wall:
                        # Broad fieldstone crowns stand proud; the old render retains a shallower profile.
                        relief=(h-.37)*(.047 if slot=='Wall' else .027)*envelope(a,b)
                        pos.append((points[0].x+n.x*relief,a,b))
                    else:
                        edge=min(1-abs(a),1-abs(b))
                        if name=='SanctuarySteps':
                            left,right=(.008,.44) if points[0].z<.15 else (.448,4.)
                            edge=min(a-left,right-a,3.5-abs(b))
                        feather=min(1,max(0,edge/.065))
                        pos.append((a,b,points[0].z+(h-.72)*.008*feather))
                add(pos,uv,mat,True)
    mesh=bpy.data.meshes.new(name+'_Relief');mesh.from_pydata(vertices,[],result);mesh.update()
    for slot in slots:mesh.materials.append(slot)
    layer=mesh.uv_layers.new(name='SurfaceMetres')
    for f,uv,m,sh in zip(mesh.polygons,coords,mats,smooth):
        f.material_index=m
        f.use_smooth=sh
        for loop,xy in zip(f.loop_indices,uv):layer.data[loop].uv=xy
    # FBX cannot export a tangent basis for any face of a mesh containing n-gons.
    bm=bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='EAR_CLIP')
    if name.startswith('Yard'):
        bm.normal_update()
        for edge in bm.edges:
            if edge.is_manifold and edge.calc_face_angle()>.68:
                edge.smooth=False
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    if name=='Foundation' or name.startswith('Yard'):
        band=mesh.uv_layers.new(name='SoilContact',do_init=False)
        for loop in mesh.loops:
            # The shader reads only U. FBX is free to flip V.
            ground_offset=.34 if name=='Foundation' else 0.
            band.data[loop.index].uv=(mesh.vertices[loop.vertex_index].co.z+ground_offset,0.)
    return mesh

