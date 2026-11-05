"""User-requested GIF frames sampled from the actually saved M24 profile data."""
import sys,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent
code=(O/'author.py').read_text().split('# Read physical assembly geometry')[0]
exec(compile(code,'saved pose composition','exec'))
saved=O/'saved_motion.json.gz';D['profiles']=json.load(gzip.open(saved,'rt'))
receipt=json.loads((O/'publish_receipt.json').read_text())
for row in receipt['saved']:
    file=O.parents[1]/'Content'/(row['asset'].split('.')[0].removeprefix('/Game/')+'.uasset')
    if hashlib.sha256(file.read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Saved asset changed; capture current profile before preview: '+row['family'])
OUT=O/'GIF';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_QuickMelee_CurrentGrip_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig'];r.animation_data_clear();r.matrix_world=Matrix.Identity(4)
skin=bpy.data.objects['M24_CurrentV9_Arms'];skin.data.shape_keys.animation_data_clear()
exec(compile((O.parent/'M24ThumbRootRoute20261102/corrective_weights.py').read_text(),'runtime joint shapes','exec'))
for ob in s.objects:
    if ob.type=='MESH':ob.hide_render=True
bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.clip_start=.001;cam.data.clip_end=20.
s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=640;s.render.resolution_y=420;s.render.resolution_percentage=100
s.display.shading.light='STUDIO';s.display.shading.studiolight_rotate_z=.4;s.display.shading.color_type='OBJECT'
s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH';s.display.shading.show_shadows=True;s.display.shading.show_specular_highlight=True
s.display.shading.background_type='WORLD';s.world.color=(.065,.075,.09);s.display.render_aa='16'
s.render.image_settings.file_format='PNG';s.render.film_transparent=False
for ob in s.objects:
    if ob.type=='MESH':ob.color=(.19,.23,.27,1.)
skin.color=(.70,.47,.32,1.)
for polygon in skin.data.polygons:polygon.use_smooth=True
KEEP={'M24_CurrentV9_Arms','M24_Advanced_RetainedNativeBody','M24_Advanced_stock','M24_Advanced_front','M24_MainScope_Lowpoly','M24_bolt'}

def camera_ue(location,target,scale=None):
    p=CI@Vector(location);target=CI@Vector(target);up=(CI.to_3x3()@Vector((0,0,1))).normalized()
    forward=(target-p).normalized();right=forward.cross(up).normalized();up=right.cross(forward).normalized()
    cam.location=p;cam.rotation_euler=Matrix((right,up,-forward)).transposed().to_euler()
    cam.data.type='ORTHO' if scale else 'PERSP'
    if scale:cam.data.ortho_scale=scale
    else:
        cam.data.sensor_fit='VERTICAL';cam.data.sensor_height=24.;cam.data.lens=24/(2*math.tan(math.radians(75/2)))

def pose(family,time):
    row,local=compose(entry(family,'quick_melee'),time)
    for n in names:
        bone=r.pose.bones[n];bone.rotation_mode='QUATERNION';bone.matrix_basis=local_rest[n].inverted()@local[n]
    weights,_=corrective_weights(row,[k.name for k in skin.data.shape_keys.key_blocks])
    for key in skin.data.shape_keys.key_blocks:
        if key.name!='Basis':key.value=weights.get(key.name,0.)
    variant=next((v for v in ('balanced','phantom','stable') if family.endswith('_'+v)),'Default')
    visible=KEEP|{'M24_Advanced_grip_'+variant,'M24_Magazine10' if 'mag10' in family else 'M24_clip'}
    for ob in s.objects:
        if ob.type=='MESH':ob.hide_render=ob.name not in visible;ob.hide_set(ob.hide_render)
    # The source extended magazine is a standalone rigid mesh, not skinned.
    bpy.data.objects['M24_Magazine10'].matrix_world=row['WPN_Magazine']@rest['WPN_Magazine'].inverted()
    bpy.context.view_layer.update();return row

def draw(family,time,view,path):
    row=pose(family,time)
    if view=='fps':camera_ue((0,0,0),(100,0,0))
    elif view=='arms':camera_ue((35,110,60),(22,0,10),1.60)
    else:
        root=row['WPN_root']@rest['WPN_root'].inverted()
        target=(row['hand_r'].translation+row['middle_02_r'].translation)*.5
        cam.location=target+root.to_quaternion()@Vector((.26,-.12,-.09))
        cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.32
    s.render.filepath=str(path);bpy.ops.render.render(write_still=True)

if '--layout' in sys.argv:
    for t in (0.,.15,.25,.325,.46,.72,.9):
        for view in ('fps','arms','grip'):draw('skeleton_base',t,view,OUT/f'layout_{t:.3f}_{view}.png')
    print('M24_MELEE_GIF_LAYOUT_COMPLETE',flush=True)
else:
    R={'complete':False,'fps':30,'playback_speed':.5,'source':'saved_motion.json.gz','source_sha256':hashlib.sha256(saved.read_bytes()).hexdigest(),'game_recording':False,'profiles':{}}
    for family in ('skeleton_base','skeleton_mag10_balanced','skeleton_mag10_phantom','skeleton_mag10_stable'):
        folder=OUT/family;folder.mkdir(exist_ok=True)
        for i in range(28):
            t=i/30
            for view in ('fps','arms'):draw(family,t,view,folder/f'{i:03d}_{view}.png')
        for t in (.15,.25,.325,.46):draw(family,t,'grip',folder/f'contact_{t:.3f}.png')
        R['profiles'][family]={'frames':28,'duration':.9,'views':['fps','arms'],'folder':str(folder)}
        (OUT/'render_receipt.json').write_text(json.dumps(R,indent=2));print('M24_MELEE_GIF_FRAMES',family,flush=True)
    R['complete']=True;(OUT/'render_receipt.json').write_text(json.dumps(R,indent=2));print('M24_MELEE_GIF_RENDER_COMPLETE',flush=True)
