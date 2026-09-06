import bpy,bmesh,math,json,sys
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'foreman-model.blend'))
scene=bpy.context.scene
mesh=next(o for o in scene.objects if o.type=='MESH')
mesh.name='ForemanBody'
bm=bmesh.new();bm.from_mesh(mesh.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001);bm.to_mesh(mesh.data);bm.free()
arm=bpy.data.objects.new('ForemanRig',bpy.data.armatures.new('ForemanSkeleton'));scene.collection.objects.link(arm)
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT')
defs={}
def bone(n,h,t,parent=None,deform=True):
 b=arm.data.edit_bones.new(n);b.head=h;b.tail=t;b.use_deform=deform
 if parent:b.parent=arm.data.edit_bones[parent]
 defs[n]={'head':Vector(h),'tail':Vector(t),'parent':parent}
bone('root',(0,0,0),(0,0,.2),deform=False)
bone('pelvis',(0,.06,1.23),(0,.06,1.42),'root')
bone('spine',(0,.06,1.42),(0,.02,1.73),'pelvis')
bone('chest',(0,.02,1.73),(0,0,2.03),'spine')
bone('neck',(0,0,2.03),(0,-.015,2.20),'chest')
bone('head',(0,-.015,2.20),(0,0,2.57),'neck')
for side,s in [('L',1),('R',-1)]:
 bone('clavicle.'+side,(s*.08,0,1.98),(s*.48,.02,1.98),'chest')
 bone('upper_arm.'+side,(s*.48,.02,1.98),(s*.68,.025,1.63),'clavicle.'+side)
 bone('forearm.'+side,(s*.68,.025,1.63),(s*.82,-.01,1.27),'upper_arm.'+side)
 bone('hand.'+side,(s*.82,-.01,1.27),(s*.87,-.025,1.10),'forearm.'+side)
 bone('thigh.'+side,(s*.25,.065,1.23),(s*.30,.065,.73),'pelvis')
 bone('shin.'+side,(s*.30,.065,.73),(s*.34,.12,.19),'thigh.'+side)
 bone('foot.'+side,(s*.34,.12,.19),(s*.35,-.22,.075),'shin.'+side)
whip_start=Vector((-.87,-.025,1.10))
for i in range(32):bone('whip.%02d'%i,whip_start+Vector((0,0,-i*.10)),whip_start+Vector((0,0,-(i+1)*.10)),'hand.R' if i==0 else 'whip.%02d'%(i-1))
bpy.ops.object.mode_set(mode='OBJECT')
for pb in arm.pose.bones:pb.rotation_mode='QUATERNION'
mesh.parent=arm;mod=mesh.modifiers.new('Skin','ARMATURE');mod.object=arm
groups={n:mesh.vertex_groups.new(name=n) for n in defs if n!='root' and not n.startswith('whip')}
def distance(p,a,b):
 d=b-a;return (p-a-d*max(0,min(1,(p-a).dot(d)/d.length_squared))).length
for v in mesh.data.vertices:
 p=v.co;x=abs(p.x);z=p.z;s='L' if p.x>=0 else 'R'
 names=['pelvis','spine','chest','neck','head']+[n+'.'+s for n in ['clavicle','upper_arm','forearm','hand','thigh','shin','foot']]
 ws=sorted([(n,1/(distance(p,defs[n]['head'],defs[n]['tail'])+.025)**4) for n in names],key=lambda a:-a[1])[:4];total=sum(w for n,w in ws)
 for n,w in ws:groups[n].add([v.index],w/total,'REPLACE')
# Continuous foreman-specific arm/trunk boundary; thick belly stays on spine.
for v in mesh.data.vertices:
 p=v.co;x=abs(p.x);z=p.z;side='L' if p.x>=0 else 'R'
 body=['pelvis','spine','chest','neck','head']
 if z<1.25:body+=['thigh.'+side,'shin.'+side,'foot.'+side]
 limbs=['clavicle.'+side,'upper_arm.'+side,'forearm.'+side,'hand.'+side]
 boundary=max(.36,.68-.32*(z-1.0))
 blend=max(0,min(1,(x-boundary+.055)/.11)) if z>.85 else 0
 blend=blend*blend*(3-2*blend)
 def normalized(names):
  ws=[(n,1/(distance(p,defs[n]['head'],defs[n]['tail'])+.02)**4) for n in names];total=sum(w for n,w in ws)
  return [(n,w/total) for n,w in ws]
 ws=sorted([(n,w*(1-blend)) for n,w in normalized(body)]+[(n,w*blend) for n,w in normalized(limbs)],key=lambda p:-p[1])[:4];total=sum(w for n,w in ws)
 for g in mesh.vertex_groups:g.remove([v.index])
 for n,w in ws:mesh.vertex_groups[n].add([v.index],w/total,'REPLACE')
