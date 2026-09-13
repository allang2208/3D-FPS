import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent
bpy.context.preferences.filepaths.save_version=0

def bounds(ob):
 vs=[v.co for v in ob.data.vertices]
 return Vector([min(v[i] for v in vs) for i in range(3)]),Vector([max(v[i] for v in vs) for i in range(3)])

def select(ob):
 bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob

report={}
for family in ['M4','AKM','QBZ191']:
 for kind,seed,length in [('laser',91803,.085)]:
  bpy.ops.wm.open_mainfile(filepath=str(S/'PhantomRearGripSeamFit20260913'/(family+'_Assembly_Editable.blend')))
  names={'M4':['Receiver_M4_Handguard Kmode Unreal_Export'],'AKM':['Receiver_AKM_Soviet_Native'],'QBZ191':['Receiver_QBZ_Handguard']}[family]
  vertices=[];faces=[]
  for name in names:
   gun=bpy.data.objects[name];offset=len(vertices);vertices.extend([gun.matrix_world@v.co for v in gun.data.vertices]);faces.extend([[offset+i for i in p.vertices] for p in gun.data.polygons])
  surface=BVHTree.FromPolygons(vertices,faces)
  # Rail shoe situated on each source handguard's side, away from the support palm.
  cy,cz={'M4':(-.320,.078),'AKM':(-.310,.057),'QBZ191':(-.292,.070)}[family]
  inner=[];ny,nz=12,6
  for iz in range(nz+1):
   for iy in range(ny+1):
    y=cy+(iy/ny-.5)*.038;z=cz+(iz/nz-.5)*.018
    hit,normal,_,_=surface.ray_cast(Vector((.15,y,z)),Vector((-1,0,0)),.15)
    inner.append(Vector((hit.x-.0004 if hit is not None else float('nan'),y,z)))
  solid=[v for v in inner if math.isfinite(v.x)]
  if not solid:raise RuntimeError('No solid mounting surface '+family)
  for v in inner:
   if not math.isfinite(v.x):v.x=min(solid,key=lambda q:(q.y-v.y)**2+(q.z-v.z)**2).x
  mountx=max(v.x for v in inner)+.002
  report[family]={'mount_x':mountx,'center_y':cy,'center_z':cz}
  (O/'mount_measurements.json').write_text(json.dumps(report,indent=2))
  print('TACTICAL_MOUNT',family,mountx,flush=True)
