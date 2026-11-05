"""Author native-grip M24 strikes; preserve the shared clip and gameplay clock."""
import bpy,json,gzip,math,bisect,ast,struct
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion,Euler
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent;S=O.parent
D=json.load(gzip.open(O/'input_motion.json.gz','rt'));names=D['names'];parents=D['parents'];indices={n:i for i,n in enumerate(names)}
K=Matrix.Diagonal((1,-1,1,1))
source=json.loads((S/'M24ArmRebuild20261027/source_after.json').read_text())
rest={n:Matrix(m) for n,m in source['rest'].items()}
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
C=Matrix(json.loads((S/'M24Hold20261027/hip-calibration.json').read_text())['hip_transform'])@Matrix.Diagonal((100,-100,100,1));CI=C.inverted()
G=json.loads((S/'M24ReloadDonor20261101/kaitlin_skin_geometry.json').read_text())

def transform(v):return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:10]))
native={}
for n,v in G['rest'].items():
    m=K@transform(v)@K
    for i in range(3):
        for j in range(4):m[i][j]*=.01
    native[n]=m
def smooth(x):
    x=max(0.,min(1.,x));return x*x*x*(10+x*(-15+6*x))
def envelope(t):return smooth(t/.12)*(1-smooth((t-.58)/.32))
def under(n,parent):
    while n:
        if n==parent:return True
        n=parents.get(n)
    return False
def lerp(a,b,w):
    p,q,s=a.decompose();pp,qq,ss=b.decompose();return Matrix.LocRotScale(p.lerp(pp,w),q.slerp(qq,w),s.lerp(ss,w))
def sampled(values,times,t):
    def parts(v):return Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:10])
    if len(times)==1:return parts(values[:10])
    i=max(0,min(len(times)-2,bisect.bisect_right(times,t)-1));w=max(0.,min(1.,(t-times[i])/(times[i+1]-times[i])))
    a,b=parts(values[10*i:10*i+10]),parts(values[10*i+10:10*i+20])
    return a[0].lerp(b[0],w),a[1].slerp(b[1],w),a[2].lerp(b[2],w)
def entry(family,role):return next(c for c in D['profiles'][family]['clips'] if c['base'].split('.')[-1]=='A_M24_'+role)
def raw(data,t,n):
    f=max(0.,min(t*data['fps'],data['keys']-1));a=int(f);b=min(a+1,data['keys']-1)
    return lerp(transform(data['poses'][str(a)][indices[n]]),transform(data['poses'][str(b)][indices[n]]),f-a)
def compose(e,t):
    tracks={v['bone']:v for v in e['tracks']};data=D['clips'][e['base']];out={};local={}
    for n in names:
        p,q,s=raw(data,t,n).decompose()
        if n in tracks:
            tr=tracks[n];dp,dq,ds=sampled(tr['values'],tr['times'],t);p+=dp;q=dq@q;s+=ds
        local[n]=K@Matrix.LocRotScale(p,q,s)@K;out[n]=out[parents[n]]@local[n] if parents[n] else local[n]
    return out,local
def frame(x,z):
    x=x.normalized();z=(z-x*z.dot(x)).normalized();return Matrix((x,z.cross(x),z)).transposed()
def wrap(v):return (v+math.pi)%(2*math.pi)-math.pi

# Read physical assembly geometry for the stock endpoint and arm-clearance fit.
bpy.ops.wm.read_factory_settings(use_empty=True)
assembly=json.loads((O/'assembly.json').read_text());geometry={}
for key,spec in assembly.items():
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=spec['fbx'],use_custom_normals=True)
    obs=[ob for ob in set(bpy.data.objects)-before if ob.type=='MESH'];points=[];faces=[]
    for ob in obs:
        offset=len(points);points.extend([ob.matrix_world@v.co for v in ob.data.vertices]);ob.data.calc_loop_triangles()
        faces.extend([tuple(offset+i for i in tri.vertices) for tri in ob.data.loop_triangles])
    geometry[key]=(points,faces)
    for ob in list(set(bpy.data.objects)-before):bpy.data.objects.remove(ob,do_unlink=True)
