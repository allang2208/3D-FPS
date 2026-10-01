"""User-requested, scoped source diagnosis of pipes and gauge faces. No rendering."""
import bpy,bmesh,json,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent
(ROOT/'Receipts').mkdir(parents=True,exist_ok=True)
v2='--v2' in sys.argv;suffix='_V2' if v2 else ''
bpy.ops.wm.open_mainfile(filepath=str((ROOT if v2 else HALL)/'Authored/AbandonedFlueGasStation_Source.blend'))
result={}
for kind in ('WetPipework','GasDucts','Exhaust','Instruments'):
    ob=bpy.data.objects['SM_FlueGas_'+kind+suffix];me=ob.data;bm=bmesh.new();bm.from_mesh(me)
    item=dict(boundary_edges=sum(e.is_boundary for e in bm.edges),wire_edges=sum(e.is_wire for e in bm.edges),
        unused_vertices=sum(not v.link_faces for v in bm.verts),triangles=len(me.polygons))
    if kind=='WetPipework':
        outer=[];inner=[]
        for f in me.polygons:
            p=f.center
            if -5.60<p.x<-5.30 and abs(p.y+5.65)<.105 and abs(p.z-.4)<.105:
                radial=Vector((0,p.y+5.65,p.z-.4))
                target=outer if me.materials[f.material_index].name.startswith('RS_PipeEnamel') else inner
                target.append(f.normal.dot(radial.normalized()))
        item['drain_outer_radial_dots']=outer;item['drain_inner_radial_dots']=inner
    if kind=='Instruments':
        item['label_normals']={}
        for f in me.polygons:
            if me.materials[f.material_index].name.startswith('RS_Labels'):
                key=str(tuple(round(float(v),2) for v in f.normal));item['label_normals'][key]=item['label_normals'].get(key,0)+1
    result[kind]=item;bm.free()
if v2:
    result['rail_collision_hulls']=sum(ob.name.startswith('UCX_') for ob in bpy.data.objects)
    result['dial_orientation_correct']=all(
        f.normal.x>.99 if f.center.x<-5 else f.normal.y<-.99
        for f in bpy.data.objects['SM_FlueGas_Instruments_V2'].data.polygons
        if bpy.data.objects['SM_FlueGas_Instruments_V2'].data.materials[f.material_index].name.startswith('RS_Labels'))
(ROOT/('Receipts/source-diagnosis-v2.json' if v2 else 'Receipts/source-diagnosis.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:{kk:vv for kk,vv in v.items() if not kk.endswith('_dots')} if isinstance(v,dict) else v for k,v in result.items()}))
for k in ('drain_outer_radial_dots','drain_inner_radial_dots'):
    a=result['WetPipework'][k];print(k,len(a),sum(v<0 for v in a),sum(v>0 for v in a))
