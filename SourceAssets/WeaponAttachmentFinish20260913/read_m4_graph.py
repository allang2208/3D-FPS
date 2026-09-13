import unreal as u,json
from pathlib import Path
L=u.MaterialEditingLibrary;m=u.load_asset('/Game/Weapons/M4InfimaV3/Body_001').get_base_material()
r={}
for n in L.get_material_expressions(m):
 inputs=L.get_inputs_for_material_expression(m,n)
 r[n.get_name()]={'names':list(map(str,L.get_material_expression_input_names(n))),
                  'inputs':[x.get_name() if x else None for x in inputs]}
Path(__file__).with_name('m4_graph_links.json').write_text(json.dumps(r,indent=2))
