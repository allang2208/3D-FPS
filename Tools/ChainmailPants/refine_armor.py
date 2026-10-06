"""Blender production: traced shield knees and overlapping curved waist plates.

Preserve existing cloth, hems and native skinning verbatim. Author only armor
and its fasteners, with closed thickness, applied bevels and split normals.
"""
import json
import math
import shutil
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Vector

P=Path('D:/FPS3D/FPSGAME');OLD=P/'SourceAssets/ChainmailPants20261004';R=OLD/'ArmorRefineV2'
R.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
reference=json.loads((OLD/'Jason_ChainmailPants.json').read_text())
bones={b['name']:b['index'] for b in reference['bones']}
objects=[]

def unit(v):
    a=np.array(v,float);return a/max(float(np.linalg.norm(a)),1e-10)

def torso(z,theta,offset=0.):
    rx=np.interp(z,[80,85,90,95,100.2],[18.3,18.7,18.3,17.7,17.1])+offset
    ry=np.interp(z,[80,85,90,95,100.2],[13.8,14.4,14.2,13.7,12.7])+offset
    return np.array([rx*math.sin(theta),.8+ry*math.cos(theta),z])

def spline(points,steps=7):
    """Centripetal-style closed contour with restrained tangent lengths."""
    p=np.array(points,float);out=[]
    for i in range(len(p)):
        a,b,c,d=p[(i-1)%len(p)],p[i],p[(i+1)%len(p)],p[(i+2)%len(p)]
        m0=(c-a)*.42;m1=(d-b)*.42
        for t in np.linspace(0,1,steps,endpoint=False):
            out.append((2*t**3-3*t*t+1)*b+(t**3-2*t*t+t)*m0+(-2*t**3+3*t*t)*c+(t**3-t*t)*m1)
    return np.array(out)

def rounded_polygon(points,radius=.4,steps=4):
    p=np.array(points,float);out=[]
    for i,b in enumerate(p):
        before=p[(i-1)%len(p)];after=p[(i+1)%len(p)]
        cut=min(radius,np.linalg.norm(before-b)*.2,np.linalg.norm(after-b)*.2)
        a=b+unit(before-b)*cut;c=b+unit(after-b)*cut
        for t in np.linspace(0,1,steps,endpoint=False):out.append((1-t)**2*a+2*(1-t)*t*b+t*t*c)
        next_b=after;next_after=p[(i+2)%len(p)]
        next_cut=min(radius,np.linalg.norm(b-next_b)*.2,np.linalg.norm(next_after-next_b)*.2)
        end=next_b+unit(b-next_b)*next_cut
        intervals=max(2,int(np.linalg.norm(end-c)/1.1))
        out.extend(c*(1-t)+end*t for t in np.linspace(0,1,intervals,endpoint=False))
    return np.array(out)

def mesh_object(name,points,faces,binding,material=1):
    mesh=bpy.data.meshes.new(name)
    # UE +Y front becomes Blender -Y; reverse mathematical winding on reflection.
    mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in points],[],[list(reversed(f)) for f in faces]);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    obj['binding']=json.dumps(binding);obj['material_slot']=material
    objects.append(obj);return obj

def finish(obj,bevel=.06,thickness=0.):
    bpy.context.view_layer.objects.active=obj
    if thickness:
        solid=obj.modifiers.new('Forged wall - cm','SOLIDIFY');solid.thickness=thickness*.01;solid.offset=-1;solid.use_even_offset=True
        bpy.ops.object.modifier_apply(modifier=solid.name)
    if bevel:
        mod=obj.modifiers.new('Continuous rounded edge','BEVEL');mod.width=bevel*.01;mod.segments=3
        mod.limit_method='ANGLE';mod.angle_limit=.45;mod.harden_normals=True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    mesh=obj.data
    # Applied bevels on closely spaced contour corners can collapse tiny faces.
    # Clean those construction remnants before authoring normals and UVs.
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-8)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(mesh);bm.free()
    for poly in mesh.polygons:poly.use_smooth=True
    mesh.set_sharp_from_angle(angle=math.radians(55))
    # Physical UVs on each locally dominant plane; tiny return walls get their
    # own valid coordinates instead of zero-area inherited edge UVs.
    uv=mesh.uv_layers.new(name='Physical25cm')
    for poly in mesh.polygons:
        normal=poly.normal;axis=max(range(3),key=lambda i:abs(normal[i]))
        plane=[i for i in range(3) if i!=axis]
        for li in poly.loop_indices:
            co=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=(co[plane[0]]/.25,co[plane[1]]/.25)
    mesh.update();obj.select_set(False)

