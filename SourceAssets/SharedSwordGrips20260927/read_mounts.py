"""Read the original grip interfaces as manufacturing inputs, without rendering."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
HOSTS={
 'Rune':('ue_rune_sword','rune-sword-modules.json','RuneSwordModules20260919/RuneSword_Modular_Editable.blend','SM_RuneSword_Grip_factory'),
 'Frost':('ue_frost_crystal_sword','frost-sword-modules.json','FrostSwordModules20260915/FrostSword_Modular_Editable.blend','SM_FrostSword_Grip_factory'),
 'Highland':('ue_highland_claymore','highland-claymore-modules.json','HighlandClaymoreMeshy20260922/JunctionBlendV5_20260927/Highland_ContinuousJunctionV5_Editable.blend','SM_Highland_Grip_factory'),
}
result={}
for host,(weapon,catalog,file,name) in HOSTS.items():
 bpy.ops.wm.open_mainfile(filepath=str(P.parent/file))
 obj=bpy.data.objects[name];m=obj.data
 bvh=BVHTree.FromPolygons([v.co for v in m.vertices],[list(p.vertices) for p in m.polygons])
 low=min(v.co.z for v in m.vertices);high=max(v.co.z for v in m.vertices)
 rows=[]
 for t in [.001,.025,.05,.075,.1,.125,.15,.2,.35,.5,.65,.8,.85,.875,.9,.925,.95,.975,.999]:
  z=high+(low-high)*t
  hits=[bvh.ray_cast(Vector((0,0,z)),Vector((math.cos(a),math.sin(a),0)),.2)[0] for a in [0,math.pi/2,math.pi,math.pi*1.5]]
  rows.append({'t':t,'z':z,'radii':[round(math.hypot(p.x,p.y),6) if p is not None else None for p in hits]})
 cat=json.loads((P.parents[1]/'Content/ColdSteelData'/catalog).read_text(encoding='utf-8-sig'))
 result[host]={'weapon':weapon,'catalog':catalog,'blend':file,'object':name,'factory':cat['slots']['grip']['factory'],
  'bounds':[[min(v.co[i] for v in m.vertices) for i in range(3)],[max(v.co[i] for v in m.vertices) for i in range(3)]],
  'materials':[x.name for x in m.materials],'uvs':[x.name for x in m.uv_layers],
  'colors':[{ 'name':x.name,'domain':x.domain,'type':x.data_type} for x in m.color_attributes],
  'sections':rows}
(P/'mount_inputs.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result),flush=True)
