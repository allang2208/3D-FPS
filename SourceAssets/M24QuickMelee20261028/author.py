"""Author a compact, stock-led M24 bash with its own native grip and arm support.

Produces the current base/mag10 profile deltas and an editable native rig.
No renderer, gameplay launch or acceptance checks are invoked.
"""
from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text().split("if __name__=='__main__':")[0],'library','exec'))
layout=json.loads((O/'layout.json').read_text())
LENGTH=.9;CONTACT=.25;FPS=120
stock=Vector(layout['stock_source_m']);stock_local=rest['WPN_root'].inverted()@stock
CI=C.inverted()

def frame(axis,normal):
    x=axis.normalized();z=(normal-x*normal.dot(x)).normalized()
    return Matrix((x,z.cross(x).normalized(),z)).transposed()
def signed_twist(q,axis):
    if q.w<0:q=-q
    return 2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)
def rotation(yaw,pitch,roll):
    return Quaternion((0,0,1),math.radians(yaw))@Quaternion((0,1,0),math.radians(pitch))@Quaternion((1,0,0),math.radians(roll))

def support(idle,row,side,weight,write=False,pole_angle=None,previous_phi=None,step_seconds=0.):
    u,l,h=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
    S=idle[u].translation;T=row[h].translation
    iu=idle[l].translation-S;il=idle[h].translation-idle[l].translation
    a,b=iu.length,il.length;v=T-S;d=v.length;axis=v.normalized()
    along=(a*a-b*b+d*d)/(2*max(d,1e-8));radius=math.sqrt(max(0,a*a-along*along));center=S+axis*along
    start=idle[l].translation-center;start=(start-axis*start.dot(axis)).normalized()
    down=CI.to_3x3()@Vector((-2,-8 if side=='l' else 8,-22));down=(down-axis*down.dot(axis)).normalized()
    preferred=start.lerp(down,weight).normalized()
    wanted=row[h].to_quaternion()@idle[h].to_quaternion().inverted()@il.normalized()
    native_normal=iu.cross(il).normalized()
    def candidate(phi):
        E=center+Quaternion(axis,phi)@preferred*radius
        U=E-S;L=T-E;N=U.cross(L).normalized()
        uq=(frame(U,N)@frame(iu,native_normal).transposed()).to_quaternion()@idle[u].to_quaternion()
        lq=(frame(L,N)@frame(il,native_normal).transposed()).to_quaternion()@idle[l].to_quaternion()
        ax=idle[l].to_quaternion().inverted()@il.normalized()
        relative=(lq.inverted()@row[h].to_quaternion())@(idle[l].to_quaternion().inverted()@idle[h].to_quaternion()).inverted()
        roll=signed_twist(relative,ax)
        bend=L.normalized().angle(wanted)
        ec,tc,sc=C@E,C@T,C@S
        # The support elbow stays below its wrist and on its own body side.
        up=max(0,ec.z-min(tc.z,sc.z)+3)
        inside=max(0,ec.y+9) if side=='l' else max(0,7-ec.y)
        score=16*bend*bend+12*max(0,abs(roll)-math.radians(95))**2
        score+=weight*(.04*up*up+.035*inside*inside)+.30*phi*phi
        return score,E,uq,lq,roll,ax,bend
    cap=math.radians(35 if side=='l' else 55)*weight
    if pole_angle is None:
        low,high=-cap,cap
        if previous_phi is not None and weight>1e-5:
            travel=math.radians(190)*step_seconds
            low=max(low,previous_phi-travel);high=min(high,previous_phi+travel)
        phi=min((low+(high-low)*i/36 for i in range(37)),key=lambda p:candidate(p)[0])
        step=(high-low)/18
        for _ in range(4):
            phi=min((max(low,phi-step),phi,min(high,phi+step)),key=lambda p:candidate(p)[0]);step*=.5
    else:phi=pole_angle
    score,E,uq,lq,roll,ax,bend=candidate(phi)
    if write:
        U=Matrix.LocRotScale(S,uq,Vector((1,1,1)));L=Matrix.LocRotScale(E,lq,Vector((1,1,1)))
        for n in names:
            if under(n,h):continue
            if under(n,l):row[n]=L@idle[l].inverted()@idle[n]
            elif under(n,u):row[n]=U@idle[u].inverted()@idle[n]
        for index,share in ((1,1.),(2,.5)):
            n=f'lowerarm_twist_{index:02d}_{side}'
            rel=idle[l].inverted()@idle[n]
            row[n]=L@Matrix.LocRotScale(rel.translation,Quaternion(ax,roll*share)@rel.to_quaternion(),rel.to_scale())
        row['clavicle_'+side]=idle['clavicle_'+side].copy()
    return score,phi