stock_points=geometry['stock'][0];rear=min(v.y for v in stock_points)
pad=[v for v in stock_points if v.y<rear+.006];pad_source=sum(pad,Vector())/len(pad)
stock_local=rest['WPN_root'].inverted()@pad_source
trees={}
for kind in ('Default','balanced','phantom','stable'):
    vs=[];fs=[]
    for key in ('stock','front','grip_'+kind):
        p,f=geometry[key];off=len(vs);vs.extend(p);fs.extend([tuple(off+i for i in face) for face in f])
    trees[kind]=BVHTree.FromPolygons(vs,fs,all_triangles=True)

def arm(row,idle,side,weight,phi,tree=None):
    u,l,h=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
    S0=idle[u].translation;E0=idle[l].translation;H0=idle[h].translation
    A=(E0-S0).length;B=(H0-E0).length;H=row[h].translation
    shift=CI.to_3x3()@Vector((.8*weight,0.,-1.2*weight))
    S1=S0+shift;v=H-S1;d=v.length
    stretch=max(0.,d-(A+B)*.955)
    shift+=v.normalized()*stretch;S1=S0+shift;v=H-S1;d=v.length;axis=v.normalized()
    along=(A*A-B*B+d*d)/(2*max(d,.00001));radius=math.sqrt(max(1e-10,A*A-along*along));center=S1+axis*along
    preferred=E0-S0;preferred=(preferred-axis*preferred.dot(axis)).normalized()
    down=CI.to_3x3()@Vector((0.,-14. if side=='l' else 14.,-30.));down=(down-axis*down.dot(axis)).normalized()
    preferred=preferred.lerp(down,.68*weight).normalized()
    E=center+Quaternion(axis,phi)@preferred*radius
    U=E-S1;F=H-E;N=U.cross(F).normalized()
    Uref=native[l].translation-native[u].translation;Fref=native[h].translation-native[l].translation;Nref=Uref.cross(Fref).normalized()
    du=(frame(U,N)@frame(Uref,Nref).transposed()).to_quaternion();dl=(frame(F,N)@frame(Fref,Nref).transposed()).to_quaternion()
    uq=du@native[u].to_quaternion();lq=dl@native[l].to_quaternion()
    hand_delta=row[h].to_quaternion()@native[h].to_quaternion().inverted()
    delta=dl.inverted()@hand_delta
    tau=wrap(2*math.atan2(Vector((delta.x,delta.y,delta.z)).dot(Fref.normalized()),delta.w))
    wanted=hand_delta@Fref.normalized();bend=F.normalized().angle(wanted)
    ec,hc,sc=C@E,C@H,C@S1
    inside=max(0.,ec.y+5.) if side=='l' else max(0.,5.-ec.y)
    high=max(0.,ec.z-min(hc.z,sc.z)+2.)
    roll_change=wrap(tau-idle_roll.get(side,tau))
    score=35*bend*bend+180*max(0.,bend-math.radians(45))**2
    score+=28*roll_change*roll_change+100*max(0.,abs(roll_change)-math.radians(65))**2+80*max(0.,abs(tau)-math.radians(125))**2
    score+=weight*(.025*inside*inside+.03*high*high)+.5*phi*phi+shift.length_squared*900+max(0.,shift.length-.045)**2*80000
    if tree:
        inverse=rest['WPN_root']@row['WPN_root'].inverted()
        for t,radius_cm in ((.18,1.2),(.36,2.3),(.58,3.),(.78,3.1)):
            dist=tree.find_nearest(inverse@H.lerp(E,t))[3]*100
            score+=12*max(0.,radius_cm-dist)**2
    return {'score':score,'S':S1,'E':E,'uq':uq,'lq':lq,'du':du,'dl':dl,'tau':tau,'shift':shift,'bend_deg':math.degrees(bend),'phi':phi}

def pick_arm(row,idle,side,w,tree):
    if w<1e-8:return arm(row,idle,side,w,0.,tree)
    cap=math.radians(55)*w
    best=min((arm(row,idle,side,w,cap*i/8,tree) for i in range(-8,9)),key=lambda v:v['score'])
    for step in (cap/16,cap/32):
        best=min((arm(row,idle,side,w,max(-cap,min(cap,best['phi']+step*i)),tree) for i in (-1,0,1)),key=lambda v:v['score'])
    return best