def plate(name,outline,project,binding,thickness=.19,bevel=.07,center=None):
    outline=np.array(outline);center=np.mean(outline,axis=0) if center is None else np.array(center,float)
    n=len(outline);vertices=[project(*center,0.)];faces=[]
    # Density follows curved silhouette and bevels; small flat keepers do not
    # need the same interior ring count as the shaped knee shield.
    radii=([.12,.27,.45,.63,.79,.90,.96,1.] if 'TracedShield' in name else
           [.3,.65,1.] if np.ptp(outline,axis=0).max()<4 else [.2,.42,.65,.84,1.])
    for rho in radii:
        vertices.extend(project(*(center+(p-center)*rho),rho) for p in outline)
    for i in range(n):faces.append([0,1+i,1+(i+1)%n])
    for ring in range(len(radii)-1):
        for i in range(n):
            a=1+ring*n+i;b=1+ring*n+(i+1)%n;faces.append([a,b,b+n,a+n])
    obj=mesh_object(name,vertices,faces,binding)
    # Open patches must face outside before Solidify. The generated front points
    # define this directly; do not let a volume heuristic flip separate plates.
    n0=np.array(obj.data.polygons[0].normal);c=np.array(obj.data.polygons[0].center)
    if n0[:2]@c[:2]<0:
        bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    finish(obj,bevel,thickness);return obj

def fastener(name,center,normal,binding,radius=.235):
    normal=unit(normal);a=unit(np.cross(normal,[0,0,1] if abs(normal[2])<.9 else [1,0,0]));b=np.cross(normal,a)
    profile=[(0.,.155),(.35,.15),(.68,.125),(.90,.075),(1.,.018),(1.24,.004),(1.28,-.055),(.9,-.085),(0.,-.09)]
    vertices=[np.array(center)+normal*profile[0][1]];sides=20;faces=[]
    for r,h in profile[1:-1]:
        vertices.extend(np.array(center)+normal*h+radius*r*(math.cos(t)*a+math.sin(t)*b) for t in np.linspace(0,2*np.pi,sides,endpoint=False))
    for i in range(sides):faces.append([0,1+i,1+(i+1)%sides])
    for j in range(len(profile)-3):
        for i in range(sides):
            x=1+j*sides+i;y=1+j*sides+(i+1)%sides;faces.append([x,y,y+sides,x+sides])
    last=len(vertices);vertices.append(np.array(center)+normal*profile[-1][1]);base=1+(len(profile)-3)*sides
    for i in range(sides):faces.append([base+i,last,base+(i+1)%sides])
    ob=mesh_object(name,vertices,faces,binding);finish(ob,.015)

