"""Repair only this delivery's derived concrete asset and authoring file."""
from pathlib import Path
from datetime import datetime
import bpy,json,hashlib,sys,shutil
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
from concrete_mesh import prepare_concrete,project_uv
manifest=json.loads((ROOT/'geometry.json').read_text('utf8'))
item=next(m for m in manifest['meshes'] if m['kind']=='BreachConcrete')
backup=ROOT/'Backups'/('concrete-'+datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True)
for path in (ROOT/'geometry.json',ROOT/'Authored/ReceptionFinish.blend',Path(item['fbx'])):shutil.copy2(path,backup/path.name)
old_hash=item['sha256']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authored/ReceptionFinish.blend'))
obj=bpy.data.objects[item['name']]
prepare_concrete(obj.data);project_uv(obj.data)
obj.data.calc_tangents()
bad=sum(l.tangent.length<.99 for l in obj.data.loops)
print('REPAIRED_CONCRETE_ZERO_TANGENTS',bad)
if bad:raise RuntimeError('Concrete still has zero tangents')
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.fbx(filepath=item['fbx'],use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/ReceptionFinish.blend'))
item['previous_sha256']=old_hash;item['sha256']=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest();item['triangles']=len(obj.data.polygons)
(ROOT/'geometry.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
print('CONCRETE_REPAIRED',item['triangles'],str(backup))
