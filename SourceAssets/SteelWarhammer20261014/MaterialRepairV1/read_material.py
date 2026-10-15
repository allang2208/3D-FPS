"""Read only the active warhammer material bindings and surface inputs."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
R=P.parents[2]
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
L=u.MaterialEditingLibrary
D='/Game/Weapons/SteelWarhammer20261014'
def path(obj):return obj.get_path_name() if obj else None
report={'meshes':[]}
for name in ('SM_SteelWarhammer','SK_SteelWarhammer_BareArmsV7','SprintDragV1/SK_Warhammer_BareArmsSprintV1'):
    mesh=u.load_asset(D+'/'+name)
    if not mesh:raise RuntimeError('Missing mesh '+name)
    slots=mesh.get_editor_property('static_materials' if isinstance(mesh,u.StaticMesh) else 'materials')
    report['meshes'].append({'mesh':path(mesh),'slots':[{'name':str(s.material_slot_name),'material':path(s.material_interface)} for s in slots]})
mat=u.load_asset(D+'/Materials/M_SteelWarhammerSurface')
if not mat:raise RuntimeError('Missing warhammer surface')
report['material']=path(mat)
report['skeletal_usage']=mat.get_editor_property('used_with_skeletal_mesh')
report['inputs']={name:path(L.get_material_property_input_node(mat,getattr(u.MaterialProperty,'MP_'+name))) for name in ('BASE_COLOR','NORMAL','ROUGHNESS','METALLIC','FRONT_MATERIAL')}
report['expressions']=[]
for node in L.get_material_expressions(mat):
    row={'name':path(node),'class':node.get_class().get_name()}
    if isinstance(node,u.MaterialExpressionTextureSample):
        tex=node.get_editor_property('texture')
        row.update(texture=path(tex),sampler=str(node.get_editor_property('sampler_type')))
        if tex:row.update(srgb=tex.get_editor_property('srgb'),compression=str(tex.get_editor_property('compression_settings')))
    report['expressions'].append(row)
after='-warhammermaterialreadback' in u.SystemLibrary.get_command_line().lower()
(P/('material_after.json' if after else 'material_before.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
if after:
    active=report['meshes'][-1]
    if any(s['material'] is None for s in active['slots']):raise RuntimeError('Active viewmodel has an empty material slot')
    if not report['inputs']['FRONT_MATERIAL']:raise RuntimeError('Substrate output did not persist')
print('WARHAMMER_MATERIAL_'+('AFTER ' if after else 'BEFORE ')+json.dumps(report))
