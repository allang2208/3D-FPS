import bpy,json,importlib.util
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;S=O.parent;C=S/'HK416CommonAttachments20260930';H=S/'HK416Reworked20260930'
spec=importlib.util.spec_from_file_location('reargrip_interfaces',C/'reargrip_interfaces.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
R=Matrix(json.loads((H/'authoring.json').read_text())['root_matrix'])
sources=json.loads((S/'M16UniversalAttachments20260920/sources.json').read_text())
bpy.context.preferences.filepaths.save_version=0
out=O/'Meshes';out.mkdir(exist_ok=True);report={'parts':{},'runtime_tested':False}
for key in h.CUT:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(O/'Inputs'/('SM_HK416_'+key+'.blend')),link=False) as (a,b):b.objects=a.objects
    body=next(o for o in b.objects if o.type=='MESH');bpy.context.collection.objects.link(body)
    body.data.transform(R.inverted()@body.matrix_world);body.parent=None;body.matrix_world=Matrix.Identity(4);body.hide_set(False)
    for i,slot in enumerate(sources[key]['slots']):body.data.materials[i].name=slot['slot']
    steel=body.data.materials[-1];steel.name='HK416_InterfaceSteel'
    neck,fit=h.fit_reargrip(key,body,R,H/'HK416_Gameplay_Editable.blend',steel)
    bpy.ops.object.select_all(action='DESELECT');body.select_set(True);neck.select_set(True);bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
    body.name='SM_HK416_'+key;body.data.uv_layers.active_index=0;body.data.uv_layers[0].active_render=True
    file=out/(body.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
    bpy.data.libraries.write(str(file.with_suffix('.blend')),{body},fake_user=True)
    body.data.calc_loop_triangles()
    report['parts'][key]={'name':body.name,'file':str(file),'fit':fit,'triangles':len(body.data.loop_triangles),'slots':[m.name for m in body.data.materials]}
    print('HK416_REARGRIP_AUTHORED',key,len(body.data.loop_triangles),flush=True)
(O/'models.json').write_text(json.dumps(report,indent=2))
