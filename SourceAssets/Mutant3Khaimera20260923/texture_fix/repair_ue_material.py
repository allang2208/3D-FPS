"""Connect the existing Mutant3 texture graph to its Substrate surface output."""
import unreal as u,json,os,shutil
from pathlib import Path
ROOT=Path(__file__).parent
PROJECT=ROOT.parents[2]
ASSET='/Game/Monsters/Mutant3Meshy/Materials/M_Mutant3_Meshy'
REL='Monsters/Mutant3Meshy/Materials/M_Mutant3_Meshy.uasset'
HEADLESS=os.environ.get('MUTANT3_TEXTURE_INSPECT_HEADLESS')=='1'
if not HEADLESS:
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if ASSET in dirty:raise RuntimeError('Target material has unsaved edits; preserving them')
mat=u.load_asset(ASSET)
M=u.MaterialEditingLibrary
inputs=[]
for key,pin in [('MP_BASE_COLOR','BaseColor'),('MP_NORMAL','Normal'),('MP_ROUGHNESS','Roughness'),('MP_METALLIC','Metallic')]:
    prop=getattr(u.MaterialProperty,key)
    node=M.get_material_property_input_node(mat,prop)
    if not node:raise RuntimeError('Missing existing texture input: '+key)
    if not node.get_editor_property('texture'):raise RuntimeError('Missing texture: '+key)
    output=M.get_material_property_input_node_output_name(mat,prop)
    inputs.append((key,pin,node,output))
backup=ROOT/'before_content'/REL;backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():shutil.copy2(PROJECT/'Content'/REL,backup)
front=M.get_material_property_input_node(mat,u.MaterialProperty.MP_FRONT_MATERIAL)
if not front:
    front=M.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels,0,0)
    front.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
elif not isinstance(front,u.MaterialExpressionSubstrateShadingModels):
    raise RuntimeError('Unexpected custom surface output; preserving it')
for key,pin,node,output in inputs:
    if not M.connect_material_expressions(node,output,front,pin):raise RuntimeError('Cannot connect '+pin)
if not M.connect_material_property(front,'',u.MaterialProperty.MP_FRONT_MATERIAL):
    raise RuntimeError('Cannot connect front material')
mat.set_editor_property('used_with_skeletal_mesh',True)
M.layout_material_expressions(mat)
errors=M.recompile_material(mat)
if errors:raise RuntimeError('Material compilation reported: '+str(errors))
if not u.EditorAssetLibrary.save_loaded_asset(mat,False):raise RuntimeError('Material save failed')
report={'state':'saved in authoring project; installation pending' if HEADLESS else 'installed',
        'asset':ASSET,'front_material':front.get_class().get_name(),
        'preserved_inputs':{k:{'texture':n.get_editor_property('texture').get_path_name(),'output':o} for k,p,n,o in inputs},
        'mesh_and_animation_modified':False,'game_started':False}
(ROOT/'material_repair_state.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('MUTANT3_MATERIAL_SURFACE_SAVED '+ASSET)
