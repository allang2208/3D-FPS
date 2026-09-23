"""Author a held rearward pull and manual forward push, retaining the 6.6 s reload."""
from pathlib import Path
prior=Path(__file__).parent.parent/'EquipCharge31/author_actions.py'
# Reuse the current fixed-length whole-arm solver, glove-pad contact and baker.
exec(compile(prior.read_text().split('records={};authoring={}')[0].replace('PKM31','PKM34'),str(prior),'exec'))
PULL=5.13;REAR=5.36;PUSH=5.48;FRONT=5.82;FREE=5.835;END=6.6

def event(t,empty):return t-.9 if empty and t>=2.30 else t
def assembly_ramp(t,a,b):
    x=max(0.,min(1.,(t-a)/(b-a)));return x*x*(3-2*x)
assembly_source=(R/'Reload16/author_reload.py').read_text()
exec(compile(assembly_source[assembly_source.index('def pulse('):assembly_source.index('records={};params=')].replace('ramp(', 'assembly_ramp('),'<Reload16 assembly>','exec'))

def new_assembly(t):
    work=assembly_ramp(t,.25,.75)*(1-assembly_ramp(t,END-.48,END))
    box=assembly_ramp(t,1.45,1.90)*(1-assembly_ramp(t,3.45,3.80))
    cover=assembly_ramp(t,.50,.85)*(1-assembly_ramp(t,1.08,1.40))
    charge=ramp(t,5.00,REAR)*(1-ramp(t,PUSH,FRONT))
    impact=sum(a*pulse(t,event(at,True)) for at,a in [(.65,.45),(2.6,.60),(4.35,1.),(5.1,.35),(5.72,1.15)])
    impact+=.70*pulse(t,FRONT,10,21)
    loc=Vector((.0028*math.sin(t*2)*work-.002*box,.003*box-.004*charge,-.0035*box-.002*cover-.0018*impact))
    angles=(math.radians(.55)*work*math.sin(t*2.4)+math.radians(.7)*impact,
            math.radians(1.65)*box-math.radians(.7)*cover+math.radians(.5)*impact,
            math.radians(.75)*math.sin(t*1.7)*work+math.radians(.65)*charge)
    return Matrix.Translation(loc)@Euler(angles,'XYZ').to_matrix().to_4x4()