for p in mesh.data.polygons:p.use_smooth=True
# A continuous tapered leather tube, isolated from body skin weights.
verts=[];faces=[]
for i in range(33):
 center=whip_start+Vector((0,0,-i*.10));r=.022*(1-i/40)
 for j in range(8):verts.append(center+Vector((r*math.cos(j*math.tau/8),r*math.sin(j*math.tau/8),0)))
for i in range(32):
 for j in range(8):faces.append((i*8+j,i*8+(j+1)%8,(i+1)*8+(j+1)%8,(i+1)*8+j))
data=bpy.data.meshes.new('WhipLeather');data.from_pydata(verts,[],faces);data.update()
whip=bpy.data.objects.new('Whip',data);scene.collection.objects.link(whip);whip.parent=arm
mat=bpy.data.materials.new('Worn leather');mat.diffuse_color=(.14,.065,.025,1);mat.use_nodes=True;next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=mat.diffuse_color;next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Roughness'].default_value=.8;data.materials.append(mat)
for i in range(32):
 g=whip.vertex_groups.new(name='whip.%02d'%i)
 for ring in [i,i+1]:g.add(list(range(ring*8,ring*8+8)),1 if ring in [0,32] else .5,'REPLACE')
mod=whip.modifiers.new('Whip chain','ARMATURE');mod.object=arm
rest={n:arm.data.bones[n].matrix_local.copy() for n in defs}
lengths={n:(d['tail']-d['head']).length for n,d in defs.items()}
def orient(name,h,t,axial_twist=0):
    d=defs[name];rot=(d['tail']-d['head']).rotation_difference(t-h) @ rest[name].to_quaternion()
    if axial_twist:rot=Quaternion((t-h).normalized(),axial_twist) @ rot
    mat=rot.to_matrix().to_4x4();mat.translation=h
    arm.pose.bones[name].matrix=mat
    bpy.context.view_layer.update()
    return mat
def solve_two(a,target,l1,l2,pole):
    delta=target-a;dist=max(.0001,min(delta.length,l1+l2-.0001));u=delta.normalized()
    middle=(l1*l1-l2*l2+dist*dist)/(2*dist)
    v=pole-u*pole.dot(u)
    if v.length<.001:v=Vector((0,1,0))-u*u.y
    v.normalize();b=a+u*middle+v*math.sqrt(max(0,l1*l1-middle*middle))
    return b,a+u*dist
def lerp(a,b,t):return a+(b-a)*t
def sample(t,keys):
    # Monotone cubic Hermite: carry velocity through intermediate poses instead
    # of easing to a complete stop at every key. Flat holds remain exactly flat.
    def tangent(i,k):
        if i==0 or i==len(keys)-1:return keys[i][1][k]*0
        a,b,c=keys[i-1:i+2];h0=b[0]-a[0];h1=c[0]-b[0]
        d0=(b[1][k]-a[1][k])/h0;d1=(c[1][k]-b[1][k])/h1
        def slope(x,y):
            return 0 if x*y<=0 else (3*(h0+h1))/((2*h1+h0)/x+(h1+2*h0)/y)
        return Vector([slope(x,y) for x,y in zip(d0,d1)]) if isinstance(d0,Vector) else slope(d0,d1)
    for i in range(len(keys)-1):
        a,b=keys[i],keys[i+1]
        if t<=b[0]:
            dt=b[0]-a[0];u=max(0,min(1,(t-a[0])/dt))
            return {k:(2*u**3-3*u*u+1)*a[1][k]+(u**3-2*u*u+u)*dt*tangent(i,k)+(-2*u**3+3*u*u)*b[1][k]+(u**3-u*u)*dt*tangent(i+1,k) for k in a[1]}
    return keys[-1][1]

