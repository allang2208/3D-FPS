"""Author SVD post-insertion elbow routing and distributed forearm pronation.
Uses the current ArmPlane sources. Preserves all wrist/finger/weapon targets and
source timing; writes only the left arm's existing tracks. No rendering/tests.
"""
import bpy, json, math, hashlib, importlib.util
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

O = Path(__file__).parent
P = O.parents[1]
PREV = P / 'SourceAssets/SVDReloadArmPlane20260930'
spec = importlib.util.spec_from_file_location('svd_arm_source', PREV / 'author_arm.py')
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
bpy.context.preferences.filepaths.save_version = 0

def window(f, end):
    return B.ease((f - 242.) / 44.) * B.ease((end - f) / 56.)

def perpendicular(v, axis):
    return (v - axis * v.dot(axis)).normalized()

def angle_delta(q, axis):
    q.normalize()
    angle = 2 * math.atan2(Vector((q.x,q.y,q.z)).dot(axis), q.w)
    return (angle + math.pi) % (2 * math.pi) - math.pi

def fix(old, rest, w):
    out = {n:m.copy() for n,m in old.items()}
    if w < 1.e-9:
        return out
    un, ln, hn = 'upperarm_l','lowerarm_l','hand_l'
    A, E, H = (old[n].translation.copy() for n in (un,ln,hn))
    RA, RE, RH = (rest[n].translation.copy() for n in (un,ln,hn))
    ru, rf = RE-RA, RH-RE
    bind_hinge = ru.cross(rf).normalized()
    l1, l2 = (E-A).length, (H-E).length
    # Shoulder support only when required; never lengthen the limb to hold contact.
    supported = math.sqrt(l1*l1+l2*l2+2*l1*l2*math.cos(math.radians(36)))
    reach = H-A
    if reach.length > supported:
        A = A.lerp(H-reach.normalized()*supported, w)
    axis = (H-A).normalized()
    old_axis = (H-old[un].translation).normalized()
    old_pole = old_axis.rotation_difference(axis) @ perpendicular(E-old[un].translation,old_axis)
    # Blender rig convention: +Y forward, -X player's left, +Z up.
    # Independent of the old elbow's wrong inward swing and of palm pronation.
    target_pole = perpendicular(Vector((-1., -.05, -.75)), axis)
    across = rest['index_01_l'].translation-rest['pinky_01_l'].translation
    palm = (old[hn].to_quaternion() @ rest[hn].to_quaternion().inverted()) @ across
    distance = (H-A).length
    along = (l1*l1-l2*l2+distance*distance)/(2*distance)
    radius = math.sqrt(max(l1*l1-along*along,0.))

    def candidate(deg):
        pole = Quaternion(axis, math.radians(deg)) @ target_pole
        elbow = A + axis*along + pole*radius
        upper, fore = (elbow-A).normalized(), (H-elbow).normalized()
        hinge = upper.cross(fore).normalized()
        upper_delta = B.frame(upper,hinge,True) @ B.frame(ru,bind_hinge,True).inverted()
        fore_delta = B.frame(fore,hinge,True) @ B.frame(rf,bind_hinge,True).inverted()
        palm_delta = B.frame(fore,palm) @ B.frame(rf,across).inverted()
        pronation = angle_delta(palm_delta @ fore_delta.inverted(), fore)
        score = (deg/24.)**2 + (max(0.,abs(math.degrees(pronation))-100.)/22.)**2
        # Keep the elbow to the left of the wrist and below the shoulder.
        score += (max(0.,elbow.x-H.x+.055)/.018)**2
        score += (max(0.,elbow.z-A.z+.025)/.018)**2
        return score,pole,elbow,upper,fore,hinge,upper_delta,fore_delta,pronation

    best = min(range(-24,25,2),key=lambda a:candidate(a)[0])
    lo,hi = max(-24.,best-2.),min(24.,best+2.)
    for _ in range(14):
        x,y = lo+(hi-lo)/3., hi-(hi-lo)/3.
        if candidate(x)[0] < candidate(y)[0]:hi=y
        else:lo=x
    target = candidate((lo+hi)*.5)[1]
    swivel = B.signed(old_pole,target,axis)
    pole = Quaternion(axis,swivel*w) @ old_pole
    NE = A + axis*along + pole*radius
    upper,fore = (NE-A).normalized(),(H-NE).normalized()
    hinge = upper.cross(fore).normalized()
    upper_delta = B.frame(upper,hinge,True) @ B.frame(ru,bind_hinge,True).inverted()
    fore_delta = B.frame(fore,hinge,True) @ B.frame(rf,bind_hinge,True).inverted()
    palm_delta = B.frame(fore,palm) @ B.frame(rf,across).inverted()
    pronation = angle_delta(palm_delta @ fore_delta.inverted(),fore)
    # Anatomical elbow first; hand rotation accumulates along the real skin stations.
    for root,origin,tip,reference_axis,delta in ((un,A,NE,ru,upper_delta),(ln,NE,H,rf,fore_delta)):
        old_tip = old[ln].translation if root==un else H
        swing = (old_tip-old[root].translation).rotation_difference(tip-origin)
        base_q = swing @ old[root].to_quaternion()
        q = delta @ rest[root].to_quaternion()
        out[root] = Matrix.LocRotScale(origin,base_q.slerp(q,w),old[root].to_scale())
        for suffix in ('01','02'):
            name = root.replace('_l','_twist_'+suffix+'_l')
            station = (rest[name].translation-rest[root].translation).dot(reference_axis)/reference_axis.length_squared
            offset = rest[name].translation-rest[root].translation-reference_axis*station
            rotation = delta
            if root==ln:
                rotation = Quaternion(fore,pronation*max(0.,min(1.,station))) @ delta
            target_pos = origin + (tip-origin)*station + rotation @ offset
            aligned = (out[root] @ old[root].inverted()) @ old[name]
            target_q = rotation @ rest[name].to_quaternion()
            out[name] = Matrix.LocRotScale(aligned.translation.lerp(target_pos,w),
                       aligned.to_quaternion().slerp(target_q,w),old[name].to_scale())
    out['clavicle_l'].translation += A-old[un].translation
    return out

