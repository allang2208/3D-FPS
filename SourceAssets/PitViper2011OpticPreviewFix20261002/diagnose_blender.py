import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent;C=S/'PitViper2011Integration20261002'
auth=json.loads((C/'Single/authoring.json').read_text());align=Matrix(auth['alignment'])
bpy.ops.wm.open_mainfile(filepath=str(C/'Single/PitViper2011_single_Editable.blend'))
rig=bpy.data.objects['SK_PitViper2011_Manny'];root=rig.data.bones['WPN_root'].matrix_local
rear=root.inverted()@rig.data.bones['WPN_RearSight'].head_local
front=root.inverted()@rig.data.bones['WPN_FrontSight'].head_local
up=Vector((0,0,1));forward=(front-rear);forward.z=0;forward.normalize()
right=forward.cross(up).normalized()  # Blender exporter reflects Y in UE.
origin=rear+forward*.016+up*.0045
data={'native_rear_root_m':list(rear),'native_front_root_m':list(front),'forward':list(forward),
      'blender_canonical_y_root':list(right),'runtime_origin_root_m':list(origin),'parts':{}}
raw=json.loads((C/'canonical_parts.json').read_text());v=[];f=[]
for part in raw:
 if part['identity']=='2011pv slide_1' and part['material']=='h-190':
  start=len(v);v.extend(align@Vector(p) for p in part['verts']);f.extend([start+i for i in face] for face in part['faces'])
slide=BVHTree.FromPolygons(v,f)
for key in ('holographic','panoramic_red_dot','eoth_holographic'):
 bpy.ops.wm.open_mainfile(filepath=str(S/f'PitViper2011Attachments20261002/Exports/SM_PitViper2011_{key}_Editable.blend'))
 ob=bpy.data.objects['SM_PitViper2011_'+key]
 summary={}
 for slot,mat in enumerate(ob.data.materials):
  ids={i for face in ob.data.polygons if face.material_index==slot for i in face.vertices}
  if not ids:continue
  points=[ob.matrix_world@ob.data.vertices[i].co for i in ids]
  summary[mat.name]={'min_m':[min(p[i] for p in points) for i in range(3)],'max_m':[max(p[i] for p in points) for i in range(3)],'vertices':len(ids)}
 saddle=[face for face in ob.data.polygons if 'PitViper2011_Adapter' in ob.data.materials[face.material_index].name]
 coords=[ob.matrix_world@x.co for x in ob.data.vertices]
 bvh=BVHTree.FromPolygons(coords,[list(p.vertices) for p in saddle])
 contacts=[];thickness=[]
 for x in (-.002,.002,.006,.010,.012):
  for y in (-.006,0,.006):
   roof=slide.ray_cast(origin+forward*x+right*y+up*.08,-up)[0]
   bottom=bvh.ray_cast(Vector((x,y,-.08)),up)[0]
   top=bvh.ray_cast(Vector((x,y,.08)),-up)[0]
   if roof is not None and bottom is not None:
    contacts.append((origin+forward*x+right*y+up*bottom.z-roof).dot(up)*1000)
   if bottom is not None and top is not None:thickness.append((top.z-bottom.z)*1000)
 data['parts'][key]={'object_matrix': [list(r) for r in ob.matrix_world], 'regions':summary,
     'current_bottom_vs_runtime_slide_mm':contacts,'current_seat_thickness_mm':thickness}
(O/'geometry_diagnosis.json').write_text(json.dumps(data,indent=2))
print('PIT_VIPER_OPTIC_DIAGNOSIS_SAVED',flush=True)
