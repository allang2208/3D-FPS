"""First-person before/after pose inspection using current catalog hip offset.
This is an offline animation inspection, not an in-game acceptance capture.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).parent;ROOT=P.parents[1];OUT=P/'Review';OUT.mkdir(exist_ok=True)
catalog=json.loads((ROOT/'Content/ColdSteelData/bows.json').read_text(encoding='utf-8'))['bow_dark']
off=Vector(tuple(float(v) for v in catalog['bow_hip_offset_cm'].split(',')))
for version,case,script in [('before',P.parent/'BowQuickCombatPush20260927','generated_push_v3.py'),('after',P,'generated_contact_v4.py')]:
    ns={'__file__':str(case/script)}
    exec(compile((case/script).read_text().split('bpy.ops.wm.open_mainfile')[0],str(case/script),'exec'),ns)
    bpy.ops.wm.open_mainfile(filepath=str(case/'Bow_QuickCombat.blend'))
    rig=bpy.data.objects['Bow_V7_Native'];arms=bpy.data.objects['SK_Bow_BareArmsV7']
    for o in list(bpy.data.objects):
        if o not in (rig,arms):bpy.data.objects.remove(o,do_unlink=True)
    for o in (rig,arms):o.hide_render=False
    # Armatures are keyed in metres; modular bow meshes are authored in cm.
    rig.location=Vector((off.x,-off.y,off.z))*.01
    parts=[]
    for blend in (ROOT/'SourceAssets/BowModular20260926/Bow_ModularParts.blend',
                  ROOT/'SourceAssets/BowWoodSight20260926/Bow_CarvedWoodSight.blend'):
        with bpy.data.libraries.load(str(blend),link=False) as (a,b):
            b.objects=[n for n in a.objects if n.startswith('SM_Bow_')]
        for o in b.objects:
            if o and o.type=='MESH':
                bpy.context.collection.objects.link(o);o.parent=None;o.animation_data_clear()
                parts.append(o)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=12
    scene.cycles.use_denoising=True
    scene.render.resolution_x=960;scene.render.resolution_y=540;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
    scene.world=bpy.data.worlds.new('InspectionWorld');scene.world.use_nodes=True
    nt=scene.world.node_tree;nt.nodes.clear()
    bg=nt.nodes.new('ShaderNodeBackground');output=nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(bg.outputs[0],output.inputs[0])
    bg.inputs[0].default_value=(.12,.15,.18,1);bg.inputs[1].default_value=.55
    cam_data=bpy.data.cameras.new('Player75Vertical');cam=bpy.data.objects.new('Player75Vertical',cam_data)
    scene.collection.objects.link(cam);cam.rotation_euler=Vector((1,0,0)).to_track_quat('-Z','Y').to_euler()
    cam_data.sensor_fit='VERTICAL';cam_data.sensor_height=32;cam_data.lens=32/(2*math.tan(math.radians(75/2)))
    cam_data.clip_start=.01;scene.camera=cam
    for name,position,power,size in [('Key',(.35,-.8,1.0),100,1.5),('Fill',(.4,.6,.25),45,1.)]:
        ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.shape='DISK';ld.size=size
        lo=bpy.data.objects.new(name,ld);scene.collection.objects.link(lo);lo.location=position
        lo.rotation_euler=(Vector((.5,-.2,-.2))-lo.location).to_track_quat('-Z','Y').to_euler()
    # Keep hands readable independently of the game's texture/lighting state.
    for m in arms.data.materials:
        m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        p.inputs['Base Color'].default_value=(.36,.20,.125,1);p.inputs['Roughness'].default_value=.62
    rows=[];data=ns['ns']['data'];R=ns['R'];rest=ns['rest']
    hand_ids=[i for i,w in enumerate(data['weights']) if sum(v for n,v in w.items() if n=='hand_r' or (n.endswith('_r') and n.split('_')[0] in ('index','middle','ring','pinky','thumb')))>0.8]
    for t in (.10,.14,.32,.66):
        scene.frame_set(round(t*240));bow=ns['pose'](t)['bow_grip']
        shown=bow.copy();shown.translation+=off
        for o in parts:o.matrix_world=ns['world_to_blender'](shown)@Matrix.Scale(.01,4)
        bpy.context.view_layer.update()
        scene.render.filepath=str(OUT/f'{version}_{round(t*1000):03d}.png')
        bpy.ops.render.render(write_still=True)
print('BOW_GRAB_REVIEW_SAVED',str(OUT))
