"""Inspect fitted interfaces and rear-grip/hand relationship on current mesh."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;R=O.parent
def import_objects(path):
    with bpy.data.libraries.load(str(path),link=False) as (src,dst):dst.objects=src.objects
    obs=[]
    for ob in dst.objects:
        if ob.type=='MESH':
            bpy.context.scene.collection.objects.link(ob);ob.hide_render=False;ob.hide_set(False);ob.color=(.7,.39,.12,1);obs.append(ob)
    return obs
def camera(center,offset,scale):
    s=bpy.context.scene
    cd=bpy.data.cameras.new('GripFitReview');cam=bpy.data.objects.new('GripFitReview',cd);s.collection.objects.link(cam);s.camera=cam
    cam.location=center+offset;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=scale;cd.clip_start=.001
    s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT'
    s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH';s.display.shading.background_type='WORLD';s.world.color=(.07,.07,.07)
    s.render.resolution_x=900;s.render.resolution_y=680;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
    return cam

spec=json.loads((O/'authoring.json').read_text())
for key,info in spec.items():
    bpy.ops.wm.open_mainfile(filepath=str(O/'MountInspection.blend'),use_scripts=False)
    for ob in bpy.context.scene.objects:
        ob.hide_render=not ob.name.startswith('Factory_')
        if info['kind']=='rear' and ob.name in ['Factory_PKM_Part_045','Factory_PKM_Part_046']:ob.hide_render=True
    obs=import_objects(O/(info['name']+'.blend'))
    center=Vector((0,.012,-.025) if info['kind']=='rear' else (0,-.36,-.013))
    for view,offset in [('side',Vector((.6,0,.025))),('oblique',Vector((.47,.25,-.18)))]:
        camera(center,offset,.255 if info['kind']=='rear' else .3)
        s=bpy.context.scene;s.render.filepath=str(O/f'after_{key}_{view}.png');bpy.ops.render.render(write_still=True)

# Same PKM right-hand pose in both versions. Front attachment correction never
# moves the grasp region and therefore needs no animation replacement.
for key in ['phantom_reargrip','balanced_reargrip','stable_antislip_reargrip']:
    for revision in ['before','after']:
        bpy.ops.wm.open_mainfile(filepath=str(R/'Motion21/PKM_HingedOutlet_Editable.blend'),use_scripts=False)
        r=bpy.data.objects['PKM_Manny_Rig'];s=bpy.context.scene
        with bpy.data.libraries.load(str(R/'Melee24/PKM_base_Melee24.blend'),link=False) as (src,dst):dst.actions=['PKM24_base_quick_melee']
        a=dst.actions[0];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];r.data.pose_position='POSE';s.frame_set(0);bpy.context.view_layer.update()
        W=r.matrix_world@r.pose.bones['WPN_root'].matrix
        for ob in s.objects:
            ob.hide_render=not (ob.type=='MESH' and (ob.name=='SK_Manny_Arms_Export' or 'mechanical_bone' in ob))
            if ob.name in ['PKM_Part_045','PKM_Part_046'] or ob.name.startswith('New_'):ob.hide_render=True
            ob.color=(.43,.53,.65,1) if 'Arms' in ob.name else (.24,.28,.33,1)
        src=O if revision=='after' else R/'GripContact15'
        obs=import_objects(src/f'SM_PKM_{key}.blend')
        for ob in obs:ob.matrix_world=W@ob.matrix_world
        center=W@Vector((0,.025,-.020));offset=W.to_3x3()@Vector((-.38,.13,-.09))
        camera(center,offset,.23);s.render.filepath=str(O/f'{revision}_{key}_hand.png');bpy.ops.render.render(write_still=True)
print('PKM25_FIT_REVIEW_COMPLETE',flush=True)
