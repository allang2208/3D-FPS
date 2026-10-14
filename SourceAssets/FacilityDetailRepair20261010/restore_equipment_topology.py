"""Recover the compact manufactured topology, retaining the UV/edge cleanup."""
from pathlib import Path
import bpy,json,hashlib,sys,shutil
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
from uv_finish import finish
backup=ROOT/'Backups/EquipmentUvOriginal.blend'
if not backup.exists():shutil.copy2(ROOT/'Authored/FacilityDetailRepair.blend1',backup)
bpy.ops.wm.open_mainfile(filepath=str(backup))
manifest=json.loads((ROOT/'geometry.json').read_text('utf-8-sig'));changes=[]
for item in manifest['meshes']:
    if item['kind'] not in ('IsolatorCabinet','MaintenancePanel','ServiceBench'):continue
    name=item['mesh'].rsplit('/',1)[1];ob=bpy.data.objects[name];count=finish(ob.data)
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
    hulls=[o for o in bpy.data.objects if o.name.startswith('UCX_'+name+'_')]
    for hull in hulls:hull.hide_set(False);hull.select_set(True)
    bpy.ops.export_scene.fbx(filepath=item['fbx'],use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,colors_type='LINEAR',add_leaf_bones=False,path_mode='STRIP')
    for hull in hulls:hull.hide_set(True)
    # The previous_sha256 still names the last imported compact mesh; the
    # subdivision candidate was never imported into UE.
    item['sha256']=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest();item['triangles']=len(ob.data.polygons)
    item['authored_tangents']=False;item['tangent_basis']='ue_legacy'
    changes.append(dict(mesh=item['mesh'],refined_uv_faces=count,triangles=item['triangles']))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/FacilityDetailRepair.blend'))
(ROOT/'geometry.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
(ROOT/'Receipts/uv-source.json').write_text(json.dumps(changes,indent=2),encoding='utf8')
print('EQUIPMENT_TOPOLOGY_SAVED',changes,flush=True)
