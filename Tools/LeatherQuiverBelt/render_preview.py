"""Actual Blender model previews, explicitly requested before UE integration."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector
R=Path('D:/FPS3D/FPSGAME/SourceAssets/LeatherQuiverBelt20261025')
def bv(p):return Vector((p[0]*.01,-p[1]*.01,p[2]*.01))
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
def plain(name,color,rough=.65):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes.get('Principled BSDF');n.inputs['Base Color'].default_value=(*color,1);n.inputs['Roughness'].default_value=rough;return m
def setup(body):
    bpy.ops.wm.open_mainfile(filepath=str(R/'Exports'/f'LeatherQuiverBelt_{body}_Editable.blend'))
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
    scene.render.threads_mode='FIXED';scene.render.threads=6
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
        use_gpu=False
        for d in prefs.devices:d.use=d.type!='CPU';use_gpu|=d.type!='CPU'
        if use_gpu:scene.cycles.device='GPU'
    except Exception:pass
    scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
    if scene.world is None:scene.world=bpy.data.worlds.new('Preview_Studio_World')
    scene.world.use_nodes=True;world=scene.world.node_tree.nodes.get('Background');world.inputs[0].default_value=(.33,.31,.27,1);world.inputs[1].default_value=.18
    fit=read(R/'Authored'/f'{body}_waist_fit.json');mount=read(R/'Authored'/f'{body}_attachments.json')
    forward=bv(fit['front_axis']).normalized();right=bv(fit['right_axis']).normalized();up=Vector((0,0,1))
    objects=[o for o in bpy.data.collections['01_EDITABLE_LOD0'].objects if o.type=='MESH']
    corners=[o.matrix_world@Vector(v) for o in objects for v in o.bound_box]
    low=Vector(tuple(min(v[i] for v in corners) for i in range(3)));high=Vector(tuple(max(v[i] for v in corners) for i in range(3)))
    center=(low+high)*.5
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,low.z-.025));floor=bpy.context.object;floor.name='Preview_Studio_Floor';floor.data.materials.append(plain('Preview_Studio_Clay',(.24,.225,.205),.83))
    def light(name,offset,energy,size):
        data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
        ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=center+offset;aim(ob,center)
    light('Softbox_Key',forward*1.15+right*.95+up*1.50,60,1.1)
    light('Softbox_Fill',forward*.85-right*.95+up*.55,20,.95)
    light('Softbox_Rim',-forward*.85+right*.70+up*1.05,70,.9)
    camdata=bpy.data.cameras.new('Actual_Model_Camera');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.lens=70
    def render(name,target,offset,scale,res=(1500,1500)):
        cam.location=Vector(target)+offset;aim(cam,target);camdata.ortho_scale=scale
        scene.render.resolution_x,scene.render.resolution_y=res;scene.render.resolution_percentage=100
        scene.render.filepath=str(R/'Preview'/(name+'.png'));bpy.ops.render.render(write_still=True)
        print('QUIVER_MODEL_PREVIEW_SAVED',name,flush=True)
    if body=='Jason':
        render('model-hero',center,forward*1.5+right*1.05+up*.78,.72)
        target=bv(mount['frame_origin_cm'])+up*(-.055)
        render('model-attachment-detail',target,forward*.45+right*1.3+up*.67,.34,(1600,1150))
        render('model-buckle-detail',bv([0,11.7,98]),forward*1.4-right*.12+up*.43,.225,(1600,1050))
    # Render actual sampled trousers as a neutral reference, not a game claim.
    ref=bpy.data.collections['06_NATIVE_REFERENCES'];ref.hide_render=False
    pants=bpy.data.objects.get(body+'_ST6_Pants_REFERENCE');pants.hide_render=False;pants.display_type='TEXTURED'
    pants.data.materials.clear();pants.data.materials.append(plain('Preview_ST6_Fit_Reference',(.13,.15,.16),.86))
    for f in pants.data.polygons:f.material_index=0
    floor.hide_render=True
    render('fit-'+body,center+up*.015,forward*1.5+right*1.05+up*.25,.80,(1200,1500))

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['Jason','Kaitlin']
    for body in args:setup(body)
    (R/'Preview/render_receipt.json').write_text(json.dumps(dict(renderer='Blender Cycles',source='Exports/LeatherQuiverBelt_*_Editable.blend',concept_image_used_as_render=False,game_screenshot=False,requested_preview=True),indent=2)+'\n',encoding='utf-8')
