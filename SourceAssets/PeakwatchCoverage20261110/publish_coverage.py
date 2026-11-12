"""Replace only the Peakwatch coverage branch in the existing lens material."""
from pathlib import Path
from datetime import datetime
import hashlib, json, shutil
import unreal as u

P=Path('D:/FPS3D/FPSGAME/SourceAssets/PeakwatchCoverage20261110')
ROOT=P.parents[1]
PKG='/Game/Weapons/SharedPhysicalOptics20261030/M_PhysicalScopeLens'
if Path(u.Paths.project_dir()).resolve()!=ROOT.resolve():
    raise RuntimeError('Wrong project')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world() is not None:
    raise RuntimeError('Preserving active PIE')
if any(p.get_path_name()==PKG for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserving unsaved shared lens changes')

E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
m=u.load_asset(PKG)
if not isinstance(m,u.Material):raise RuntimeError('Shared lens material missing')
todo=[L.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY)]
nodes={}
while todo:
    node=todo.pop()
    if not node or node.get_path_name() in nodes:continue
    nodes[node.get_path_name()]=node
    todo.extend(L.get_inputs_for_material_expression(m,node))
coverage=[n for n in nodes.values() if isinstance(n,u.MaterialExpressionCustom)
          and 'dot(Position' in n.get_editor_property('code')
          and 'Depth' in n.get_editor_property('code')]
if len(coverage)!=1:raise RuntimeError('Coverage node is ambiguous')
alpha=coverage[0]

# The existing ReticleStyle parameter already belongs to the scene/reticle
# branch. Reuse that exact node and leave the entire picture graph untouched.
todo=[L.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR)]
while todo:
    node=todo.pop()
    if not node or node.get_path_name() in nodes:continue
    nodes[node.get_path_name()]=node
    todo.extend(L.get_inputs_for_material_expression(m,node))
styles=[n for n in nodes.values() if isinstance(n,u.MaterialExpressionScalarParameter)
        and str(n.get_editor_property('parameter_name'))=='ReticleStyle']
if len(styles)!=1:raise RuntimeError('ReticleStyle parameter is ambiguous')

source=ROOT/'SourceAssets/SharedPhysicalOptics20261030/lens_coverage.hlsl'
code=source.read_text(encoding='utf-8')
before=P/'Before'/datetime.now().strftime('%Y%m%d-%H%M%S')
before.mkdir(parents=True,exist_ok=False)
asset=ROOT/'Content'/PKG.removeprefix('/Game/')
shutil.copy2(asset.with_suffix('.uasset'),before/'M_PhysicalScopeLens.uasset')
(before/'coverage.hlsl').write_text(alpha.get_editor_property('code'),encoding='utf-8')

inputs=list(alpha.get_editor_property('inputs'))
if not any(str(pin.get_editor_property('input_name'))=='ReticleStyle' for pin in inputs):
    pin=u.CustomInput();pin.set_editor_property('input_name','ReticleStyle');inputs.append(pin)
alpha.set_editor_property('inputs',inputs)
if not L.connect_material_expressions(styles[0],'',alpha,'ReticleStyle'):
    raise RuntimeError('Cannot connect ReticleStyle')
alpha.set_editor_property('code',code)
alpha.set_editor_property('desc','Peakwatch full native glass coverage; other optic masks preserved')
errors=L.recompile_material(m)
if errors:raise RuntimeError(str(errors))
stats=L.get_statistics(m)
if stats.num_pixel_shader_instructions<=0:raise RuntimeError('Lens shader compilation did not finish')
if not E.save_loaded_asset(m,False):raise RuntimeError('Lens material save failed')
receipt=dict(saved=m.get_path_name(),coverage_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    pixel_instructions=stats.num_pixel_shader_instructions,vertex_instructions=stats.num_vertex_shader_instructions,
    samplers=stats.num_samplers,backup=str(before),runtime_tested=False)
(P/'asset-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('PEAKWATCH_COVERAGE_COMPILED_AND_SAVED '+json.dumps(receipt),flush=True)