def waist():
    binding={'pelvis':1.}
    for number,(a,b) in enumerate([(.016,1.58),(1.60,math.pi-.018),(math.pi+.018,4.69),(4.71,2*math.pi-.016)]):
        mid=(a+b)/2;half=(b-a)*9
        contour=rounded_polygon([[-half,0],[half,0],[half,8.8],[-half,8.8]],.5)
        def project(u,v,rho,mid=mid):
            angle=mid+u/18;z=91.65+v-.3*math.cos(angle)
            return torso(z,angle,.65+.04*(1-rho*rho))
        plate('Waist_MainCurved_%02d'%number,contour,project,binding,thickness=.22,bevel=.08)
        band=rounded_polygon([[-half,0],[half,0],[half,2.25],[-half,2.25]],.32)
        plate('Waist_LowerBand_%02d'%number,band,lambda u,v,r,mid=mid:torso(91.6+v-.3*math.cos(mid+u/18),mid+u/18,.93),binding,thickness=.14,bevel=.055)
        for angle in np.linspace(a+.22,b-.22,3):
            for z in [92.75,97.2]:
                offset=1.10 if z<94 else .88;point=torso(z-.3*math.cos(angle),angle,offset)
                fastener('Waist_Rivet_%s_%s_%s'%(number,angle,z),point,[math.sin(angle),math.cos(angle),0],binding)
    # The reference has two overlapping columns on each hip. Their front edges
    # reach onto the front thigh, rather than reading as narrow side-only tabs.
    for sign,side in [(1,'l'),(-1,'r')]:
        for column,(angle0,angle1) in enumerate([(.26,1.06),(.98,1.93)]):
            width=(angle1-angle0)*18
            for row in range(3):
                top=93.1-row*3.6+column*.15
                contour=rounded_polygon([[0,0],[width,0],[width-.45,-4.75-row*.15],[1.15,-3.65-row*.2]],.46)
                binding={'pelvis':1.-row*.11,'thigh_'+side:row*.11}
                def project(u,v,rho,top=top,row=row,column=column):
                    angle=sign*(angle0+u/18)
                    return torso(top+v,angle,1.02+row*.30+column*.13+.065*(1-rho*rho))
                plate('Hip_'+side+'_Column%d_Lame%d'%(column,row),contour,project,binding,thickness=.18,bevel=.08)
                for u in [1.9,width-1.65]:
                    point=project(u,-.9,0);angle=sign*(angle0+u/18);normal=[math.sin(angle),math.cos(angle),0]
                    fastener('Hip_'+side+'_Rivet_%d_%d_%s'%(column,row,u),point+unit(normal)*.13,normal,binding,.23)
    binding={'pelvis':1.}
    # Paired broad keeper plates and center latch match the flat front clasp.
    for index,cx in enumerate([-2.15,2.15]):
        contour=rounded_polygon([[-.85,-2.9],[.85,-2.9],[.85,2.9],[-.85,2.9]],.45)
        def project(u,v,rho,cx=cx):
            angle=math.asin((u+cx)/18.5);return torso(96+v,angle,1.19)
        plate('Waist_ClaspKeeper_'+str(index),contour,project,binding,thickness=.18,bevel=.07)
        for z in [93.95,98.05]:fastener('Waist_ClaspRivet_%s_%s'%(index,z),project(0,z-96,0)+[0,.13,0],[0,1,0],binding,.22)
    contour=rounded_polygon([[-1.05,-1.05],[1.05,-1.05],[1.05,1.05],[-1.05,1.05]],.22)
    plate('Waist_CenterLatch',contour,lambda x,z,r:torso(96+z,math.asin(x/18.5),1.08),binding,.2,.06)

