"""SVD-private WS1 adapters retaining original UV/normal/AO/material-identity graphs.
No original graph or shared master is edited. Unreferenced legacy finish nodes are
excluded by shader compilation after their outputs have been bypassed.
"""
import json,hashlib,sys
from pathlib import Path
import unreal as u
HERE=Path(__file__).parent
sys.path.insert(0,str(HERE))
import ws_graph as W
L,E=u.MaterialEditingLibrary,u.EditorAssetLibrary
ROOT='/Game/Weapons/SVDDragunov20260922/SurfaceStandard20261001'
PLAN=json.loads((HERE/'slot_plan.json').read_text())
RP=HERE/'master_receipt.json'
receipt=json.loads(RP.read_text()) if RP.exists() else {'masters':{},'complete':False,'tested':False}

def record():RP.write_text(json.dumps(receipt,indent=1))
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing source '+path)
 return a

def const(m,v):
 if isinstance(v,tuple):return W.node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*v,1))
 return W.node(m,u.MaterialExpressionConstant,r=float(v))

def old_output(m,prop,default):
 p=getattr(u.MaterialProperty,'MP_'+prop);n=L.get_material_property_input_node(m,p)
 return (n,L.get_material_property_input_node_output_name(m,p)) if n else const(m,default)

def source_input(m,n,pin):
 names=[str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')]
 v=L.get_inputs_for_material_expression(m,n)[names.index(pin)]
 if not v:raise RuntimeError('Missing original '+pin+' '+n.get_name())
 out=L.get_input_node_output_name_for_material_expression(n,v)
 if out is None:raise RuntimeError('Missing input output name '+pin)
 return (v,str(out))

def custom(m,code,inputs,size,label):
 W.CODE[label]=code
 return W.custom(m,label,inputs,size)

sources={}
for key,row in PLAN.items():
 for spec in row['slots'].values():
  if spec['action']!='preset':continue
  b=spec['source_base'];sources[b]=sources.get(b,False) or key=='SVD'
for path,skeletal in sources.items():
 name='M_SVD_WS_'+path.split('/')[-1].split('.')[0].removesuffix('_Base')+'_'+hashlib.sha1(path.encode()).hexdigest()[:6]
 target=ROOT+'/Master/'+name
 if path in receipt['masters']:
  if not E.does_asset_exist(target):raise RuntimeError('Recorded master missing '+target)
  continue
 if E.does_asset_exist(target):raise RuntimeError('Unrecorded private master exists; preserve partial graph '+target)
 m=E.duplicate_asset(path,target)
 if not m:raise RuntimeError('Cannot clone source '+path)
 original=list(L.get_material_expressions(m));two_sided=m.get_editor_property('two_sided')
 cs={str(n.get_editor_property('description')):n for n in original if isinstance(n,u.MaterialExpressionCustom)}
 color=next(n for desc,n in cs.items() if 'matte' in desc.lower() and desc.endswith('BASE_COLOR'))
 rough=next(n for desc,n in cs.items() if 'matte' in desc.lower() and desc.endswith('ROUGHNESS'))
 metal=cs['SVD refined metal coating']
 rawcolor=source_input(m,color,'Base');rawrough=source_input(m,rough,'Base')
 rawmetal=source_input(m,metal,'Base');region=source_input(m,rough,'Region')
 normal=old_output(m,'NORMAL',(0,0,1));ao=old_output(m,'AMBIENT_OCCLUSION',1.);specular=old_output(m,'SPECULAR',.5)
 weather=cs.get('PSOMatte weather region',cs.get('SVDMatte WeatherRegion'))
 if weather is None:weather=const(m,1.)
 # The captured sources are dry graphs. A separate wet source must never stack here.
 if any('wetness' in str(n.get_editor_property('parameter_name')).lower() for n in original if isinstance(n,u.MaterialExpressionScalarParameter)):
  raise RuntimeError('Unexpected wet source '+path)
 W.build(m)
 new=[n for n in L.get_material_expressions(m) if n not in original]
 params={};code={}
 for n in new:
  if isinstance(n,u.MaterialExpressionCustom):code[str(n.get_editor_property('description'))]=n
  if isinstance(n,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter,u.MaterialExpressionTextureSampleParameter2D,u.MaterialExpressionTextureObjectParameter)):
   key=str(n.get_editor_property('parameter_name'));params[key]=n
   if key!='WeaponWetness':n.set_editor_property('parameter_name','WS_'+key)
 # Base normal, tiling, AO, vertex masks and material-instance atlas choices survive exactly.
 W.wire(rawcolor,code['WS_ColorRough'],'Src');W.wire(rawrough,code['WS_ColorRough'],'SrcR')
 W.wire(normal,code['WS_WetNormal'],'Base');W.output(specular,'SPECULAR')
 keep=custom(m,'float marks=smoothstep(.32,.66,max(Base.r,max(Base.g,Base.b))); return saturate(Region)*(1-marks);',
  {'Base':rawcolor,'Region':region},1,'SVD WS1 exposed metal excluding markings')
 cr=custom(m,'return float4(lerp(Base,Finish.rgb,Region),lerp(Rough,Finish.a,Region));',
  {'Base':rawcolor,'Rough':rawrough,'Finish':code['WS_ColorRough'],'Region':keep},4,'SVD WS1 preserve polymer rubber cheekpad and PSO interior')
 W.wire(cr,code['WS_Wet'],'CR')
 met=custom(m,'return lerp(Base,Finish.r,Region);',{'Base':rawmetal,'Finish':code['WS_MetalAO'],'Region':keep},1,'SVD WS1 metal identity')
 W.output(met,'METALLIC')
 ambient=custom(m,'return min(saturate(Source),saturate(WS.g));',{'Source':ao,'WS':code['WS_MetalAO']},1,'SVD WS1 combine AO without multiplying twice')
 W.output(ambient,'AMBIENT_OCCLUSION')
 wet=custom(m,'return saturate(Wet)*saturate(Exterior);',{'Wet':params['WeaponWetness'],'Exterior':weather},1,'SVD WS1 exposed weather coverage')
 W.wire(wet,code['WS_Beads'],'Wet')
 m.set_editor_property('two_sided',two_sided)
 for prop,value in [('used_with_skeletal_mesh',skeletal),('used_with_morph_targets',False),('used_with_clothing',False),('automatically_set_usage_in_editor',False)]:m.set_editor_property(prop,value)
 E.set_metadata_tag(m,'WeaponSurfaceGraph','WS1-SVD-Source-g1')
 E.set_metadata_tag(m,'WeaponSurfaceSourceGraph',path)
 E.set_metadata_tag(m,'WeaponSurfaceVersion','WS1-SVD-20261001')
 errors=L.recompile_material(m)
 if errors:raise RuntimeError('SVD material compile failed '+target+' '+str(errors))
 if not E.save_loaded_asset(m,False):raise RuntimeError('Save failed '+target)
 receipt['masters'][path]={'path':target,'skeletal':skeletal,'source':path,'normal':'original complete graph','regions':'original metal + markings + PSO exterior'};record()
 print('SVD_WS_MASTER_SAVED',name,flush=True)
receipt['complete']=True;record()
print('SVD_WS_MASTERS_COMPLETE',len(receipt['masters']),flush=True)