def values(lean=.08,drop=.03,twist=0,step=0,reach=0,raise_left=0,whip_phase=0):return locals()
attack_keys=[(0,values()),(.18,values(lean=-.08,twist=-.32,reach=-.15)),(.40,values(lean=-.12,twist=-.55,reach=-.25,whip_phase=.3)),(.50,values(lean=.12,twist=-.2,step=.14,reach=.3,whip_phase=.6)),(.59625,values(lean=.42,drop=.12,twist=.5,step=.25,reach=.6,whip_phase=1)),(.67,values(lean=.43,drop=.13,twist=.56,step=.25,reach=.56,whip_phase=1)),(.95,values(lean=.2,twist=.25,step=.16,reach=.2,whip_phase=.7)),(1.5,values())]
def pose(t,clip):
 for pb in arm.pose.bones:pb.matrix_basis=Matrix.Identity(4)
 bpy.context.view_layer.update()
 p=values();phase=t/1.5
 if clip=='Walk':p.update(drop=.04+.035*(1-math.cos(phase*math.tau*2)),twist=.065*math.sin(phase*math.tau))
 if clip=='Idle':p['lean']+=.009*math.sin(t*math.tau)
 if clip=='Attack':p=sample(t,attack_keys)
 if clip=='Howl':p.update(raise_left=math.sin(math.pi*min(1,t/3))**.7,lean=.08-.14*math.sin(math.pi*t/3))
 death=clip=='Death';fall=max(0,min(1,(t-.1)/1.15)) if death else 0
 smooth=fall*fall*(3-2*fall)
 base=Vector((.035*math.sin(phase*math.tau) if clip=='Walk' else 0,.60*smooth,1.23-p['drop']-.80*smooth))
 lean=p['lean'] if not death else .08-1.65*smooth
 rot=Matrix.Rotation(p['twist'],3,'Z') @ Matrix.Rotation(lean,3,'X')
 head=base;mats={}
 for n in ['pelvis','spine','chest','neck','head']:
  tail=head+rot@Vector((0,0,lengths[n]));mats[n]=orient(n,head,tail,p['twist']*.3 if n=='chest' else 0);head=tail
 cd=mats['chest'] @ rest['chest'].inverted()
 wrists={}
 for side,sign in [('L',1),('R',-1)]:
  cl='clavicle.'+side;u='upper_arm.'+side;f='forearm.'+side;h='hand.'+side
  shoulder=cd @ defs[cl]['tail'];orient(cl,cd @ defs[cl]['head'],shoulder)
  target=shoulder+Vector((sign*.17,-.07,-.72))
  if clip=='Walk':target.y+=.10*math.sin(phase*math.tau+(math.pi if side=='R' else 0))
  if clip=='Howl' and side=='L':target=target.lerp(shoulder+Vector((.13,-.24,.65)),p['raise_left'])
  if clip=='Attack':
   if side=='R':
    raised=min(1,max(0,t/.4)) if t<.4 else max(0,1-(t-.4)/.19625)
    target=shoulder+Vector((-.12,-.07-p['reach'], -.65+.98*raised))
   else:target+=Vector((.10*math.sin(math.pi*t/1.5),-.20*math.sin(math.pi*t/1.5),.20*math.sin(math.pi*t/1.5)))
  if death:target=target.lerp(shoulder+Vector((sign*.12,-.66,-.04)),smooth)
  elbow,wrist=solve_two(shoulder,target,lengths[u],lengths[f],Vector((sign,.35,.15)))
  orient(u,shoulder,elbow);orient(f,elbow,wrist)
  direction=Vector((0,-.25,-1)).lerp(Vector((0,-1,-.1)),smooth if death else p['whip_phase'] if side=='R' else 0).normalized()
  orient(h,wrist,wrist+direction*lengths[h]);wrists[side]=wrist+direction*lengths[h]*.65
  th='thigh.'+side;sh='shin.'+side;fo='foot.'+side
  hip=base+(defs[th]['head']-defs['pelvis']['head']);ankle=defs[sh]['tail'].copy()
  if clip=='Walk':
   ph=(phase+(0 if side=='L' else .5))%1;stance=.62;travel=.40
   if ph<stance:ankle.y+=-travel/2+travel*ph/stance
   else:
    q=(ph-stance)/(1-stance);ankle.y+=travel/2-travel*q*q*(3-2*q);ankle.z+=.08*math.sin(math.pi*q)**2
  if clip=='Attack' and side=='L':ankle.y-=p['step']
  if death:ankle.y-=.72*smooth;ankle.z+=.16*math.sin(math.pi*smooth)
  knee,ankle=solve_two(hip,ankle,lengths[th],lengths[sh],Vector((sign*.07,-1, .5*smooth)))
  orient(th,hip,knee);orient(sh,knee,ankle)
  fd=Matrix.Rotation(-1.1*smooth,3,'X')@(defs[fo]['tail']-defs[fo]['head']);orient(fo,ankle,ankle+fd)
 # Separate whip chain: right-hand coil, overhead arc, then full forward snap.
 start=wrists['R'];points=[]
 for i in range(33):
  u=i/32;ang=u*math.tau*2.15
  coil=start+Vector((.24*math.sin(ang),.05*u,-.24*(1-math.cos(ang))-.10*u))
  overhead=start+Vector((-.22*math.sin(u*math.pi),1.8*u,.7*math.sin(u*math.pi)))
  extended=start+Vector((.07*math.sin(u*math.tau),-2.70*u,-.65*u))
  v=coil
  if clip=='Attack':
   if t<.45:v=coil.lerp(overhead,min(1,t/.40))
   elif t<.59625:v=overhead.lerp(extended,min(1,(t-.45)/.14625))
   elif t<.70:v=extended
   else:v=extended.lerp(coil,min(1,(t-.70)/.80))
  if death:v.z=max(.05,v.z)
  points.append(v)
 for i in range(32):
  n='whip.%02d'%i;delta=points[i+1]-points[i]
  if delta.length<.001:delta=Vector((.001,0,0))
  m=orient(n,points[i],points[i]+delta);m=m@Matrix.Diagonal((1,delta.length/lengths[n],1,1));arm.pose.bones[n].matrix=m
 bpy.context.view_layer.update()
 # Foot/back grounding uses evaluated skinned geometry, not the undeformed A-pose.
 evaluated=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());tmp=evaluated.to_mesh();low=min((evaluated.matrix_world@v.co).z for v in tmp.vertices);evaluated.to_mesh_clear()
 arm.pose.bones['root'].location.z-=low
 bpy.context.view_layer.update()
