"""Apply the VRE donor grasp to existing timed clips, preserving reload contacts."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;OLD=O.parent/'VerticalGripFront20260911';sys.path.insert(0,str(OLD))
from front_pose import solve_arm

def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def weights(weapon,clip,f,end):
    if 'reload' not in clip:return 1.,1.
    if weapon=='m4':
        w=1-smooth((f-(20 if clip.startswith('drum') else 9))/(8 if clip.startswith('drum') else 7))+smooth((f-(end-24))/8)
        u=max(0,min(1,f/9)) if f<end/2 else 1-max(0,min(1,(f-(end-12))/12))
    else:
        start=380 if 'empty' in clip else 270;finish=start+60
        w=1-smooth((f-18)/24)+smooth((f-start)/40)
        u=max(0,min(1,f/18)) if f<end/2 else 1-max(0,min(1,(f-(finish-24))/24))
    return w,w*(1-smooth(u))

fit=json.loads((O/'Opening/0.8/aligned_fit.json').read_text())
OUT=O/'Final';OUT.mkdir(exist_ok=True)
hand_in_grip=Matrix(fit['grip_in_root']).inverted()@Matrix(fit['hand_in_root'])
donor={n:Matrix(m).to_quaternion() for n,m in fit['basis'].items()}
requested=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
report=json.loads((OUT/'build.json').read_text()) if (OUT/'build.json').exists() else {}
for weapon in ['m4','akm']:
    D=OUT/weapon/'vertical';D.mkdir(parents=True,exist_ok=True)
    sources=OLD/weapon/'vertical'
    info=json.loads((sources/('animation_build.json' if weapon=='m4' else 'build.json')).read_text())
    prefix=f'A_{weapon.upper()}_{"Vertical" if weapon=="m4" else "vertical"}_'
    bpy.ops.wm.open_mainfile(filepath=str(sources/(prefix+'idle.blend')))
    r=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(0)
    heldroot=r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones['hand_l'].matrix
    heldbasis={n:r.pose.bones[n].matrix_basis.to_quaternion() for n in donor}
    griproot=Matrix(fit['grip_in_root']) if weapon=='m4' else Matrix(json.loads((OLD/'akm/fits.json').read_text())['vertical']['grip_in_root'])
    newroot=griproot@hand_in_grip
    deltas={n:donor[n]@heldbasis[n].inverted() for n in donor}
    for clip,meta in info.items():
        if requested and clip not in requested:continue
        name=prefix+clip;source=sources/(name+'.blend')
        bpy.ops.wm.open_mainfile(filepath=str(source));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
        a=r.animation_data.action.copy();r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
        curves={fc.data_path+'#'+str(fc.array_index):fc for la in a.layers for st in la.strips for bag in st.channelbags for fc in bag.fcurves}
        frames=[p.co.x for p in curves['pose.bones["hand_l"].rotation_quaternion#0'].keyframe_points]
        names=['clavicle_l','upperarm_l','lowerarm_l','hand_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_twist_01_l','lowerarm_twist_02_l']+list(donor)
        rest={b.name:b.matrix_local.copy() for b in r.data.bones}
        localrest={n:(rest[r.pose.bones[n].parent.name].inverted()@rest[n]) for n in names}
        samples=[];prev={};metrics={'max_wrist_bend_deg':0,'preserved_frames':0}
        for f in frames:
            s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
            armw,fingerw=weights(weapon,clip,f,meta['frames'])
            baseline={n:r.pose.bones[n].matrix_basis.copy() for n in names}
            row={n:m.copy() for n,m in baseline.items()}
            if armw>0:
                p={b.name:b.matrix.copy() for b in r.pose.bones};root=p['WPN_root'];H=p['hand_l'].copy()
                oldtarget=root@heldroot;newtarget=root@newroot
                deltaq=newtarget.to_quaternion()@oldtarget.to_quaternion().inverted()
                H=Matrix.LocRotScale(H.translation+(newtarget.translation-oldtarget.translation)*armw,Quaternion().slerp(deltaq,armw)@H.to_quaternion(),H.to_scale())
                metric=solve_arm(p,rest,H,root@griproot,armw)
                if armw>.999:metrics['max_wrist_bend_deg']=max(metrics['max_wrist_bend_deg'],metric['wrist_axis_bend_deg'])
                for n in names:
                    loc,q,scale=baseline[n].decompose()
                    if n in donor:q=Quaternion().slerp(deltas[n],fingerw)@q
                    else:
                        local=localrest[n].inverted()@(p[r.pose.bones[n].parent.name].inverted()@p[n]);q=local.to_quaternion()
                        if n=='clavicle_l':loc=local.translation
                    row[n]=Matrix.LocRotScale(loc,q,scale)
            else:metrics['preserved_frames']+=1
            for n in names:
                loc,q,scale=row[n].decompose()
                if n in prev and prev[n].dot(q)<0:q.negate()
                prev[n]=q.copy();row[n]=(loc,q,scale)
            samples.append(row)
        # Modify existing left-arm tracks only. Other tracks and all frame times
        # remain byte-for-byte values from the prior editable animation.
        for n in names:
            for prop,index,length in [('rotation_quaternion',1,4)]+([('location',0,3)] if n=='clavicle_l' else []):
                for axis in range(length):
                    fc=curves[f'pose.bones["{n}"].{prop}#{axis}'];assert len(fc.keyframe_points)==len(frames)
                    for k,key in enumerate(fc.keyframe_points):key.co.y=samples[k][n][index][axis]
                    fc.update()
        s.frame_set(0);bpy.context.view_layer.update()
        bpy.ops.wm.save_as_mainfile(filepath=str(D/(name+'.blend')))
        bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
        bpy.ops.export_scene.fbx(filepath=str(D/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=s.render.fps/meta['sample_rate'],bake_anim_simplify_factor=0)
        report[weapon+':'+clip]={**meta,'previous_editable':str(source),'output':str(D/(name+'.fbx')),'action':a.name,'donor':'VRExpPluginExample/GrabAnimation','closure':0.8,'metrics':metrics}
        (OUT/'build.json').write_text(json.dumps(report,indent=2));print('DONOR_CLIP_PASS',weapon,clip,flush=True)
print('DONOR_FAMILY_BUILD_PASS',len(report),flush=True)
