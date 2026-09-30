"""Read current 201 magazine visibility and export the drum for the reported gap."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];(O/'Inputs').mkdir(exist_ok=True);out={'assets':{},'instances':[]}
def tr(t):return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
for name,path in [('Body','/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'),('Drum','/Game/Weapons/LMG201/Drum46/SM_LMG201_LargeDrum')]:
 a=u.load_asset(path)
 if not a:raise RuntimeError(path)
 slots=a.materials if name=='Body' else a.static_materials
 out['assets'][name]={'asset':path,'sha256':hashlib.sha256((P/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest(),'slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in slots]}
 if name=='Drum':
  task=u.AssetExportTask();task.object=a;task.filename=str(O/'Inputs/CurrentDrum.fbx');task.automated=True;task.prompt=False;task.replace_identical=True;task.options=u.FbxExportOption();task.options.level_of_detail=False;task.options.collision=False;task.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
  if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export drum')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem);world=editor.get_game_world();out['pie']=bool(world)
if world:
 for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  for mesh in actor.get_components_by_class(u.SkeletalMeshComponent):
   asset=mesh.get_skinned_asset()
   if not asset or not asset.get_path_name().startswith('/Game/Weapons/LMG201/'):continue
   row={'actor':actor.get_name(),'component':mesh.get_name(),'asset':asset.get_path_name(),'visible':mesh.is_visible(),'sections':[],'bones':{},'children':[]}
   for i,slot in enumerate(asset.materials):
    if 'Magazine' in str(slot.material_slot_name):row['sections'].append({'slot':i,'name':str(slot.material_slot_name),'shown':mesh.is_material_section_shown(i,0)})
   for n in ['WPN_root','WPN_SOCKET_Magazine']:row['bones'][n]=tr(mesh.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT))
   for c in mesh.get_children_components(True):
    if isinstance(c,u.StaticMeshComponent) and c.static_mesh and ('Drum' in c.static_mesh.get_path_name() or 'Mag' in c.get_name()):
     row['children'].append({'name':c.get_name(),'asset':c.static_mesh.get_path_name(),'visible':c.is_visible(),'socket':str(c.get_attach_socket_name()),'relative':tr(c.get_relative_transform()),'world':tr(c.get_world_transform())})
   out['instances'].append(row)
(O/'capture.json').write_text(json.dumps(out,indent=2));print('D47_CURRENT_STATE',json.dumps(out['instances']),flush=True)