def knees():
    # Explicit traced, rounded shield. High shoulders and tapered lower point
    # replace the circular polar cup from V1.
    trace=[[0,6.45],[2.7,5.65],[5.55,3.5],[6.85,1.15],[6.45,-1.75],[4.6,-4.0],[2.15,-5.35],[0,-5.85],[-2.15,-5.35],[-4.6,-4.0],[-6.45,-1.75],[-6.85,1.15],[-5.55,3.5],[-2.7,5.65]]
    for sign,side in [(1,'l'),(-1,'r')]:
        cx=sign*12.04;cz=47.35;bind={'thigh_'+side:.45,'calf_'+side:.55}
        def wrap(x,z,extra=0.):
            front=.85+9.55*math.sqrt(max(.1,1-(x/8.2)**2))
            return np.array([cx+x,front+extra,cz+z])
        contour=spline(trace,6)
        plate('Knee_'+side+'_TracedShield',contour,
              lambda x,z,r:wrap(x,z,.32+1.4*(1-r*r)+.11*math.exp(-(x/2.4)**2)*(1-r*r)),
              bind,thickness=.22,bevel=.09,center=[0,0])
        # An inset border is made as an actual narrow rolled strip, following
        # the shield outline, not a separate generic circular torus.
        rim_outer=contour*.985;rim_inner=contour*.956
        vertices=[];faces=[]
        for rho,loop in [(.985,rim_outer),(.977,contour*.977),(.965,contour*.965),(.956,rim_inner)]:
            h=.32+1.4*(1-rho*rho)+.055*math.sin((rho-.956)/(.985-.956)*math.pi)
            vertices.extend(wrap(x,z,h) for x,z in loop)
        n=len(contour)
        for ring in range(3):
            for i in range(n):
                a=ring*n+i;b=ring*n+(i+1)%n;faces.append([a,b,b+n,a+n])
        ob=mesh_object('Knee_'+side+'_ShieldRolledBorder',vertices,faces,bind);finish(ob,.015,.05)
        for index,(label,width,top,bottom,curvature,offset) in enumerate([
            ('Upper',7.2,8.9,6.0,-.035,.06),
            ('Lower01',6.9,-3.65,-6.95,.040,-.17),
            ('Lower02',6.45,-6.15,-9.6,.051,-.43)]):
            upper=[[x,top+curvature*x*x] for x in np.linspace(-width,width,13)]
            lower=[[x,bottom+curvature*x*x] for x in np.linspace(width-.25,-width+.25,13)]
            contour=rounded_polygon(upper+lower,.26,3)
            binding={'thigh_'+side:1.} if index==0 else {'calf_'+side:1.}
            plate('Knee_'+side+'_CurvedLame_'+label,contour,lambda x,z,r,offset=offset:wrap(x,z,offset+.09*(1-r*r)),binding,.18,.075)
            for x in [-width+.9,width-.9]:
                z=(top+bottom)/2+curvature*x*x
                normal=unit([x/9,1,0]);point=wrap(x,z,offset+.2)
                fastener('Knee_'+side+'_LameRivet_'+label+'_'+str(x),point,normal,binding,.235)
        for x in [-6.35,6.35]:
            point=wrap(x,1.6,.7)
            fastener('Knee_'+side+'_Pivot_'+str(x),point,unit([x/8,1,0]),bind,.30)
    return trace

def export_armor():
    output={k:[] for k in ['positions','triangles','uv','normals','weights','triangle_materials','parts']}
    for ob in objects:
        mesh=ob.data;mesh.calc_loop_triangles();uv=mesh.uv_layers.active
        start=len(output['positions']);binding=json.loads(ob['binding']);slot=int(ob['material_slot'])
        output['positions'].extend([[float(v.co.x*100),float(-v.co.y*100),float(v.co.z*100)] for v in mesh.vertices])
        weights=[[bones[n],weight] for n,weight in binding.items() if weight>0]
        output['weights'].extend([weights for _ in mesh.vertices])
        valid_triangles=0
        for tri in mesh.loop_triangles:
            coords=[mesh.vertices[i].co for i in tri.vertices]
            # Degenerate tessellation slivers have no surface to export.
            if (coords[1]-coords[0]).cross(coords[2]-coords[0]).length<1e-13:continue
            output['triangles'].append([start+i for i in tri.vertices])
            mapped=np.array([[float(uv.data[i].uv.x),float(1-uv.data[i].uv.y)] for i in tri.loops])
            output['uv'].append(surface_uv(mapped,np.array(coords)*100).tolist())
            output['normals'].append([[float(mesh.corner_normals[i].vector.x),float(-mesh.corner_normals[i].vector.y),float(mesh.corner_normals[i].vector.z)] for i in tri.loops])
            output['triangle_materials'].append(slot)
            valid_triangles+=1
        output['parts'].append(dict(name=ob.name,first_vertex=start,vertices=len(mesh.vertices),triangles=valid_triangles,material=slot))
    return output

