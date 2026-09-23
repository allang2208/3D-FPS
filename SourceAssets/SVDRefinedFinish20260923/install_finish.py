"""SVD-private A762-inspired satin finish; preserve structural and optical layers."""
import unreal as u,json,shutil,hashlib
from pathlib import Path
O=Path(__file__).parent;PROJECT=Path(u.Paths.project_dir()).resolve()
P='/Game/Weapons/SVDDragunov20260922';DEST=P+'/RefinedFinish20260923'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
data=json.loads((O/'inputs.json').read_text());receiptpath=O/'finish_receipt.json'
receipt=json.loads(receiptpath.read_text()) if receiptpath.exists() else {'materials':{},'meshes':{},'hardware':{},'game_tested':False}
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Active play session; preserve state')
targets={m['asset'] for m in data['meshes'].values()}|{P+'/Accessories20260923/DA_SVD_AttachmentWetMaterials'}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in targets or p.startswith(DEST+'/') for p in dirty):raise RuntimeError('Unsaved SVD target assets')

def record():receiptpath.write_text(json.dumps(receipt,indent=2))
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def backup(a):
 path=a.get_path_name().split('.')[0];f=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset');to=O/'Before'/f.relative_to(PROJECT/'Content')
 if f.exists() and not to.exists():to.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,to)
def clone(a,path):
 obj=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(a.get_path_name(),path)
 if not obj:raise RuntimeError('Cannot duplicate '+path)
 return obj
def node(m,cls,**props):
 n=L.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def link(value,n,pin):
 a,out=value if isinstance(value,tuple) else (value,'')
 if not L.connect_material_expressions(a,out,n,pin):raise RuntimeError('Connection failed '+pin)
