"""Finish the newly generated grip surfaces for runtime after joining and UV work."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent;R=O/'RuntimeSource';(R/'Exports').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'LMG201_GripJunction44.blend'),use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
model=json.loads((O/'model.json').read_text())
def select(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
for key in ['stable','balanced','phantom']:
    ob=bpy.data.objects['RearGrip_'+key+'_J44'];select(ob)
    source=ob.copy();source.data=ob.data.copy();bpy.context.scene.collection.objects.link(source);source.name='J44_DenseJoinedSource_'+key
    original=sum(len(f.vertices)-2 for f in ob.data.polygons)
    # Collapse the completed connected surface; creating the seam first avoids
    # slicing a pinched reduced surface. UVs and normals follow the joined source.
    simplify=ob.modifiers.new('Runtime connected surface','DECIMATE');simplify.decimate_type='COLLAPSE';simplify.ratio=min(1.,45000/original);simplify.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=simplify.name)
    for f in ob.data.polygons:f.use_smooth=True;f.material_index=1
    transfer=ob.modifiers.new('Joined surface corner data','DATA_TRANSFER');transfer.object=source;transfer.use_loop_data=True;transfer.data_types_loops={'UV','CUSTOM_NORMAL'};transfer.loop_mapping='POLYINTERP_NEAREST';transfer.layers_uv_select_src='ALL';transfer.layers_uv_select_dst='NAME'
    bpy.ops.object.datalayout_transfer(modifier=transfer.name);bpy.ops.object.modifier_apply(modifier=transfer.name)
    output=R/'Exports'/('SM_LMG201_J44_'+key+'.fbx');select(ob)
    bpy.ops.export_scene.fbx(filepath=str(output),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE')
    model['grip_fbx'][key]=str(output);model['grips'][key]['runtime_triangles']=sum(len(f.vertices)-2 for f in ob.data.polygons);model['grips'][key]['authoring_triangles']=original
    print('J44_RUNTIME_EXPORTED',key,original,model['grips'][key]['runtime_triangles'],flush=True)
    source.hide_render=True;source.hide_set(True);ob.hide_render=True;ob.hide_set(True)
model['runtime_blend']=str(R/'LMG201_GripJunction44_Runtime.blend')
bpy.ops.wm.save_as_mainfile(filepath=model['runtime_blend']);(R/'model.json').write_text(json.dumps(model,indent=2));print('J44_RUNTIME_SAVED',flush=True)