def write_arm(row,idle,side,w,result):
    u,l,h=[n+'_'+side for n in ('upperarm','lowerarm','hand')];S1,E=result['S'],result['E'];H=row[h].translation
    us=(idle[l].translation-idle[u].translation).normalized().rotation_difference((E-S1).normalized())
    ls=(idle[h].translation-idle[l].translation).normalized().rotation_difference((H-E).normalized())
    uq=(us@idle[u].to_quaternion()).slerp(result['uq'],w);lq=(ls@idle[l].to_quaternion()).slerp(result['lq'],w)
    row['clavicle_'+side]=idle['clavicle_'+side].copy();row['clavicle_'+side].translation+=result['shift']
    row[u]=Matrix.LocRotScale(S1,uq,idle[u].to_scale());row[l]=Matrix.LocRotScale(E,lq,idle[l].to_scale())
    for n in names:
        if n in (u,l) or under(n,h):continue
        if under(n,u):
            local=idle[parents[n]].inverted()@idle[n];pos=row[parents[n]]@local.translation
            upper=n.startswith('upperarm');swing=us if upper else ls
            q0=swing@idle[n].to_quaternion()
            q1=(result['du'] if upper else result['dl'])@native[n].to_quaternion()
            if n.startswith('lowerarm_twist'):
                q1=Quaternion((H-E).normalized(),result['tau']*(1. if '_01_' in n else .5))@q1
            row[n]=Matrix.LocRotScale(pos,q0.slerp(q1,w),idle[n].to_scale())

