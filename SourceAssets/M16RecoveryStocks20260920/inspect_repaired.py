import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M16_ClosedStockInterfaces_Editable.blend'),use_scripts=False)
s=bpy.context.scene;report={}
for o in s.objects:o.hide_set(False);o.hide_render=True
parts=json.loads((O/'factory_geometry.json').read_text());data=parts['M16A2_Receiver']
me=bpy.data.meshes.new('ReceiverReference');me.from_pydata(data['vertices'],[],data['faces']);receiver=bpy.data.objects.new('ReceiverReference',me);s.collection.objects.link(receiver);receiver.color=(.3,.33,.36,1)
if not s.world:s.world=bpy.data.worlds.new('InterfaceWorld')
s.world.color=(.12,.12,.12);s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_cavity=True;s.display.shading.background_type='WORLD';s.render.resolution_x=720;s.render.resolution_y=540;s.render.resolution_percentage=100;s.render.use_compositing=False;s.render.use_sequencer=False
c=bpy.data.objects.new('InterfaceCamera',bpy.data.cameras.new('InterfaceCamera'));s.collection.objects.link(c);s.camera=c;c.data.type='ORTHO';c.data.ortho_scale=.16;c.data.clip_start=.001;center=Vector((0,.041,.084));c.location=center+Vector((-.12,.24,.115));c.rotation_euler=(center-c.location).to_track_quat('-Z','Y').to_euler()
for key in ['skeleton','qr_performance','core_stock','tactical_telescopic']:
 o=bpy.data.objects['SM_M16_'+key];o.hide_render=False;o.color=(.48,.36,.22,1)
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000002)
 report[key]={'boundary_edges':sum(e.is_boundary for e in bm.edges),'uv_layers':len(o.data.uv_layers),'interface_faces':sum(f.material_index==0 for f in o.data.polygons),'zero_normals':sum(n.vector.length<.5 for n in o.data.corner_normals)};bm.free()
 s.render.filepath=str(O/('after_'+key+'.png'));bpy.ops.render.render(write_still=True);o.hide_render=True
(O/'repaired_topology.json').write_text(json.dumps(report,indent=2));print('M16_REPAIRED_STOCKS',json.dumps(report),flush=True)
