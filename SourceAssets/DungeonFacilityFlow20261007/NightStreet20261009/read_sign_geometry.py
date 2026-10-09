import bpy,json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonFacilityFlow20261007')
with bpy.data.libraries.load(str(root/'FrontEntry20261008/Authored/FrontEntry.blend'),link=False) as (src,dst):dst.objects=['SM_FrontEntry_Signs']
o=dst.objects[0]
print('SIGN_MATERIALS',[m.name for m in o.data.materials])
for p in o.data.polygons:
 c=p.center
 if -23.3<c.x<-22.7 and abs(abs(c.y)-4.8)<.6 and .7<c.z<2:
  print('DIRECTORY_FACE',list(c),list(p.normal),o.data.materials[p.material_index].name,'uv',[tuple(o.data.uv_layers.active.data[i].uv) for i in p.loop_indices])
cat=json.loads((root/'Config/catalog.json').read_text('utf8'))
m=next(m for m in cat['modules'] if m['id']=='FacilityReceptionHall')
for p in m['parts']:
 if any(k in p['mesh'] for k in ['Directory','FrontEntry','Vestibule','PreviewCaps']):print('PART',p)
for l in m['lights']:
 if l['position'][0]<-2400:print('VESTIBULE_LIGHT',l)
