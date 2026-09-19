import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME/SourceAssets/ResonanceGrip20260913');O=P/'Repaired91871/Game/Review';O.mkdir(exist_ok=True);report={}
bpy.context.preferences.filepaths.save_version=0
for seed in [91871]:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(P/'Repaired91871/Game/M4/ResonanceGrip_Surface.glb'))
 obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];pts=[o.matrix_world@v.co for o in obs for v in o.data.vertices]
 lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)]);center=(lo+hi)/2;span=max(hi-lo)
 stat={'bounds':list(hi-lo),'meshes':[]}
 for ob in obs:
  me=ob.data;me.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(me)
  stat['meshes'].append({'vertices':len(me.vertices),'triangles':len(me.loop_triangles),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'uv_channels':len(me.uv_layers),'textures':[{'image':n.image.name,'size':list(n.image.size)} for m in me.materials if m and m.use_nodes for n in m.node_tree.nodes if n.type=='TEX_IMAGE']});bm.free()
 report[str(seed)]=stat
 s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True;s.render.resolution_x=1200;s.render.resolution_y=1000;s.render.resolution_percentage=100
 s.world=bpy.data.worlds.new('ReviewWorld');s.world.use_nodes=True;next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.19,.19,.19,1);s.view_settings.view_transform='AgX'
 for off,power,size in [((2,-2,3),350,2),((-2,-1,1),220,2),((1,3,2),450,1.5)]:
  bpy.ops.object.light_add(type='AREA',location=center+Vector(off)*span);light=bpy.context.object;light.data.energy=power*span*span;light.data.shape='DISK';light.data.size=size*span;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
 bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';s.camera=cam
 clay=bpy.data.materials.new('ReviewClay');clay.use_nodes=True;bs=next(n for n in clay.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.3,.32,.34,1);bs.inputs['Roughness'].default_value=.38;bs.inputs['Metallic'].default_value=.0
 for view,off in [('side',(3,0,0)),('quarter',(3,-1.7,1))]:
  cam.location=center+Vector(off)*span;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=span*1.2
  for mode in ['material','clay']:
   s.view_layers[0].material_override=clay if mode=='clay' else None;s.render.filepath=str(O/f'{seed}_{view}_{mode}.png');bpy.ops.render.render(write_still=True)
 (O/'model_data.json').write_text(json.dumps(report,indent=2))
print('REVIEW_RENDER_COMPLETE')
