"""Build three wraps inside the retained grip envelope, with editable sources.

Blender coordinates match the V13 source in centimetres. FBX converts the same
axes as the shipped parts. No arm pose, world fixture or camera is modified.
"""
from pathlib import Path
import bpy,bmesh,json,math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P=Path(__file__).parent
OUT=P/'Export';OUT.mkdir(exist_ok=True)
rows=json.loads((P/'series.json').read_text(encoding='utf8'))['variants']
SOURCE=P.parent/'BowModular20260926/Bow_ModularParts.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
grip=bpy.data.objects['SM_Bow_GripWrap']
body=bpy.data.objects['SM_Bow_BodyModular']

def bvh(o):
    vs=[o.matrix_world@v.co for v in o.data.vertices]
    return vs,BVHTree.FromPolygons(vs,[list(p.vertices) for p in o.data.polygons])

gv,gt=bvh(grip)
bv,bt=bvh(body)
Z0=min(v.z for v in gv)+.025
Z1=max(v.z for v in gv)-.025
NX,NZ=64,113
C=Vector((-.7,0,0))

def radius_at(tree,a,z):
    radial=Vector((math.cos(a),math.sin(a),0))
    center=Vector((C.x,C.y,z))
    hit,_,_,_=tree.ray_cast(center+radial*12,-radial,24)
    return (hit-center).dot(radial) if hit is not None else None

# The original wrap is a set of round cords. Sample neighbouring heights to
# derive its outer contact envelope instead of swelling the existing hand fit.
envelope=np.zeros((NZ,NX))
wood=np.zeros((NZ,NX))
for iz in range(NZ):
    z=Z0+(Z1-Z0)*iz/(NZ-1)
    for j in range(NX):
        a=math.tau*j/NX
        rb=radius_at(bt,a,z)
        if rb is None:raise RuntimeError('Wood contact surface missing '+str((a,z)))
        samples=[radius_at(gt,a,min(Z1,max(Z0,z+dz))) for dz in (0,-.08,.08,-.17,.17,-.28,.28)]
        samples=[r for r in samples if r is not None and r>rb]
        wood[iz,j]=rb
        envelope[iz,j]=max(samples) if samples else rb+.12
for _ in range(2):
    padded=np.pad(envelope,((1,1),(0,0)),mode='edge')
    envelope=(padded[:-2]+2*padded[1:-1]+padded[2:])/4
    envelope=(np.roll(envelope,1,1)+2*envelope+np.roll(envelope,-1,1))/4
envelope=np.maximum(wood+.07,envelope-.025)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01

def sampled(a,t,which=envelope):
    fz=max(0,min(1,t))*(NZ-1);iz=min(NZ-2,int(fz));fz-=iz
    fa=(a/math.tau%1)*NX;j=int(fa)%NX;fa-=int(fa)
    return float((which[iz,j]*(1-fa)+which[iz,(j+1)%NX]*fa)*(1-fz)+
                 (which[iz+1,j]*(1-fa)+which[iz+1,(j+1)%NX]*fa)*fz)

def point(a,t,offset=0):
    r=sampled(a,t)+offset
    return Vector((C.x+math.cos(a)*r,C.y+math.sin(a)*r,Z0+(Z1-Z0)*t))

def create_material(row):
    m=bpy.data.materials.new(row['material']);m.use_nodes=True
    n=m.node_tree.nodes;links=m.node_tree.links
    p=next(a for a in n if a.type=='BSDF_PRINCIPLED')
    for kind in ('BaseColor','ORM','Normal'):
        tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(P/'Textures'/('T_Bow_Grip_'+row['name']+'_'+kind+'.png')))
        if kind=='BaseColor':links.new(tex.outputs['Color'],p.inputs['Base Color'])
        else:
            tex.image.colorspace_settings.name='Non-Color'
            if kind=='Normal':
                normal=n.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.7
                links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],p.inputs['Normal'])
            else:
                sep=n.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],sep.inputs['Color'])
                links.new(sep.outputs['Green'],p.inputs['Roughness'])
    m.diffuse_color=(*row['color'],1)
    return m

