"""M08 fitted canine-derived rig, surface-constrained skin, authored actions.
Retains the V02 mesh/UV/materials; no decimation, renders or gameplay tests.
"""
import bpy, json, math, shutil, hashlib, sys
from pathlib import Path
import numpy as np
from mathutils import Matrix, Vector, Quaternion

PROJECT=Path('D:/FPS3D/FPSGAME')
BASE=PROJECT/'SourceAssets/Monsters/LurkerM08'
OUT=BASE/'CanineRigV03_20261004'; OUT.mkdir(exist_ok=True)
ANIM=OUT/'Animations';ANIM.mkdir(exist_ok=True)
OLD=json.loads((BASE/'ProductionV01_20261004/authoring.json').read_text(encoding='utf-8'))
DONOR=json.loads((OUT/'canine_source.json').read_text(encoding='utf-8'))
SOURCE=BASE/'ProductionV01_20261004/M08_Rigged_Animated_V01.blend'
REUSE_SKIN='--actions-only' in sys.argv
if REUSE_SKIN:
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'M08_CanineRig_Skin_V03.blend'))
    scene=bpy.context.scene;scene.render.fps=120;scene.render.fps_base=1
    obj=bpy.data.objects['SK_LurkerM08'];rig=bpy.data.objects['Armature'];arm=rig.data
    mod=next(m for m in obj.modifiers if m.type=='ARMATURE')
    prior=json.loads((OUT/'authoring.json').read_text(encoding='utf-8'))
    spec=prior['bones'];by={r['name']:r for r in spec}
    coords=np.empty((len(obj.data.vertices),0))
    rig.animation_data_clear()
    for action in list(bpy.data.actions):bpy.data.actions.remove(action)
