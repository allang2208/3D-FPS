"""Read the source geometry/skin needed to repair the reported chain stretching."""
from pathlib import Path
import bpy, numpy as np, json
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004')
OUT=ROOT/'ProductionV11';(OUT/'Records').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'ProductionV08/Authoring/M14_Rigged_Bite_v08.blend'))
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
mesh=obj.data;n=len(mesh.vertices)
p=np.empty(n*3,np.float32);mesh.vertices.foreach_get('co',p);p=p.reshape(-1,3)
f=np.empty(len(mesh.loops),np.int32);mesh.loops.foreach_get('vertex_index',f);f=f.reshape(-1,3)
material=np.empty(len(mesh.polygons),np.int32);mesh.polygons.foreach_get('material_index',material)
metal_slots=[i for i,m in enumerate(mesh.materials) if 'Metal' in m.name]
metal=np.isin(material,metal_slots)
selected=np.unique(f[metal])
groups=[g.name for g in obj.vertex_groups]
weights=np.zeros((len(selected),4),np.float32);bones=np.full((len(selected),4),-1,np.int32)
for index,vi in enumerate(selected):
    for k,g in enumerate(sorted(mesh.vertices[int(vi)].groups,key=lambda g:-g.weight)[:4]):
        weights[index,k]=g.weight;bones[index,k]=g.group
np.savez(OUT/'Records/hardware_source.npz',p=p,f=f,material=material,metal=metal,selected=selected,weights=weights,bones=bones)
record={'object':obj.name,'vertices':n,'triangles':len(f),'metal_triangles':int(metal.sum()),
        'metal_vertices':len(selected),'groups':groups,'material_slots':[m.name for m in mesh.materials],
        'source_height_scale':bpy.data.objects['M14_Rig'].get('source_scale'),
        'bones':{b.name:{'head':list(b.head_local),'tail':list(b.tail_local),'parent':b.parent.name if b.parent else None} for b in bpy.data.objects['M14_Rig'].data.bones}}
(OUT/'Records/hardware_source.json').write_text(json.dumps(record,indent=2),encoding='utf8')
print('M14_HARDWARE_SOURCE',record['vertices'],record['triangles'],record['metal_triangles'],flush=True)