thread=bpy.data.materials.new('M_Bow_Grip_Stitch');thread.use_nodes=True
bsdf=next(n for n in thread.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
bsdf.inputs['Base Color'].default_value=(.23,.155,.085,1)
bsdf.inputs['Roughness'].default_value=.86
thread.diffuse_color=(.23,.155,.085,1)

def mesh(name,verts,faces,uvfaces,mat):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    uv=data.uv_layers.new(name='UVMap')
    for p,coords in zip(data.polygons,uvfaces):
        p.use_smooth=True
        for l,c in zip(p.loop_indices,coords):uv.data[l].uv=c
    bm=bmesh.new();bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    data.materials.append(mat)
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    return obj

def tube(name,path,radius,mat):
    vv,ff,uv=[],[],[];sides=6
    for i,p in enumerate(path):
        d=(path[min(i+1,len(path)-1)]-path[max(0,i-1)]).normalized()
        across=d.cross(Vector((0,0,1))).normalized()
        if across.length<.1:across=Vector((1,0,0))
        side=d.cross(across).normalized()
        for j in range(sides):vv.append(p+radius*(across*math.cos(j*math.tau/sides)+side*math.sin(j*math.tau/sides)))
    for i in range(len(path)-1):
        for j in range(sides):
            k=(j+1)%sides;ff.append((i*sides+j,i*sides+k,(i+1)*sides+k,(i+1)*sides+j))
            uv.append(((j/sides,i/len(path)),((j+1)/sides,i/len(path)),((j+1)/sides,(i+1)/len(path)),(j/sides,(i+1)/len(path))))
    for index in (0,len(path)-1):
        ff.append(tuple(index*sides+j for j in range(sides)))
        uv.append(tuple((.5+.4*math.cos(j*math.tau/sides),.5+.4*math.sin(j*math.tau/sides)) for j in range(sides)))
    return mesh(name,vv,ff,uv,mat)

construction=bpy.data.collections.new('EDITABLE_WRAP_COMPONENTS')
scene.collection.children.link(construction)
records=[]
for row in rows:
    mat=create_material(row)
    vv,ff,uv=[],[],[]
    for inner in (False,True):
        for iz in range(NZ):
            t=iz/(NZ-1)
            for j in range(NX):
                a=math.tau*j/NX
                if inner:r=sampled(a,t,wood)+.01
                else:
                    relief=0
                    if row['name']=='WovenLinen':relief=.014*(1-math.cos(a*12+t*math.tau*27)*math.cos(a*12-t*math.tau*27))
                    elif row['name']=='SlimLeather':
                        phase=(t*8-a/math.tau)%1
                        relief=.045*(1-math.exp(-(min(phase,1-phase)/.06)**2))
                    else:
                        d=abs(a/math.tau-.25)
                        relief=.028*math.exp(-(d/.013)**2)
                    edge=min(t,1-t)
                    edge_taper=.055*max(0,1-edge/.035)
                    r=max(sampled(a,t,wood)+.025,sampled(a,t)-relief-edge_taper)
                vv.append((C.x+r*math.cos(a),C.y+r*math.sin(a),Z0+(Z1-Z0)*t))
    layer=NZ*NX
    for offset in (0,layer):
        for iz in range(NZ-1):
            for j in range(NX):
                k=(j+1)%NX
                ff.append((offset+iz*NX+j,offset+iz*NX+k,offset+(iz+1)*NX+k,offset+(iz+1)*NX+j))
                uv.append(((j/NX,iz/(NZ-1)),((j+1)/NX,iz/(NZ-1)),((j+1)/NX,(iz+1)/(NZ-1)),(j/NX,(iz+1)/(NZ-1))))
    for iz in (0,NZ-1):
        for j in range(NX):
            a=iz*NX+j;b=iz*NX+(j+1)%NX
            ff.append((a,b,b+layer,a+layer))
            uv.append(((j/NX,iz/(NZ-1)),((j+1)/NX,iz/(NZ-1)),((j+1)/NX,.02+iz/(NZ-1)),(j/NX,.02+iz/(NZ-1))))
    shell=mesh(row['mesh'],vv,ff,uv,mat);parts=[shell]
    if row['name']=='WovenLinen':
        for t in (.018,.982):
            for strand in (0,1):
                path=[]
                for j in range(193):
                    a=j*math.tau/192
                    tt=t+.002*math.sin(a*20+strand*math.pi)
                    path.append(point(a,tt,-.034+.009*math.cos(a*20+strand*math.pi)))
                parts.append(tube('Braided_edge_'+str(t)+'_'+str(strand),path,.026,mat))
    if row['name']=='PaddedLeather':
        # Real short saddler's stitches, recessed into the retained envelope.
        for i in range(34):
            t=.06+.88*i/34
            a0=math.pi/2-.052;a1=math.pi/2+.052
            path=[point(a0+(a1-a0)*f,t+.006*f,-.023) for f in (0,.25,.5,.75,1)]
            parts.append(tube('Linen_saddle_stitch_'+str(i),path,.021,thread))
        for t in (.025,.975):
            parts.append(tube('Rolled_leather_edge_'+str(t),[point(j*math.tau/128,t,-.061) for j in range(129)],.055,mat))
    for part in parts:
        copy=part.copy();copy.data=part.data.copy();construction.objects.link(copy)
        copy.name='SOURCE_'+row['name']+'_'+part.name;copy.hide_render=True;copy.hide_set(True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=shell;bpy.ops.object.join()
    obj=bpy.context.object;obj.name=row['mesh']
    scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    mod=obj.modifiers.new('Final_triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,use_tspace=True,mesh_smooth_type='FACE')
    records.append({**row,'triangles':len(obj.data.polygons),'material_slots':[m.name for m in obj.data.materials]})
construction.hide_render=True
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_GripSeries.blend'))
(P/'authoring.json').write_text(json.dumps({'assets':records,'source':str(SOURCE),
    'grip_z_cm':[Z0,Z1],'fit':'radial contact envelope from retained wrap; recessed details; fixed origin and axes',
    'gameplay_tested':False},ensure_ascii=False,indent=2),encoding='utf8')
print('BOW_GRIP_SERIES_AUTHORED',[(r['name'],r['triangles']) for r in records])
