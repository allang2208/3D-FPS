import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;S=O.parent;report={}
def topology(o):
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000002);bm.normal_update()
 edges={e for e in bm.edges if e.is_boundary};groups=[]
 while edges:
  edge=edges.pop();group={edge};stack=list(edge.verts)
  while stack:
   v=stack.pop()
   for e in v.link_edges:
    if e in edges:edges.remove(e);group.add(e);stack.extend(e.verts)
  vs={v for e in group for v in e.verts};pts=[v.co.copy() for v in vs];c=sum(pts,Vector())/len(pts)
  groups.append({'edges':len(group),'center_m':list(c),'bounds_m':[[min(p[i] for p in pts),max(p[i] for p in pts)] for i in range(3)],'points_m':[list(p) for p in pts]})
 out={'vertices':len(bm.verts),'faces':len(bm.faces),'boundary_edges':sum(x['edges'] for x in groups),'boundaries':groups};bm.free();return out
bpy.ops.wm.open_mainfile(filepath=str(S/'M16Gameplay20260919/M16_Manny_Editable.blend'),use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['M16_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();W=(r.matrix_world@r.pose.bones['WPN_root'].matrix).inverted();dg=bpy.context.evaluated_depsgraph_get();parts={}
for name in ['M16A2_Receiver','M16A2_Stock']:
 ob=bpy.data.objects[name];ev=ob.evaluated_get(dg);mesh=ev.to_mesh();pts=[W@ev.matrix_world@v.co for v in mesh.vertices];faces=[list(p.vertices) for p in mesh.polygons]
 me=bpy.data.meshes.new(name+'_ref');me.from_pydata(pts,[],faces);obj=bpy.data.objects.new(name+'_ref',me);parts[name]={'vertices':[list(v) for v in pts],'faces':faces};report[name]=topology(obj);ev.to_mesh_clear()
bpy.ops.wm.open_mainfile(filepath=str(S/'M16UniversalAttachments20260920/M16_CommonAttachments_Editable.blend'),use_scripts=False);s=bpy.context.scene
for o in s.objects:
 if o.type=='MESH':o.hide_render=True
for name,data in parts.items():
 me=bpy.data.meshes.new(name+'_ref');me.from_pydata(data['vertices'],[],data['faces']);o=bpy.data.objects.new(name+'_ref',me);s.collection.objects.link(o);o.color=(.3,.33,.36,1);o.hide_render=name.endswith('Stock')
if not s.world:s.world=bpy.data.worlds.new('InterfaceWorld')
s.world.color=(.12,.12,.12);s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_cavity=True;s.display.shading.background_type='WORLD';s.render.resolution_x=720;s.render.resolution_y=540;s.render.resolution_percentage=100;s.render.use_compositing=False;s.render.use_sequencer=False
c=bpy.data.objects.new('InterfaceCamera',bpy.data.cameras.new('InterfaceCamera'));s.collection.objects.link(c);s.camera=c;c.data.type='ORTHO';c.data.ortho_scale=.16;c.data.clip_start=.001;center=Vector((0,.041,.084));c.location=center+Vector((-.12,.24,.115));c.rotation_euler=(center-c.location).to_track_quat('-Z','Y').to_euler()
for key in ['skeleton','qr_performance','core_stock','tactical_telescopic']:
 o=bpy.data.objects['SM_M16_'+key];o.hide_set(False);o.hide_render=False;o.color=(.48,.36,.22,1);report[key]=topology(o);s.render.filepath=str(O/('before_'+key+'.png'));bpy.ops.render.render(write_still=True);o.hide_render=True
(O/'stock_topology.json').write_text(json.dumps(report,indent=2));(O/'factory_geometry.json').write_text(json.dumps(parts,indent=2));print('M16_STOCK_BOUNDARIES',json.dumps({k:{'edges':v['boundary_edges'],'loops':len(v['boundaries'])} for k,v in report.items()}),flush=True)
