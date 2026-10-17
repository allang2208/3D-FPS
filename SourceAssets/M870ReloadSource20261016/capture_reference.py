"""Observe and capture the original UC Blend, including its evaluated hand rig."""
import bpy,bmesh,json,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;S=O.parent/'M870UrbanAnimations20261015/Original/870'
bpy.ops.wm.open_mainfile(filepath=str(S/'Renmington 870 unfucked.blend'),use_scripts=False)
r=bpy.data.objects['gmod_arms'];scene=bpy.context.scene
data={'rest':{b.name:[list(v) for v in r.matrix_world@b.matrix_local] for b in r.data.bones},'parents':{b.name:b.parent.name if b.parent else None for b in r.data.bones},'clips':{},'source':str(S/'Renmington 870 unfucked.blend')}
for name,end in [('Idle',0),('reloadstart',20),('reloadinsert',26),('reloadend',22),('reloadendCycle',39)]:
 a=bpy.data.actions[name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 rows=[]
 for f in range(end+1):
  scene.frame_set(f);bpy.context.view_layer.update();ev=r.evaluated_get(bpy.context.evaluated_depsgraph_get())
  rows.append({b.name:[list(v) for v in ev.matrix_world@b.matrix] for b in ev.pose.bones})
 data['clips'][name]={'fps':30,'rows':rows}
(O/'reference_poses.json').write_text(json.dumps(data,separators=(',',':')))
print('REFERENCE_BIND_HAND',data['rest'].get('ValveBiped.Bip01_R_Hand'),flush=True)
print('ORIGINAL_VISIBLE',[(o.name,o.hide_render,o.hide_viewport) for o in scene.objects if o.type=='MESH' and o.name.startswith('c_arms')],flush=True)
shown={'c_arms_combine','shotgun','shotgun_barrel','shotgun_stock','shotgun_slide_wood','shotgun_tube_6','shell for animating '}
# Isolate the actually held shell, excluding the source's static modelling
# duplicate and the second/ejected prop. The original file is never saved.
proxy=bpy.data.objects['shell for animating '];proxy.data=proxy.data.copy();group=proxy.vertex_groups['870_shell2'].index
ids={v.index for v in proxy.data.vertices if any(g.group==group and g.weight>.5 for g in v.groups)}
bm=bmesh.new();bm.from_mesh(proxy.data);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=[f for f in bm.faces if not all(v.index in ids for v in f.verts)],context='FACES');bm.to_mesh(proxy.data);bm.free()
for ob in scene.objects:
 if ob.type=='MESH':
  ob.hide_render=ob.name not in shown;ob.hide_set(False);ob.hide_viewport=False
  ob.color=(.52,.36,.23,1) if ob.name.startswith('c_arms') else (.8,.05,.01,1) if ob.name.startswith('shell') else (.12,.14,.17,1)
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1100;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.render.image_settings.media_type='IMAGE';scene.render.image_settings.file_format='PNG'
scene.display.shading.color_type='OBJECT';scene.display.shading.light='STUDIO';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
scene.display.shading.background_type='WORLD'
if not scene.world:scene.world=bpy.data.worlds.new('ReferenceWorld')
scene.world.color=(.075,.075,.075)
cam=bpy.data.objects.new('ReferenceCloseCamera',bpy.data.cameras.new('ReferenceCloseCamera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO'
a=bpy.data.actions['reloadinsert'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
for f in (0,6,12,20):
 scene.frame_set(f);bpy.context.view_layer.update();ev=r.evaluated_get(bpy.context.evaluated_depsgraph_get())
 h=ev.matrix_world@ev.pose.bones['ValveBiped.Bip01_R_Hand'].matrix
 elbow=(ev.matrix_world@ev.pose.bones['ValveBiped.Bip01_R_Forearm'].matrix).translation
 size=(h.translation-elbow).length
 cam.data.ortho_scale=size*1.7;cam.location=h.translation+Vector((size*1.5,-size*1.8,size*1.3));cam.rotation_euler=(h.translation-cam.location).to_track_quat('-Z','Y').to_euler()
 scene.render.filepath=str(O/f'reference_insert_{f:02d}.png');bpy.ops.render.render(write_still=True)
print('M870_ORIGINAL_REFERENCE_CAPTURED',flush=True)
