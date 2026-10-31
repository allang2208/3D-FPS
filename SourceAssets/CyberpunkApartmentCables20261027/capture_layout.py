"""Read the saved apartment's actual device transforms for cable authoring."""
from pathlib import Path
import unreal as u,json
R=Path(__file__).resolve().parent;MAP='/Game/GameMaps/L_CyberpunkApartment'
def v(x):return [round(n,6) for n in x.to_tuple()]
def main(background=True):
 w=u.EditorLoadingAndSavingUtils.load_map(MAP) if background else u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 if not w or w.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Apartment world required')
 rows=[];meshes={}
 for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
  label=a.get_actor_label()
  if not label.startswith(('AP_','BP_','KP_','KR_','AC_')) and not isinstance(a,u.CableActor):continue
  row=dict(actor=label,cls=a.get_class().get_name(),position=v(a.get_actor_location()),rotation=str(a.get_actor_rotation()),scale=v(a.get_actor_scale3d()),components=[])
  for c in a.get_components_by_class(u.StaticMeshComponent):
   m=c.static_mesh
   if not m:continue
   t=c.get_world_transform();path=m.get_path_name()
   row['components'].append(dict(name=c.get_name(),mesh=path,p=v(t.transform_location(u.Vector())),axes=[v(t.transform_location(u.Vector(*q))-t.transform_location(u.Vector())) for q in [(1,0,0),(0,1,0),(0,0,1)]],materials=[x.get_path_name() if x else None for x in c.get_materials()],collision=str(c.get_collision_enabled())))
   if path not in meshes:
    b=m.get_bounding_box();bs=m.get_editor_property('body_setup');boxes=[]
    if bs:
     for q in bs.get_editor_property('agg_geom').get_editor_property('box_elems'):
      boxes.append(dict(center=v(q.get_editor_property('center')),size=[q.get_editor_property(k) for k in ['x','y','z']],rotation=str(q.get_editor_property('rotation'))))
    meshes[path]=dict(min=v(b.min),max=v(b.max),boxes=boxes)
  if isinstance(a,u.CableActor):
   c=a.cable_component
   row['cable']={k:c.get_editor_property(k) for k in ['cable_length','num_segments','cable_width','enable_collision']}
  rows.append(row)
 data=dict(map=MAP,actors=rows,meshes=meshes)
 (R/'scene_inputs.json').write_text(json.dumps(data,indent=2),encoding='utf8')
 print('APARTMENT_CABLE_LAYOUT_CAPTURED',len(rows),len(meshes))
if __name__=='__main__':main()
