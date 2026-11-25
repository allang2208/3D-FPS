"""Centimetre-scale grain measure, winnowed wheat and wheelwright's hand tools."""
import math
import os
import random
from pathlib import Path

import bpy
from mathutils import Vector

out = Path(os.environ['WINDMILL_DETAIL_SOURCE'])
out.mkdir(parents=True, exist_ok=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = .01


def mesh(name, verts, faces, slot):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    ob = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(ob)
    data.materials.append(bpy.data.materials.get(slot) or bpy.data.materials.new(slot))
    uv = data.uv_layers.new()
    for face in data.polygons:
        for i in face.loop_indices:
            v = data.vertices[data.loops[i].vertex_index].co
            axis = max(range(3), key=lambda a: abs(face.normal[a]))
            u, w = ((v.y,v.z),(v.x,v.z),(v.x,v.y))[axis]
            uv.data[i].uv = (u/54+.38,w/54+.27)
    return ob


def save(name):
    bpy.ops.object.select_all(action='SELECT')
    bpy.context.view_layer.objects.active = next(iter(bpy.context.scene.objects))
    if len(bpy.context.selected_objects)>1:
        bpy.ops.object.join()
    bpy.ops.export_scene.fbx(filepath=str(out/('SM_Mill'+name+'.fbx')), use_selection=True,
        axis_forward='Y', axis_up='Z', apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
        mesh_smooth_type='FACE', use_tspace=True, bake_anim=False, path_mode='STRIP')


def section(name, profile, start, end, steps, material, cap=False):
    verts,faces=[],[]
    for i in range(steps+1):
        a=start+(end-start)*i/steps
        for radius,z in profile:
            verts.append((radius*math.cos(a),radius*math.sin(a),z))
    count=len(profile)
    for i in range(steps):
        for j in range(count):
            q=i*count+j
            k=i*count+(j+1)%count
            faces.append((q,q+count,k+count,k))
    if cap:
        faces.extend((tuple(range(count)),tuple(reversed(range(steps*count,(steps+1)*count)))))
    return mesh(name,verts,faces,material)


def measure():
    reset()
    sides=18
    for i in range(sides):
        a=math.tau*i/sides
        height=24.5+.23*math.sin(i*3.1)
        section('Split oak stave',[(10.8,.3),(13.15,height-.23),(12.95,height),
            (11.95,height),(11.78,height-.25),(9.72,1.8)],a+.002,a+math.tau/sides-.002,2,'Oak',True)
    section('Recessed oak bottom',[(.01,0),(10.8,0),(10.85,2.1),(.01,2.1)],0,math.tau,36,'End')
    for z in (3.4,19.6):
        radius=10.8+2.35*z/24.5
        section('Hoop',[(radius-.09,z),(radius+.18,z),(radius+.35,z+1.52),
                 (radius+.09,z+1.52)],0,math.tau,48,'Iron')
    save('Measure')


def grain():
    reset()
    rng=random.Random(671)
    verts,faces,colors=[],[],[]
    for _ in range(1470):
        a=rng.random()*math.tau
        r=math.sqrt(rng.random())
        x=10.1*r*math.cos(a)
        y=8.7*r*math.sin(a)
        z=.19+.94*(1-r*r)+rng.uniform(-.18,.19)
        angle=rng.uniform(0,math.tau)
        along=Vector((math.cos(angle),math.sin(angle),rng.uniform(-.15,.15)))*rng.uniform(.29,.41)
        side=Vector((-math.sin(angle),math.cos(angle),0))*rng.uniform(.125,.16)
        off=len(verts)
        center=Vector((x,y,z))
        for u,v,w in [(-1,0,0),(-.53,1,.17),(.62,.86,.21),(1,0,0),(.53,-.88,.2),
                      (-.57,-1,.16),(-.57,0,.41),(.52,0,.46),(0,0,-.21)]:
            verts.append(center+along*u+side*v+Vector((0,0,w*.43)))
        for face in [(0,1,6),(1,2,7,6),(2,3,7),(3,4,7),(4,5,6,7),(5,0,6),(0,8,1),(1,8,2),
                     (2,8,3),(3,8,4),(4,8,5),(5,8,0)]:
            faces.append(tuple(off+j for j in reversed(face)))
        tint=rng.uniform(.74,1.19)
        colors.extend([(min(.72,.50*tint),.30*tint,.10*tint,1)]*9)
    ob=mesh('Winnowed wheat',verts,faces,'Grain')
    colorset=ob.data.color_attributes.new('Kernel colour','BYTE_COLOR','CORNER')
    for loop in ob.data.loops:
        colorset.data[loop.index].color=colors[loop.vertex_index]
    save('Grain')


def rod(name, a, b, r1, r2, mat, n=12):
    a,b=Vector(a),Vector(b)
    axis=(b-a).normalized()
    ref=Vector((0,0,1)) if abs(axis.z)<.9 else Vector((1,0,0))
    u=axis.cross(ref).normalized()
    v=axis.cross(u)
    verts=[p+(u*math.cos(t*math.tau/n)+v*math.sin(t*math.tau/n))*radius
           for p,radius in [(a,r1),(b,r2)] for t in range(n)]
    faces=[(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)]
    faces.extend((tuple(reversed(range(n))),tuple(range(n,n*2))))
    mesh(name,verts,faces,mat)


def stone_tools():
    reset()
    rod('Turned mallet handle',(-13,-4,2.2),(7,-2,3.6),1.55,1.05,'Oak')
    rod('Octagonal mallet head',(7,-8,4),(7,4,4),3.8,3.65,'End',8)
    rod('Stone dressing chisel',(-9,7,1.15),(6,7,1.15),1.06,.78,'Iron',8)
    rod('Cutting edge',(6,7,1.15),(9,7,.55),.78,.24,'Iron',6)
    save('StoneTools')


if __name__=='__main__':
    measure()
    grain()
    stone_tools()
