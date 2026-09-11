import bpy,json,math
from pathlib import Path
from mathutils import Vector
root=Path('D:/FPS3D/FPSGAME/SourceAssets/PoisonMaggot20260911');out=root/'delivery';pre=root/'previews';pre.mkdir(exist_ok=True)
report={};contracts={'Idle':3,'Move':2.5,'Spit':3,'Death':1.8,'Hit':.6}
for action,duration in contracts.items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.view.language='en_US';bpy.ops.import_scene.fbx(filepath=str(out/f'A_PoisonMaggot_{action}.fbx'))
 rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH');s=bpy.context.scene;s.render.fps=30;s.frame_start=round(rig.animation_data.action.frame_range[0]);s.frame_end=round(rig.animation_data.action.frame_range[1])
 # Blender infers connected bones on FBX import; that locks valid exported
 # translation tracks. Restore the authored unconnected semantics (UE has no such lock).
 bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
 for bone in rig.data.edit_bones:bone.use_connect=False
 bpy.ops.object.mode_set(mode='OBJECT')
 mat=bpy.data.materials.new('ExportPBR');mat.use_nodes=True;nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');mesh.data.materials.clear();mesh.data.materials.append(mat)
 for sem,input_name in [('BaseColor','Base Color'),('Roughness','Roughness'),('Normal','Normal')]:
  n=nt.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(out/f'T_Maggot_{sem}.png'));n.image.colorspace_settings.name='sRGB' if sem=='BaseColor' else 'Non-Color'
  if sem=='Normal':normal=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(n.outputs['Color'],normal.inputs['Color']);nt.links.new(normal.outputs['Normal'],bs.inputs['Normal'])
  else:nt.links.new(n.outputs['Color'],bs.inputs[input_name])
 bs.inputs['Subsurface Weight'].default_value=.045;bs.inputs['Subsurface Scale'].default_value=.012
 bbox=[];poses=[];weights=[sum(g.weight for g in v.groups) for v in mesh.data.vertices];minz=99;maxz=-99
 for f in range(s.frame_start,s.frame_end+1):
  s.frame_set(f);dg=bpy.context.evaluated_depsgraph_get();me=mesh.evaluated_get(dg);m=me.to_mesh();coords=[me.matrix_world@v.co for v in m.vertices];minz=min(minz,min(p.z for p in coords));maxz=max(maxz,max(p.z for p in coords));
  if f in (s.frame_start,s.frame_end):poses.append([p.copy() for p in coords])
  me.to_mesh_clear()
 loop=max((a-b).length for a,b in zip(*poses)) if action in ('Idle','Move') else None
 report[action]={'imported_action_range':list(rig.animation_data.action.frame_range),'seconds':(rig.animation_data.action.frame_range[1]-rig.animation_data.action.frame_range[0])/30,'bones':len(rig.data.bones),'vertices':len(mesh.data.vertices),'max_weight_error':max(abs(w-1) for w in weights),'loop_max_vertex_delta_m':loop,'min_z_m':minz,'max_z_m':maxz}
 assert abs(report[action]['seconds']-duration)<.002;assert max(abs(w-1) for w in weights)<.001
 print('FRAME_VALIDATION',action,json.dumps(report[action]),flush=True)
 if loop is not None:assert loop<.001
 s.render.engine='CYCLES';s.cycles.samples=16;s.render.resolution_x=960;s.render.resolution_y=640;s.render.resolution_percentage=100
 world=bpy.data.worlds.new('ReferenceStudio');world.use_nodes=True;s.world=world;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.13,.14,.16,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65
 bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object;floor.location.z=-.013;floor.name='ReferenceGround';fm=bpy.data.materials.new('Ground');fm.diffuse_color=(.075,.085,.09,1);floor.data.materials.append(fm)
 for name,pos,power,size in [('Key',(0,-3,5),750,4),('Fill',(-3,-1,2),400,3),('Rim',(0,3,4),850,3)]:
  d=bpy.data.lights.new(name,'AREA');d.energy=power;d.size=size;o=bpy.data.objects.new(name,d);s.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,.4))-o.location).to_track_quat('-Z','Y').to_euler()
 d=bpy.data.cameras.new('Preview');cam=bpy.data.objects.new('Preview',d);s.collection.objects.link(cam);cam.location=(3,-5,2.3);cam.rotation_euler=(Vector((0,0,.45))-cam.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=3.1;s.camera=cam
 folder=pre/action;folder.mkdir(exist_ok=True)
 # Reimported actual FBX rendered at 10 fps; image sequences are editable inspection evidence.
 for f in range(s.frame_start,s.frame_end,3):
  s.frame_set(f);s.render.filepath=str(folder/f'{f:03}.png');bpy.ops.render.render(write_still=True)
 print('VERIFIED_RENDERED',action,json.dumps(report[action]),flush=True)
(pre/'export_validation.json').write_text(json.dumps(report,indent=2));print('MAGGOT_EXPORT_VERIFIED',flush=True)
