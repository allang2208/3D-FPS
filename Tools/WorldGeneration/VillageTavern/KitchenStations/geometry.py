"""Centimetre-based kitchen joinery. +X is the service face, Z is the floor normal."""
import math
import random
from collections import defaultdict

import bpy
from mathutils import Vector
from mathutils.geometry import normal

X, Y, Z = (Vector(v) for v in ((1,0,0), (0,1,0), (0,0,1)))
BOX = [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]

def game_to_blender(p):
    return (.01*p[0],-.01*p[1],.01*p[2])

class Station:
    def __init__(self,name,seed):
        self.name = 'SM_Tavern'+name
        self.rng = random.Random(seed)
        self.parts = defaultdict(lambda: ([],[],[]))
        self.hulls = []

    def shape(self,verts,faces,surface='Oak',grain=Y,edge=.12,endcaps=True,smooth=False):
        points = [Vector(p) for p in verts]
        positions, polygons, channels = self.parts[edge]
        offset = len(positions)
        positions.extend(game_to_blender(p) for p in points)
        phase = (self.rng.random(),self.rng.random())
        grain = Vector(grain).normalized()
        for index,face in enumerate(faces):
            face = tuple(face)
            ps = [points[q] for q in face]
            n = normal(ps)
            mat = surface if isinstance(surface,str) else surface[index]
            is_end = endcaps and mat in ('Oak','OiledOak','Sawn') and abs(n.dot(grain))>.84
            if is_end:
                mat = 'Endgrain'
            v = grain-n*grain.dot(n)
            if v.length_squared < .02:
                v = Y-n*n.y if abs(n.y)<.95 else Z-n*n.z
            v.normalize()
            u = v.cross(n).normalized()
            scale = {'Endgrain':54,'Cloth':9,'Clay':35,'AshGlaze':35}.get(mat,100)
            uv = [(phase[0]+p.dot(u)/scale,phase[1]+p.dot(v)/scale) for p in ps]
            polygons.append(tuple(offset+i for i in reversed(face)))
            channels.append((mat,uv[::-1],smooth))

    def box(self,center,size,mat='Oak',edge=.23,collision=False,draw=True):
        verts = [(center[0]+x*size[0]/2,center[1]+y*size[1]/2,center[2]+z*size[2]/2)
                 for z in (-1,1) for x,y in ((-1,-1),(1,-1),(1,1),(-1,1))]
        if draw:
            grain = (X,Y,Z)[max(range(3),key=lambda i:size[i])]
            self.shape(verts,BOX,mat,grain,edge)
        if collision:
            self.hulls.append((verts,BOX))

    def beam(self,a,b,w,d,mat='Oak',edge=.17):
        a,b=Vector(a),Vector(b)
        axis=(b-a).normalized()
        u=(Z if abs(axis.z)<.9 else Y).cross(axis).normalized()
        v=axis.cross(u)
        verts=[end+u*i*w/2+v*j*d/2 for end in (a,b) for i,j in ((-1,-1),(1,-1),(1,1),(-1,1))]
        self.shape(verts,BOX,mat,axis,edge)

    def rings(self,rings,surf,grain=Z,edge=0,smooth=True,caps=True):
        n=len(rings[0])
        faces=[tuple(reversed(range(n)))] if caps else []
        for j in range(len(rings)-1):
            for i in range(n):
                nxt=(i+1)%n
                faces.append((j*n+i,j*n+nxt,(j+1)*n+nxt,(j+1)*n+i))
        if caps:
            faces.append(tuple(range((len(rings)-1)*n,len(rings)*n)))
        self.shape([p for ring in rings for p in ring],faces,surf,grain,edge,False,smooth)

    def turned(self,a,b,profile,mat,sides=12):
        a,b=Vector(a),Vector(b)
        axis=(b-a).normalized()
        u=(Z if abs(axis.z)<.9 else Y).cross(axis).normalized()
        v=axis.cross(u)
        rings=[[a.lerp(b,t)+(u*math.cos(i*math.tau/sides)+v*math.sin(i*math.tau/sides))*r
                for i in range(sides)] for t,r in profile]
        self.rings(rings,mat,axis)

    def tube(self,points,r,mat,sides=8):
        pts=list(map(Vector,points))
        axis=(pts[-1]-pts[0]).normalized()
        # Choose an axis perpendicular to the plane of this bent handle.
        reference=(pts[len(pts)//2]-pts[0]).cross(pts[-1]-pts[0])
        if reference.length_squared<.0001:
            reference=axis.cross(Y if abs(axis.y)<.9 else X)
        reference.normalize()
        rings=[]
        for i,p in enumerate(pts):
            tangent=(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized()
            up=tangent.cross(reference).normalized()
            cross=up.cross(tangent).normalized()
            rings.append([p+r*(cross*math.cos(j*math.tau/sides)+up*math.sin(j*math.tau/sides)) for j in range(sides)])
        self.rings(rings,mat,axis)

    def slab(self,poly,z,h,mat,grain=Y,edge=.2):
        if sum(x*v-y*u for (x,y),(u,v) in zip(poly,poly[1:]+poly[:1]))<0:
            poly=poly[::-1]
        self.rings([[(x,y,height) for x,y in poly] for height in (z,z+h)],mat,grain,edge,False)

    def export(self,source,offset):
        bpy.ops.object.select_all(action='DESELECT')
        objs=[]
        for edge,(verts,faces,channels) in self.parts.items():
            data=bpy.data.meshes.new(self.name+' Joinery')
            data.from_pydata(verts,[],faces)
            data.update()
            keys=list(dict.fromkeys(m for m,_,_ in channels))
            for k in keys:
                data.materials.append(bpy.data.materials[k])
            uv=data.uv_layers.new(name='Grain')
            for p,(mat,coords,smooth) in zip(data.polygons,channels):
                p.material_index=keys.index(mat)
                p.use_smooth=smooth
                for j,co in zip(p.loop_indices,coords):
                    uv.data[j].uv=co
            obj=bpy.data.objects.new('Station joinery',data)
            bpy.context.collection.objects.link(obj)
            bpy.context.view_layer.objects.active=obj
            if edge:
                mod=obj.modifiers.new('Worn corners','BEVEL')
                mod.width=edge/100
                mod.segments=2
                mod.limit_method='ANGLE'
                mod.harden_normals=True
                bpy.ops.object.modifier_apply(modifier=mod.name)
                mod=obj.modifiers.new('Planed faces','WEIGHTED_NORMAL')
                mod.keep_sharp=True
                bpy.ops.object.modifier_apply(modifier=mod.name)
            mod=obj.modifiers.new('Triangle export','TRIANGULATE')
            mod.keep_custom_normals=True
            bpy.ops.object.modifier_apply(modifier=mod.name)
            objs.append(obj)
        for obj in objs:
            obj.select_set(True)
        bpy.context.view_layer.objects.active=objs[0]
        bpy.ops.object.join()
        model=objs[0]
        model.name=self.name
        model.data.name=self.name
        hulls=[]
        for i,(points,faces) in enumerate(self.hulls):
            name=f'UCX_{self.name}_{i:02d}'
            mesh=bpy.data.meshes.new(name)
            mesh.from_pydata([game_to_blender(p) for p in points],[],[tuple(reversed(f)) for f in faces])
            mesh.update()
            obj=bpy.data.objects.new(name,mesh)
            bpy.context.collection.objects.link(obj)
            obj.select_set(True)
            hulls.append(obj)
        bpy.ops.export_scene.fbx(filepath=str(source/(self.name+'.fbx')),use_selection=True,
            object_types={'MESH'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',
            use_tspace=True,bake_anim=False,add_leaf_bones=False)
        model.location=offset
        for obj in hulls:
            obj.display_type='WIRE'
            obj.hide_render=True
            obj.hide_set(True)
            obj.location=offset
