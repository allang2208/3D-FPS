"""Fitted cloth hat, independent four-bone tip rig and production icon."""
import sys,json,math,shutil
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageHat20261019';ROBE=P/'SourceAssets/BlueMageRobe20261018';sys.path.insert(0,str(P/'Tools/BlueMageRobe'))
from geometry import vertex,face,finish,tube,unit,smooth
for folder in ('Authored','Exports','Textures'):(R/folder).mkdir(exist_ok=True)
head=json.loads((R/'native_head_jason.json').read_text());hp=np.array(head['positions']);brim_z=float(hp[:,2].max())-7.8;sample=hp[(hp[:,2]>brim_z-1.6)&(hp[:,2]<brim_z+1.5)]
center=(sample.min(0)+sample.max(0))*.5;center[2]=brim_z;xy=sample[:,:2]-center[:2];radii=(sample[:,:2].max(0)-sample[:,:2].min(0))*.5+.50;radii*=max(1.,float(np.sqrt(((xy/radii)**2).sum(1)).max())+.025);RX,RY=radii+.16
slots=['Fabric','Lining','BandEmbroidery','BorderEmbroidery','Thread','Silver','Gem'];d=dict(profile='BlueMageHat',positions=[],weights=[],triangles=[],uv=[],normals=[],triangle_materials=[],material_slots=slots,contract='Fitted Jason scalp opening; sewn lining and brim; independent three-joint flexible upper tip, fixed lower crown')
def curve(t):
    if t<=.65:return np.array([0.,.30*(t/.65)**2,25*t/.65])
    q=(t-.65)/.35;a=np.array([0.,.3,25]);b=np.array([0.,.5,40]);c=np.array([0.,10,39]);e=np.array([0.,13.5,31.8]);return (1-q)**3*a+3*(1-q)**2*q*b+3*(1-q)*q*q*c+q**3*e
def weight(t):
    names=['HatRoot','HatTipBase','HatTipMid','HatTipEnd'];knots=[.58,.72,.86,.98]
    if t<=knots[0]:return {names[0]:1.}
    if t>=knots[-1]:return {names[-1]:1.}
    i=next(i for i in range(3) if knots[i]<=t<=knots[i+1]);a=float(smooth((t-knots[i])/(knots[i+1]-knots[i])));return {names[i]:1-a,names[i+1]:a}
def cone(t,a,inner=False,raise_cm=0):
    tangent=unit(curve(min(1,t+.0001))-curve(max(0,t-.0001)));v=np.array([0.,-tangent[2],tangent[1]]);scale=max(.006,(1-t)**.8);wrinkle=1+(.012*math.sin(a*5+.4)+.008*math.cos(a*9-2*t))*float(smooth(t/.15))*(1-t)
    radial=np.array([RX*math.sin(a),0,0])+v*RY*math.cos(a);radial*=scale*wrinkle;normal=unit(radial);thickness=min(.14,float(np.linalg.norm(radial))*.55)
    return curve(t)+radial+normal*((-thickness if inner else 0)+raise_cm)
def brim(u,a,lower=False,lift=0):
    x=((1-u)*RX+u*23.)*math.sin(a);y=-((1-u)*RY+u*21.5)*math.cos(a);z=(1.8*math.cos(2*a)+.6*math.cos(a))*u*u-(.22 if lower else 0)+lift;return np.array([x,y,z])
def surface(rows,segments,position,material,uv,bindings,reverse=False):
    rings=[[vertex(d,position(t,a),bindings(t)) for a in np.linspace(0,math.tau,segments,endpoint=False)] for t in rows]
    for j in range(len(rows)-1):
        for i in range(segments):
            ids=[rings[j][i],rings[j][(i+1)%segments],rings[j+1][(i+1)%segments],rings[j+1][i]];coords=[uv(rows[j],i/segments),uv(rows[j],(i+1)/segments),uv(rows[j+1],(i+1)/segments),uv(rows[j+1],i/segments)]
            for tri in (((0,2,1),(0,3,2)) if reverse else ((0,1,2),(0,2,3))):face(d,[ids[k] for k in tri],material,[coords[k] for k in tri])
    return rings
rows=np.linspace(0,1,100);outer=surface(rows,128,lambda t,a:cone(t,a),0,lambda t,a:[a*math.tau*(RX+RY)*.5/25,curve(t)[2]/25],weight,True);inside=surface(rows,128,lambda t,a:cone(t,a,True),1,lambda t,a:[a*2.4,curve(t)[2]/25],weight)
# Close the real fabric thickness at the opening and tip.
for j in (0,):
    for i in range(128):
        ids=[outer[j][i],outer[j][(i+1)%128],inside[j][(i+1)%128],inside[j][i]]
        for tri in ((0,1,2),(0,2,3)):face(d,[ids[k] for k in tri],1,[[0,0],[1,0],[1,.01]],(0,0,-1) if j==0 else curve(1)-curve(.99))