else:
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    scene=bpy.context.scene;scene.render.fps=120;scene.render.fps_base=1
    obj=bpy.data.objects['SK_LurkerM08']
    obj.parent=None;obj.matrix_world=Matrix.Identity(4)
    for m in list(obj.modifiers):
        if m.type=='ARMATURE':obj.modifiers.remove(m)
    for other in list(bpy.data.objects):
        if other!=obj:bpy.data.objects.remove(other,do_unlink=True)
    obj.vertex_groups.clear()
    for a in list(bpy.data.actions):bpy.data.actions.remove(a)
    spec=[dict(r) for r in OLD['bones']]
    by={r['name']:r for r in spec}
    SCALE=OLD['scale']
    # Reconstruct original modelling coordinates from the known fitted pelvis.
    offset=Vector(by['pelvis']['head'])/SCALE-Vector((0,.52,-.055))
    def point(x,y,z):return (Vector((x,y,z))+offset)*SCALE
    def append(name,head,tail,parent,region):
        r=dict(name=name,head=list(head),tail=list(tail),parent=parent,region=region,deform=True)
        spec.append(r);by[name]=r
    # Keep the physical/attack bone interface, but subdivide the deforming arch.
    for side,s in [('L',1),('R',-1)]:
        for n,yy,zz in [('front',-.24,.24),('rear',.41,.275)]:
            row=by['arch_'+n+'.'+side]
            oldtail=Vector(row['tail']);row['tail']=list(point(s*.118,yy,zz))
            append('arch_'+n+'_mid.'+side,Vector(row['tail']),oldtail,row['name'],'arch')
        append('arch_crown.'+side,point(s*.085,-.08,.36),point(s*.085,.23,.38),'arch_crown','arch')
        for a,b in [('upperarm','forearm'),('forearm','hand')]:
            h=Vector(by[a+'.'+side]['head']);t=Vector(by[b+'.'+side]['head'])
            append(a+'_twist.'+side,h.lerp(t,.5),t,a+'.'+side,'front_'+side)
        for name,parent,child,region in [('elbow_support','upperarm','forearm','front_'),('knee_support','thigh','calf','rear_')]:
            h=Vector(by[child+'.'+side]['head'])
            append(name+'.'+side,h,h+Vector((0,0,.07)),parent+'.'+side,region+side)

    arm=bpy.data.armatures.new('M08_CanineFitted_V03')
    rig=bpy.data.objects.new('Armature',arm);scene.collection.objects.link(rig)
    rig.show_in_front=True;bpy.context.view_layer.objects.active=rig;rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for r in spec:
        b=arm.edit_bones.new(r['name']);b.head=r['head'];b.tail=r['tail'];b.use_deform=r['deform']
        if r['parent']:b.parent=arm.edit_bones[r['parent']]
        d=(b.tail-b.head).normalized();b.align_roll(Vector((1,0,0)) if abs(d.x)<.8 else Vector((0,0,1)))
    bpy.ops.object.mode_set(mode='OBJECT')
    for label,match in [('Axial body',('body',)),('Oral complex',('head','jaw','anchor')),
                        ('Forelimbs',('front_','finger_')),('Hindlimbs',('rear_',)),('Continuous arch',('arch',))]:
        col=arm.collections.new(label)
        for r in spec:
            if r['region'].startswith(match):col.assign(arm.bones[r['name']])

    print('M08_V03: authoring compartment skin and welded surface transitions',flush=True)
    coords=np.empty(len(obj.data.vertices)*3,dtype=np.float32);obj.data.vertices.foreach_get('co',coords);coords=coords.reshape(-1,3)
    raw=coords/SCALE-np.array(offset);x,y,z=raw.T;ax=np.abs(x)
    def smooth(a,b,v):
        t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)
    deforms=[r for r in spec if r['deform']];names=[r['name'] for r in deforms]
    W=np.zeros((len(coords),len(deforms)),dtype=np.float32)
    # Explicit shared compartment gates. Unlike V01, body/head cannot compete
    # freely for every vertex on a folded limb or finger.
    arch=smooth(.015,.145,z)
    head=(1-smooth(-.64,-.43,y))*(1-smooth(.21,.31,ax))*(1-arch)
    front=smooth(.16,.30,ax)*(1-smooth(-.17,.04,y))*(1-smooth(.005,.085,z))*(1-head)*(1-arch)
    rear=smooth(.16,.29,ax)*smooth(.10,.34,y)*(1-smooth(.025,.105,z))*(1-arch)
    body=np.maximum(0.,1-np.maximum.reduce([arch,head,front,rear]))
    # Soft tissue under the oral midline belongs to jaw; upper palate/teeth stay
    # with head. Transition is behind the mouth, not through its visible teeth.
    jaw=(1-smooth(-.67,-.605,y))*(1-smooth(-.225,-.185,z))
    for i,r in enumerate(deforms):
        a=np.array(r['head']);b=np.array(r['tail']);d=b-a
        u=np.clip(((coords-a)@d)/np.dot(d,d),0,1)
        dist=np.linalg.norm(coords-(a+u[:,None]*d),axis=1)
        reg=r['region'];n=r['name'];mask=body.copy()
        if reg=='arch':
            mask=arch.copy()
            if n.endswith('.L'):mask*=smooth(-.055,.055,x)
            elif n.endswith('.R'):mask*=1-smooth(-.055,.055,x)
            else:mask*=1-smooth(.035,.105,ax)
        elif reg=='head':mask=head*(1-jaw)
        elif reg=='jaw':mask=head*jaw
        elif reg.startswith(('front_','finger_','rear_')):
            mask=(rear if reg.startswith('rear_') else front).copy()
            mask*=smooth(-.015,.075,x*(1 if reg.endswith('L') else -1))
            if reg.startswith('finger_'):mask*=1-smooth(-.755,-.655,y)
            elif n.startswith(('scapula','upperarm')):mask*=smooth(-.64,-.43,y)
            elif n.startswith('forearm'):mask*=smooth(-.79,-.65,y)
            if '_support' in n:
                dist=np.linalg.norm(coords-a,axis=1)
                mask*=.25*(1-smooth(.075,.16,dist))
            if '_twist' in n:mask*=.65
        W[:,i]=mask/(np.square(dist)+(.035*SCALE)**2)**1.65
    W/=np.maximum(W.sum(axis=1,keepdims=True),1e-20)
    # Weld coincident UV vertices for weight computation only; preserve mesh,
    # loops, UVs, custom normals and topology exactly in the exported surface.
    _,first,inverse=np.unique(np.round(coords,5),axis=0,return_index=True,return_inverse=True)
    nv=len(first);count=np.bincount(inverse,minlength=nv).astype(np.float32)
    seed=np.empty((nv,len(deforms)),dtype=np.float32)
    for j in range(len(deforms)):seed[:,j]=np.bincount(inverse,weights=W[:,j],minlength=nv)/count
    del W
    ed=np.empty(len(obj.data.edges)*2,dtype=np.int32);obj.data.edges.foreach_get('vertices',ed)
    ed=inverse[ed.reshape(-1,2)];ed=np.unique(np.sort(ed,axis=1),axis=0);ed=ed[ed[:,0]!=ed[:,1]]
    aa,bb=ed.T
    length=np.linalg.norm(coords[first[aa]]-coords[first[bb]],axis=1)
    conductance=1/np.maximum(length,.002)
    degree=np.bincount(aa,weights=conductance,minlength=nv)+np.bincount(bb,weights=conductance,minlength=nv)
    degree=np.maximum(degree,1)
    # Screened harmonic surface relaxation: retains anatomical seed regions while
    # making joint/UV-seam transitions continuous along actual surface edges.
    for j in range(len(deforms)):
        base=seed[:,j].copy();v=base.copy()
        for iteration in range(20):
            avg=(np.bincount(aa,weights=v[bb]*conductance,minlength=nv)+
                 np.bincount(bb,weights=v[aa]*conductance,minlength=nv))/degree
            v=.18*base+.82*avg
        seed[:,j]=v
        if j%18==0:print('M08_SKIN',j,'/',len(deforms),flush=True)
    seed/=np.maximum(seed.sum(axis=1,keepdims=True),1e-20)
    top=np.argpartition(seed,-4,axis=1)[:,-4:]
    chosen=np.take_along_axis(seed,top,axis=1);chosen/=np.maximum(chosen.sum(axis=1,keepdims=True),1e-20)
    units=np.rint(chosen*4095).astype(np.int32)
    units[np.arange(nv),np.argmax(units,axis=1)]+=4095-units.sum(axis=1)
    top=top[inverse];units=units[inverse]
    for i,n in enumerate(names):
        group=obj.vertex_groups.new(name=n);rows,cols=np.where(top==i);values=units[rows,cols]
        for value in np.unique(values):
            if value>0:group.add(rows[values==value].tolist(),float(value)/4095.,'REPLACE')
    del seed,top,chosen,units
    mod=obj.modifiers.new('M08 anatomical skin V03','ARMATURE');mod.object=rig
    mod.use_deform_preserve_volume=False;obj.parent=rig

