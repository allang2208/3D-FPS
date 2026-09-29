"""Render source-pack motion for the user's requested selection review."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'Frames';OUT.mkdir(exist_ok=True)
mode=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'all'
receipt=json.loads((ROOT/'export_receipt.json').read_text(encoding='utf-8'))
if mode.startswith('reframe'):
    receipt['selected']=[r for r in receipt['selected'] if r['name'] in ['anim_Attack_A','anim_Attack_C','anim_Burst_A']]
    OUT=ROOT/'FramesReframed';OUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene;s.render.fps=30
bpy.ops.import_scene.fbx(filepath=receipt['mesh_fbx'],use_image_search=False)
rig=next(o for o in s.objects if o.type=='ARMATURE')
keep=rig.matrix_world.copy();rig.parent=None;rig.matrix_world=keep
meshes=[o for o in s.objects if o.type=='MESH']
mat=bpy.data.materials.new('Review source mannequin');mat.use_nodes=True
bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.21,.30,.37,1)
bs.inputs['Metallic'].default_value=.23;bs.inputs['Roughness'].default_value=.40
for o in meshes:
    for i in range(len(o.data.materials)):o.data.materials[i]=mat
    if not o.data.materials:o.data.materials.append(mat)

sources=[]
for row in receipt['selected']:
    before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=row['fbx'],use_image_search=False)
    added=set(bpy.data.objects)-before
    source=next(o for o in added if o.type=='ARMATURE')
    action=source.animation_data.action;action.name=row['name'];action.use_fake_user=True
    sources.append((row,action,float(action.frame_range[0])))
    for o in added:bpy.data.objects.remove(o,do_unlink=True)

bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.007))
floor=bpy.context.object;floor.name='ReviewFloor'
fm=bpy.data.materials.new('ReviewFloor');fm.use_nodes=True
fbs=fm.node_tree.nodes.get('Principled BSDF');fbs.inputs['Base Color'].default_value=(.05,.061,.072,1);fbs.inputs['Roughness'].default_value=.85
floor.data.materials.append(fm)
s.world=bpy.data.worlds.new('ReviewWorld');s.world.use_nodes=True
s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.18,.20,.23,1)
s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
s.render.engine='BLENDER_EEVEE';s.render.resolution_x=384;s.render.resolution_y=448;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB'
s.view_settings.view_transform='AgX'
def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
for name,pos,power,size in [('Key',(3,-4,5),600,4),('Fill',(-4,-2,3),350,4),('Rim',(0,4,4),700,3)]:
    ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.shape='DISK';ld.size=size
    ob=bpy.data.objects.new(name,ld);s.collection.objects.link(ob);ob.location=pos;aim(ob,(0,0,1))
cd=bpy.data.cameras.new('SourceCamera');camera=bpy.data.objects.new('SourceCamera',cd);s.collection.objects.link(camera)
camera.location=(3.6,-6,2.1);aim(camera,(0,0,.96));cd.type='ORTHO';cd.ortho_scale=2.28;s.camera=camera
rig.animation_data_create()
report=[]
for row,action,first in sources:
    is_burst=row['name'].startswith('anim_Burst_')
    if mode=='primary' and is_burst:continue
    if mode=='burst' and not is_burst:continue
    rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    for track in rig.animation_data.nla_tracks:track.mute=True
    folder=OUT/row['name'];folder.mkdir(exist_ok=True)
    if is_burst:
        times=[row['seconds']*f for f in [0,.125,.25,.375,.50,.625,.75,.875]]
    else:times=[i/15 for i in range(math.ceil(row['seconds']*15))]
    if mode.startswith('reframe'):
        # Fit a fixed camera to the full source trajectory without changing the animation.
        orientation=camera.rotation_euler.to_quaternion()
        right=orientation@Vector((1,0,0));up=orientation@Vector((0,1,0))
        projected=[]
        for t in times:
            f=first+t*30;s.frame_set(math.floor(f),subframe=f-math.floor(f));bpy.context.view_layer.update()
            for bone in rig.pose.bones:
                for point in [bone.head,bone.tail]:
                    world=rig.matrix_world@point
                    projected.append((world.dot(right),world.dot(up)))
        xmin=min(v[0] for v in projected);xmax=max(v[0] for v in projected)
        ymin=min(v[1] for v in projected);ymax=max(v[1] for v in projected)
        target=right*((xmin+xmax)*.5)+up*((ymin+ymax)*.5)
        camera.location=target+Vector((3.6,-6,1.14));aim(camera,target)
        cd.ortho_scale=max(ymax-ymin+.30,(xmax-xmin+.30)*448/384)
    positions=[]
    for i,t in enumerate(times):
        f=first+t*30;s.frame_set(math.floor(f),subframe=f-math.floor(f));bpy.context.view_layer.update()
        # Preserve the source root trajectory and use one fixed camera.
        positions.append({b:list(rig.matrix_world@rig.pose.bones[b].head) for b in ['pelvis','head','hand_l','hand_r','foot_l','foot_r']})
        s.render.filepath=str(folder/f'{i:03d}.png');bpy.ops.render.render(write_still=True)
    report.append({'name':row['name'],'asset':row['asset'],'seconds':row['seconds'],'folder':str(folder.relative_to(ROOT)),
                   'frames':len(times),'times':times,'fps':15 if not is_burst else None,'positions_m':positions})
    (ROOT/f'render_{mode}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('ZOMBIE_REVIEW_RENDERED',row['name'],len(times),flush=True)
print('ZOMBIE_SOURCE_REVIEW_DONE',mode,flush=True)
