import json
from pathlib import Path
import unreal as u
P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/KukriAssetRepair20261026')
E=u.MaterialEditingLibrary
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
def path(x):return x.get_path_name() if x else None
def safe(fn):
    try:return fn()
    except Exception as exc:return str(exc)
blades=json.loads((P.parent/'KukriBladeSurfaceV220261026/surfaces.json').read_text(encoding='utf-8'))['variants']
parts=json.loads((P.parent/'KukriComponentVariants20261026/components.json').read_text(encoding='utf-8'))['variants']
level=None if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower() else u.get_editor_subsystem(u.LevelEditorSubsystem)
report={'pie_running':bool(level and level.is_in_play_in_editor()),'meshes':[],'materials':[]}
for entry in blades+parts:
    mesh=u.load_asset(entry['mesh'])
    row={'asset':entry['mesh'],'lods':mesh.get_num_lods(),'vertices':mesh.get_num_vertices(0),
         'triangles':mesh.get_num_triangles(0),'uv_channels':mesh.get_num_tex_coords(0),'sections':mesh.get_num_sections(0),
         'section_materials':safe(lambda:[SM.get_lod_material_slot(mesh,0,s) for s in range(mesh.get_num_sections(0))]),
         'min_lod':safe(lambda:str(mesh.get_editor_property('min_lod'))),
         'source_description':safe(lambda:path(mesh.get_static_mesh_description(0))),
         'slots':[{'name':str(s.get_editor_property('material_slot_name')),'imported':str(s.get_editor_property('imported_material_slot_name')),'material':path(s.get_editor_property('material_interface'))} for s in mesh.get_editor_property('static_materials')]}
    report['meshes'].append(row)
    (P/'failure-state.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    mat=u.load_asset(entry['material'])
    expressions=[]
    for exp in E.get_material_expressions(mat):
        expressions.append({'class':exp.get_class().get_name(),'texture':safe(lambda:path(exp.get_editor_property('texture'))),
                            'inputs':safe(lambda:[path(n) for n in E.get_inputs_for_material_expression(mat,exp)])})
    report['materials'].append({'asset':entry['material'],
        'front':path(E.get_material_property_input_node(mat,u.MaterialProperty.MP_FRONT_MATERIAL)),
        'base':path(E.get_material_property_input_node(mat,u.MaterialProperty.MP_BASE_COLOR)),
        'textures':[path(t) for t in E.get_material_used_textures(mat)],'expressions':expressions})
    (P/'failure-state.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('KUKRI_FAILURE_STATE_RECORDED')
