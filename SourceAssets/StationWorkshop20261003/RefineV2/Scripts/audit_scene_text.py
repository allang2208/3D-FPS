"""User-requested freight-line printed-face direction audit; geometry/UV only, no render."""
import json,math
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent;PROJECT=PARENT.parents[1]
read=lambda p:json.loads(p.read_text('utf-8-sig'))
groups=[]
for group,manifest in [('WorkshopBefore',PARENT/'Authored/manifest.json'),('WorkshopFixed',ROOT/'Authored/manifest.json'),
    ('WarehouseSigns',PROJECT/'SourceAssets/DungeonCargoWarehouse20261001/RefineV2/Authored/manifest.json'),
    ('WarehouseContainersBefore',PROJECT/'SourceAssets/WarehouseContainers20261002/Authored/manifest.json')]:
    for e in read(manifest)['objects']:
        slots=[k for k,v in e['materials'].items() if any(s in str(v).lower() for s in ('_labels','_print','_screen','_label'))]
        if slots:groups.append((group,e['name'],Path(e['fbx']),slots))
for e in read(PROJECT/'SourceAssets/DungeonWorkbenchKit20260921/Authored/manifest.json')['components']:
    slots=[k for k in e['materials'] if 'Label' in k]
    if slots:groups.append(('ReusedWorkbench',e['name'],Path(e['fbx']),slots))
report=dict(scope='All printed face families used in the freight transfer / warehouse / station subject',
    method='FBX triangle normal and UV-U derivative; Blender-to-UE Y conversion; vertical camera-right direction',
    entries=[],source_family_notes=[
        'Transit station structural meshes and freight transfer marking meshes do not contain glyph print slots.',
        'Shared cargo prop atlas cargo() geometry contains strapping/wood patterns, not wall typography.',
        'Horizontal workroom documents now read from the operator side; square keyboard legend cells retain native aspect.'],
    tests_run=False,game_run=False,rendered=False)
for group,name,file,slots in groups:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(file),use_custom_normals=True)
    forward=mirrored=horizontal=0;areas=dict(forward=0.,mirrored=0.)
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH' or obj.name.startswith('UCX_'):continue
        mesh=obj.data;layer=mesh.uv_layers[0] if mesh.uv_layers else None
        if not layer:continue
        for face in mesh.polygons:
            material=mesh.materials[face.material_index]
            slot=material.name if material else ''
            if not any(slot==s or slot.startswith(s+'.') for s in slots):continue
            loops=list(face.loop_indices)[:3]
            p=[obj.matrix_world @ mesh.vertices[mesh.loops[i].vertex_index].co for i in loops]
            uv=[layer.data[i].uv.copy() for i in loops]
            e1,e2=p[1]-p[0],p[2]-p[0];normal=e1.cross(e2).normalized()
            if abs(normal.z)>.8:horizontal+=1;continue
            a,c=uv[1]-uv[0],uv[2]-uv[0];det=a.x*c.y-a.y*c.x
            if abs(det)<1.e-10:continue
            tangent=(e1*c.y-e2*a.y)/det;right=Vector((0,0,1)).cross(normal)
            if abs(tangent.dot(right))<1.e-10:continue
            if tangent.dot(right)>0:forward+=1;areas['forward']+=e1.cross(e2).length/2
            else:mirrored+=1;areas['mirrored']+=e1.cross(e2).length/2
    report['entries'].append(dict(group=group,mesh=name,file=str(file),forward_triangles=forward,
        mirrored_triangles=mirrored,horizontal_triangles=horizontal,vertical_area_m2=areas))
report['historical_mirrored_meshes']=[r['mesh'] for r in report['entries'] if r['group']=='WorkshopBefore' and r['mirrored_triangles']]
report['remaining_mirrored_families']=[r for r in report['entries'] if not r['group'].endswith('Before') and r['mirrored_triangles']]
(ROOT/'Receipts/text-direction-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('REQUESTED_TEXT_AUDIT_SAVED',len(report['entries']),len(report['remaining_mirrored_families']),flush=True)