KEYS=(0.,.05,.15,.25,.325,.46,.60,.74,.9);FPS=200
patch={};final={};idle_roll={};report={'duration':.9,'contact':.25,'sample_rate':FPS,'profiles':{},'runtime_tested':False,'rendered':False,'method':'Current family idle contact, native arm hinge and fixed bone lengths; independent pistol grips never return to absent stock neck.'}
for family in D['profiles']:
    idle,_=compose(entry(family,'idle'),0.);old_entry=entry(family,'quick_melee');old_idle,_=compose(old_entry,0.)
    independent=family.startswith('skeleton_');kind=next((v for v in ('balanced','phantom','stable') if family.endswith('_'+v)),'Default')
    tree=trees[kind] if independent else None
    idle_roll={side:arm(idle,idle,side,0.,0.)['tau'] for side in ('l','r')}
    current_pad=C@(idle['WPN_root']@stock_local);old_pad=C@old_idle['WPN_StockContact'].translation
    def group(t,offset):
        old,_=compose(old_entry,t);w=envelope(t)
        if not independent:
            row={n:m.copy() for n,m in old.items()};move=row['WPN_root']@idle['WPN_root'].inverted()
            # Keep the established club regrip; only its boundary follows the
            # current idle arm/hand rather than the historical author snapshot.
            edge=1-smooth(t/.045) if t<.45 else smooth((t-.72)/.18)
            for n in names:
                if n.startswith('clavicle_') or under(n,'upperarm_l') or under(n,'upperarm_r'):row[n]=lerp(row[n],move@idle[n],edge)
            row['ik_hand_l']=row['hand_l'].copy();row['ik_hand_r']=row['hand_r'].copy();return row
        if .25<t<.46:
            # Carry the loaded impact pose into a short rigid rebound. The old
            # stock-neck follow-through is not a valid second pistol-grip pose.
            hit,_=compose(old_entry,.25);recover,_=compose(old_entry,.46)
            recovery=smooth((t-.325)/.135)
            for n in ('WPN_root','WPN_StockContact'):old[n]=lerp(hit[n],recover[n],recovery)
            old['WPN_StockContact'].translation+=CI.to_3x3()@Vector((-2.,0.,-1.))*(smooth((t-.25)/.075)*(1-recovery))
        old_motion=old['WPN_root']@old_idle['WPN_root'].inverted()
        rot=CI.to_3x3()@Euler(tuple(math.radians(v) for v in offset[:3]),'XYZ').to_matrix()@C.to_3x3()
        rotation=rot.to_quaternion()@old_motion.to_quaternion()
        target=C@old['WPN_StockContact'].translation+(current_pad-old_pad)*(1-w)+Vector(offset[3:])
        world_target=CI@target;source_point=idle['WPN_root']@stock_local
        move=Matrix.LocRotScale(world_target-rotation@source_point,rotation,Vector((1,1,1)))
        row={n:m.copy() for n,m in idle.items()}
        for n in names:
            if under(n,'WPN_root') or under(n,'hand_l') or under(n,'hand_r'):row[n]=move@idle[n]
        row['WPN_StockContact'].translation=row['WPN_root']@stock_local
        row['ik_hand_l']=row['hand_l'].copy();row['ik_hand_r']=row['hand_r'].copy();return row
    controls=[]
    for t in KEYS:
        w=envelope(t);offset=[0.]*6
        if independent and abs(t-.325)<1e-8:
            # Impact and follow-through share one grip solution. Independently
            # optimizing them can choose opposite arm/weapon roll branches.
            offset=controls[-1]['offset'].copy()
        elif independent and w>1e-8:
            previous=controls[-1]['offset']
            def score(v):
                row=group(t,v)
                barrel=(C.to_3x3()@(row['WPN_root']@rest['WPN_root'].inverted()).to_3x3()@Vector((0,1,0))).normalized()
                strike=smooth((t-.08)/.12)*(1-smooth((t-.40)/.22))
                return sum(pick_arm(row,idle,side,w,tree)['score'] for side in ('l','r'))+sum((x/55)**2 for x in v[:3])*.6+sum(((x-y)/40)**2 for x,y in zip(v[:3],previous[:3]))*3+sum(x*x for x in v[3:])*.025+100*strike*max(0.,barrel.x)**2
            def bounded(v):
                out=list(v)
                for axis in range(6):
                    cap=((75. if axis==2 else 90.) if axis<3 else (10. if axis==3 else 14.))*w
                    low,high=-cap,cap
                    if axis<3:low=max(low,previous[axis]-40);high=min(high,previous[axis]+40)
                    out[axis]=max(low,min(high,out[axis]))
                return out
            seeds=[bounded([x*w,y*w,z*w,0.,6*w,-6*w]) for x in (-60.,0.,60.) for y in (-60.,0.,60.) for z in (-50.,0.,50.)]+[bounded(previous)]
            offset=min(seeds,key=score)
            for step in (16.,8.,4.,2.):
                for axis in (3,4,5,0,1,2,0,3,4,5):
                    choices=[]
                    for sign in (-1,0,1):
                        v=offset.copy();v[axis]+=step*sign*(.375 if axis>=3 else 1.);choices.append(bounded(v))
                    offset=min(choices,key=score)
        row=group(t,offset);sides=('l','r') if independent else ()
        solved={side:pick_arm(row,idle,side,w,tree) for side in sides}
        poles={side:value['phi'] for side,value in solved.items()}
        controls.append({'time':t,'offset':offset,'poles':poles,'fit':{side:{'shoulder_shift_mm':v['shift'].length*1000,'wrist_axis_bend_deg':v['bend_deg'],'forearm_roll_deg':math.degrees(v['tau'])} for side,v in solved.items()}})
    rows=[];times=[i/FPS for i in range(181)];tracks={n:[] for n in names};last={};roll_hint={}
    for t in times:
        i=max(0,min(len(KEYS)-2,bisect.bisect_right(KEYS,t)-1));a,b=controls[i:i+2];mix=smooth((t-a['time'])/(b['time']-a['time']))
        offset=[x*(1-mix)+y*mix for x,y in zip(a['offset'],b['offset'])];row=group(t,offset);w=envelope(t)
        for side in a['poles']:
            phi=a['poles'][side]*(1-mix)+b['poles'][side]*mix
            result=arm(row,idle,side,w,phi,tree)
            if side in roll_hint:result['tau']+=2*math.pi*round((roll_hint[side]-result['tau'])/(2*math.pi))
            roll_hint[side]=result['tau'];write_arm(row,idle,side,w,result)
        if t==0 or abs(t-.9)<1e-8:
            marker=row['WPN_StockContact'].copy();row={n:m.copy() for n,m in idle.items()}
            if independent:row['WPN_StockContact']=marker
        rows.append(row)
        for n in names:
            local=row[parents[n]].inverted()@row[n] if parents[n] else row[n]
            p,q,scale=(K@local@K).decompose();bp,bq,bs=raw(D['clips'][old_entry['base']],t,n).decompose();dq=q@bq.inverted();dq.normalize()
            if n in last and dq.dot(last[n])<0:dq.negate()
            last[n]=dq.copy();tracks[n].extend([*(p-bp),dq.x,dq.y,dq.z,dq.w,*(scale-bs)])
    compact=[]
    for n,v in tracks.items():
        seq=[v[i:i+10] for i in range(0,len(v),10)];constant=all(max(abs(x-y) for x,y in zip(a,seq[0]))<2e-7 for a in seq)
        compact.append({'bone':n,'times':[0.] if constant else times,'values':seq[0] if constant else v})
    patch[family]={'base':old_entry['base'],'duration':old_entry['duration'],'tracks':compact};final[family]=rows
    report['profiles'][family]={'grip':kind if independent else 'factory club regrip retained','controls':controls,'keys':len(times)}
    print('M24_CURRENT_GRIP_MELEE_AUTHORED',family,flush=True)
