"""Import the user's existing portable FBX into an editable Blender source library.
Preserves topology, UVs, material slots and native pivots. No renders/tests.
"""
import bpy,json,sys,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'References/ReuseBundle';HAND=json.loads((B/'HANDOFF.json').read_text());OUT=ROOT/'Authored'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
report=[]
for asset in HAND['assets']:
 p=B/asset['package_fbx'];old=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(p),use_custom_normals=True,use_image_search=False)
 new=[o for o in bpy.data.objects if o not in old];visual=[o for o in new if o.type=='MESH' and not o.name.startswith(('UCX_','UBX_','USP_','UCP_'))];coll=[o for o in new if o.type=='MESH' and o not in visual]
 if len(visual)!=1:raise RuntimeError('Expected one original render mesh: '+asset['name']+' '+repr([o.name for o in visual]))
 obj=visual[0];obj.name=asset['name'];obj['ue_asset']=asset['ue_asset'];obj['source_fbx']=asset['package_fbx'];obj['source_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();obj['approved_existing_asset']=True
 # Import transform is applied to vertices once; original asset pivot remains at origin.
 # FBX data is already in metres via importer, so never multiply units a second time.
 bpy.ops.object.select_all(action='DESELECT')
 for o in [obj]+coll:o.select_set(True)
 bpy.context.view_layer.objects.active=obj;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
 pts=[obj.matrix_world@v.co for v in obj.data.vertices]
 bounds=dict(min=[min(v[k] for v in pts) for k in range(3)],max=[max(v[k] for v in pts) for k in range(3)])
 for co in coll:co.hide_render=True;co.hide_viewport=True;co['owner_mesh']=obj.name
 obj['source_material_map']=json.dumps(asset.get('materials',{asset.get('slot','Material'):asset.get('material','')}))
 report.append(dict(name=obj.name,ue_asset=asset['ue_asset'],blender_location=list(obj.location),bounds_world_m=bounds,vertices=len(obj.data.vertices),polygons=len(obj.data.polygons),triangles=sum(len(p.vertices)-2 for p in obj.data.polygons),materials=[m.name if m else None for m in obj.data.materials],uv_layers=[u.name for u in obj.data.uv_layers],color_attributes=[c.name for c in obj.data.color_attributes],collision_objects=[c.name for c in coll]))
 print('REUSE_IMPORTED',json.dumps(report[-1]),flush=True)
(OUT/'reuse-import.json').write_text(json.dumps(dict(blender_version=bpy.app.version_string,source='References/ReuseBundle/HANDOFF.json',objects=report,tests_run=False,rendered=False),ensure_ascii=False,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Reused_Original_Assets.blend'))
