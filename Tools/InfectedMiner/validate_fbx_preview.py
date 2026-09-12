"""Fresh FBX roundtrip, then render actual exported actions with the authored PBR materials."""
import bpy,json,math,sys,numpy as np
from pathlib import Path
from mathutils import Vector
root=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260912');source=root/('Candidates/CMU02_07' if '--cmu' in sys.argv else 'Delivery');out=root/('Previews/FBX_CMU' if '--cmu' in sys.argv else 'Previews/FBX');out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source/'InfectedMiner_Editable.blend'))
materials={m.name:m for m in bpy.data.materials}
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
bpy.ops.import_scene.fbx(filepath=str(root/'Delivery/SK_InfectedMiner.fbx'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
for o in meshes:
    for slot in o.material_slots:
        base=slot.material.name.split('.')[0]
        if base in materials:slot.material=materials[base]
def bounds():
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();points=[]
    for o in meshes:
        ev=o.evaluated_get(dg);m=ev.to_mesh();points.extend(tuple(ev.matrix_world@v.co) for v in m.vertices);ev.to_mesh_clear()
    a=np.array(points);return {'min':a.min(axis=0).tolist(),'max':a.max(axis=0).tolist()}
def positions():
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();points=[]
    for o in meshes:
        ev=o.evaluated_get(dg);m=ev.to_mesh();points.extend(tuple(ev.matrix_world@v.co) for v in m.vertices);ev.to_mesh_clear()
    return np.array(points)
rest=bounds();assert 1.75<rest['max'][2]-rest['min'][2]<2.1,rest
report={'rest':rest,'bones':len(rig.data.bones),'clips':{}}
for name,frames in [('Idle',308),('Walk',98),('Attack',json.loads((source/'attack-authoring.json').read_text())['frames']),('Hit',18)]:
    file=(source if name=='Attack' else root/'Delivery')/f'A_Miner_{name}.fbx'
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(file),anim_offset=0.0);added=set(bpy.data.objects)-before;donor=next(o for o in added if o.type=='ARMATURE');action=donor.animation_data.action;action.name='Roundtrip_'+name
    action.use_frame_range=True;action.frame_start=1;action.frame_end=frames+1
    action.use_fake_user=True
    for o in added:bpy.data.objects.remove(o,do_unlink=True)
    rig.animation_data_create();rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    samples=[]
    for f in range(1,frames+2,3):bpy.context.scene.frame_set(f);samples.append(bounds())
    report['clips'][name]={'seconds':frames/30,'minimum_z':min(v['min'][2] for v in samples),'maximum_z':max(v['max'][2] for v in samples)}
    if name in ['Idle','Walk']:
        bpy.context.scene.frame_set(1);first=positions();bpy.context.scene.frame_set(frames+1);last=positions();gap=float(np.linalg.norm(last-first,axis=1).max());report['clips'][name]['loop_max_vertex_gap_m']=gap;assert gap<.003,(name,gap)
    assert report['clips'][name]['minimum_z']>-.03,(name,report['clips'][name])
    assert report['clips'][name]['maximum_z']<2.8,(name,report['clips'][name])
(out/'fbx-validation.json').write_text(json.dumps(report,indent=2))
if '--validate-only' in sys.argv:print('MINER_FBX_VALIDATION '+json.dumps(report),flush=True);raise SystemExit(0)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=8;s.render.resolution_x=510;s.render.resolution_y=600;s.render.resolution_percentage=100
w=bpy.data.worlds.new('RoundtripStudio');s.world=w;w.use_nodes=True;next(n for n in w.node_tree.nodes if n.type=='BACKGROUND').inputs['Strength'].default_value=.5
for pos,power,size in [((2,-3,4),500,3),((-3,-1,3),350,3),((0,3,4),550,3)]:
    d=bpy.data.lights.new('Softbox','AREA');d.energy=power;d.size=size;o=bpy.data.objects.new('Softbox',d);s.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.012));floor=bpy.context.object;fm=bpy.data.materials.new('RoundtripFloor');fm.use_nodes=True;next(n for n in fm.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(.07,.075,.08,1);floor.data.materials.append(fm)
d=bpy.data.cameras.new('Camera');c=bpy.data.objects.new('Camera',d);s.collection.objects.link(c);c.location=(2.5,-5,2.2);c.rotation_euler=(Vector((0,-.12,1.22))-c.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=3.05;s.camera=c
for name,frames in [('Attack',json.loads((source/'attack-authoring.json').read_text())['frames']),('Walk',98),('Idle',90),('Hit',18)]:
    if '--attack-only' in sys.argv and name!='Attack':continue
    action=bpy.data.actions['Roundtrip_'+name];rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    folder=out/name;folder.mkdir(exist_ok=True)
    for i,f in enumerate(range(1,frames+1,2)):
        s.frame_set(f);s.render.filepath=str(folder/f'{i:04d}.png');bpy.ops.render.render(write_still=True)
print('MINER_FBX_VERIFIED_AND_RENDERED '+json.dumps(report),flush=True)