def main():
    baseline=json.loads((PREV/'import_receipt.json').read_text())
    (O/'Blends').mkdir(exist_ok=True);(O/'Animations').mkdir(exist_ok=True)
    for family in ('base','angled','canted','prism','vertical'):
        for clip,end in (('reload',400),('reload_empty',515)):
            src=PREV/'Blends'/f'SVD_{family}_{clip}_ArmPlane.blend'
            bpy.ops.wm.open_mainfile(filepath=str(src),use_scripts=False)
            rig=bpy.data.objects['SK_M4_Infima']
            for ob in bpy.context.scene.objects:
                if ob.type=='MESH':ob.hide_viewport=True
            name='A_SVD_'+('' if family=='base' else family+'_')+clip
            action=bpy.data.actions[name]
            rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
            old=B.sample(rig,action,end)
            new=[fix(p,rest,window(f,end)) for f,p in enumerate(old)]
            B.bake(rig,action,rest,new,end,name)
            scene=bpy.context.scene;scene.render.fps=120;scene.render.fps_base=1
            scene.frame_start=0;scene.frame_end=end;scene.frame_set(304)
            bpy.context.view_layer.update()
            blend=O/'Blends'/f'SVD_{family}_{clip}_Return.blend'
            bpy.ops.wm.save_as_mainfile(filepath=str(blend))
            for ob in scene.objects:ob.select_set(ob==rig)
            bpy.context.view_layer.objects.active=rig
            fbx=O/'Animations'/(name+'.fbx')
            bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
            report={'family':family,'clip':clip,'action':name,'frames':end,'source':str(src),
                    'fbx':str(fbx),'blend':str(blend),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),
                    'expected_asset_sha256':baseline[family+'/'+clip]['saved_sha256'],
                    'window':'frame 242 to end; 44-frame entry, 56-frame exit',
                    'method':'left-down elbow route, anatomical hinge, measured forearm twist stations',
                    'tested':False}
            (O/f'authoring_{family}_{clip}.json').write_text(json.dumps(report,indent=1))
            print('SVD_RETURN_AUTHORED',family,clip,flush=True)

if __name__=='__main__':main()