def surface_uv(uv,points):
    a,b=uv[1]-uv[0],uv[2]-uv[0]
    if abs(a[0]*b[1]-a[1]*b[0])>=1e-12:return uv
    tangent=unit(points[1]-points[0]);normal=unit(np.cross(points[1]-points[0],points[2]-points[0]));bitangent=np.cross(normal,tangent)
    local=points-points[0]
    return np.stack([local@tangent,local@bitangent],axis=1)/25

def combine(old,armor):
    data={key:old[key] for key in ['source','binding_source','skeleton','bones']}
    for key in ['positions','triangles','uv','normals','weights','triangle_materials','parts']:data[key]=[]
    face_start=0
    for part in old['parts']:
        first=part['first_vertex'];last=first+part['vertices'];end_face=face_start+part['triangles']
        if part['name'].startswith(('Mail','Lining','HemBinding')) or '_Strap_' in part['name']:
            start=len(data['positions']);delta=start-first
            for key in ['positions','weights']:data[key].extend(old[key][first:last])
            for key in ['normals','triangle_materials']:data[key].extend(old[key][face_start:end_face])
            if '_Strap_' in part['name']:
                for fi in range(face_start,end_face):
                    uv=np.array(old['uv'][fi]);points=np.array([old['positions'][i] for i in old['triangles'][fi]])
                    data['uv'].append(surface_uv(uv,points).tolist())
            else:data['uv'].extend(old['uv'][face_start:end_face])
            data['triangles'].extend([[i+delta for i in face] for face in old['triangles'][face_start:end_face]])
            data['parts'].append(dict(part,first_vertex=start))
        face_start=end_face
    offset=len(data['positions'])
    for key in ['positions','weights','uv','normals','triangle_materials']:data[key].extend(armor[key])
    data['triangles'].extend([[i+offset for i in face] for face in armor['triangles']])
    data['parts'].extend(dict(part,first_vertex=part['first_vertex']+offset) for part in armor['parts'])
    data['contract']='ArmorRefineV2: traced shield, overlapping curved lames, bevels; original cloth and native weights retained'
    return data

waist();trace=knees();armor=export_armor()
shutil.copy2(OLD/'Concept.png',R/'Concept.png')
(R/'shield-contour.json').write_text(json.dumps(dict(units='cm',local_xz=trace,reference='Concept.png',description='rounded upper shoulders, tapered lower shield; not circular'),indent=2))
counts={}
for suffix in ['', '_BootsFit']:
    old=json.loads((OLD/('Jason_ChainmailPants'+suffix+'.json')).read_text())
    new=combine(old,armor)
    (R/('Jason_ChainmailPants'+suffix+'.json')).write_text(json.dumps(new,separators=(',',':')))
    counts['boots' if suffix else 'standard']=dict(vertices=len(new['positions']),triangles=len(new['triangles']),parts=len(new['parts']))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'ArmorConstruction.blend'))
(R/'production.json').write_text(json.dumps(dict(item='ue_chainmail_pants',revision='ArmorRefineV2',counts=counts,
    source=str(OLD),reference='Concept.png',armor_parts=len(objects),changes=['traced noncircular knee shield','one upper and two curved lower lames','frontward overlapping hip plates','closed thickness and three-segment bevels','domed seated rivets and flat clasp plates'],
    preserved=['cloth geometry, UV and normals','cloth and strap native weights','boot cuff variant','item ID, equipment slot and stats'],runtime_tested=False),indent=2))
print('CHAINMAIL_ARMOR_REFINED',counts,flush=True)
