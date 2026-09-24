"""Requested geometric diagnosis: compare frame-coincident shell faces before/after."""
import json
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
targets=json.loads((ROOT/'Config/geometry-targets.json').read_text())
made=json.loads((ROOT/'Receipts/geometry.json').read_text())['meshes']
rows={}
def read(path,ports):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path),use_custom_normals=True)
    ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');mesh=ob.data
    coincidences=0
    for port in ports:
        p=Vector((port['position'][0]/100,-port['position'][1]/100,port['position'][2]/100))
        n=Vector((port['normal'][0],-port['normal'][1],port['normal'][2]));r=Vector((-n.y,n.x,0))
        w=port.get('width',300)/100;h=port.get('height',280)/100
        for face in mesh.polygons:
            qs=[ob.matrix_world@mesh.vertices[i].co-p for i in face.vertices]
            ts=[q.dot(r) for q in qs];ds=[q.dot(n) for q in qs];zs=[q.z for q in qs]
            if min(ds)>.145 or max(ds)<-.145 or max(zs)<=.001:continue
            jamb=(all(abs(t-w/2)<.0001 for t in ts) or all(abs(t+w/2)<.0001 for t in ts)) and min(zs)<h
            lintel=all(abs(z-h)<.0001 for z in zs) and min(ts)<w/2 and max(ts)>-w/2
            if jamb or lintel:coincidences+=1
    return dict(polygons=len(mesh.polygons),frame_coincident_faces=coincidences,uv_layers=len(mesh.uv_layers))
for item in targets:
    if item['operation']!='portal_shell':continue
    authored=made[item['path']]
    rows[item['path']]=dict(before=read(authored['original'],item['ports']),after=read(authored['fbx'],item['ports']))
report=dict(meshes=rows,runtime_tested=False,rendered=False)
(ROOT/'Receipts/reveal-diagnosis.json').write_text(json.dumps(report,indent=2))
print('REVEAL_DIAGNOSIS',len(rows),'before',sum(r['before']['frame_coincident_faces'] for r in rows.values()),
      'after',sum(r['after']['frame_coincident_faces'] for r in rows.values()),flush=True)
