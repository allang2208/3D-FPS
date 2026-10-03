import bpy,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'G18Integration20260929/Single/G18_single_Editable.blend'))
r=bpy.data.objects['SK_G18_Manny'];root=r.data.bones['WPN_root'].matrix_local.copy()
inv=root.inverted();mag=bpy.data.objects['G18_G18_mag']
pts=[inv@v.co for v in mag.data.vertices]
report={'root': [list(row) for row in root], 'mag_bind':[list(row) for row in r.data.bones['WPN_SOCKET_Magazine'].matrix_local],
        'mag_bounds_root':[[min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]],
        'materials':[m.name for m in mag.data.materials], 'textures':[{ 'name':im.name,'path':im.filepath} for im in bpy.data.images if im.source=='FILE'],
        'cross_sections':{str(z):[[min(p[i] for p in pts if abs(p.z-z)<.006) for i in (0,1)],[max(p[i] for p in pts if abs(p.z-z)<.006) for i in (0,1)]] for z in (-.025,-.065,-.09,-.10) if any(abs(p.z-z)<.006 for p in pts)}}
(O/'interface.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='textures'}),flush=True)
