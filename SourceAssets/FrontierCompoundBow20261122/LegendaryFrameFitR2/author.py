"""Refit the two legendary game meshes against the continuous factory riser."""
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

src=Path(__file__).resolve().parent
family=src.parent
batch=Path(os.environ['FIT_BATCH'])
factory=family/'RigContactR2/FrontierCompoundBow_R2.blend'
aurora=family/'AuroraFrameR1/Frontier_Aurora.blend'
eclipse=family/'EclipseFrameR1/Frontier_Eclipse.blend'
hardware=('UpperLimb','LowerLimb','UpperCam','LowerCam','ControlCable1','ControlCable2')
# (half, slope of cut in X, section on factory / on the decorative web)
joins=[('Upper',0,12.28,14.22),('Upper',.9,43.56,39.64),
       ('Lower',0,10.77,13.05),('Lower',.9,34.02,28.72)]
def level(co,half,k):return (co.z if half=='Upper' else -co.z)+k*co.x
def original_data(obj,path):
    with bpy.data.libraries.load(str(path),link=False) as (_,donor):donor.objects=[obj.name]
    ob=donor.objects[0]
    if [g.name for g in obj.vertex_groups]!=[g.name for g in ob.vertex_groups]:raise ValueError(obj.name+' bone map')
    obj.data=ob.data.copy()
    for slot in obj.material_slots:
        slot.material=bpy.data.materials[slot.material.name.split('.')[0]]
    bpy.data.objects.remove(ob,do_unlink=True)
def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
def cut(bm,half,k,h):
    normal=Vector((k,0,1 if half=='Upper' else -1))
    bmesh.ops.bisect_plane(bm,geom=bm.verts[:]+bm.edges[:]+bm.faces[:],dist=.000003,
        plane_co=Vector((0,0,h if half=='Upper' else -h)),plane_no=normal.normalized())
def clipped(obj,mode,half=None):
    bm=bmesh.new();bm.from_mesh(obj.data)
    for h,k,base,web in joins:
        if not half or h==half:cut(bm,h,k,base if mode=='factory' else web)
    discard=[]
    for f in bm.faces:
        c=f.calc_center_median();side='Upper' if c.z>0 else 'Lower'
        root_joint,tip_joint=[j for j in joins if j[0]==side]
        base_root,web_root=root_joint[2:];base_tip,web_tip=tip_joint[2:]
        if mode=='factory':remove=(level(c,side,0)>base_root and level(c,side,.9)<base_tip)
        else:remove=(level(c,half,0)<web_root or level(c,half,.9)>web_tip)
        if remove:discard.append(f)
    bmesh.ops.delete(bm,geom=discard,context='FACES');bm.to_mesh(obj.data);bm.free()
def cycles(edges):
    adjacent={}
    for e in edges:
        a,b=e.verts
        adjacent.setdefault(a,[]).append(b);adjacent.setdefault(b,[]).append(a)
    if any(len(ns)!=2 for ns in adjacent.values()):
        raise ValueError('Non-cyclic section vertices: '+str([(tuple(v.co),len(ns)) for v,ns in adjacent.items() if len(ns)!=2][:8]))
    rings=[]
    while adjacent:
        start=next(iter(adjacent));prev=None;v=start;ring=[]
        while True:
            ns=adjacent.pop(v);ring.append(v)
            v,prev=(ns[0] if ns[0]!=prev else ns[1]),v
            if v==start:break
        rings.append(ring)
    return sorted(rings,key=lambda r:sum(v.co.x for v in r)/len(r))
def canonical(ring):
    area=sum(a.co.x*b.co.y-b.co.x*a.co.y for a,b in zip(ring,ring[1:]+ring[:1]))
    return ring if area>0 else list(reversed(ring))
