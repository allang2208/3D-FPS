"""Repair only the five audited print slots in separately owned mesh copies, retaining UCX."""
import json,re
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[2]
read=lambda p:json.loads(p.read_text('utf8'))
source=read(PROJECT/'SourceAssets/WarehouseContainers20261002/Authored/manifest.json')
target=read(ROOT/'Authored/manifest.json');target['objects']=[e for e in target['objects'] if e.get('kind')!='WarehouseText']
mapping={}
for e in source['objects']:
    if not any('_Labels' in p for p in e['materials'].values()):continue
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=e['fbx'],use_custom_normals=True)
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith('UCX_')]
    obj=meshes[0];old=e['name'];name=old+'_TextV2';obj.name=name
    for face in obj.data.polygons:
        if not obj.data.materials[face.material_index].name.startswith('RS_Labels'):continue
        loops=list(face.loop_indices)[:3];uv=[obj.data.uv_layers[0].data[i].uv.copy() for i in loops]
        points=[obj.matrix_world @ obj.data.vertices[obj.data.loops[i].vertex_index].co for i in loops]
        a,c=uv[1]-uv[0],uv[2]-uv[0];det=a.x*c.y-a.y*c.x
        e1,e2=points[1]-points[0],points[2]-points[0]
        if abs(det)<1.e-10:continue
        tangent=(e1*c.y-e2*a.y)/det;right=Vector((0,0,1)).cross(e1.cross(e2).normalized())
        if tangent.dot(right)>=0:continue
        for layer in obj.data.uv_layers:
            for li in face.loop_indices:layer.data[li].uv.x=1-layer.data[li].uv.x
    colliders=[o for o in bpy.context.scene.objects if o.name.startswith('UCX_')]
    for o in colliders:o.name=o.name.replace('UCX_'+old,'UCX_'+name)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    for o in colliders:o.select_set(True)
    bpy.context.view_layer.objects.active=obj;file=ROOT/'Authored'/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    obj.data.calc_loop_triangles();path='/Game/Dungeons/StationWorkshop20261003/RefineV2/Meshes/'+name
    previous='/Game/Dungeons/WarehouseContainers20261002/Meshes/'+old;mapping[previous]=path
    target['objects'].append(dict(name=name,kind='WarehouseText',asset=path,fbx=str(file),materials=e['materials'],
        triangles=len(obj.data.loop_triangles),nanite=e.get('nanite',True),collision=e['collision'],source_asset=previous))
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored'/(name+'.blend')))
(ROOT/'Authored/manifest.json').write_text(json.dumps(target,ensure_ascii=False,indent=2),encoding='utf8')
(ROOT/'Config/text-asset-remap.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf8')
print('WAREHOUSE_TEXT_COPIES_AUTHORED',len(mapping),flush=True)
