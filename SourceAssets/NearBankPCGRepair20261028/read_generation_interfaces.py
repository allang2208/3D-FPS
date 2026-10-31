from pathlib import Path
import unreal as u,json
R=Path(__file__).resolve().parent
names=['Compose/Compose_Areas_Exclusion','Compose/Compose_Areas_Union','Transform/Transform_Areas_Contract','Filter/Filter_Areas_BySize','Filter/Filter_RandomChoice','Subdivide/Subdivide_Areas_WithRecursiveSplit','Create/Create_Mesh_Planar','Fill/Fill_Areas_WithFittingAssets_with_Corrective','Fill/Fill_Areas_Randomly','Transform/Transform_Offset','Assign/Assign_Assets','Spawn/Spawn_Assets']
out=[]
for name in names:
    path='/PCGPrimitives/Primitives/'+name;g=u.load_asset(path)
    if not g:continue
    out.append(dict(path=path,parameters=json.loads(u.NearBankPCGAuthoringTools.describe_parameters(g)),inputs=[str(p.properties.label) for p in g.get_input_node().output_pins],outputs=[str(p.properties.label) for p in g.get_output_node().input_pins]))
assets=[]
for name in ['Road_City/SGD_Road_City','Sidewalk_A/SGD_Sidewalk_A','Sidewalk_A/SGD_Sidewalk_A_noParking','Sidewalk_A/SGD_Sidewalk_Corners','Road_City/SGD_Road_City_HighRes']:
    p='/CitySamplePCG/PCG/DataAssets/Roads/'+name;a=u.load_asset(p)
    if not a:continue
    schema=json.loads(u.ToolsetLibrary.list_struct_properties(a.get_class(),False))
    keys=list(schema.get('properties',schema))
    assets.append(dict(path=p,schema=schema,properties=u.ToolsetLibrary.get_object_properties(a,keys)))
(R/'generation_interfaces.json').write_text(json.dumps({'graphs':out,'assets':assets},indent=2),encoding='utf8')
print('GENERATION_INTERFACES_SAVED',len(out),len(assets),flush=True)
