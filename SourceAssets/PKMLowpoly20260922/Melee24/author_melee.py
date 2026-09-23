"""Bake only five PKM quick-melee clips. Mesh, sprint and reload are untouched."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
O=Path(__file__).parent; R=O.parent; S=R.parent
sys.path.insert(0,str(S/'M4QuickMeleeRefine20260919K'))
from arm_support import ArmSupport, axial_angle
FPS=240
bpy.context.preferences.filepaths.save_version=0
sources=json.loads((O/'grips.json').read_text())
motion=json.loads((O/'motion.json').read_text())
design=json.loads((O/'design.json').read_text())
records={};measurements={}
def smooth(x):
    x=max(0.,min(1.,x)); return x*x*(3-2*x)
def mix(a,b,t):
    p,q,s=a.decompose();p2,q2,s2=b.decompose()
    return Matrix.LocRotScale(p.lerp(p2,t),q.slerp(q2,t),s.lerp(s2,t))
def frame(axis,normal):
    axis=axis.normalized();normal=normal-axis*normal.dot(axis);normal.normalize()
    return Matrix((axis,normal.cross(axis).normalized(),normal)).transposed().to_quaternion()

for family,data in sources.items():
    bpy.ops.wm.open_mainfile(filepath=data['source'],use_scripts=False)
    r=bpy.data.objects['PKM_Manny_Rig'];s=bpy.context.scene;r.data.pose_position='POSE'
    a=bpy.data.actions[data['idle_action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
    s.frame_set(0);bpy.context.view_layer.update()
    idle={n:Matrix(v) for n,v in data['idle'].items()};rest={n:Matrix(v) for n,v in data['rest'].items()}
    parents=data['parents'];names=list(rest);W0=idle['WPN_root']
    localrest={n:rest[parents[n]].inverted()@m if parents[n] else m.copy() for n,m in rest.items()}
    weapon={'WPN_root'}|{b.name for b in r.data.bones['WPN_root'].children_recursive}
    weapon|={n for n in names if n.startswith(('WPN_','PKM_','New_PKM_'))}
    hands={side:{'hand_'+side}|{b.name for b in r.data.bones['hand_'+side].children_recursive} for side in 'rl'}
    # Borrow only the skin-station measurement, not M4's shoulder anchors.
    stations=ArmSupport(r,idle).stations
    previous={side:{'pole':0.,'roll':0.} for side in 'rl'}
    poses=[];rows=[]

    def solve(pose,side,H,support_weight,weight):
        un,fn,hn,cn=[p+'_'+side for p in ('upperarm','lowerarm','hand','clavicle')]
        sh0,el0,wr0=[idle[n].translation for n in (un,fn,hn)];wr=H.translation
        sh=sh0+Vector(design['shoulder_offsets_m'][side])*support_weight
        U,L=el0-sh0,wr0-el0;a,b=U.length,L.length;axis=(wr-sh).normalized();d=(wr-sh).length
        along=(a*a-b*b+d*d)/(2*d);radius=math.sqrt(max(0,a*a-along*along));center=sh+axis*along
        ref=(rest[hn].translation-rest[fn].translation).normalized()
        handrot=H.to_quaternion()@rest[hn].to_quaternion().inverted();desired=handrot@ref
        base=el0-center;base-=axis*base.dot(axis)
        if base.length<1e-7:base=axis.orthogonal()
        base.normalize();ideal=-desired+axis*desired.dot(axis)
        if ideal.length<1e-7:ideal=base.copy()
        ideal.normalize()
        angle=math.atan2(axis.dot(base.cross(ideal)),base.dot(ideal))
        # At full weight +/-pi describes the same elbow. Do not accumulate
        # a full revolution and then scale it during recovery: that winds the
        # left elbow around the wrist/shoulder axis while returning to idle.
        previous[side]['pole']=angle
        elbow=center+(Quaternion(axis,angle*weight)@base)*radius
        u=(elbow-sh).normalized();f=(wr-elbow).normalized();normal=u.cross(f).normalized()
        uq=frame(u,normal)@frame(U,U.cross(L)).inverted()@idle[un].to_quaternion()
        fq=frame(f,normal)@frame(L,U.cross(L)).inverted()@idle[fn].to_quaternion()
        natural_fq=(desired.rotation_difference(f)@handrot)@rest[fn].to_quaternion()
        roll=axial_angle(natural_fq@fq.inverted(),f,previous[side]['roll'])
        previous[side]['roll']=roll
        pose[cn]=idle[cn].copy()
        pose[cn].translation+=sh-sh0
        for main,origin,q,v,residual in [(un,sh,uq,u,0.),(fn,elbow,fq,f,roll)]:
            pose[main]=Matrix.LocRotScale(origin,q,idle[main].to_scale())
            transport=q@idle[main].to_quaternion().inverted()
            neutral=q@rest[main].to_quaternion().inverted()
            for suffix in ('01','02'):
                name=main[:-2]+'_twist_'+suffix+'_'+side
                oldpos=origin+transport@(idle[name].translation-idle[main].translation)
                oldrot=transport@idle[name].to_quaternion()
                twist=Quaternion(v,residual*stations[name])
                newpos=origin+twist@neutral@(rest[name].translation-rest[main].translation)
                newrot=twist@neutral@rest[name].to_quaternion()
                pose[name]=Matrix.LocRotScale(oldpos.lerp(newpos,weight),oldrot.slerp(newrot,weight),idle[name].to_scale())
        handdelta=H@idle[hn].inverted()
        for n in hands[side]:pose[n]=handdelta@idle[n]
        if 'ik_hand_'+side in pose:pose['ik_hand_'+side]=H.copy()
        return {'bend_deg':math.degrees(desired.angle(f)),'reach':d/(a+b),
                'elbow':list(elbow),'pole_deg':math.degrees(angle),'roll_deg':math.degrees(roll),
                'upper_length_error':abs((elbow-sh).length-a),'lower_length_error':abs((wr-elbow).length-b)}

    for f in range(217):
        t=f/FPS;source_frame=f*.5;i=min(108,int(source_frame));j=min(108,i+1)
        W=mix(Matrix(motion[family][i]['root']),Matrix(motion[family][j]['root']),source_frame-i)
        delta=W@W0.inverted();p={n:m.copy() for n,m in idle.items()}
        weight=smooth(t/.075)*(1-smooth((t-.67)/.19))
        elbow_weight=smooth(t/.030)*(1-smooth((t-.75)/.11))
        for n in weapon:p[n]=delta@idle[n]
        arms={side:solve(p,side,delta@idle['hand_'+side],weight,elbow_weight) for side in 'rl'}
        if f==0 or t>=.86:p={n:m.copy() for n,m in idle.items()}
        grip_error=max((p['WPN_root'].inverted()@p['hand_'+side]).translation.__sub__(
                       (W0.inverted()@idle['hand_'+side]).translation).length for side in 'rl')
        rows.append({'frame':f,'time':t,'arms':arms,'grip_error_m':grip_error,
                     'stock':list(p['WPN_root']@Vector((-.00003818,.359063,-.027)))})
        poses.append(p)
    a=bpy.data.actions.new(f'PKM24_{family}_quick_melee');a.use_fake_user=True;r.animation_data.action=a
    for b in r.pose.bones:
        b.rotation_mode='QUATERNION'
        for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
    curves={(c.data_path,c.array_index):c for layer in a.layers for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves}
    for n in names:
        values=[];prev=None
        for p in poses:
            basis=localrest[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n])
            loc,q,scale=basis.decompose()
            if prev is not None and prev.dot(q)<0:q.negate()
            prev=q.copy();values.append((loc,q,scale))
        for prop,field,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
            for axis in range(count):
                c=curves[(f'pose.bones["{n}"].{prop}',axis)];c.keyframe_points.clear();c.keyframe_points.add(len(values))
                c.keyframe_points.foreach_set('co',[v for i,row in enumerate(values) for v in (i,row[field][axis])])
                for k in c.keyframe_points:k.interpolation='LINEAR'
                c.update()
    r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
    s.render.fps=FPS;s.render.fps_base=1;s.frame_start=0;s.frame_end=216;s.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
    name='A_PKM_'+('' if family=='base' else family+'_')+'quick_melee';dest=O/'Animations'/family;dest.mkdir(parents=True,exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=str(dest/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
    bpy.ops.wm.save_as_mainfile(filepath=str(O/f'PKM_{family}_Melee24.blend'))
    records[family]={'name':name,'action':a.name,'fps':FPS,'duration':.9,'contact':1/6}
    measurements[family]=rows
    print('PKM24_EXPORTED',family,'wrists',{side:round(max(row['arms'][side]['bend_deg'] for row in rows),1) for side in 'rl'},flush=True)
(O/'animations.json').write_text(json.dumps(records,indent=2))
(O/'measurements.json').write_text(json.dumps(measurements,indent=2))
