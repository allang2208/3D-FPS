"""Render the requested GIF inputs from the current UE-baked editable miner."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260913')
if '--pickaxe' in sys.argv:ROOT=ROOT/'PickaxeSingleHand'
if '--drag-ground' in sys.argv:ROOT=ROOT/'DragGround'
if '--natural-wrist' in sys.argv:ROOT=ROOT/'NaturalWrist'
state=sys.argv[sys.argv.index('--state')+1] if '--state' in sys.argv else 'Attack'
OUT=ROOT/('Previews/SingleHandPickaxe' if '--pickaxe' in sys.argv else 'Previews/DefaultAxe')
if '--drag-ground' in sys.argv:OUT=ROOT/'Previews'/state
if '--natural-wrist' in sys.argv:OUT=ROOT/'Previews'/state
OUT.mkdir(parents=True,exist_ok=True)
contract=json.loads((ROOT/'Delivery/rebuild.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Delivery/InfectedMiner_Editable.blend'))
scene=bpy.context.scene
rig=bpy.data.objects['MinerRig']
action=bpy.data.actions['A_Miner_'+state]
rig.animation_data.action=action
rig.animation_data.action_slot=action.slots[0]
meshes=[o for o in scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
for obj in list(scene.objects):
    if obj.type in ['CAMERA','LIGHT'] or (obj.type=='MESH' and obj not in meshes):
        bpy.data.objects.remove(obj,do_unlink=True)
scene.render.engine='CYCLES'
scene.cycles.device='CPU'
scene.cycles.samples=12
scene.cycles.use_denoising=True
scene.render.resolution_x=620
scene.render.resolution_y=720
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGB'
scene.render.film_transparent=False
scene.render.use_persistent_data=True
scene.render.fps=30
scene.view_settings.view_transform='AgX'
world=bpy.data.worlds.new('DefaultToolPreviewWorld')
world.use_nodes=True
background=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND')
background.inputs['Color'].default_value=(.17,.19,.23,1)
background.inputs['Strength'].default_value=.45
scene.world=world
for location,power,size in [((3,-4,4.5),850,4),((-3,-1,3),500,3),((1,3,4),1000,3)]:
    data=bpy.data.lights.new('PreviewSoftbox','AREA');data.energy=power;data.size=size
    obj=bpy.data.objects.new('PreviewSoftbox',data);scene.collection.objects.link(obj)
    obj.location=location;obj.rotation_euler=(Vector((0,0,1.1))-obj.location).to_track_quat('-Z','Y').to_euler()

frames=list(range(1,round(contract['clips'][state]['seconds']*30)+1,2))
points=[]
for frame in frames:
    scene.frame_set(frame);bpy.context.view_layer.update()
    depsgraph=bpy.context.evaluated_depsgraph_get()
    for obj in meshes:
        evaluated=obj.evaluated_get(depsgraph)
        points.extend(evaluated.matrix_world@Vector(corner) for corner in evaluated.bound_box)
minimum=Vector(tuple(min(p[i] for p in points) for i in range(3)))
maximum=Vector(tuple(max(p[i] for p in points) for i in range(3)))
center=(minimum+maximum)/2
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.012))
floor=bpy.context.object
material=bpy.data.materials.new('PreviewFloor');material.use_nodes=True
bsdf=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
bsdf.inputs['Base Color'].default_value=(.055,.065,.082,1)
bsdf.inputs['Roughness'].default_value=.9
floor.data.materials.append(material)
camera_data=bpy.data.cameras.new('PreviewCamera')
camera=bpy.data.objects.new('PreviewCamera',camera_data)
scene.collection.objects.link(camera);scene.camera=camera
camera_data.type='ORTHO'
camera_data.sensor_fit='HORIZONTAL'
views=[('front',Vector((2.7,-6,1.5))),('side',Vector((6,-.65,1.15)))]
framing={}
for name,offset in views:
    camera.location=center+offset
    camera.rotation_euler=(-offset).to_track_quat('-Z','Y').to_euler()
    rotation=camera.rotation_euler.to_matrix().transposed()
    projected=[rotation@(point-center) for point in points]
    width=max(p.x for p in projected)-min(p.x for p in projected)
    height=max(p.y for p in projected)-min(p.y for p in projected)
    # ORTHO scale is the horizontal aperture for this camera's AUTO fit.
    camera_data.ortho_scale=max(width,height*620/720)*1.12
    framing[name]={'scale':camera_data.ortho_scale,'center':list(center),'offset':list(offset)}
    folder=OUT/name;folder.mkdir(exist_ok=True)
    for i,frame in enumerate(frames):
        if '--still' in sys.argv and i!=0:continue
        if '--keyposes' in sys.argv and i not in [0,5,9,11]:continue
        destination=folder/f'{i:04d}.png'
        if destination.exists() and '--replace' not in sys.argv:continue
        scene.frame_set(frame)
        scene.render.filepath=str(destination)
        bpy.ops.render.render(write_still=True)
        print(f'MINER_PREVIEW_FRAME {name} {i+1}/{len(frames)}',flush=True)
(OUT/'render.json').write_text(json.dumps({'source':str(ROOT/'Delivery/InfectedMiner_Editable.blend'),
    'action':'A_Miner_'+state,'seconds':contract['clips'][state]['seconds'],
    'baked_speed':contract.get('source_play_rate',1),
    'source_frames_1_based':frames,'framing':framing,'size_per_view':[620,720],
    'render':'offline Blender Cycles; editable animation and current model/materials',
    'gameplay_tested':False},indent=2))
print('MINER_DEFAULT_PREVIEW_RENDERED',flush=True)