def bridge_eclipse(shell,scene):
    upper=scene.objects['Eclipse_UpperWeb'];lower=scene.objects['Eclipse_LowerWeb']
    clipped(shell,'factory');clipped(upper,'skin','Upper');clipped(lower,'skin','Lower')
    select([shell,upper,lower]);bpy.ops.object.join()
    bm=bmesh.new();bm.from_mesh(shell.data)
    finish_index=shell.data.materials.find('M_Eclipse_Frame')
    stock_index=shell.data.materials.find('M_Frontier_Surface')
    group=shell.vertex_groups['bow_body_root'].index
    deform=bm.verts.layers.deform.verify()
    uv=bm.loops.layers.uv.active
    # Continue the graphite finish along the original webs to their natural joints.
    # The factory collars, axle hardware and the grip itself keep their original UVs.
    for f in bm.faces:
        c=f.calc_center_median();side='Upper' if c.z>0 else 'Lower'
        height=abs(c.z);end=level(c,side,.9)
        in_web=(height>6.60 and end<43.75) if side=='Upper' else (height>9.20 and end<34.25)
        if f.material_index!=stock_index or not in_web or c.x < -3.42:continue
        f.material_index=finish_index
        for corner in f.loops:
            x,y,z=corner.vert.co
            corner[uv].uv=(.12+(x+.29*y)*.005,.1+(z+34)*.010)
    def joint_rings(half,k,h):
        predicate=lambda v:abs(level(v.co,half,k)-h)<.00014
        rim=[v for v in bm.verts if predicate(v) and any(e.is_boundary for e in v.link_edges)]
        bmesh.ops.remove_doubles(bm,verts=rim,dist=.00013)
        return cycles([e for e in bm.edges if e.is_boundary and all(predicate(v) for v in e.verts)])
    endpoints=[];jobs=[]
    for half,k,h0,h1 in joins:
        r0=joint_rings(half,k,h0);r1=joint_rings(half,k,h1)
        if not r0 or not r1:raise RuntimeError('Missing exact end ring: '+str((half,h0,h1)))
        print('SECTION',half,h0,h1,[len(r) for r in r0],[len(r) for r in r1],flush=True)
        endpoints.append((r0,r1))
        jobs.append({key:[[[v.co.x,v.co.y] for v in ring] for ring in rings] for key,rings in [('start',r0),('end',r1)]})
    args=[os.environ['FIT_PYTHON'],str(src/'blend_sections.py')]
    result=subprocess.run(args,input=json.dumps(jobs),text=True,capture_output=True)
    if result.returncode:raise RuntimeError(result.stderr)
    meshes=json.loads(result.stdout)
    report=[]
    def add_face(vs):
        f=bm.faces.new(vs);f.smooth=True;f.material_index=finish_index
        # Dominant-plane parameterization for the existing brushed graphite atlas.
        f.normal_update();n=f.normal
        for l in f.loops:
            x,y,z=l.vert.co
            u=(x+.29*y) if abs(n.y)>=abs(n.x) else (y+.13*x)
            l[uv].uv=(.12+u*.005,.1+(z+34)*.010)
        return f
    def seam(old,new):
        a=canonical(old);b=canonical(new)
        # Match the seam phase at the closest spatial samples on the two measured outlines.
        j=min(range(len(b)),key=lambda n:(b[n].co-a[0].co).length_squared)
        b=b[j:]+b[:j]
        def arc(r):
            s=[0.]
            for p,q in zip(r,r[1:]+r[:1]):s.append(s[-1]+(p.co-q.co).length)
            return [x/s[-1] for x in s]
        ad,bd=arc(a),arc(b);i=j=0;fs=[]
        while i<len(a) or j<len(b):
            if j==len(b) or (i<len(a) and ad[i+1]<=bd[j+1]):
                fs.append(add_face([a[i%len(a)],a[(i+1)%len(a)],b[j%len(b)]]));i+=1
            else:
                fs.append(add_face([a[i%len(a)],b[(j+1)%len(b)],b[j%len(b)]]));j+=1
        return fs
    for (half,k,h0,h1),(end0,end1),mesh in zip(joins,endpoints,meshes):
        verts=[];values={};fs=[]
        for x,y,t in mesh['v']:
            z=(h0+(h1-h0)*t-k*x)*(1 if half=='Upper' else -1)
            v=bm.verts.new((x,y,z));v[deform][group]=1.;verts.append(v);values[v]=t
        for tri in mesh['f']:fs.append(add_face([verts[i] for i in tri]))
        rim=[e for f in fs for e in f.edges if e.is_boundary]
        for old,t in [(end0,.022),(end1,.978)]:
            new=cycles([e for e in rim if all(abs(values[v]-t)<.00002 for v in e.verts)])
            if len(old)!=len(new):raise ValueError(('section topology',half,h0,t,len(old),len(new)))
            for a,b in zip(old,new):fs.extend(seam(a,b))
        # Orient against the undisturbed adjacent faces.
        for edge in end0[0][0].link_edges:
            witnesses=[f for f in edge.link_faces if f not in fs]
            fresh=[f for f in edge.link_faces if f in fs]
            if witnesses and fresh:
                break
        bmesh.ops.recalc_face_normals(bm,faces=fs)
        if witnesses and fresh:
            va=edge.verts[0]
            lhs=next(l for l in witnesses[0].loops if l.edge==edge)
            rhs=next(l for l in fresh[0].loops if l.edge==edge)
            if lhs.vert==rhs.vert:bmesh.ops.reverse_faces(bm,faces=fs)
        boundary=sum(e.is_boundary for rings in (end0,end1) for ring in rings for v in ring for e in v.link_edges)
        if boundary:raise ValueError('Unstitched edges at '+str((half,h0,boundary)))
        report.append({'side':half,'factory_section':h0,'web_section':h1,'factory_loops':len(end0),'web_loops':len(end1),'open_seam_edges':boundary})
    bm.to_mesh(shell.data);bm.free()
    return report

