"""Publish the workbench card and the per-guard, charge-driven V1 metal variants."""
import json
import runpy
from pathlib import Path
import unreal as u

here=Path(__file__).resolve().parent
project=here.parents[2]
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()!=project:
    raise RuntimeError('Unexpected output project')
receipt=json.loads((here/'Art/import_receipt.json').read_text(encoding='utf8'))
base=u.load_asset(receipt['ice_material']).get_editor_property('parent').get_path_name()
folder=base.split('/V1/')[0]+'/GuardCharge'
el,ml=u.EditorAssetLibrary,u.MaterialEditingLibrary
paths=[]
for temporal in (False,True):
    path=folder+'/M_EagleTalon_GuardCharge'+('_Whirlwind' if temporal else '')
    mat=u.load_asset(path) if el.does_asset_exist(path) else el.duplicate_asset(base.split('.')[0],path)
    if not mat:
        raise RuntimeError('Could not create '+path)
    if not el.get_metadata_tag(mat,'EagleGuardCharge'):
        emission=ml.get_material_property_input_node(mat,u.MaterialProperty.MP_EMISSIVE_COLOR)
        stack=[emission]
        while stack:
            node=stack.pop()
            if isinstance(node,u.MaterialExpressionScalarParameter) and str(node.get_editor_property('parameter_name'))=='IceStrength':
                node.set_editor_properties({'use_custom_primitive_data':True,'primitive_data_index':0})
                break
            stack.extend(ml.get_inputs_for_material_expression(mat,node))
        else:
            raise RuntimeError('Missing V1 ice mask strength input')
        if temporal:
            response=ml.create_material_expression(mat,u.MaterialExpressionTemporalResponsivenessOutput)
            one=ml.create_material_expression(mat,u.MaterialExpressionConstant)
            one.set_editor_property('r',1.)
            if not ml.connect_material_expressions(one,'',response,''):
                raise RuntimeError('Temporal output connection failed')
        if ml.recompile_material(mat):
            raise RuntimeError('Could not compile '+path)
        el.set_metadata_tag(mat,'EagleGuardCharge','1')
    if not el.save_loaded_asset(mat,False):
        raise RuntimeError('Could not save '+path)
    paths.append(mat.get_path_name())
surfaces=dict(next(iter(receipt['meshes'].values())))
surfaces['M_EagleTalon_ForgedSteel']=paths[0]
bind=runpy.run_path(str(here.parent/'CommonMods/guard_surface_defaults.py'))['bind_saved_guards']
bind([path for path in receipt['assets'] if path.rsplit('/',1)[-1].startswith('SM_')],surfaces)
key='guard_eagle_talon_guard'
icons=runpy.run_path(str(here.parent/'CommonMods/install_stock_icons.py'))['install_cards']({key:key})
(here/'Art/gameplay_assets.json').write_text(json.dumps({'materials':paths,'icons':icons},indent=2)+'\n',encoding='utf8')