def smooth(a,b,v):
    t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)

NAMES=[b.name for b in arm.bones];PARENT={b.name:b.parent.name if b.parent else None for b in arm.bones}
REST={b.name:b.matrix_local.copy() for b in arm.bones}
LOCAL={n:REST[PARENT[n]].inverted()@REST[n] if PARENT[n] else REST[n].copy() for n in NAMES}
def fk(local):
    w={}
    for n in NAMES:w[n]=w[PARENT[n]]@local[n] if PARENT[n] else local[n].copy()
    return w
def world(local,n,m):local[n]=fk(local)[PARENT[n]].inverted()@m if PARENT[n] else m.copy()
def orient(local,n,q):
    w=fk(local);m=Matrix.LocRotScale(w[n].translation,q,Vector((1,1,1)));world(local,n,m)
def aim(local,n,d,child=None):
    ref=(REST[child].translation-REST[n].translation) if child else Vector(by[n]['tail'])-REST[n].translation
    orient(local,n,ref.normalized().rotation_difference(d.normalized())@REST[n].to_quaternion())
def turn(local,n,a,axis=(1,0,0)):
    orient(local,n,Quaternion(Vector(axis),a)@fk(local)[n].to_quaternion())
def move_world(local,n,v):
    w=fk(local)[n];w.translation+=v;world(local,n,w)