def group(idle,target,q,weight):
    at=C@(idle['WPN_root']@stock_local)
    dc=Matrix.LocRotScale(target-q@at,q,Vector((1,1,1)))
    D=CI@dc@C
    # Reach is solved on the rigid gun/two-palm assembly, never by stretching
    # an arm or independently sliding either palm along the stock.
    shift=Vector();corrections={side:Vector() for side in ('l','r')}
    for _ in range(12):
        for side in ('l','r'):
            sh,el,wr=[idle[n+'_'+side].translation for n in ('upperarm','lowerarm','hand')]
            reach=(el-sh).length+(wr-el).length
            fraction=(wr-sh).length/reach+.002
            limit=reach*(fraction*(1-weight)+.94*weight)
            point=D@wr+shift+corrections[side];delta=point-sh
            projected=sh+delta.normalized()*limit if delta.length>limit else point
            corrections[side]=point-projected;shift+=projected-point
    D=Matrix.Translation(shift)@D
    row=clone(idle)
    for n in names:
        if under(n,'WPN_root') or under(n,'hand_l') or under(n,'hand_r'):
            row[n]=D@idle[n]
    row['WPN_StockContact'].translation=row['WPN_root']@stock_local
    for side in ('l','r'):
        if 'ik_hand_'+side in row:row['ik_hand_'+side]=row['hand_'+side].copy()
    return row,shift

base,_=pose('idle',0)
start=C@(base['WPN_root']@stock_local)
# Time, buttpad camera position (cm), yaw/pitch/roll of the whole held assembly.
# Long barrel swings down the left side while the buttpad leads the short thrust.
keys=[(0,list(start),(0,0,0)),(.05,[-1,18,-20],(-12,4,-6)),
      (.15,[22,23,-10],(-83,25,-12)),(.25,[47,6,-5],(-128,18,-8)),
      (.325,[44,4,-8],(-132,23,-6)),(.46,[28,16,-17],(-85,20,-9)),
      (.68,[0,18,-22],(-22,4,-4)),(.9,list(start),(0,0,0))]
def support_weight(t):return ease(t/.10)*(1-ease((t-.64)/.26))

# Fit only authored pose controls. Interpolate their solutions smoothly; do not
# leave a per-frame parameter search jitter in the final gun trajectory.
fitted=[]
for t,target,angles in keys:
    value=list(angles);w=support_weight(t)
    prev_poles=fitted[-1][4] if fitted else {'l':0.,'r':0.}
    dt=t-fitted[-1][0] if fitted else 0.
    if t==.325:
        # Follow-through retains the loaded contact wrist orientation; no
        # independent optimizer is allowed to flip the rifle roll after impact.
        prior=fitted[-1][3];value=[prior[0]-4,prior[1]+3,prior[2]]
    elif 0<t<LENGTH:
        def cost(v):
            row,shift=group(base,Vector(target),rotation(*v),w)
            temporal=((v[2]-fitted[-1][3][2])/25)**2*2 if fitted else 0
            return sum(support(base,row,side,w,previous_phi=prev_poles[side],step_seconds=dt)[0] for side in ('l','r'))+shift.length_squared*1000+sum(((v[i]-angles[i])/25)**2*.8 for i in range(3))+temporal
        for step in (12,6,3):
            for axis in (2,1,0,2):
                candidates=[]
                for delta in (-step,0,step):
                    v=value.copy();v[axis]=max(angles[axis]-(35 if axis==2 else 18),min(angles[axis]+(35 if axis==2 else 18),v[axis]+delta))
                    candidates.append(v)
                value=min(candidates,key=cost)
    row,_=group(base,Vector(target),rotation(*value),w)
    poles={side:support(base,row,side,w,previous_phi=prev_poles[side],step_seconds=dt)[1] for side in ('l','r')}
    fitted.append((t,Vector(target),rotation(*value),value,poles))

