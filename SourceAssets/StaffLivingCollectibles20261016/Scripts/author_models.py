"""Build editable masters and real FBX/GLB deliverables; no validation render or game launch."""
from pathlib import Path
import sys,json,math
import bpy
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Scripts'))
import geometry as H
import models
ONLY=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
report={'stage':'authoring','assets':{},'alternate_exports':{},'glass_materials':models.GLASS,'game_run':False,'inventory_integrated':False}
if ONLY and (ROOT/'model_manifest.json').exists():report=json.loads((ROOT/'model_manifest.json').read_text('utf-8'))
def record():(ROOT/'model_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def export_mesh(spec,parts,collision,meshname):
 bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();obs=[]
 for part in parts:
  data=bpy.data.meshes.new_from_object(part.evaluated_get(deps),preserve_all_data_layers=True,depsgraph=deps)
  out=bpy.data.objects.new(part.name+'_Export',data);bpy.context.collection.objects.link(out);out.matrix_world=part.matrix_world.copy()
  H.select(out);tri=out.modifiers.new('Production triangulation','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
  if not part.get('authored_decal'):H.uv(out,part['surface_region'])
  obs.append(out)
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.select_set(True)
 bpy.context.view_layer.objects.active=obs[0];bpy.ops.object.join();game=bpy.context.object;game.name=meshname
 game.data.transform(game.matrix_world);game.matrix_world=Matrix.Identity(4)
 points=[v.co for v in game.data.vertices]
 lo=Vector([min(p[k] for p in points) for k in range(3)]);hi=Vector([max(p[k] for p in points) for k in range(3)])
 shift=Vector((-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,-lo.z));game.data.transform(Matrix.Translation(shift))
 game.data.calc_loop_triangles();triangles=len(game.data.loop_triangles);colliders=[]
 for i,desc in enumerate(collision):
  pos,size=desc[:2];bpy.ops.mesh.primitive_cube_add(size=1,location=Vector(pos)+shift);c=bpy.context.object
  c.name='UCX_'+meshname+'_'+str(i).zfill(2);c.scale=size
  if len(desc)>2:c.rotation_euler['XYZ'.index(desc[2][0])]=desc[2][1]
  bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);colliders.append(c)
 H.select(game)
 for c in colliders:c.select_set(True)
 fbx=ROOT/'Export'/(meshname+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Y',axis_up='Z',bake_space_transform=True,mesh_smooth_type='FACE',use_mesh_modifiers=True,use_tspace=True,path_mode='STRIP',add_leaf_bones=False)
 H.select(game);bpy.context.scene.unit_settings.scale_length=1;game.scale=(.01,.01,.01)
 glb=ROOT/'Export'/(meshname+'.glb');bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_materials='EXPORT')
 slots=[m.name for m in game.data.materials if m]
 for o in [game]+colliders:bpy.data.objects.remove(o,do_unlink=True)
 bpy.context.scene.unit_settings.scale_length=.01
 return dict(mesh=meshname,fbx=str(fbx),glb=str(glb),actual_dimensions_cm=list(hi-lo),triangles_lod0=triangles,collision_hulls=len(collision),material_slots=slots,nanite_requested=len(slots)==1,pivot='bottom centre')
for key,builder in models.BUILDERS.items():
 if ONLY and key not in ONLY:continue
 print('LIVING_MODEL_START',key,flush=True)
 bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
 models.init(key);builder();bpy.context.view_layer.update();spec=H.SPEC['assets'][key]
 lid=None
 if key=='Laptop':
  lid=bpy.data.objects.new('EDITABLE_LID_HINGE__rotate_X_108deg_to_close',None);scene.collection.objects.link(lid);lid.location=models.LID_PIVOT
  bpy.context.view_layer.update()
  for o in models.LID_OBJECTS:
   transform=o.matrix_world.copy();o.parent=lid;o.matrix_parent_inverse=lid.matrix_world.inverted();o.matrix_world=transform
  lid['open_angle_degrees']=108;lid['pose_instruction']='Source is open. Rotate this control +108 degrees about local X to close.'
 source=ROOT/'Authored'/(spec['mesh']+'_Source.blend')
 scene['stage']='Editable manufactured source; no visual or gameplay acceptance'
 scene['scale_contract']='Centimetres. Original CS labels. Separate optical and opaque materials.'
 bpy.ops.wm.save_as_mainfile(filepath=str(source))
 result=export_mesh(spec,H.PARTS,H.COLLISIONS,spec['mesh'])
 report['assets'][key]={**spec,**result,'source':str(source),'source_components':len(H.PARTS),'geometry_features':[o.name for o in H.PARTS]};record()
 print('LIVING_MODEL_EXPORTED',key,result['triangles_lod0'],result['actual_dimensions_cm'],flush=True)
 if lid:
  lid.rotation_euler.x=math.radians(108);bpy.context.view_layer.update()
  closed_source=ROOT/'Authored'/'SM_Living_Laptop_Closed_Source.blend';bpy.ops.wm.save_as_mainfile(filepath=str(closed_source))
  closed=export_mesh(spec,H.PARTS,[((0,0,1.3),(32.1,21.8,2.65))],'SM_Living_Laptop_Closed')
  report['alternate_exports']['LaptopClosed']={**spec,**closed,'source':str(closed_source),'pose':'closed','parent_item':'Laptop'};record()
report['stage']='sources_and_exports_saved';record();print('LIVING_AUTHORING_COMPLETE',len(report['assets']),flush=True)