def ease(x):x=max(0.,min(1.,x));return x*x*x*(10+x*(-15+6*x))
def curve(t,keys):
    if t<=keys[0][0]:return keys[0][1]
    for (a,av),(b,bv) in zip(keys,keys[1:]):
        if t<=b:return av+(bv-av)*ease((t-a)/(b-a))
    return keys[-1][1]
def two_bone(local,chain,goal,pole):
    w=fk(local);a=w[chain[0]].translation
    l1=(REST[chain[1]].translation-REST[chain[0]].translation).length
    l2=(REST[chain[2]].translation-REST[chain[1]].translation).length
    d=goal-a;axis=d.normalized();r=max(abs(l1-l2)+.0001,min(d.length,(l1+l2)*.975))
    pp=pole-axis*pole.dot(axis);pp.normalize()
    along=(l1*l1-l2*l2+r*r)/(2*r)
    mid=a+axis*along+pp*math.sqrt(max(0,l1*l1-along*along))
    aim(local,chain[0],mid-a,chain[1]);aim(local,chain[1],a+axis*r-mid,chain[2])
def rest_pole(a,b,c):
    av,bv,cv=[REST[n].translation for n in (a,b,c)];axis=(cv-av).normalized()
    return (bv-av-axis*(bv-av).dot(axis)).normalized()
def fit_hock(local,side,foot,preferred):
    a,b,h,f=['%s.%s'%(n,side) for n in ('thigh','calf','ankle','hindfoot')]
    hip=fk(local)[a].translation;l1=(REST[b].translation-REST[a].translation).length
    l2=(REST[h].translation-REST[b].translation).length;l3=(REST[f].translation-REST[h].translation).length
    delta=foot-hip;distance=delta.length;axis=delta.normalized()
    reach=math.sqrt(l1*l1+l2*l2+2*l1*l2*math.cos(math.radians(15)))
    if distance>reach+l3-.001:distance=reach+l3-.001;foot=hip+axis*distance
    desired=foot-preferred*l3;rd=(desired-hip).length
    if rd>reach:
        along=(reach*reach-l3*l3+distance*distance)/(2*distance)
        center=hip+axis*along;off=desired-center;off-=axis*off.dot(axis)
        if off.length<1e-5:off=Vector((0,1,0))-axis*axis.y
        desired=center+off.normalized()*math.sqrt(max(0,reach*reach-along*along))
    two_bone(local,[a,b,h],desired,rest_pole(a,b,h))
    aim(local,h,foot-desired,f)

def source_position(row,n):return Vector(row[n]['head'])
def source_dir(row,a,b=None):return (source_position(row,b) if b else Vector(row[a]['tail']))-source_position(row,a)
def source_at(action,phase):
    rows=DONOR['actions'][action]['samples'];v=min(len(rows)-1,max(0,phase*(len(rows)-1)))
    i=min(len(rows)-2,int(v));f=v-i;r={}
    for n in rows[i]:
        a,b=rows[i][n],rows[i+1][n]
        q=Matrix(a['matrix']).to_quaternion().slerp(Matrix(b['matrix']).to_quaternion(),f)
        p=Vector(a['head']).lerp(Vector(b['head']),f)
        r[n]={'head':p,'tail':Vector(a['tail']).lerp(Vector(b['tail']),f),
              'matrix':Matrix.LocRotScale(p,q,Vector((1,1,1)))}
    return r
def filtered_source(action,phase,loop):
    rows=[]
    for dp,weight in [(-.022,.15),(0,.70),(.022,.15)]:
        p=(phase+dp)%1 if loop else max(0,min(1,phase+dp));rows.append((source_at(action,p),weight))
    result=rows[1][0]
    for n in result:
        for k in ('head','tail'):result[n][k]=sum((Vector(r[n][k])*w for r,w in rows),Vector())
    return result
