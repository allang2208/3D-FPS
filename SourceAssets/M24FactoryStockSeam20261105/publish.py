"""Continue the factory wrist surface onto its advanced-action transition.

Only the standard advanced-action mesh's coating slot is rebound. The separate
independent-grip chassis, stock meshes, arms, UVs and geometry are not edited.
"""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).resolve().parent
D=json.loads((O/'inputs.json').read_text())
ROOT='/Game/Weapons/M24/FactoryStockSeam20261105'
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
R={'complete':False,'saved':[],'runtime_tested':False,'geometry_changed':False,'animations_changed':False}
def record():(O/'saved.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
def disk(p):return Path(u.Paths.project_content_dir())/(p.split('.')[0][6:]+'.uasset')
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing '+p)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
 R['saved'].append(a.get_path_name());record()
def clone(source,path):
 if E.does_asset_exist(path):raise RuntimeError('Existing revision retained '+path)
 a=E.duplicate_asset(source,path)
 if not a:raise RuntimeError('Duplicate refused '+source)
 return a
def node(m,kind,**kw):
 n=L.create_material_expression(m,kind)
 for k,v in kw.items():n.set_editor_property(k,v)
 return n
def wire(a,b,pin,out=''):
 if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot wire '+pin)
def add_input(n,key,src):
 ins=list(n.get_editor_property('inputs'))
 if any(str(x.get_editor_property('input_name'))==key for x in ins):raise RuntimeError('Already patched '+key)
 p=u.CustomInput();p.set_editor_property('input_name',key);ins.append(p);n.set_editor_property('inputs',ins);wire(src,n,key)
def replace(n,old,new):
 code=n.get_editor_property('code')
 if code.count(old)!=1:raise RuntimeError('Unexpected graph '+str(n.get_editor_property('description')))
 n.set_editor_property('code',code.replace(old,new))

row=D['meshes']['advanced'];src=row['slots'][0]['material'];master=D['materials'][src]['master']
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
 if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; preserve assets')
for p,h in [(row['path'],row['sha256']),(src,D['materials'][src]['sha256']),(master,D['masters'][master]['sha256'])]:
 if p.split('.')[0] in dirty:raise RuntimeError('Unsaved target retained '+p)
 if hashlib.sha256(disk(p).read_bytes()).hexdigest()!=h:raise RuntimeError('Concurrent change retained '+p)
backup=O/'Before'/disk(row['path']).name;backup.parent.mkdir(exist_ok=True)
if backup.exists():
 if hashlib.sha256(backup.read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Different prior backup retained')
else:shutil.copy2(disk(row['path']),backup)

# Use the exact imported glTF colour/ORM sampled at the retained factory cut.
samples=[x for x in json.loads((O/'source_seam.json').read_text())['neck_samples'] if x['center'][1]>=.012]
area=sum(x['area'] for x in samples)
colour=[sum(x['area']*x['color'][i] for x in samples)/area for i in range(3)]
rough=sum(x['area']*x['roughness'] for x in samples)/area
host_path=D['meshes']['body']['slots'][6]['material'];host=D['materials'][host_path]['parameters']
weight=host['scalar']['SourceColorWeight'];poly=host['vector']['PolymerColor']
finish=[poly[i]*(1-weight)+colour[i]*weight for i in range(3)]
roughness=.59+(rough-host['scalar']['SourceRoughnessPivot'])*host['scalar']['SourceRoughnessWeight']
m=clone(master,ROOT+'/M_M24_FactoryStockTransition')
cs={str(n.get_editor_property('description')):n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)}
p=node(m,u.MaterialExpressionPreSkinnedPosition)
interp=node(m,u.MaterialExpressionVertexInterpolator);wire(p,interp,'VS')
mask=node(m,u.MaterialExpressionCustom,description='M24 actual factory wrist transition',
 code='float longitudinal=1-smoothstep(3.10,6.00,-P.y);float width=1-smoothstep(2.39,2.53,abs(P.x));float height=smoothstep(4.20,4.40,P.z)*(1-smoothstep(10.40,10.70,P.z));return longitudinal*width*height;',
 output_type=u.CustomMaterialOutputType.CMOT_FLOAT1)
pin=u.CustomInput();pin.set_editor_property('input_name','P');mask.set_editor_property('inputs',[pin]);wire(interp,mask,'P')
col=node(m,u.MaterialExpressionVectorParameter,parameter_name='FactoryWristColor',default_value=u.LinearColor(*finish,1))
rgh=node(m,u.MaterialExpressionScalarParameter,parameter_name='FactoryWristRoughness',default_value=roughness)
normal=node(m,u.MaterialExpressionScalarParameter,parameter_name='FactoryWristNormalStrength',default_value=host['scalar']['ContinuityNormalStrength'])
for name in ('WS_ColorRough','WS_MetalAO','WS_Wet','WS_WetNormal'):add_input(cs[name],'FactoryWrist',mask)
add_input(cs['WS_ColorRough'],'FactoryColor',col);add_input(cs['WS_ColorRough'],'FactoryRough',rgh)
add_input(cs['WS_WetNormal'],'FactoryNormalStrength',normal)
replace(cs['WS_ColorRough'],'float3 base=lerp(Finish,Src,saturate(SrcW));','float3 base=lerp(lerp(Finish,Src,saturate(SrcW)),FactoryColor.rgb,FactoryWrist);')
replace(cs['WS_ColorRough'],'float r=Rough+(SrcR-Pivot)*SrcRW;','float r=lerp(Rough+(SrcR-Pivot)*SrcRW,FactoryRough,FactoryWrist);')
replace(cs['WS_MetalAO'],'return float4(metal,ao,0,0);','return float4(metal*(1-FactoryWrist),ao,0,0);')
# Dry and wet material identity must agree; retain the automatic response that
# the original factory stock uses instead of forcing the old metal profile.
replace(cs['WS_Wet'],'float wet=saturate(Data.a),metal=saturate(Metal);','float wet=saturate(Data.a),metal=saturate(Metal)*(1-FactoryWrist);')
replace(cs['WS_Wet'],'float film=min(CR.a,max(floorRough,CR.a*filmScale));',
 'float factoryPorous=saturate((CR.a-.45)/.35);filmScale=lerp(filmScale,lerp(.80,.88,factoryPorous),FactoryWrist);floorRough=lerp(floorRough,lerp(.12,.20,factoryPorous),FactoryWrist);darken=lerp(darken,lerp(.075,.09,factoryPorous),FactoryWrist);\nfloat film=min(CR.a,max(floorRough,CR.a*filmScale));')
replace(cs['WS_WetNormal'],'if(Data.a<.0001)return Base;',
 'Base=normalize(float3(Base.xy*lerp(1.,FactoryNormalStrength,FactoryWrist),Base.z));\nif(Data.a<.0001)return Base;')
errs=L.recompile_material(m)
if errs:raise RuntimeError('Material compile failed '+str(errs))
E.set_metadata_tag(m,'M24FactoryStockSeam','Native cut measured 2.0163-3.0502 cm forward. Match nonmetal factory wrist; metal receiver retained beyond 6 cm. Source recipe: '+str(O/'publish.py'))
save(m)
mi=clone(src,ROOT+'/MI_M24_FactoryStockTransition');L.set_material_instance_parent(mi,m)
L.set_material_instance_vector_parameter_value(mi,'FactoryWristColor',u.LinearColor(*finish,1))
L.set_material_instance_scalar_parameter_value(mi,'FactoryWristRoughness',roughness)
L.set_material_instance_scalar_parameter_value(mi,'FactoryWristNormalStrength',host['scalar']['ContinuityNormalStrength'])
L.update_material_instance(mi);save(mi)
mesh=load(row['path'])
if str(mesh.static_materials[0].material_slot_name)!='M24_AAS_CoatedMetal':raise RuntimeError('Coating slot changed')
mesh.set_material(0,mi);save(mesh)
R.update(complete=True,mesh=mesh.get_path_name(),slot=str(mesh.static_materials[0].material_slot_name),
 material=mesh.get_material(0).get_path_name(),source_material=src,
 recipe={'factory_wrist_linear_colour':finish,'factory_wrist_roughness':roughness,'factory_wrist_metallic':0,
         'receiver_metallic':1,'transition_forward_cm':[3.10,6.00],'factory_cut_forward_cm':[2.0163,3.0502],
         'wet_response':'matches original automatic dielectric response'},
 source_hashes={row['path']:row['sha256'],src:D['materials'][src]['sha256']})
record();print('M24_FACTORY_STOCK_SEAM_SAVED',len(R['saved']),flush=True)