records={};authoring={}
for family in ('base','vertical','canted','prism','angled'):
    source=R/'EquipCharge31'/f'PKM_{family}_EquipCharge_Editable.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
    r=bpy.data.objects['PKM_Manny_Rig'];s=bpy.context.scene;r.data.pose_position='POSE'
    rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
    localrest={n:rest[parents[n]].inverted()@m if parents[n] else m.copy() for n,m in rest.items()}
    fingers={side:[n for n in rest if n.endswith('_'+side) and n.startswith(('thumb_','index_','middle_','ring_','pinky_'))] for side in ('l','r')}
    idle={n:Matrix(m) for n,m in grips[family]['idle'].items()};idle_q={side:finger_q(idle,side) for side in ('l','r')}
    W0=idle['WPN_root'];B=rest['WPN_root']@fit
    dr={n:Matrix(m) for n,m in donor['rest'].items()};closed={n:Matrix(m) for n,m in donor['poses']['75'].items()};opened={n:Matrix(m) for n,m in donor['poses']['54'].items()}
    hook={};opening={}
    for n in fingers['r']:
        parent=parents[n];lr=dr[parent].inverted()@dr[n]
        hook[n]=(lr.inverted()@closed[parent].inverted()@closed[n]).to_quaternion()
        opening[n]=(lr.inverted()@opened[parent].inverted()@opened[n]).to_quaternion()
    Hi=rest['hand_r'].inverted();forward=(Hi@rest['middle_01_r'].translation).normalized()
    width=(Hi.to_3x3()@(rest['index_01_r'].translation-rest['pinky_01_r'].translation)).normalized()
    palm_normal=-forward.cross(width).normalized();semantic=frame(forward,palm_normal)
    hand_rotation=(frame((0,-.88,-.48),(1,0,0))@semantic.transposed()).to_quaternion()
    anchor=skin_pad_anchor(hook);lug=Vector((-.060,.115,.0215))
    frames=[sample(bpy.data.actions[f'PKM31_{family}_reload_empty'],f/FPS) for f in range(round(END*FPS)+1)]
    home_frame=frames[round(5.0*FPS)];home=home_frame['WPN_root'].inverted()@home_frame['PKM_Charge']
    travel=max(((row['WPN_root'].inverted()@row['PKM_Charge']).translation-home.translation
                for row in frames[round(PULL*FPS):round(5.55*FPS)+1]),key=lambda v:v.length_squared)
    support_frame=frames[round(PULL*FPS)]
    result=[]
    for f,original in enumerate(frames):
        t=f/FPS;p={n:m.copy() for n,m in original.items()}
        if 4.82<t<6.30:
            # Replace the old 5.55 s whole-assembly release with the new front
            # stop. Apply the same rigid correction to gun, left support and rig.
            old_local=assembly_motion(t,True,END,Matrix.Identity(4))
            pre_world=original['WPN_root']@fit@old_local.inverted()
            correction=pre_world@new_assembly(t)@old_local.inverted()@pre_world.inverted()
            for n in p:
                if parents[n]:p[n]=correction@p[n]
            fraction=ramp(t,PULL,REAR)*(1-ramp(t,PUSH,FRONT))
            charge=home.copy();charge.translation+=travel*fraction
            p['PKM_Charge']=p['WPN_root']@charge
            W=p['WPN_root']@fit;Rhand=W.to_quaternion()@hand_rotation
            contact=p['PKM_Charge']@rest['PKM_Charge'].inverted()@B@lug
            locked=Rhand.to_matrix().to_4x4();locked.translation=contact-Rhand@anchor
            hover=locked.copy();hover.translation+=W.to_3x3()@Vector((-.065,-.020,.055))
            away=locked.copy();away.translation+=W.to_3x3()@Vector((-.065,.010,.045))
            returning=p['WPN_root']@W0.inverted()@idle['hand_r']
            back=returning.copy();back.translation+=W.to_3x3()@Vector((-.045,-.025,.018))
            if t<PULL:
                H=mix(hover,locked,ramp(t,5.005,PULL));closed_amount=ramp(t,5.015,PULL)
            elif t<FREE:
                H=locked;closed_amount=1.
            elif t<5.99:
                H=mix(locked,away,ramp(t,FREE,5.99));closed_amount=1-ramp(t,FREE,5.94)
            elif t<6.14:
                H=mix(away,back,ramp(t,5.99,6.14));closed_amount=0.
            else:
                H=mix(back,returning,ramp(t,6.14,6.27));closed_amount=0.
            weight=ramp(t,4.82,5.015)*(1-ramp(t,6.27,6.30))
            H=mix(p['hand_r'],H,weight)
            # Use one support pose through the full pull/push rather than the
            # obsolete source elbow already retreating during the forward push.
            support_xform=p['WPN_root']@support_frame['WPN_root'].inverted()
            target_support={n:support_xform@m for n,m in support_frame.items()}
            support={n:m.copy() for n,m in p.items()}
            for n in ('clavicle_r','upperarm_r','lowerarm_r','hand_r'):
                parent=parents[n]
                before=p[parent].inverted()@p[n]
                after=target_support[parent].inverted()@target_support[n]
                # Blend rotations in FK space so the reference enters/exits
                # continuously while preserving the actual local bone lengths.
                local=Matrix.LocRotScale(before.translation,before.to_quaternion().slerp(after.to_quaternion(),weight),before.to_scale())
                support[n]=support[parent]@local
            solve_arm(p,support,'r',H,weight)
            oldq=finger_q(original,'r');back_grip=ramp(t,6.04,6.27)
            qs={n:oldq[n].slerp(opening[n].slerp(hook[n],closed_amount).slerp(idle_q['r'][n],back_grip),weight) for n in fingers['r']}
            finger_pose(p,'r',H,qs)
        result.append(p)
    bake('reload_empty',result,END)
    authoring[family]={'source':str(source),'pull_start':PULL,'rear_stop':REAR,'push_start':PUSH,
        'front_stop':FRONT,'hand_release':FREE,'duration':END,'travel_m':list(travel),
        'pad_anchor_hand_local_m':list(anchor),'handle_lug_model_m':list(lug),'normal_reload_changed':False,'equip_changed':False}
    (O/'authoring.json').write_text(json.dumps(authoring,indent=2))
    s.frame_set(round(REAR*FPS))
    bpy.ops.wm.save_as_mainfile(filepath=str(O/f'PKM_{family}_ChargePush_Editable.blend'))
print('PKM34_AUTHOR_COMPLETE',flush=True)