BODY=[('pelvis','spine_01','Back','Torso',.38),('spine_01','spine_02','Torso','Torso2',.48),
      ('spine_02','chest','Torso2','Torso3',.50),('chest','neck','Torso3','Neck1',.40),
      ('neck','head','Neck2','Head',.32),('head',None,'Head',None,.25)]

def cycles(action,duration,speed):
    count=round(duration*120);rows=[filtered_source(action,i/count,True) for i in range(count)]
    tracks={}
    for side in ('L','R'):
        for front in (True,False):
            n=('FF' if front else 'FFB')+'.'+side
            pts=np.array([list(source_position(r,n)) for r in rows]);floor=pts[:,2].min()
            contact=1-smooth(.004,.055,pts[:,2]-floor);stance=contact>.18
            regions=[]
            for start in range(count):
                if stance[start] and not stance[(start-1)%count]:
                    indices=[];j=start
                    while stance[j%count] and len(indices)<count:indices.append(j);j+=1
                    regions.append(indices)
            slopes=[]
            for region in regions:
                ids=np.array([j for j in region if contact[j%count]>.85]);ix=ids%count
                if len(ids)>2:
                    centered=ids-ids.mean();slope=float(np.dot(centered,pts[ix,1]-pts[ix,1].mean())/np.dot(centered,centered)*120)
                    if slope>.1:slopes.append(slope)
            factor=speed/(sum(slopes)/len(slopes)) if slopes else .3
            mid=(pts[:,1].min()+pts[:,1].max())*.5
            dy=(pts[:,1]-mid)*factor
            # Bound reach for the mutant's short crouched hindquarters.
            limit=.33 if front else .31
            largest=max(abs(dy.min()),abs(dy.max()))
            if largest>limit:dy*=limit/largest
            dz=(pts[:,2]-floor)*(.24 if front else .21)
            dz=np.minimum(dz,.18 if front else .21)
            for region in regions:
                total=sum(contact[j%count] for j in region)
                center_t=sum(j*contact[j%count] for j in region)/total
                center_y=sum(dy[j%count]*contact[j%count] for j in region)/total
                for j in region:
                    ix=j%count;w=contact[ix]
                    dy[ix]=dy[ix]*(1-w)+(center_y+speed*(j-center_t)/120)*w
                    dz[ix]*=1-w
            tracks[(side,front)]=dict(dy=dy,dz=dz,contact=contact,regions=regions)
    return rows,tracks

def support_helpers(local):
    w=fk(local)
    for side in ('L','R'):
        for a,b in [('upperarm','forearm'),('forearm','hand')]:
            n=a+'_twist.'+side;an=a+'.'+side;bn=b+'.'+side
            da=w[an]@REST[an].inverted();db=w[bn]@REST[bn].inverted()
            q=da.to_quaternion().slerp(db.to_quaternion(),.30)
            pos=w[an].translation.lerp(w[bn].translation,.5)
            world(local,n,Matrix.LocRotScale(pos,q@REST[n].to_quaternion(),Vector((1,1,1))))
        for helper,a,b in [('elbow_support','upperarm','forearm'),('knee_support','thigh','calf')]:
            n=helper+'.'+side;an=a+'.'+side;bn=b+'.'+side
            qa=(w[an]@REST[an].inverted()).to_quaternion();qb=(w[bn]@REST[bn].inverted()).to_quaternion()
            world(local,n,Matrix.LocRotScale(w[bn].translation,qa.slerp(qb,.5)@REST[n].to_quaternion(),Vector((1,1,1))))
    # One continuous deformation field shared across both arch rails. Front
    # base exactly follows chest, rear base follows pelvis; no limb influence.
    front=w['chest']@REST['chest'].inverted();rear=w['pelvis']@REST['pelvis'].inverted()
    yf=REST['arch_front.L'].translation.y;yr=REST['arch_rear.L'].translation.y
    for n in [n for n in NAMES if n.startswith('arch_')]:
        t=ease((REST[n].translation.y-yf)/(yr-yf))
        p=(front@REST[n].translation).lerp(rear@REST[n].translation,t)
        q=front.to_quaternion().slerp(rear.to_quaternion(),t)
        world(local,n,Matrix.LocRotScale(p,q@REST[n].to_quaternion(),Vector((1,1,1))))