with gzip.open(O/'quick_melee_patch.json.gz','wt',compresslevel=1) as f:json.dump(patch,f,separators=(',',':'))

# Native editable rig plus the current V9 skin and runtime-equivalent JC tracks.
import numpy as np
bpy.ops.wm.open_mainfile(filepath=str(S/'M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig'];r.animation_data_clear();r.matrix_world=Matrix.Identity(4)
for ob in s.objects:
    if ob.type=='MESH' and 'Arms' in ob.name:ob.hide_set(True);ob.hide_render=True
P=np.asarray([(v[0]*.01,-v[1]*.01,v[2]*.01) for v in G['positions']])
me=bpy.data.meshes.new('M24 current native V9 skin');me.from_pydata(P.tolist(),[],[list(reversed(f['vertices'])) for f in G['faces']]);me.update()
skin=bpy.data.objects.new('M24_CurrentV9_Arms',me);s.collection.objects.link(skin)
for i,ws in G['weights'].items():
    for n,w in ws.items():
        vg=skin.vertex_groups.get(n) or skin.vertex_groups.new(name=n);vg.add([int(i)],w,'REPLACE')
modifier=skin.modifiers.new('Native_M24_Armature','ARMATURE');modifier.object=r
morphs=np.load(S/'M24ThumbRootRoute20261102/native_correctives.npz');skin.shape_key_add(name='Basis')
for n in morphs.files:
    key=skin.shape_key_add(name=n);key.data.foreach_set('co',(P+morphs[n]).reshape(-1))
exec(compile((S/'M24ThumbRootRoute20261102/corrective_weights.py').read_text(),'native JC weights','exec'))
node=next(n for n in ast.parse((S/'M24Hold20261027/author_hold.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='bake')
node.body=[n for n in node.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='twists')]
report['clips']={}
exec(compile(ast.unparse(node).replace('s.render.fps = 30','s.render.fps = 200').replace('(len(rows) - 1) / 30','(len(rows) - 1) / 200'),'native editable baking','exec'))
for family,rows in final.items():
    role='QuickMeleeGrip_'+family;bake(role,rows);action=r.animation_data.action
    shape_action=bpy.data.actions.new(action.name+'_JC');shape_action.use_fake_user=True;skin.data.shape_keys.animation_data_create();skin.data.shape_keys.animation_data.action=shape_action;action['corrective_action']=shape_action.name
    for i,row in enumerate(rows):
        weights,_=corrective_weights(row,morphs.files)
        for n in morphs.files:
            key=skin.data.shape_keys.key_blocks[n];key.value=weights.get(n,0.);key.keyframe_insert('value',frame=i)
    print('M24_MELEE_EDITABLE_SAVED_ACTION',family,flush=True)
r.animation_data.action=bpy.data.actions['A_M24_QuickMeleeGrip_skeleton_base'];r.animation_data.action_slot=r.animation_data.action.slots[0]
skin.data.shape_keys.animation_data.action=bpy.data.actions[r.animation_data.action['corrective_action']]
s.frame_start=0;s.frame_end=180;s.render.fps=FPS;s.frame_set(0)
import runpy
runpy.run_path(str(O/'assembly_source.py'))['attach_current_assembly'](r)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_QuickMelee_CurrentGrip_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_CURRENT_GRIP_MELEE_AUTHOR_COMPLETE',flush=True)
