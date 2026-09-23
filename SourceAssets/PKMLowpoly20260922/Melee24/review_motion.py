"""Scoped source-pose inspection requested by the user; does not launch UE."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;R=O.parent
def setup(source,action):
    bpy.ops.wm.open_mainfile(filepath=str(R/'Motion21/PKM_HingedOutlet_Editable.blend'),use_scripts=False)
    r=bpy.data.objects['PKM_Manny_Rig'];s=bpy.context.scene
    with bpy.data.libraries.load(str(source),link=False) as (src,dst):dst.actions=[action]
    a=dst.actions[0];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];r.data.pose_position='POSE'
    for ob in s.objects:
        if ob.type=='MESH':
            keep=any(m.type=='ARMATURE' and m.object==r for m in ob.modifiers) and not ob.name.startswith('New_')
            ob.hide_render=not keep
            if keep:ob.hide_set(False)
            ob.color=(.43,.52,.65,1) if 'Arms' in ob.name else (.19,.22,.27,1)
    cd=bpy.data.cameras.new('PKM24_PoseReview');cam=bpy.data.objects.new('PKM24_PoseReview',cd);s.collection.objects.link(cam);s.camera=cam
    cd.clip_start=.003;cd.lens=13.2
    s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT'
    s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH'
    s.display.shading.background_type='WORLD';s.world.color=(.06,.06,.06)
    s.render.resolution_x=960;s.render.resolution_y=660;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
    return r,s,cam
def camera(cam,t,mode):
    if mode=='fp':
        # Read from FPSGAMECharacter: PKM hip (9,9,-11) cm -> action (10,0,-5).
        # This is source-space framing only, without UE camera recoil/pose blending.
        x=max(0,min(1,(t/.9-.6)/.4));remaining=1-(10*x**3-15*x**4+6*x**5)
        w=min(1-math.exp(-16*t),remaining)
        cam.location=(-.09*(1-w),-.09-.01*w,.11-.06*w)
        cam.rotation_euler=(math.pi/2,0,0);cam.data.type='PERSP';cam.data.lens=13.2
    else:
        center=Vector((-.15,-.1,-.07));cam.location=(.85,-1.05,.7)
        cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=1.55

for revision,source,action,fps in [('before',R/'Combat17/PKM_base_Combat_Editable.blend','PKM17_base_quick_melee',120),
                                  ('after',O/'PKM_base_Melee24.blend','PKM24_base_quick_melee',240)]:
    r,s,cam=setup(source,action)
    for t in [0.,.0666667,.1,1/6,.2666667,.4,.6,.7666667,.9]:
        frame=t*fps;s.frame_set(int(round(frame)));bpy.context.view_layer.update()
        for mode in (['fp','oblique'] if abs(t-1/6)<.001 or abs(t-.1)<.001 else ['fp']):
            camera(cam,t,mode);s.render.filepath=str(O/f'{revision}_{mode}_{round(t*1000):03}.png');bpy.ops.render.render(write_still=True)

# The support grip families retain their own hands. Inspect their contact pose too.
for family in ['vertical','canted','prism','angled']:
    r,s,cam=setup(O/f'PKM_{family}_Melee24.blend',f'PKM24_{family}_quick_melee')
    s.frame_set(40);bpy.context.view_layer.update();camera(cam,1/6,'oblique')
    s.render.filepath=str(O/f'after_{family}_contact.png');bpy.ops.render.render(write_still=True)
print('PKM24_POSE_REVIEW_RENDERED',flush=True)