def smooth(x):
    x=max(0.,min(1.,x));return x*x*(3-2*x)
def rail_limits(tree,z,guess):
    # Intersect the outer factory rail along X, at its mid-depth away from the grip bosses.
    origin=Vector((guess+14,.17,z))
    location=tree.ray_cast(origin,Vector((-1,0,0)),30)[0]
    if location is None:raise RuntimeError(('Missing outer rail',z))
    inner=tree.ray_cast(location+Vector((-.001,0,0)),Vector((-1,0,0)),24)[0]
    if inner is None:raise RuntimeError(('Missing inner rail',z))
    return location.x,location.x-inner.x
def bvh(mesh):
    return BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices],[list(p.vertices) for p in mesh.polygons])
def fit_aurora(shell,scene):
    mesh=shell.data;tree=bvh(mesh)
    # Keep the factory web continuous through the limbs, both grip shoulders and the accessory seats.
    for high in (True,False):
        sign=1 if high else -1
        side='Upper' if high else 'Lower'
        zbase,ztip=(7.2,33.45) if high else (9.8,24.85)
        stations=np.linspace(zbase,ztip,160)
        limits=[rail_limits(tree,z*sign,4.) for z in stations]
        outside=np.asarray([a for a,b in limits]);width=np.asarray([b for a,b in limits])
        width=np.convolve(np.pad(np.clip(width,.65,2.15),(3,3),mode='edge'),np.ones(7)/7,mode='valid')
        def section(z):
            t=(z-zbase)/(ztip-zbase)
            shoulder=smooth(t/.19)*smooth((1-t)/.18)
            return float(np.interp(z,stations,outside)),float(np.interp(z,stations,width)),shoulder
        for v in mesh.vertices:
            x,y,z=v.co;h=z*sign
            if not zbase<h<ztip:continue
            outer,w,env=section(h)
            if x<outer-w-.25:continue
            v.co.x+=1.58*env*smooth((x-outer+w+.16)/(w+.16))
        mesh.update()
        surface=bvh(mesh)
        frame=scene.objects['Aurora_'+side+'_SilverFrame']
        cells=[ob for ob in scene.objects if ob.name.startswith('Aurora_'+side) and ob.name.endswith('_Enamel')]
        old=np.array([(v.co.x,v.co.z*sign) for v in frame.data.vertices])
        oldlo,oldhi=old[:,1].min(),old[:,1].max()
        # Derive the feather outline at continuous height from the traced mesh edges.
        e=np.asarray([list(edge.vertices) for edge in frame.data.edges]);p,q=old[e[:,0]],old[e[:,1]]
        section_h=np.linspace(oldlo+.007,oldhi-.007,220)
        slices=[]
        for h in section_h:
            mask=((p[:,1]<=h)&(q[:,1]>h))|((q[:,1]<=h)&(p[:,1]>h))
            pp,qq=p[mask],q[mask]
            vals=pp[:,0]+(qq[:,0]-pp[:,0])*(h-pp[:,1])/(qq[:,1]-pp[:,1])
            slices.append((vals.min(),vals.max()))
        low,highs=np.array(slices).T
        for ob in [frame,*cells]:
            for v in ob.data.vertices:
                x,y,z=v.co;h=z*sign;t=np.clip((h-oldlo)/(oldhi-oldlo),0.,1.)
                dest=zbase+(ztip-zbase)*t
                outer,w,env=section(dest)
                lo=np.interp(h,section_h,low);hi=np.interp(h,section_h,highs)
                u=np.clip((x-lo)/max(.04,hi-lo),0.,1.)
                tip=smooth(t/.125)*smooth((1-t)/.105)
                spread=(1.14+1.60*env)*(.10+.88*tip)
                nz=sign*dest
                right,actual_width=rail_limits(surface,nz,outer)
                spread=min(spread,.79*actual_width)
                center=np.clip(outer+.82*env-.5,right-.94*actual_width+spread*.5,right-.06*actual_width-spread*.5)
                nx=center+(u-.5)*spread
                landing=surface.ray_cast(Vector((nx,7,nz)),Vector((0,-1,0)),14)[0]
                if landing is None:raise ValueError(('Unsupported applique',ob.name,nx,nz))
                # Both the raised face and the inset enamel retain their original UVs.
                outer_depth=max(landing.y,1.49 if side=='Upper' else 1.65) if y>0 else landing.y
                if ob==frame:
                    lift=.11+(y-1.23)*.84 if y>0 else -.10
                else:
                    lift=.12+(y-1.25)*1.16
                v.co=(nx,outer_depth+lift,nz)
            ob.data.update()
    for name in ['Aurora_CableGuideHeel','Aurora_SightSeat']:
        bpy.data.objects.remove(scene.objects[name],do_unlink=True)
    return {'carrier':'continuous factory riser','enamel_cells':5,'surface_projection':'all decorative vertices supported'}