def trajectory(t):
    i=max(0,min(len(fitted)-2,bisect.bisect_right([k[0] for k in fitted],t)-1))
    a,b=fitted[i],fitted[i+1];f=(t-a[0])/(b[0]-a[0]);w=ease(f)
    # Rest at preparation/contact keys; compressed strike interval creates
    # the acceleration, with a slower body recovery and no extra settle phase.
    return a[1].lerp(b[1],w),a[2].slerp(b[2],w),{side:a[4][side]*(1-w)+b[4][side]*w for side in ('l','r')}

patch={};final={};report={'duration':LENGTH,'contact':CONTACT,'fps':FPS,'runtime_tested':False,'rendered':False,
    'reference':'M4 N rhythm and QBZ191 O rigid native grip; own M24 stock path, shoulders and joints',
    'keys':[{'seconds':t,'stock_target_cm':list(p),'degrees':v,'elbow_poles':poles} for t,p,q,v,poles in fitted],
    'stock_root_cm_ue':layout['stock_root_cm_ue'],'clips':{}}
for family in ('base','mag10'):
    idle,_=pose('idle',0,family);rows=[];times=[i/FPS for i in range(round(LENGTH*FPS)+1)]
    tracks={n:[] for n in names};previous={}
    for t in times:
        target,q,poles=trajectory(t);w=support_weight(t)
        row,_=group(idle,target,q,w)
        for side in ('l','r'):support(idle,row,side,w,True,poles[side])
        if t==0 or t==LENGTH:
            row=clone(idle);row['WPN_StockContact'].translation=row['WPN_root']@stock_local
        rows.append(row)
        _,raw=pose('quick_melee',t,family,False)
        for n in names:
            local=row[parents[n]].inverted()@row[n] if parents[n] else row[n]
            p,q,sc=(K@local@K).decompose();bp,bq,bs=(K@raw[n]@K).decompose();dq=q@bq.inverted()
            if n in previous and previous[n].dot(dq)<0:dq=-dq
            previous[n]=dq.copy();tracks[n].extend([*(p-bp),dq.x,dq.y,dq.z,dq.w,*(sc-bs)])
    # Exact native deltas over the current shared sequence; unchanged roles are
    # never copied from an old authoring snapshot into the live profiles.
    compact=[]
    for n,values in tracks.items():
        rows_of_values=[values[i:i+10] for i in range(0,len(values),10)]
        identity=[0,0,0,0,0,0,1,0,0,0]
        if all(max(abs(a-b) for a,b in zip(v,identity))<2e-7 for v in rows_of_values):continue
        constant=all(max(abs(a-b) for a,b in zip(v,rows_of_values[0]))<2e-7 for v in rows_of_values)
        compact.append({'bone':n,'times':[0.] if constant else times,'values':rows_of_values[0] if constant else values})
    patch[family]={'base':ue['clips']['quick_melee']['path'],'duration':LENGTH,'tracks':compact}
    final[family]=rows
    report['clips'][family]={'keys':len(rows),'profile_only':True,'contact_stock_camera_cm':list(C@rows[round(CONTACT*FPS)]['WPN_StockContact'].translation)}
(O/'quick_melee_patch.json').write_text(json.dumps(patch),encoding='utf-8')

# Save editable source and a single base FBX; mag10 reuses the shared sequence
# and receives its own native idle/grip delta, not a duplicate runtime clip.
node=next(n for n in ast.parse((O.parent/'M24Hold20261027/author_hold.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='bake')
node.body=[n for n in node.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='twists')]
exec(compile(ast.unparse(node).replace('s.render.fps = 30','s.render.fps = 120').replace('(len(rows) - 1) / 30','(len(rows) - 1) / 120'),'bake','exec'))
for family,rows in final.items():
    role='quick_melee' if family=='base' else 'quick_melee_mag10'
    r.animation_data_clear();old=bpy.data.actions.get('A_M24_'+role)
    if old:bpy.data.actions.remove(old)
    bake(role,rows)
r.animation_data.action=bpy.data.actions['A_M24_quick_melee'];r.animation_data.action_slot=r.animation_data.action.slots[0]
s.frame_start=0;s.frame_end=108;s.render.fps=120;s.frame_set(0)
bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(O/'A_M24_StockBash.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_StockBash_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_STOCK_BASH_AUTHORED',json.dumps(report),flush=True)
