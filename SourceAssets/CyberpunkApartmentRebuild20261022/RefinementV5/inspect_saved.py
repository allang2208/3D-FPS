"""User-requested saved component/material inventory; no game or viewport capture."""
from pathlib import Path
import json,runpy
import unreal as u
ROOT=Path(__file__).resolve().parent
phase='after' if (ROOT/'installed.json').exists() else 'before'
# Reuse the existing graph/instance-aware inventory, redirect its report folder.
source=(ROOT.parent/'RefinementV4/audit_components.py').read_text('utf8')
source=source.replace("phase='after' if '-ApartmentSurfaceAfter' in u.SystemLibrary.get_command_line() else 'before'",'phase='+repr(phase))
exec(compile(source,str(ROOT/'audit_components.py'),'exec'),{'__file__':str(ROOT/'audit_components.py'),'__name__':'__main__'})
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);world=ed.get_editor_world() if ed else u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_CyberpunkApartment')
rows=[]
for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
 label=a.get_actor_label()
 if not label.startswith(('AP_','Door_')):continue
 row=dict(label=label,location=list(a.get_actor_location().to_tuple()),rotation=list(a.get_actor_rotation().to_tuple()),scale=list(a.get_actor_scale3d().to_tuple()),components=[])
 for c in a.get_components_by_class(u.StaticMeshComponent):
  if not c.static_mesh:continue
  b=c.static_mesh.get_bounding_box()
  row['components'].append(dict(name=c.get_name(),mesh=c.static_mesh.get_path_name(),bounds=[list(b.min.to_tuple()),list(b.max.to_tuple())],
    relative=list(c.get_editor_property('relative_location').to_tuple()),scale=list(c.get_editor_property('relative_scale3d').to_tuple())))
 if label.startswith('Door_'):row['slide_cm']=a.get_editor_property('slide_distance_cm')
 rows.append(row)
(ROOT/('layout-'+phase+'.json')).write_text(json.dumps(rows,indent=2),encoding='utf8')
print('APARTMENT_V5_LAYOUT_READ',phase,len(rows))