common=dict(use_selection=True,add_leaf_bones=False,use_armature_deform_only=False,
            axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE')
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);obj.select_set(True)
bpy.context.view_layer.objects.active=rig
if not REUSE_SKIN:
    bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_LurkerM08_CanineV03.fbx'),object_types={'ARMATURE','MESH'},
        bake_anim=False,use_mesh_modifiers=False,mesh_smooth_type='OFF',path_mode='AUTO',**common)
    # Save a recoverable rig/skin source before baking the action set.
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M08_CanineRig_Skin_V03.blend'))
mod.show_viewport=False;rig.animation_data_create()
clips={'Idle':(3.,True,'Idle_2_HeadLow'),'IdleAlert':(1.8,True,'Idle'),
       'Walk':(.9,True,'Walk'),'Run':(.6,True,'Gallop'),
       'AttackBite':(.85,False,'Attack'),'AttackPounce':(1.1,False,'Gallop_Jump'),
       'TraverseJump':(1.1,False,'Gallop_Jump'),
       'HitFront':(.55,False,'Idle_HitReact1'),'HitLeft':(.55,False,'Idle_HitReact2'),
       'HitRight':(.55,False,'Idle_HitReact2'),'Death':(1.4,False,'Death')}
report={'revision':'M08_CanineRigV03_20261004','source_mesh':str(SOURCE),
        'canine_source':DONOR['source'],'canine_license':DONOR['license'],'source_sha256':DONOR['sha256'],
        'bones':spec,'mesh':str(OUT/'SK_LurkerM08_CanineV03.fbx'), 'clips':{},
        'vertices':len(coords),'triangles':OLD['triangles'],'weights':'compartment constraints, welded screened surface diffusion, four influences',
        'reference_speeds_cm_s':{'Walk':100.,'Run':210.},'runtime_tested':False,'preview_rendered':False}