for rings,inner in ((outer,False),(inside,True)):
    # Cap each surface once; the former tip annulus plus two fans made a
    # three-face junction on both rings. Keep finite fabric thickness here.
    tip=vertex(d,curve(1)+unit(curve(1)-curve(.99))*(-.035 if inner else .035),weight(1))
    for i in range(128):face(d,[rings[-1][i],rings[-1][(i+1)%128],tip],1 if inner else 0,[[0,0],[1,0],[.5,1]],-(curve(1)-curve(.99)) if inner else curve(1)-curve(.99))
top=surface(np.linspace(0,1,13),192,lambda u,a:brim(u,a),0,lambda u,a:[a*math.tau*((1-u)*RX+u*23)/25,u*(23-RX)/25],lambda t:{'HatRoot':1})
bottom=surface(np.linspace(0,1,13),192,lambda u,a:brim(u,a,True),1,lambda u,a:[a*4.8,u*.5],lambda t:{'HatRoot':1},True)
for j in (0,12):
    for i in range(192):
        ids=[top[j][i],bottom[j][i],bottom[j][(i+1)%192],top[j][(i+1)%192]]
        for tri in ((0,1,2),(0,2,3)):face(d,[ids[k] for k in tri],1,[[0,0],[0,.01],[1,.01]])
surface(np.linspace(.86,.98,4),192,lambda u,a:brim(u,a,lift=.045),3,lambda u,a:[a*math.tau*22/22,(u-.86)/.12],lambda t:{'HatRoot':1})
surface(np.linspace(.035,.115,5),128,lambda t,a:cone(t,a,raise_cm=.065),2,lambda t,a:[a*math.tau*(RX+RY)*.5/22,(t-.035)/.08],weight,True)
surface(np.linspace(-1.4,.4,4),128,lambda z,a:np.array([(RX-.20)*math.sin(a),-(RY-.20)*math.cos(a),z]),1,lambda z,a:[a*2.4,z/25],lambda t:{'HatRoot':1})
tube(d,[brim(1,a,lift=-.04) for a in np.linspace(0,math.tau,256,endpoint=False)],.095,4,{'HatRoot':1},closed=True,sides=6)
for a in (0,math.pi/2,math.pi,3*math.pi/2):
    # Segment stitching is root-bound below the flexible upper third.
    for t in np.arange(.02,.96,.018):tube(d,[cone(t,a,raise_cm=.035),cone(t+.010,a,raise_cm=.035)],.025,4,weight(t),sides=4)
def front(x,z,lift=.07):
    t=z/25*.65;scale=(1-t)**.8;a=math.asin(np.clip(x/(RX*scale),-.95,.95));return cone(t,a,raise_cm=lift)
def star(x,z,r,mat=4):
    points=[front(x+r*(1 if i%4==0 else .72 if i%2==0 else .26)*math.sin(i*math.pi/8),z+r*(1 if i%4==0 else .72 if i%2==0 else .26)*math.cos(i*math.pi/8)) for i in range(16)];mid=vertex(d,front(x,z),weight(z/25*.65));ids=[vertex(d,p,weight(z/25*.65)) for p in points]
    for i in range(16):face(d,[mid,ids[i],ids[(i+1)%16]],mat,[[.5,.5],[0,0],[1,0]],(0,-1,0))
star(0,9.,2.0)
for side in (-1,1):
    for k in range(35):
        z=5+k*.52;x=side*(3.1+.6*math.sin(z*.5));zz=z+.52;xx=side*(3.1+.6*math.sin(zz*.5));tube(d,[front(x,z),front(xx,zz)],.028,4,weight(z/25*.65),sides=4)
    for z in np.arange(6,22,2):
        x=side*(3.1+.6*math.sin(z*.5));sign=side*(1 if int(z)%4 else -1);path=[front(x,z),front(x+sign*.7,z+.45),front(x+sign*.85,z+.85),front(x+sign*.25,z+.65)];tube(d,path,.025,4,weight(z/25*.65),closed=True,sides=4)
gem_center=front(0,3.,.18);ring=[gem_center+np.array([1.04*math.sin(a),0,1.04*math.cos(a)]) for a in np.linspace(0,math.tau,64,endpoint=False)];tube(d,ring,.11,5,{'HatRoot':1},closed=True,sides=8)
grows=[]
for v in np.linspace(0,1,9):grows.append([vertex(d,gem_center+np.array([.88*math.sin(a)*math.sqrt(max(0,1-v*v)),-.38*v,.88*math.cos(a)*math.sqrt(max(0,1-v*v))]),{'HatRoot':1}) for a in np.linspace(0,math.tau,64,endpoint=False)])
for j in range(7):
    for i in range(64):
        ids=[grows[j][i],grows[j][(i+1)%64],grows[j+1][(i+1)%64],grows[j+1][i]]
        for tri in ((0,1,2),(0,2,3)):face(d,[ids[k] for k in tri],6,[[0,0],[1,0],[1,1]],(0,-1,0))
