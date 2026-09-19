"""User-requested focused source-mesh inspection of the guard's left arm."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
revision = args[0] if args else 'FistBraceGuardV20'
source = P.parent/revision/'AzureRunesword_Manny_Editable.blend'
out = P/('Review_'+revision)
out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source))
s = bpy.context.scene
r = bpy.data.objects['SK_RuneSword_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']
blade = bpy.data.objects['RuneSword_Blade']
for ob in s.objects:
    ob.hide_render = ob not in (r, arms, blade)
    if ob in (r, arms, blade):
        ob.hide_set(False)
        ob.hide_viewport = False
s.render.engine = 'CYCLES'
s.cycles.samples = 16
s.cycles.use_denoising = True
s.render.resolution_x = 1280
s.render.resolution_y = 800
s.render.resolution_percentage = 100
s.render.image_settings.file_format = 'PNG'
s.render.film_transparent = False
s.world = bpy.data.worlds.new('GuardReviewWorld')
s.world.use_nodes = True
s.world.node_tree.nodes['Background'].inputs[0].default_value = (.12,.15,.19,1)
s.world.node_tree.nodes['Background'].inputs[1].default_value = .5
s.view_settings.view_transform = 'AgX'
mat = bpy.data.materials.new('GuardJointInspectionClay')
mat.diffuse_color = (.55,.60,.65,1)
mat.use_nodes = True
bs = mat.node_tree.nodes.get('Principled BSDF')
bs.inputs['Base Color'].default_value = (.55,.60,.65,1)
bs.inputs['Roughness'].default_value = .66
arms.data.materials.clear()
arms.data.materials.append(mat)
for poly in arms.data.polygons: poly.material_index = 0
for name, loc, energy, size in [('Key',(-.6,-.1,1.1),100,1.3),('Fill',(.8,.2,.7),65,1.2),('Rim',(-.2,1.2,.4),80,.8)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);s.collection.objects.link(ob);ob.location=loc
    ob.rotation_euler=(Vector((0,.35,-.08))-ob.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('GuardInspectionCamera')
camera=bpy.data.objects.new('GuardInspectionCamera',data)
s.collection.objects.link(camera);s.camera=camera
data.lens=18;data.clip_start=.005

def activate(clip, frame):
    a=bpy.data.actions['A_RuneSword_'+clip]
    r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
    s.frame_set(int(frame), subframe=frame-int(frame));bpy.context.view_layer.update()

def render(name, position, target, ortho=None):
    camera.location=position
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    data.type='ORTHO' if ortho else 'PERSP'
    if ortho: data.ortho_scale=ortho
    s.render.filepath=str(out/(name+'.png'))
    bpy.ops.render.render(write_still=True)

activate('Guard',96)
render('hold_firstperson',(0,0,0),(0,1,0))
a=r.matrix_world@r.pose.bones['upperarm_l'].matrix.translation
e=r.matrix_world@r.pose.bones['lowerarm_l'].matrix.translation
h=r.matrix_world@r.pose.bones['hand_l'].matrix.translation
center=(a+e+h)/3
render('hold_left_joint',center+Vector((-.6,-.7,.24)),center,.66)
activate('Guard',48)
render('raise_midpoint',(0,0,0),(0,1,0))

rest={b.name:b.matrix_local.copy() for b in r.data.bones}
report={'revision':revision,'source':str(source),'samples':[], 'arm_vertex_groups':{}}
for vg in arms.vertex_groups:
    if any(x in vg.name for x in ('arm','clav','hand')):
        count=sum(1 for v in arms.data.vertices if any(g.group==vg.index and g.weight>.0001 for g in v.groups))
        if count:report['arm_vertex_groups'][vg.name]=count
for clip in ('Guard','GuardHit','GuardBreak'):
    action=bpy.data.actions['A_RuneSword_'+clip]
    start,end=map(int,action.frame_range)
    for f in range(start,end+1,2):
        activate(clip,f)
        pose={b.name:b.matrix.copy() for b in r.pose.bones}
        A,E,H=[pose[n].translation for n in ('upperarm_l','lowerarm_l','hand_l')]
        RU=rest['lowerarm_l'].translation-rest['upperarm_l'].translation
        RF=rest['hand_l'].translation-rest['lowerarm_l'].translation
        ud,fd=(E-A).normalized(),(H-E).normalized()
        uq,fq,hq=[pose[n].to_quaternion()@rest[n].to_quaternion().inverted() for n in ('upperarm_l','lowerarm_l','hand_l')]
        twist_q=fd.rotation_difference(uq@RF.normalized())
        # Remove the elbow swing first, leaving only forearm axial roll.
        no_roll=(uq@RF.normalized()).rotation_difference(fd)@uq
        relative=fq@no_roll.inverted()
        roll=2*math.atan2(Vector((relative.x,relative.y,relative.z)).dot(fd),relative.w)
        roll=(roll+math.pi)%(2*math.pi)-math.pi
        report['samples'].append({'clip':clip,'frame':f,'A':list(A),'E':list(E),'H':list(H),
            'elbow_flex_deg':math.degrees(ud.angle(fd)),
            'elbow_roll_deg':math.degrees(roll),
            'wrist_bend_deg':math.degrees(fd.angle(hq@RF.normalized())),
            'upper_m':(E-A).length,'fore_m':(H-E).length,
            'upper_axis_error_deg':math.degrees(ud.angle(uq@RU.normalized())),
            'fore_axis_error_deg':math.degrees(fd.angle(fq@RF.normalized()))})
(out/'left_arm_diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('GUARD_LEFT_ARM_REVIEW_COMPLETE '+revision,flush=True)
