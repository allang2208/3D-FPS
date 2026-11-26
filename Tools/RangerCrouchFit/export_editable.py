"""Save fitted native body sources using the existing ranger surface materials."""
import gc,json,sys
from pathlib import Path
import bpy
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/RangerCrouchFit20261021';OUT=R/'Exports';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(P/'Tools/FieldRangerTop'));import export_tailored_finish as materials
io=materials.io
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
exports=[]
for profile in ('Jason','Owner_Jason'):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
    d=read(R/'Authored/ue_field_sweater'/(profile+'.json'));rig=io.rig_io.rig_for(d);ob=io.mesh_for(d,rig)
    color=ob.data.color_attributes.new(name='Col',type='FLOAT_COLOR',domain='POINT');color.data.foreach_set('color',[x for c in d['colors'] for x in c]);ob.data.color_attributes.active_color=color
    bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=ob
    fbx=OUT/(profile+'_RangerCrouchFit.fbx');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE')
    bpy.ops.file.pack_all();blend=OUT/(profile+'_RangerCrouchFit.blend');bpy.ops.wm.save_as_mainfile(filepath=str(blend));exports.extend([str(fbx),str(blend)])
    print('CROUCH_FIT_EDITABLE',profile,flush=True);del d;gc.collect()
(R/'editable.json').write_text(json.dumps(dict(completed=True,exports=exports,preview_rendered=False),indent=2),encoding='utf-8')