FPS=80;scene.render.fps=FPS
clips={'Idle':1.,'Walk':1.5,'Attack':1.5,'Howl':3.,'Death':1.4}
arm.animation_data_create();actions={}
for name,duration in clips.items():
 act=bpy.data.actions.new(name);arm.animation_data.action=act;act.use_fake_user=True;actions[name]=act
 times=[i/FPS for i in range(round(duration*FPS)+1)]
 if name=='Attack':times=sorted(set(times+[.59625]))
 for t in times:
  pose(t,name)
  for pb in arm.pose.bones:
   for channel in ['location','rotation_quaternion','scale']:pb.keyframe_insert(channel,frame=t*FPS,group=pb.name)
 for slot in act.slots:
  for layer in act.layers:
   for strip in layer.strips:
    bag=strip.channelbag(slot)
    if bag:
     for fc in bag.fcurves:
      for key in fc.keyframe_points:key.interpolation='LINEAR'
arm.animation_data.action=actions['Idle'];scene.frame_set(0)
scene.frame_start=0;scene.frame_end=240
report={'height_m':2.6,'body_faces':len(mesh.data.polygons),'bones':len(defs),'max_weights':4,'clips':clips,'whip_contact_s':.59625,'walk_reference_speed_mps':.40/(1.5*.62),'in_place':True,'forward':'Blender -Y; glTF +Z','reference':'reference-contract.md'}
(ROOT/'rig-report.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'foreman-rigged.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in [mesh,whip,arm]:o.select_set(True)
bpy.context.view_layer.objects.active=arm
bpy.ops.export_scene.gltf(filepath=str(ROOT/'foreman-preview.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,export_force_sampling=True,export_frame_step=1,export_def_bones=True)
scene.render.resolution_x=640;scene.render.resolution_y=640;scene.cycles.samples=8
camera=scene.camera;camera.data.ortho_scale=4.4;camera.location=(4,-6,3);camera.rotation_euler=(Vector((0,-.25,1.25))-camera.location).to_track_quat('-Z','Y').to_euler()
for name,t in [('Idle',0),('Walk',.35),('Attack',.59625),('Howl',1.5),('Death',1.4)]:
 arm.animation_data.action=actions[name];scene.frame_set(int(t*FPS),subframe=t*FPS-int(t*FPS));scene.render.filepath=str(ROOT/('pose-'+name+'.png'));bpy.ops.render.render(write_still=True)
print(json.dumps(report),flush=True)
