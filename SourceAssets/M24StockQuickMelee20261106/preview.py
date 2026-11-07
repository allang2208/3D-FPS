import sys
from pathlib import Path
O=Path(__file__).resolve().parent
exec(compile((O/'common.py').read_text(),'current pose helpers','exec'))
if '--saved' in sys.argv:
    D['profiles']=json.load(gzip.open(O/'saved_motion.json.gz','rt'))
if '--after' in sys.argv:
    patch=json.load(gzip.open(O/'quick_melee_patch.json.gz','rt'))
    for family,clip in patch.items():
        for i,old in enumerate(D['profiles'][family]['clips']):
            if old['base']==clip['base']:D['profiles'][family]['clips'][i]=clip
geometry=setup_geometry()
bpy.ops.wm.open_mainfile(filepath=str(S/'M24QuickMeleeRightHandR3_20261104/M24_QuickMelee_RightHandR3_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig'];r.animation_data_clear();r.matrix_world=Matrix.Identity(4)
skin=bpy.data.objects['M24_CurrentV9_Arms'];skin.data.shape_keys.animation_data_clear()
exec(compile((S/'M24ThumbRootRoute20261102/corrective_weights.py').read_text(),'joint shapes','exec'))
for ob in s.objects:
    if ob.type=='MESH':ob.hide_render=True
new={}
for name,(vs,fs) in geometry.items():
    mesh=bpy.data.meshes.new('Current_'+name);mesh.from_pydata(vs,[],fs);mesh.update()
    ob=bpy.data.objects.new('Current_'+name,mesh);s.collection.objects.link(ob);new[name]=ob
    for poly in mesh.polygons:poly.use_smooth=True
bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.clip_start=.001;cam.data.clip_end=20.
s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=800;s.render.resolution_y=560;s.render.resolution_percentage=100
s.display.shading.light='STUDIO';s.display.shading.studiolight_rotate_z=.4;s.display.shading.color_type='OBJECT'
s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH';s.display.shading.show_shadows=True;s.display.shading.show_specular_highlight=True
s.display.shading.background_type='WORLD';s.world.color=(.065,.075,.09);s.display.render_aa='16'
s.render.image_settings.file_format='PNG';s.render.film_transparent=False
for ob in s.objects:
    if ob.type=='MESH':ob.color=(.19,.23,.27,1.)
skin.color=(.70,.47,.32,1.)
for polygon in skin.data.polygons:polygon.use_smooth=True
OUT=O/('SavedPreview' if '--saved' in sys.argv else 'After' if '--after' in sys.argv else 'BeforeReview');OUT.mkdir(exist_ok=True)
KEEP={'M24_CurrentV9_Arms','M24_Advanced_RetainedNativeBody','M24_MainScope_Lowpoly','M24_bolt'}

def draw(family,stock,t,view):
    row,loc=compose(entry(family,'quick_melee'),t)
    for n in names:
        bone=r.pose.bones[n];bone.rotation_mode='QUATERNION';bone.matrix_basis=local_rest[n].inverted()@loc[n]
    weights,_=corrective_weights(row,[k.name for k in skin.data.shape_keys.key_blocks])
    for key in skin.data.shape_keys.key_blocks:
        if key.name!='Basis':key.value=weights.get(key.name,0.)
    kind=next((v for v in ('balanced','phantom','stable') if family.endswith('_'+v)),'Default')
    visible=KEEP|{'Current_'+stock,'Current_front','Current_grip_'+kind,'M24_Magazine10' if 'mag10' in family else 'M24_clip'}
    root=row['WPN_root']@rest['WPN_root'].inverted()
    for ob in s.objects:
        if ob.type=='MESH':ob.hide_render=ob.name not in visible;ob.hide_set(ob.hide_render)
    for ob in new.values():ob.matrix_world=root
    bpy.data.objects['M24_Magazine10'].matrix_world=row['WPN_Magazine']@rest['WPN_Magazine'].inverted()
    bpy.context.view_layer.update()
    target=(row['hand_r'].translation+row['middle_02_r'].translation)*.5
    offset=Vector((.26,-.12,-.09)) if view=='grip' else Vector((-.28,-.15,.06))
    cam.location=target+root.to_quaternion()@offset
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.32
    if view=='fps':
        p=CI@Vector((0,0,0));at=CI@Vector((100,0,0));up=(CI.to_3x3()@Vector((0,0,1))).normalized()
        fw=(at-p).normalized();rt=fw.cross(up).normalized();up=rt.cross(fw).normalized()
        cam.location=p;cam.rotation_euler=Matrix((rt,up,-fw)).transposed().to_euler();cam.data.type='PERSP'
        cam.data.sensor_fit='VERTICAL';cam.data.sensor_height=24.;cam.data.lens=24/(2*math.tan(math.radians(75/2)))
    s.render.filepath=str(OUT/f'{family}_{stock}_{t:.3f}_{view}.png');bpy.ops.render.render(write_still=True)

for stock in ('stock','carbon'):
    if '--motion' in sys.argv:
        for i in range(55):draw('skeleton_base',stock,i/60,'grip')
        for t in (.0,.15,.25,.46,.65,.9):draw('skeleton_base',stock,t,'fps')
    else:
        for t in (.08,.125,.25,.46,.55,.65):
            for view in ('grip','palm'):draw('skeleton_base',stock,t,view)
        for family in ('skeleton_base_balanced','skeleton_base_phantom','skeleton_base_stable'):
            for t in (.25,.70,.725):draw(family,stock,t,'grip')
print('CURRENT_STOCK_MELEE_PREVIEW_DONE',flush=True)