def param(m,name,value):
 if isinstance(value,list):return node(m,u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*value,1))
 return node(m,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
def add_inputs(n,values):
 pins=list(n.get_editor_property('inputs'));names={str(i.get_editor_property('input_name')) for i in pins}
 for name in values:
  if name not in names:
   p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
 n.set_editor_property('inputs',pins)
 for name,value in values.items():link(value,n,name)
def custom(m,code,values,size,label):
 n=node(m,u.MaterialExpressionCustom,code=code,description=label,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
 add_inputs(n,values);return n
def compile_save(m,skeletal):
 m.set_editor_property('used_with_skeletal_mesh',skeletal)
 m.set_editor_property('used_with_morph_targets',False);m.set_editor_property('used_with_clothing',False)
 errors=L.recompile_material(m)
 if errors:raise RuntimeError('Material compile failed '+m.get_path_name()+str(errors))
 save(m)

texture=clone(u.load_asset(data['reference']['texture']),DEST+'/Textures/T_SVD_SatinFinish')
texture.set_editor_property('srgb',False);texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON);save(texture)
skeletal_materials={s['material'] for m in data['meshes'].values() if m['skeletal'] for s in m['slots']}
grain_code='''float3 w=pow(abs(normalize(N)),4.0); w/=max(w.x+w.y+w.z,.0001);
float3 q=P/5.0;
float g=dot(w,float3(Texture2DSample(FinishTex,FinishTexSampler,q.yz*float2(2.4,1)).r,
Texture2DSample(FinishTex,FinishTexSampler,q.xz*float2(2.4,1)).r,
Texture2DSample(FinishTex,FinishTexSampler,q.xy*float2(2.4,1)).r));
return float4(0,g,0,.5);'''
color_code='''float lum=dot(Base,float3(.2126,.7152,.0722));
float marks=smoothstep(.32,.66,max(Base.r,max(Base.g,Base.b)));
float shading=clamp(lum/.034,.72,1.30);
float3 coat=lerp(Base,Tint*shading,ColorWeight)*(1+(Detail.g-.5)*.025);
return lerp(Base,coat,saturate(Region)*(1-marks));'''
rough_code='''float structure=clamp((Base-.5)*.08,-.018,.018);
float satin=clamp(Center+structure+(Detail.g-.5)*.024,.24,.56);
return lerp(Base,satin,saturate(Region));'''

def adapt(original,path,role,skeletal):
 base=clone(original.get_base_material(),path+'_Base')
 if E.get_metadata_tag(base,'SVDRefinedFinish')!='20260923':
  customs=[n for n in L.get_material_expressions(base) if isinstance(n,u.MaterialExpressionCustom)]
  color=next(n for n in customs if 'matte' in str(n.get_editor_property('description')).lower() and str(n.get_editor_property('description')).endswith('BASE_COLOR'))
  rough=next(n for n in customs if 'matte' in str(n.get_editor_property('description')).lower() and str(n.get_editor_property('description')).endswith('ROUGHNESS'))
  micro=next(n for n in customs if 'physical micro finish' in str(n.get_editor_property('description')))
  center=.30 if 'BoltCarrier' in role else .33 if 'ChargingHandle' in role else .35 if any(k in role for k in ['Safety','Trigger','Mount','InterfaceSteel']) else .39 if 'Magazine' in role else .37
  tint=[.024,.030,.041]
  strength=0. if 'titanium' in role else .55
  tex=node(base,u.MaterialExpressionTextureObjectParameter,parameter_name='SVD_SatinFinishTexture',texture=texture)
  micro.set_editor_property('code',grain_code);add_inputs(micro,{'FinishTex':tex})
  color.set_editor_property('code',color_code)
  add_inputs(color,{'Tint':param(base,'SVD_RefinedColor',tint),'ColorWeight':param(base,'SVD_RefinedColorWeight',strength)})
  rough.set_editor_property('code',rough_code);add_inputs(rough,{'Center':param(base,'SVD_RefinedRoughness',center)})
  # Use the existing metal/optical region, before modifying its metallic output.
  pins=list(rough.get_editor_property('inputs'));index=next(i for i,p in enumerate(pins) if str(p.get_editor_property('input_name'))=='Region')
  region=L.get_inputs_for_material_expression(base,rough)[index]
  prop=u.MaterialProperty.MP_METALLIC;old=L.get_material_property_input_node(base,prop)
  oldvalue=(old,L.get_material_property_input_node_output_name(base,prop)) if old else param(base,'SourceMetallic',.83)
  met=custom(base,'return lerp(Base,Metallic,saturate(Region));',{'Base':oldvalue,'Region':region,'Metallic':param(base,'SVD_RefinedMetallic',data['reference']['metallic'])},1,'SVD refined metal coating')
  if not L.connect_material_property(met,'',prop):raise RuntimeError('Cannot connect metallic')
  E.set_metadata_tag(base,'SVDRefinedFinish','20260923')
  E.set_metadata_tag(base,'WeaponFinishReference',data['reference']['asset'])
  E.set_metadata_tag(base,'WeaponFinishRegions','SVD original metal, white markings, optical interior and polymer masks retained; structural normal/AO unchanged')
  compile_save(base,skeletal)
 if not isinstance(original,u.MaterialInstanceConstant):return base
 result=clone(original,path);L.set_material_instance_parent(result,base)
 for kind in ['scalar','vector','texture','static_switch']:
  for name in getattr(L,'get_'+kind+'_parameter_names')(original.get_base_material()):
   value=getattr(L,'get_material_instance_'+kind+'_parameter_value')(original,name)
   if value is not None:getattr(L,'set_material_instance_'+kind+'_parameter_value')(result,name,value)
 L.update_material_instance(result);save(result);return result

eligible={path:info for path,info in data['materials'].items() if any('matte' in n['description'].lower() and n['description'].endswith('ROUGHNESS') for n in info['custom'])}
for path,info in eligible.items():
 if path in receipt['materials']:continue
 role=u.load_asset(path).get_name();stem=role+'_'+hashlib.sha1(path.encode()).hexdigest()[:6]
 wetpath=data['wet_materials'].get(path)
 if not wetpath:raise RuntimeError('Missing SVD wet partner '+path)
 dry=adapt(u.load_asset(path),DEST+'/Materials/'+stem,role,path in skeletal_materials)
 wet=adapt(u.load_asset(wetpath),DEST+'/Materials/'+stem+'_Wet',role,path in skeletal_materials)
 receipt['materials'][path]={'dry':dry.get_path_name(),'wet':wet.get_path_name(),'saved':True};record()
 print('SVD_HAND_SATIN_MATERIAL_SAVED',role,flush=True)

# Small new machined fasteners use the same physical finish, with a brighter
# steel response. Their private instances cannot recolor another weapon.
steel=next(v for p,v in receipt['materials'].items() if 'M_M_SVD_InterfaceSteel_Matte.' in p)
for role,color,roughness,metal in [('Fastener',[.052,.059,.066],.29,.94),('Recess',[.012,.015,.020],.43,.83)]:
 for wet in [False,True]:
  key=role+('_Wet' if wet else '')
  if key in receipt['hardware']:continue
  parent=u.load_asset(steel['wet' if wet else 'dry']);path=DEST+'/Materials/MI_SVD_Adapter'+key
  mic=u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(path.rsplit('/',1)[1],path.rsplit('/',1)[0],u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
  L.set_material_instance_parent(mic,parent)
  L.set_material_instance_vector_parameter_value(mic,'SVD_RefinedColor',u.LinearColor(*color,1))
  for name,value in [('SVD_RefinedColorWeight',1.),('SVD_RefinedRoughness',roughness),('SVD_RefinedMetallic',metal)]:L.set_material_instance_scalar_parameter_value(mic,name,value)
  L.update_material_instance(mic);save(mic);receipt['hardware'][key]=mic.get_path_name();record()

table=u.load_asset(P+'/Accessories20260923/DA_SVD_AttachmentWetMaterials');backup(table);mapping=dict(table.get_editor_property('wet_materials'))
for v in receipt['materials'].values():mapping[v['dry']]=u.load_asset(v['wet'])
for k in ['Fastener','Recess']:mapping[receipt['hardware'][k]]=u.load_asset(receipt['hardware'][k+'_Wet'])
table.set_editor_property('wet_materials',mapping);save(table)
for key,row in data['meshes'].items():
 if key in receipt['meshes']:continue
 mesh=u.load_asset(row['asset']);prop='materials' if row['skeletal'] else 'static_materials';slots=mesh.get_editor_property(prop);changed=False
 for i,s in enumerate(slots):
  current=s.material_interface.get_path_name() if s.material_interface else None
  if current in receipt['materials']:
   if not changed:backup(mesh)
   s.material_interface=u.load_asset(receipt['materials'][current]['dry']);slots[i]=s;changed=True
 if changed:mesh.set_editor_property(prop,slots);save(mesh)
 receipt['meshes'][key]={'asset':mesh.get_path_name(),'saved':changed,'slots':{str(s.material_slot_name):s.material_interface.get_path_name() if s.material_interface else None for s in mesh.get_editor_property(prop)}};record()
receipt['complete']=True;receipt['reference']=data['reference'];record()
print('SVD_HAND_SATIN_COMPLETE',len(receipt['materials']),len(receipt['meshes']),flush=True)
