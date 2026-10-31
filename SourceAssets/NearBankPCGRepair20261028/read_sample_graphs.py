"""Read actual Epic graph interfaces and rules; do not run or modify the demo."""
from pathlib import Path
import unreal as u,json
R=Path(__file__).resolve().parent
T=u.get_default_object(u.PCGToolset)
paths=['/CitySamplePCG/Levels/PCG/'+n for n in ('PCG_3_1_1_Districts','PCG_3_1_2_Roads','PCG_3_1_4_Lots','PCG_3_3_1_Buildings')]
paths += ['/CitySamplePCG/PCG/Primitives/Buildings/Assign_CitySampleBuildings','/CitySamplePCG/PCG/Primitives/Buildings/Subgraphs/LoadCitySampleData','/CitySamplePCG/PCG/Intersection_solving','/CitySamplePCG/PCG/Crosswalks','/CitySamplePCG/Examples/City/City_Circular_1km_2_arteries']
paths += ['/PCGPrimitives/Primitives/'+p for p in ('Assign/Assign_ShapeGrammarDefinition','Get/Get_ActorData','Spawn/Spawn_Assets','Place/Place_OnSpline','Create/Create_Spline_line','Compose/Compose_Areas_Exclusion','Subdivide/Subdivide_Areas_withGrid')]
out=[]
def fields(obj,keys):return {k:str(obj.get_editor_property(k)) for k in keys}
for path in paths:
    g=u.load_asset(path)
    if not g:out.append({'path':path,'missing':True});continue
    schema=T.call_method('GetGraphSchema',(g,))
    row={'path':path,'schema_text':schema.export_text(),'nodes':[]}
    row['parameter_values']=u.ToolsetLibrary.get_object_properties(g,['UserParameters'])
    if hasattr(u,'NearBankPCGAuthoringTools'):row['parameters']=json.loads(u.NearBankPCGAuthoringTools.describe_parameters(g))
    out.append(row)
    (R/'sample_graph_interfaces.json').write_text(json.dumps(out,indent=2),encoding='utf8')
    for n in g.get_editor_property('nodes'):
        s=n.get_settings();d={'name':n.get_name(),'settings_class':s.get_class().get_name(),'inputs':[str(p.properties.label) for p in n.input_pins],'outputs':[str(p.properties.label) for p in n.output_pins]}
        if isinstance(s,u.PCGSubgraphSettings):
            inst=s.subgraph_instance;sg=inst.graph if inst else None
            if sg:
                d['subgraph']=sg.get_path_name()
                d['parameter_overrides']=u.ToolsetLibrary.get_object_properties(inst,['ParametersOverrides'])
                if hasattr(u,'NearBankPCGAuthoringTools'):d['parameters']=json.loads(u.NearBankPCGAuthoringTools.describe_parameters(inst))
        d['title']=str(n.get_editor_property('node_title'))
        row['nodes'].append(d)
    (R/'sample_graph_interfaces.json').write_text(json.dumps(out,indent=2),encoding='utf8')
    print('SAMPLE_GRAPH_READ',path,len(row['nodes']),flush=True)
print('SAMPLE_GRAPH_INTERFACES_SAVED',len(out),flush=True)
