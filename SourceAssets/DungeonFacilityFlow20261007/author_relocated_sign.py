"""Move the existing waiting-area card out of the new hole; keep its UV/aspect."""
import bpy,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent;SOURCE=ROOT.parent/'DungeonReceptionHall20261006/Refine20261007'
manifest=json.loads((SOURCE/'geometry.json').read_text('utf8'))
record=next(m for m in manifest['meshes'] if m['name']=='SM_RH2_Signs')
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(SOURCE/'Authored/ReceptionRefine.blend'),link=False) as (src,dst):
    dst.objects=['SM_RH2_Signs']
obj=dst.objects[0];bpy.context.collection.objects.link(obj)
for v in obj.data.vertices:
    x,y,z=v.co
    if -19.6<x<-15.8 and y<-16.4 and 1.95<z<3.25:v.co.x+=8.7
obj.name='SM_FacilityFlow_RelocatedSigns';obj.data.update();obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
fbx=ROOT/'Authored'/ (obj.name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')
record.update(name=obj.name,kind='RelocatedSigns',mesh='/Game/Dungeons/FacilityFlow20261007/Meshes/'+obj.name,fbx=str(fbx),sha256=hashlib.sha256(fbx.read_bytes()).hexdigest())
(ROOT/'fixture-geometry.json').write_text(json.dumps(dict(meshes=[record]),indent=2),encoding='utf8')
