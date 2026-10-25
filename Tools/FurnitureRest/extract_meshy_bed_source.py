"""Read the supplied Meshy clip at its original seconds and render source poses."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/FurnitureRest20261022/MeshySitLieBed37120261024'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Imported/source_unmodified.blend'))
rig=bpy.data.objects['target_character']
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.find_armature()==rig]
for o in bpy.context.scene.objects:
    if o.type=='MESH' and o not in meshes:o.hide_render=True
    if o.animation_data:
        for track in o.animation_data.nla_tracks:track.mute=True
        o.animation_data.action=None
scene=bpy.context.scene
names=[b.name for b in rig.data.bones]
parents=[names.index(b.parent.name) if b.parent else -1 for b in rig.data.bones]
def mat(m):return [list(row) for row in m]
data={'coordinates':'Blender world, meters, Z up','names':names,'parents':parents,
      'reference':[mat(rig.matrix_world@b.matrix_local) for b in rig.data.bones], 'clips':{}}
bounds=[]
for name in ('Sit_Lie_Bed','sleep'):
    action=bpy.data.actions[name]
    rig.animation_data_create();rig.animation_data.action=action
    rig.animation_data.action_slot=action.slots[0]
    first,last=action.frame_range
    rate=30;duration=(last-first)/(scene.render.fps/scene.render.fps_base)
    count=round(duration*rate)+1
    frames=[]
    for i in range(count):
        f=first+(last-first)*i/(count-1);scene.frame_set(math.floor(f),subframe=f%1)
        bpy.context.view_layer.update()
        frames.append([mat(rig.matrix_world@rig.pose.bones[n].matrix) for n in names])
        if name=='Sit_Lie_Bed' and i%15==0:
            deps=bpy.context.evaluated_depsgraph_get()
            for obj in meshes:
                evaluated=obj.evaluated_get(deps);me=evaluated.to_mesh()
                bounds.extend(evaluated.matrix_world@me.vertices[j].co for j in range(0,len(me.vertices),8))
                evaluated.to_mesh_clear()
    data['clips'][name]={'duration':duration,'rate':30,'frames':frames}
(OUT/'source_world.json').write_text(json.dumps(data,separators=(',',':')))

low=Vector([min(v[i] for v in bounds) for i in range(3)])
high=Vector([max(v[i] for v in bounds) for i in range(3)])
center=(low+high)*.5;size=max(high-low)
for obj in meshes:obj.color=(.25,.52,.68,1)
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('Source studio');scene.world.color=(.055,.065,.08)
scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard';scene.display.render_aa='8'
bpy.ops.mesh.primitive_plane_add(size=20,location=(center.x,center.y,min(0.,low.z)-.01));bpy.context.object.color=(.22,.24,.27,1)
cam=bpy.data.cameras.new('Source view');co=bpy.data.objects.new('Source view',cam);scene.collection.objects.link(co);scene.camera=co
cam.type='ORTHO';cam.ortho_scale=size*1.35;co.location=center+Vector((3,-5,2))*size
co.rotation_euler=(center-co.location).to_track_quat('-Z','Y').to_euler()
for name in ('Sit_Lie_Bed','sleep'):
    action=bpy.data.actions[name];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    first,last=action.frame_range;dest=OUT/'SourcePreview'/name;dest.mkdir(parents=True,exist_ok=True)
    for i in range(10 if name=='Sit_Lie_Bed' else 4):
        f=first+(last-first)*i/(9 if name=='Sit_Lie_Bed' else 3)
        scene.frame_set(math.floor(f),subframe=f%1)
        scene.render.filepath=str(dest/f'{i:03d}.png');bpy.ops.render.render(write_still=True)
print('MESHY_SOURCE_EXTRACTED',[(n,v['duration']) for n,v in data['clips'].items()], 'bounds',list(low),list(high),flush=True)