for role,(duration,loop,source) in clips.items():
    count=round(duration*120);scene.frame_start=1;scene.frame_end=count+1
    a=bpy.data.actions.new('A_M08_'+role+'_CanineV03');a.use_fake_user=True;rig.animation_data.action=a
    locomotion=role in ('Walk','Run');cycle,tracks=cycles(source,duration,1 if role=='Walk' else 2.1) if locomotion else (None,None)
    first=filtered_source(source,0,loop)
    ref=first if not locomotion else DONOR['rest']
    meanhip=sum(((source_position(r,'BackLeg.L')+source_position(r,'BackLeg.R'))*.5 for r in cycle),Vector())/count if locomotion else (source_position(first,'BackLeg.L')+source_position(first,'BackLeg.R'))*.5
    for index in range(count+1):
        t=index/120;phase=index/count
        p=phase
        if role=='AttackBite':p=curve(t,[(0,0),(.15,.16),(.30,.41),(.42,.53),(.60,.72),(.85,1)])
        if role in ('AttackPounce','TraverseJump'):p=curve(t,[(0,0),(.16,.17),(.36,.43),(.54,.68),(.72,.84),(1.1,1)])
        row=cycle[index%count] if locomotion else filtered_source(source,p,loop)
        local={n:m.copy() for n,m in LOCAL.items()}
        envelope=1. if loop else curve(t,[(0,0),(.10,1),(duration*.75,1),(duration,0)])
        if role=='Death':envelope=ease(t/.2)
        hip=(source_position(row,'BackLeg.L')+source_position(row,'BackLeg.R'))*.5
        dh=hip-meanhip
        body=Vector((dh.x*.14,dh.y*.24,dh.z*.22))*envelope
        if locomotion:body.z-=.022 if role=='Run' else .006
        if role in ('AttackPounce','TraverseJump'):
            # Actor owns airborne displacement. Pose adds compression and
            # landing load, never duplicates source root-height flight.
            body.y=curve(t,[(0,0),(.13,.05),(.30,-.035),(.56,-.02),(1.1,0)])
            body.z=curve(t,[(0,0),(.13,-.075),(.26,.015),(.48,.025),(.60,-.055),(.83,-.018),(1.1,0)])
        if role=='Death':body=Vector((.20*ease(t/.95),.015,-.32*ease(t/.95)))
        # Pelvis translation is in the container root's local basis. The
        # Blender root's Y axis points up; convert the authored world shift.
        local['pelvis'].translation+=REST['root'].inverted().to_3x3()@body
        for n,child,sa,sb,gain in BODY:
            rd=source_dir(ref,sa,sb).normalized();sd=source_dir(row,sa,sb).normalized()
            delta=rd.rotation_difference(sd)
            delta=Quaternion().slerp(delta,gain*envelope)
            targetdir=(REST[child].translation-REST[n].translation) if child else Vector(by[n]['tail'])-REST[n].translation
            aim(local,n,delta@targetdir,child)
        if role in ('HitLeft','HitRight'):
            turn(local,'chest',(.10 if role=='HitLeft' else -.10)*math.sin(math.pi*phase)*envelope,(0,1,0))
        if role=='Death':turn(local,'pelvis',.95*ease(t/.95),(0,1,0))
        jaw=-18.
        if role=='Idle':jaw=-18+1.3*math.sin(phase*math.tau)
        if role=='IdleAlert':jaw=-12.
        if role=='AttackBite':jaw=curve(t,[(0,-18),(.18,4),(.30,-32),(.42,-32),(.60,-22),(.85,-18)])
        if role=='AttackPounce':jaw=curve(t,[(0,-18),(.19,3),(.46,3),(.54,-32),(.64,-32),(.82,-22),(1.1,-18)])
        if role=='TraverseJump':jaw=-18
        if role=='Death':jaw=-18+10*ease(phase)
        turn(local,'jaw',math.radians(jaw))
        for side,sign in [('L',1),('R',-1)]:
            # Scapular glide precedes the elbow solve, so the forelimb is not
            # swinging from a fixed shoulder pin. The fingers retain their
            # mutant splay and broad support footprint.
            n='scapula.'+side
            d=source_position(row,'FrontShoulder.'+side)-source_position(ref,'FrontShoulder.'+side)
            glide=Vector((d.x*.08,max(-.045,min(.045,d.y*.15)),max(-.02,min(.025,d.z*.08))))*envelope
            move_world(local,n,glide)
            for front in (True,False):
                foot=('hand.' if front else 'hindfoot.')+side
                goal=REST[foot].translation.copy();contact=1.;swing=0.
                if locomotion:
                    tr=tracks[(side,front)];ii=index%count
                    goal+=Vector((0,float(tr['dy'][ii]),float(tr['dz'][ii])))
                    contact=float(tr['contact'][ii]);swing=1-contact
                elif role in ('AttackPounce','TraverseJump'):
                    if front:
                        goal.y+=curve(t,[(0,0),(.15,.04),(.28,-.18),(.48,-.17),(.62,-.06),(.91,-.015),(1.1,0)])
                        goal.z+=curve(t,[(0,0),(.16,0),(.26,.16),(.42,.12),(.55,0),(1.1,0)])
                    else:
                        goal.y+=curve(t,[(0,0),(.15,.035),(.27,.13),(.39,-.16),(.54,-.04),(.67,0),(1.1,0)])
                        goal.z+=curve(t,[(0,0),(.18,0),(.31,.12),(.44,.18),(.66,0),(1.1,0)])
                    contact=1-curve(t,[(0,0),(.16,0),(.23,1),(.45,1),(.55 if front else .66,0),(1.1,0)])
                    swing=1-contact
                elif role=='AttackBite' and front:
                    stagger=.0 if side=='L' else .065
                    tt=max(0,t-stagger)
                    goal.y+=curve(tt,[(0,0),(.12,0),(.27,-.065),(.49,-.065),(.72,-.01),(.85,0)])
                    goal.z+=curve(tt,[(0,0),(.12,0),(.21,.035),(.29,0),(.85,0)])
                    contact=1-smooth(.001,.015,goal.z-REST[foot].translation.z)
                elif role.startswith('Hit'):
                    # Three feet brace; one forward paw takes the recovery step.
                    active=(side=='L') if role!='HitRight' else (side=='R')
                    if front and active:
                        goal.y+=curve(t,[(0,0),(.10,.03),(.25,.07),(.55,0)])
                        goal.z+=curve(t,[(0,0),(.10,0),(.18,.03),(.29,0),(.55,0)])
                if role=='Death':
                    release=ease((t-(.18 if side=='R' else .34))/.46)
                    carried=fk(local)[foot].translation
                    goal=goal.lerp(carried,release);contact=1-release
                pawq=REST[foot].to_quaternion()
                if front:
                    # Wrist roll is restrained in support and folds on swing.
                    wrist_angle=math.radians(11)*swing
                    pawq=Quaternion(Vector((1,0,0)),wrist_angle)@pawq
                    pole=rest_pole('upperarm.'+side,'forearm.'+side,foot)
                    two_bone(local,['upperarm.'+side,'forearm.'+side,foot],goal,pole)
                else:
                    preferred=(REST[foot].translation-REST['ankle.'+side].translation).normalized()
                    sd=source_dir(row,'BackLowerLeg.'+side,'IKBackLeg.'+side).normalized()
                    rd=source_dir(ref,'BackLowerLeg.'+side,'IKBackLeg.'+side).normalized()
                    delta=Quaternion().slerp(rd.rotation_difference(sd),.36*envelope)
                    fit_hock(local,side,goal,delta@preferred)
                    pawq=Quaternion(Vector((1,0,0)),math.radians(7)*swing)@pawq
                orient(local,foot,pawq)
                if front:
                    for finger in range(1,6):
                        curl=math.radians((10+finger*1.2)*swing)
                        # Toe-off flexion follows paw release, not global time.
                        turn(local,f'finger{finger}_01.{side}',curl*.45)
                        turn(local,f'finger{finger}_02.{side}',curl)
                else:
                    for toe in range(1,4):turn(local,f'toe{toe}.{side}',math.radians(7)*swing)
        support_helpers(local)
        for n in NAMES:
            pb=rig.pose.bones[n];loc,q,s=(LOCAL[n].inverted()@local[n]).decompose()
            if index>0 and pb.rotation_quaternion.dot(q)<0:q.negate()
            pb.rotation_mode='QUATERNION';pb.location=loc;pb.rotation_quaternion=q;pb.scale=(1,1,1)
            for path in ('location','rotation_quaternion','scale'):pb.keyframe_insert(path,frame=index+1,group=n)
    scene.frame_set(1);bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    file=ANIM/(a.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),object_types={'ARMATURE'},bake_anim=True,
        bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True,bake_anim_step=1.,bake_anim_simplify_factor=0.,**common)
    contact=[.30,.42] if role=='AttackBite' else [.52,.64] if role=='AttackPounce' else [-1,-1]
    report['clips'][role]={'file':str(file),'seconds':duration,'frames':count+1,'loop':loop,'contact':contact,
                           'source':source,'adaptation':'anatomical control transfer and M08 contact/pose authoring'}
    (OUT/'authoring.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('M08_V03_ACTION_SAVED',role,flush=True)
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
mod.show_viewport=True;scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);rig.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M08_CanineRig_Animated_V03.blend'))
print('M08_V03_AUTHORING_SAVED',flush=True)
