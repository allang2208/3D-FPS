"""Focused read-only trace of the reported missing blade texture."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
D='/Game/Weapons/XuanChiZhenYue20261004/BladeV3'
E=u.MaterialEditingLibrary
def path(o):return o.get_path_name() if o else None
report={'meshes':[],'materials':[],'runtime':[]}
for part in ['Blade','Guard','Complete']:
    mesh=u.load_asset(D+'/Meshes/SM_XuanChi_'+part+'_V3')
    row={'path':path(mesh),'slots':[]}
    if mesh:
        row['sections']=mesh.get_num_sections(0)
        for i,slot in enumerate(mesh.static_materials):
            row['slots'].append({'index':i,'slot':str(slot.material_slot_name),'material':path(slot.material_interface)})
        if part=='Blade':
            row['build_settings']=str(u.get_editor_subsystem(u.StaticMeshEditorSubsystem).get_lod_build_settings(mesh,0))
            lib=getattr(u,'ProceduralMeshLibrary',None)
            if lib:
                vertices,triangles,normals,uvs,tangents=lib.get_section_from_static_mesh(mesh,0,0)
                row['uv0']={'vertices':len(vertices),'triangles':len(triangles)//3,'count':len(uvs),
                    'min':[min(t.x for t in uvs),min(t.y for t in uvs)] if uvs else None,
                    'max':[max(t.x for t in uvs),max(t.y for t in uvs)] if uvs else None,
                    'sample':[[float(t.x),float(t.y)] for t in uvs[::max(1,len(uvs)//12)]]}
    report['meshes'].append(row)
for name in ['M_XuanChi_SteelRelief_V3','M_XuanChi_SteelRelief_V3_Whirlwind']:
    mat=u.load_asset(D+'/Materials/'+name)
    row={'path':path(mat),'nodes':[],'outputs':{}}
    if mat:
        row['used_textures']=[path(t) for t in E.get_material_used_textures(mat)]
        row['statistics']=str(E.get_statistics(mat))
        for prop in ['MP_BASE_COLOR','MP_NORMAL','MP_ROUGHNESS','MP_METALLIC','MP_FRONT_MATERIAL']:
            en=getattr(u.MaterialProperty,prop)
            row['outputs'][prop]={'node':path(E.get_material_property_input_node(mat,en)),
                'pin':E.get_material_property_input_node_output_name(mat,en)}
        for n in E.get_material_expressions(mat):
            nr={'node':n.get_name(),'class':n.get_class().get_name(),
                'input_names':list(E.get_material_expression_input_names(n)),
                'input_nodes':[path(x) for x in E.get_inputs_for_material_expression(mat,n)]}
            if isinstance(n,(u.MaterialExpressionTextureSample,u.MaterialExpressionTextureObjectParameter)):
                tex=n.get_editor_property('texture');nr['texture']=path(tex)
                nr['sampler_type']=str(n.get_editor_property('sampler_type'))
                if tex:nr['size']=[tex.blueprint_get_size_x(),tex.blueprint_get_size_y()]
            row['nodes'].append(nr)
    report['materials'].append(row)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report['game_world']=path(world)
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        for comp in actor.get_components_by_class(u.StaticMeshComponent):
            mesh=comp.static_mesh
            if mesh and 'XuanChi' in mesh.get_path_name():
                report['runtime'].append({'component':path(comp),'mesh':path(mesh),
                    'materials':[path(comp.get_material(i)) for i in range(comp.get_num_materials())],
                    'override_materials':[path(x) for x in comp.get_editor_property('override_materials')],
                    'tags':[str(x) for x in comp.component_tags]})
(P/'diagnosis_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'meshes':report['meshes'],'runtime':report['runtime'],
    'materials':[{'path':x['path'],'used_textures':x.get('used_textures'),'statistics':x.get('statistics')} for x in report['materials']]},ensure_ascii=False))
