"""Fit individual finger chains around the actual bottle profile, keeping bone lengths."""
import bpy,math,json
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');OUT=ROOT/'Refinement20260922'

def normalized(m):
    p,q,_=m.decompose();return Matrix.LocRotScale(p,q,Vector((1,1,1)))

def solve_grip():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/WitchRebuilt_Idle.blend'))
    s=bpy.context.scene;s.frame_set(1);r=next(o for o in s.objects if o.type=='ARMATURE')
    original={b.name:b.matrix_basis.copy() for b in r.pose.bones}
    rest={b.name:r.matrix_world@b.matrix_local for b in r.data.bones}
    hand=r.matrix_world@r.pose.bones['hand_r'].matrix;move=normalized(hand)@normalized(rest['hand_r']).inverted()
    along=move.to_3x3()@(rest['middle_01_r'].translation-rest['hand_r'].translation).normalized()
    across=move.to_3x3()@(rest['index_01_r'].translation-rest['pinky_01_r'].translation).normalized()
    palm=along.cross(across).normalized();center=hand.translation+along*.071+palm*.027
    profile=[(.02,.047),(.10,.0474),(.12,.0428),(.13,.0324),(.14,.0163),(.15,.0171),(.16,.023),(.18,.016)]
    def radius(z):
        for (a,ra),(b,rb) in zip(profile,profile[1:]):
            if a<=z<=b:return ra+(rb-ra)*(z-a)/(b-a)
        return profile[0][1] if z<profile[0][0] else profile[-1][1]
    result={};report={}
    for finger in ('index','middle','ring','pinky','thumb'):
        names=[f'{finger}_{i:02d}_r' for i in (1,2,3)]
        for n in names:r.pose.bones[n].matrix_basis=Matrix.Identity(4)
        bpy.context.view_layer.update()
        parent=r.matrix_world@r.pose.bones[r.data.bones[names[0]].parent.name].matrix
        local=[r.data.bones[n].parent.matrix_local.inverted()@r.data.bones[n].matrix_local for n in names]
        initial=[r.matrix_world@r.pose.bones[n].matrix for n in names]
        length=(initial[2].translation-initial[1].translation).length*.85
        tipworld=initial[2].translation+(initial[2].translation-initial[1].translation).normalized()*length
        tiplocal=initial[2].inverted()@tipworld
        def evaluate(angles):
            previous=parent;matrices=[]
            for i in range(3):
                m=previous@local[i];position=m.translation.copy()
                if i==0:
                    q=Quaternion(along if finger=='thumb' else palm,math.radians(angles[3]))
                    m=q.to_matrix().to_4x4()@m;m.translation=position
                q=Quaternion(across,math.radians(angles[i]))
                m=q.to_matrix().to_4x4()@m;m.translation=position
                matrices.append(m);previous=m
            return matrices,matrices[-1]@tiplocal
        probe=evaluate([5,0,0,0])[1]-tipworld
        sign=1 if probe.dot(center-tipworld)>0 else -1
        axial=(initial[0].translation-center).dot(across)
        axial=max(-.03,min(.03,axial));rad=radius(.136+axial)+.005
        if finger=='thumb':target=center+across*(axial-.008)+along*(rad*.8)+palm*(rad*.6)
        else:target=center+across*axial-along*(rad*.45)+palm*(rad*.893)
        def cost(angles):
            matrices,tip=evaluate(angles);points=[m.translation for m in matrices]+[tip]
            value=(tip-target).length_squared*12
            for a,b in zip(points,points[1:]):
                for t in (.3,.6,.9):
                    p=a.lerp(b,t);v=p-center;z=.136+v.dot(across)
                    if .015<z<.181:
                        distance=(v-across*v.dot(across)).length
                        value+=max(0.,radius(z)+.004-distance)**2*18
            value+=((angles[2]-.65*angles[1])/120)**2*.0004
            return value
        bounds=[(min(0,sign*90),max(0,sign*90)),(min(0,sign*110),max(0,sign*110)),(min(0,sign*80),max(0,sign*80)),(-65,65) if finger=='thumb' else (-12,12)]
        best=None
        for start in (20,45,70):
            angles=[sign*start,sign*start,sign*start*.65,0.];score=cost(angles)
            for step in (25,12,6,3,1.5,.6):
                for iteration in range(10):
                    improved=False
                    for j in range(4):
                        for direction in (-1,1):
                            trial=angles[:];trial[j]=max(bounds[j][0],min(bounds[j][1],trial[j]+direction*step))
                            c=cost(trial)
                            if c<score:angles,score=trial,c;improved=True
                    if not improved:break
            if best is None or score<best[0]:best=(score,angles)
        matrices,tip=evaluate(best[1]);previous=parent
        for n,lr,m in zip(names,local,matrices):
            basis=lr.inverted()@previous.inverted()@m
            # Only rotation changes. The original local translation/scale stay.
            q=basis.to_quaternion().normalized();result[n]=list(q);previous=m
        report[finger]={'target_error_cm':(tip-target).length*100,'angles_degrees':best[1],
                        'tip_to_bottle_axis_cm':((tip-center)-across*(tip-center).dot(across)).length*100}
        for n in names:r.pose.bones[n].matrix_basis=original[n]
    payload={'closed_quaternions':result,'contact_report':report,'bottle_grip_height_cm':13.6,'palm_offset_cm':2.7}
    (OUT/'bottle_grip.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    print('Bottle grip contact fit:',report)
    return payload

def apply_carry(payload):
    roles=('Idle','Walk','CastPoison','Hit','DeathBackward','TurnLeft','TurnRight')
    for role in roles:
        path=ROOT/f'Authoring/WitchRebuilt_{role}.blend';bpy.ops.wm.open_mainfile(filepath=str(path))
        s=bpy.context.scene;r=next(o for o in s.objects if o.type=='ARMATURE')
        for frame in range(s.frame_start,s.frame_end+1):
            s.frame_set(frame)
            for name,values in payload['closed_quaternions'].items():
                b=r.pose.bones[name];b.rotation_mode='QUATERNION';b.rotation_quaternion=Quaternion(values)
                b.keyframe_insert('rotation_quaternion',frame=frame)
        s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(path))
        bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
        bpy.ops.export_scene.fbx(filepath=str(ROOT/f'Delivery/A_WitchRebuilt_{role}.fbx'),use_selection=True,object_types={'ARMATURE'},add_leaf_bones=False,
            use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=True,bake_anim_use_all_bones=True,
            bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,bake_anim_force_startend_keying=True,
            bake_anim_step=1,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS')
        print('Updated right-finger carry tracks only:',role)

if __name__=='__main__':apply_carry(solve_grip())