def make(kind):
    before=aurora if kind=='Aurora' else eclipse
    bpy.ops.wm.open_mainfile(filepath=str(before))
    bpy.context.preferences.filepaths.save_version=0;scene=bpy.context.scene;rig=scene.objects['Armature']
    rig.data.pose_position='REST';scene.frame_set(1)
    shell=scene.objects['Riser'];original_data(shell,factory)
    if kind=='Eclipse':
        for cam in ('UpperCam','LowerCam'):original_data(scene.objects[cam],aurora)
        # Bring the terminal relief and its matching panel inward together, leaving
        # enough graphite beyond the full pointed end of each bronze crescent.
        for side in ('Upper','Lower'):
            sign=1 if side=='Upper' else -1
            begin,compression=(30.,.31) if sign==1 else (21.,.35)
            web=scene.objects['Eclipse_'+side+'Web'].data
            coords=np.array([[v.co.x,level(v.co,side,.9)] for v in web.vertices])
            edges=np.array([list(e.vertices) for e in web.edges]);a,b=coords[edges[:,0]],coords[edges[:,1]]
            levels=np.linspace(begin-.02,coords[:,1].max()-.003,350)
            widths=[]
            for h in levels:
                take=((a[:,1]<=h)&(b[:,1]>h))|((b[:,1]<=h)&(a[:,1]>h))
                p,q=a[take],b[take]
                xs=p[:,0]+(h-p[:,1])*(q[:,0]-p[:,0])/(q[:,1]-p[:,1])
                widths.append([xs.min(),xs.max()])
            lo,hi=np.array(widths).T
            for ob in scene.objects:
                if not ob.name.startswith('Eclipse_') or ob.name.endswith(('Seat','Heel')):continue
                islower='Lower' in ob.name and not ob.name.endswith('LowerKeel')
                if islower!=(side=='Lower'):continue
                # Subdivide only across the tapered region. Long cap triangles must follow the same arc as their rim.
                bm=bmesh.new();bm.from_mesh(ob.data)
                for h in np.arange(begin,levels[-1],.58):cut(bm,side,.9,float(h))
                bm.to_mesh(ob.data);bm.free()
                for v in ob.data.vertices:
                    h=level(v.co,side,.9);d=h-begin
                    if d<=0:continue
                    dest=h-compression*(d-1.15*(1-math.exp(-d/1.15)))
                    left=np.interp(h,levels,lo);right=np.interp(h,levels,hi)
                    fraction=np.clip((v.co.x-left)/max(.006,right-left),-.05,1.05)
                    left2=np.interp(dest,levels,lo);right2=np.interp(dest,levels,hi)
                    v.co.x=left2+fraction*(right2-left2)
                    v.co.z=sign*(dest-.9*v.co.x)
        bpy.data.objects.remove(scene.objects['Eclipse_CableGuideHeel'],do_unlink=True)
        info=bridge_eclipse(shell,scene)
        # Fold the relief tips into their panel before the new pocket transitions.
        for ob in list(scene.objects):
            if not ob.name.startswith('Eclipse_') or ob.name.endswith('Seat') or ob.name.endswith('Heel'):continue
            side='Lower' if 'Lower' in ob.name and ob.name!='Eclipse_LowerKeel' else 'Upper'
            for v in ob.data.vertices:
                h=level(v.co,side,.9);end=39.64 if side=='Upper' else 28.72
                v.co.y*=1-.32*smooth((h-end+.6)/.6)
                root=level(v.co,side,0)
                v.co.y*=1-.32*smooth(((14.22 if side=='Upper' else 13.05)-root+1.0)/1.0)
            clipped(ob,'skin',side)
        # Keep the optic pad on the outer cheek and give its unused lateral ends a slope.
        # The two outside mounting faces and their centre stay available at the stock position.
        seat=scene.objects['Eclipse_SightSeat']
        for v in seat.data.vertices:
            x,y,z=v.co
            if y>1.45:v.co.y=1.55-.24*smooth(abs(x-1.10)/1.22)
    else:info=fit_aurora(shell,scene)
    pieces=[shell,*[scene.objects[n] for n in hardware],*[o for o in scene.objects if o.type=='MESH' and o.name.startswith(kind+'_')]]
    copies=[]
    for ob in pieces:
        cp=ob.copy();cp.data=ob.data.copy();scene.collection.objects.link(cp);copies.append(cp)
    select(copies);bpy.ops.object.join();out=copies[0];out.name='SK_Frontier_'+kind
    select([rig,out])
    bpy.ops.export_scene.fbx(filepath=str(src/'Export'/(out.name+'.fbx')),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',
        apply_unit_scale=True,add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
    bpy.data.objects.remove(out,do_unlink=True)
    select([shell]);rig.data.pose_position='POSE';scene.frame_set(1)
    bpy.ops.outliner.orphans_purge(do_recursive=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(src/('Frontier_'+kind+'.blend')),compress=True)
    (batch/(kind+'-fit.json')).write_text(json.dumps(info,indent=2))
for name in sys.argv[sys.argv.index('--')+1:]:make(name)
