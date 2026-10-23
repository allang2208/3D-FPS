"""Read the two expedition fabric graphs implicated by the SM6 error log."""
import json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BackpackMotion20261022/FabricRepair';R.mkdir(exist_ok=True)
paths=['/Game/Characters/ExpeditionBackpack20261022/M_ExpeditionHarness_Fabric',
       '/Game/Characters/BackpackMotion20261022/Materials/M_Motion_M_ExpeditionHarness_Fabric_b63f8c']
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
rows=[]
for path in paths:
    mat=u.load_asset(path)
    if not mat:raise RuntimeError('Missing fabric material '+path)
    nodes=[]
    for n in u.MaterialEditingLibrary.get_material_expressions(mat):
        record={'class':n.get_class().get_name(),'name':n.get_name(),'inputs':[str(x) for x in u.MaterialEditingLibrary.get_material_expression_input_names(n)]}
        if isinstance(n,u.MaterialExpressionTextureSample):
            texture=n.get_editor_property('texture');record['texture']=texture.get_path_name() if texture else None
        if isinstance(n,u.MaterialExpressionDesaturation):
            record['connected_nodes']=[x.get_name() if x else None for x in u.MaterialEditingLibrary.get_inputs_for_material_expression(mat,n)]
        nodes.append(record)
    rows.append({'material':path,'dirty_before':path in dirty,'nodes':nodes})
(R/'graphs_before.json').write_text(json.dumps(rows,indent=2))
print('FABRIC_GRAPH_INPUTS',json.dumps([{'material':r['material'],'dirty':r['dirty_before'],'desaturation':[n for n in r['nodes'] if n['class']=='MaterialExpressionDesaturation']} for r in rows]),flush=True)
