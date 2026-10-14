"""Repair the narrow bevel triangulation, keeping a separate import revision."""
from pathlib import Path
from datetime import datetime
import bpy,json,hashlib,sys,shutil
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
sys.path.insert(0,str(PROJECT/'SourceAssets/ReceptionFinish20261010'))
from concrete_mesh import project_uv
sys.path.insert(0,str(ROOT))
from frame_mesh import prepare_frame,localize_uv
manifest=json.loads((ROOT/'geometry.json').read_text('utf8'));item=next(m for m in manifest['meshes'] if m['kind']=='ArrivalFrame')
backup=ROOT/'Backups'/('frame-'+datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True)
for path in (ROOT/'geometry.json',ROOT/'Authored/TransitFinish.blend'):shutil.copy2(path,backup/path.name)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authored/TransitFinish.blend'))
obj=bpy.data.objects[item['name']];prepare_frame(obj.data);project_uv(obj.data);localize_uv(obj.data)
obj.data.calc_tangents();bad=sum(l.tangent.length<.99 for l in obj.data.loops)
print('FRAME_ZERO_TANGENTS',bad)
if bad:raise RuntimeError('Frame still has zero tangents')
obj.name='SM_TransitFinish_ArrivalFrameV2';path=ROOT/'Authored'/(obj.name+'.fbx')
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/TransitFinish.blend'))
item.update(name=obj.name,fbx=str(path),mesh='/Game/Dungeons/TransitFinish20261010/Meshes/'+obj.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),triangles=len(obj.data.polygons))
(ROOT/'geometry.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
print('TRANSIT_FRAME_REPAIRED',item['triangles'])