tip=vertex(d,gem_center+[0,-.38,0],{'HatRoot':1})
for i in range(64):face(d,[grows[7][i],grows[7][(i+1)%64],tip],6,[[0,0],[1,0],[.5,1]],(0,-1,0))
bone_pos=[np.zeros(3),curve(.62),curve(.80),curve(.93)];names=['HatRoot','HatTipBase','HatTipMid','HatTipEnd'];d['bones']={name:dict(index=i,parent=i-1,position=pos.tolist(),axes=np.eye(3).tolist()) for i,(name,pos) in enumerate(zip(names,bone_pos))};finish(d)
(R/'Authored/hat.json').write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
axes=np.array(head['bones']['head']['axes']).T;scale=np.linalg.norm(axes,axis=0);rot=axes/scale;quat=Matrix(rot.T.tolist()).to_quaternion();w,x,y,z=quat;pitch=math.asin(np.clip(2*(z*x-w*y),-1,1));yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z));roll=math.atan2(-2*(w*x+y*z),1-2*(x*x+y*y))
fit=dict(location=np.linalg.solve(axes,center-np.array(head['bones']['head']['position'])).tolist(),rotation=[math.degrees(v) for v in (pitch,yaw,roll)],scale=(1/scale).tolist());(R/'fit.json').write_text(json.dumps(dict(fits={'jason':fit},native_head=head['source'],brim_world_z=brim_z,opening_radii_cm=radii.tolist(),triangles=len(d['triangles'])),indent=2),encoding='utf-8')
bpy.ops.wm.read_factory_settings(use_empty=True)
# Reuse the robe's physically scaled fabric and embroidery source maps.
for family in ('BlueMageFabric','BlueMageEmbroidery'):
    for channel in ('BaseColor','Normal','ORM'):shutil.copy2(ROBE/'Textures'/('T_'+family+'_'+channel+'.png'),R/'Textures'/('T_'+family+'_'+channel+'.png'))
sys.path.insert(0,str(P/'Tools/BlueMageHat'));from hat_materials_blender import make_materials
materials=make_materials(R)
mesh=bpy.data.meshes.new('BlueMageHat');mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in d['positions']],[],d['triangles']);mesh.update();ob=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(ob)
for m in materials:mesh.materials.append(m)
uv=mesh.uv_layers.new(name='PhysicalGarmentUV')
for fi,poly in enumerate(mesh.polygons):
    poly.material_index=d['triangle_materials'][fi];poly.use_smooth=True
    for ci,li in enumerate(poly.loop_indices):a,b=d['uv'][fi][ci];uv.data[li].uv=(a,1-b)
mesh.normals_split_custom_set([(x,-y,z) for n in d['normals'] for x,y,z in n]);arm=bpy.data.armatures.new('MageHatRig');rig=bpy.data.objects.new('MageHatRig',arm);bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for i,name in enumerate(names):
    b=arm.edit_bones.new(name);b.head=(bone_pos[i][0]*.01,-bone_pos[i][1]*.01,bone_pos[i][2]*.01);b.tail=b.head+Vector((0,.025,0))
    if i:b.parent=arm.edit_bones[names[i-1]]
bpy.ops.object.mode_set(mode='OBJECT');groups={n:ob.vertex_groups.new(name=n) for n in names}
for vi,ws in enumerate(d['weights']):
    for n,value in ws.items():
        if value>0:groups[n].add([vi],value,'REPLACE')
ob.parent=rig;ob.modifiers.new('Independent flexible tip','ARMATURE').object=rig
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=ob
bpy.ops.export_scene.fbx(filepath=str(R/'Exports/BlueMageHat.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE')
high=bpy.data.collections.new('HIGH_SurfaceBakeSources');bpy.context.scene.collection.children.link(high);high.hide_render=True;high.hide_viewport=True
for family,span in [('BlueMageFabric',(4,4)),('BlueMageEmbroidery',(22,3.5))]:
    heights=np.load(ROBE/'Textures'/(family+'_height_cm.npy'))[::4,::4];ny,nx=heights.shape;hmesh=bpy.data.meshes.new('HIGH_'+family);hmesh.from_pydata([(x/(nx-1)*span[0]*.01,y/(ny-1)*span[1]*.01,float(heights[y,x])*.01) for y in range(ny) for x in range(nx)],[],[(y*nx+x,y*nx+x+1,(y+1)*nx+x+1,(y+1)*nx+x) for y in range(ny-1) for x in range(nx-1)]);ho=bpy.data.objects.new(hmesh.name,hmesh);high.objects.link(ho)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'Exports/BlueMageHat.blend'))
sys.path.insert(0,str(P/'Tools/BlueMageSetIcons'))
from render_icons import render_current
render_current('ue_blue_mage_hat',ob)
(R/'authored.json').write_text(json.dumps(dict(completed=True,triangles=len(d['triangles']),bones=names,fit=fit,fbx=str(R/'Exports/BlueMageHat.fbx'),blend=str(R/'Exports/BlueMageHat.blend'),icon=str(R/'ue_blue_mage_hat.png'),runtime_tested=False),indent=2),encoding='utf-8');print('BLUE_MAGE_HAT_AUTHORED',len(d['triangles']),flush=True)
