"""PSO-only matte upgrade, respecting host coatings and existing optical regions."""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;S=O.parent;DEST='/Game/Weapons/PSO1Russian20260923/MatteFinish20260923'
P=Path(u.Paths.project_dir()).resolve();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
sources=json.loads((S/'PSOSeamRepair20260923/import_receipt.json').read_text())
tables={'SVD':'/Game/Weapons/SVDDragunov20260922/Accessories20260923/DA_SVD_AttachmentWetMaterials',
 'Russian':'/Game/Weapons/PSO1Russian20260923/DA_PSO1_WetMaterials'}
report={'materials':{},'meshes':{},'tables':{},'tests_run':False};receipt=O/'import_receipt.json'
if receipt.exists():report=json.loads(receipt.read_text())
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Active PIE; preserve loaded assets')
targets={row['asset'] for row in sources['meshes']}|set(tables.values())
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in targets or p.startswith(DEST+'/') for p in dirty):raise RuntimeError('Unsaved PSO target packages')

def record():receipt.write_text(json.dumps(report,indent=2))
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def backup(a):
 f=P/'Content'/(a.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset');dest=O/'Before'/f.relative_to(P/'Content')
 if f.exists() and not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
def node(m,cls,**props):
 n=L.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def link(value,target,pin):
 n,out=value if isinstance(value,tuple) else (value,'')
 if not L.connect_material_expressions(n,out,target,pin):raise RuntimeError('Connection failed '+pin)
def output(value,key):
 n,out=value if isinstance(value,tuple) else (value,'')
 if not L.connect_material_property(n,out,getattr(u.MaterialProperty,'MP_'+key)):raise RuntimeError('Output failed '+key)
def constant(m,value):
 return node(m,u.MaterialExpressionConstant,r=value)
def previous(m,key,default):
 prop=getattr(u.MaterialProperty,'MP_'+key);n=L.get_material_property_input_node(m,prop)
 if n:return (n,L.get_material_property_input_node_output_name(m,prop))
 return node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*default,1)) if isinstance(default,tuple) else constant(m,default)
def custom(m,code,values,size,label):
 n=node(m,u.MaterialExpressionCustom,code=code,description=label,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
 inputs=[]
 for name in values:
  p=u.CustomInput();p.set_editor_property('input_name',name);inputs.append(p)
 n.set_editor_property('inputs',inputs)
 for name,value in values.items():link(value,n,name)
 return n
def clone(original,path):
 a=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(original.get_path_name(),path)
 if not a:raise RuntimeError('Cannot copy '+path)
 return a
def material_finish(m,host):
 if host=='SVD':L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
 errors=L.recompile_material(m)
 if errors:raise RuntimeError('Material compilation failed '+str(errors))
 E.set_metadata_tag(m,'PSOMatteFinish','20260923');save(m)
def instance(original,base,path):
 if not isinstance(original,u.MaterialInstanceConstant):return base
 a=clone(original,path);L.set_material_instance_parent(a,base)
 for kind in ['scalar','vector','texture','static_switch']:
  for name in getattr(L,'get_'+kind+'_parameter_names')(original.get_base_material()):
   value=getattr(L,'get_material_instance_'+kind+'_parameter_value')(original,name)
   if value is not None:getattr(L,'set_material_instance_'+kind+'_parameter_value')(a,name,value)
 L.update_material_instance(a);save(a);return a
def vertex(m,cls):
 n=node(m,u.MaterialExpressionVertexInterpolator);link(node(m,cls),n,'VS');return n

maskpath=DEST+'/Textures/T_PSO_ExteriorMask'
if not report.get('mask'):
 task=u.AssetImportTask();task.filename=str(O/'Textures/T_PSO_ExteriorMask.png');task.destination_path=DEST+'/Textures';task.destination_name='T_PSO_ExteriorMask'
 task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
 if not task.imported_object_paths:raise RuntimeError('Exterior mask import failed')
 mask=u.load_asset(maskpath);mask.set_editor_property('srgb',False);mask.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
 mask.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON);mask.set_editor_property('max_texture_size',4096);save(mask)
 report['mask']={'asset':mask.get_path_name(),'saved':True};record()
else:mask=u.load_asset(maskpath)
micro=(O/'MicroFinish.hlsl').read_text();rough=(O/'MatteRoughness.hlsl').read_text();color=(O/'PSOColor.hlsl').read_text()
beads=(S/'WeatherNatural20260912/WeaponBeads.hlsl').read_text().replace('return float4(slope,beads,saturate(Wet));','float coverage=saturate(Wet*20.0); return float4(slope*coverage,beads*coverage,saturate(Wet));')
newmaps={k:{} for k in tables}

for row in sources['meshes']:
 host='SVD' if 'SK_SVD_Modular' in row['asset'] else row['asset'].rsplit('_',1)[1]
 mesh=u.load_asset(row['asset']);skeletal=host=='SVD';prop='materials' if skeletal else 'static_materials'
 selected={k:v['material'] for k,v in row['slots'].items() if 'ScopeBody' in k or 'ScopeMount' in k} if skeletal else {k:v['material'] for k,v in row['slots'].items() if 'Shell' in k or 'Adapter' in k}
 bindings={str(s.material_slot_name):s.material_interface for s in mesh.get_editor_property(prop)};replacements={}
 for slot,path in selected.items():
  role='Mount' if 'ScopeMount' in slot or 'Adapter' in slot else 'Body';key=host+'_'+role
  if key in report['materials']:
   info=report['materials'][key];replacements[slot]=u.load_asset(info['dry']);newmaps['SVD' if skeletal else 'Russian'][info['dry']]=u.load_asset(info['wet']);continue
  original=bindings[slot]
  if original.get_path_name()!=path:raise RuntimeError('PSO binding changed before authoring '+slot)
  base=original.get_base_material()
  if base.blend_mode!=u.BlendMode.BLEND_OPAQUE:raise RuntimeError('PSO metal expected opaque')
  drybase=clone(base,DEST+'/Materials/M_PSO_'+key+'_Matte')
  # The current SVD already has a matte layer. Edit that layer in the private
  # copy rather than wrapping its result in another matte layer.
  if E.get_metadata_tag(drybase,'PSOMatteFinish')!='20260923':
   strength=node(drybase,u.MaterialExpressionScalarParameter,parameter_name='PSO_MicroScratchStrength',default_value=.24)
   exterior=constant(drybase,1.)
   if role=='Body' or skeletal:
    sample=node(drybase,u.MaterialExpressionTextureSample,texture=mask,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    exterior=(sample,'R')
   region=custom(drybase,'return saturate(Exterior)*smoothstep(.25,.72,Metal);',{'Exterior':exterior,'Metal':previous(drybase,'METALLIC',0.)},1,'PSO exterior metal only')
   tone='float3(.036,.043,.049)' if role=='Body' else 'float3(.030,.037,.044)'
   code=color.replace('__TINT__',tone if skeletal else 'Base').replace('__TINT_WEIGHT__','.45' if skeletal else '0.0')
   old={str(n.get_editor_property('description')):n for n in L.get_material_expressions(drybase) if isinstance(n,u.MaterialExpressionCustom)}
   if skeletal:
    for label,codevalue in [('SVDMatte BASE_COLOR',code),('SVDMatte ROUGHNESS',rough)]:
     n=old.get(label)
     if not n:raise RuntimeError('Current SVD matte layer missing '+label)
     n.set_editor_property('code',codevalue);link(region,n,'Region');link(strength,n,'Strength')
     n.set_editor_property('description',label.replace('SVDMatte','PSOMatte'))
   else:
    detail=custom(drybase,micro,{'P':vertex(drybase,u.MaterialExpressionPreSkinnedPosition),'N':vertex(drybase,u.MaterialExpressionPreSkinnedNormal)},4,'PSOMatte physical micro finish')
    for keyprop,program,size,default in [('BASE_COLOR',code,3,(.03,.035,.04)),('ROUGHNESS',rough,1,.4)]:
     value=previous(drybase,keyprop,default)
     output(custom(drybase,program,{'Base':value,'Detail':detail,'Strength':strength,'Region':region},size,'PSOMatte '+keyprop),keyprop)
   custom(drybase,'return Exterior;',{'Exterior':exterior},1,'PSOMatte weather region')
   E.set_metadata_tag(drybase,'PSOHost',host);E.set_metadata_tag(drybase,'PSOFinishSource',original.get_path_name())
   material_finish(drybase,host)
  dry=instance(original,drybase,DEST+'/Materials/MI_PSO_'+key+'_Matte')
  wetbase=clone(drybase,DEST+'/Materials/M_PSO_'+key+'_Matte_Wet')
  if E.get_metadata_tag(wetbase,'PSOMatteWet')!='20260923':
   vals={p:previous(wetbase,p,v) for p,v in [('BASE_COLOR',(.03,.035,.04)),('ROUGHNESS',.6),('NORMAL',(0,0,1))]}
   exterior=next(n for n in L.get_material_expressions(wetbase) if isinstance(n,u.MaterialExpressionCustom) and n.get_editor_property('description')=='PSOMatte weather region')
   wet=node(wetbase,u.MaterialExpressionScalarParameter,parameter_name='WeaponWetness',default_value=0.)
   wet=custom(wetbase,'return saturate(Wet)*Exterior;',{'Wet':wet,'Exterior':exterior},1,'PSOMatte exposed water coverage')
   data=custom(wetbase,beads,{'UV':node(wetbase,u.MaterialExpressionTextureCoordinate),'Wet':wet},4,'PSOMatte water beads')
   output(custom(wetbase,'return Base*(1-Data.a*.065);',{'Base':vals['BASE_COLOR'],'Data':data},3,'PSOMatte water film'),'BASE_COLOR')
   output(custom(wetbase,'return lerp(lerp(Base,max(.12,Base*.76),Data.a),.085,Data.b*.72);',{'Base':vals['ROUGHNESS'],'Data':data},1,'PSOMatte wet roughness'),'ROUGHNESS')
   output(custom(wetbase,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.12)+Data.xy*.55,Base.z));',{'Base':vals['NORMAL'],'Data':data},3,'PSOMatte wet normal'),'NORMAL')
   E.set_metadata_tag(wetbase,'PSOMatteWet','20260923');material_finish(wetbase,host)
  wet=instance(dry,wetbase,DEST+'/Materials/MI_PSO_'+key+'_Matte_Wet')
  info={'source':original.get_path_name(),'dry':dry.get_path_name(),'wet':wet.get_path_name(),'slot':slot,'saved':True,'structural_normal_preserved':True}
  report['materials'][host+'_'+role]=info;record();replacements[slot]=dry
  newmaps['SVD' if skeletal else 'Russian'][dry.get_path_name()]=wet
  print('PSO_MATTE_PAIR_SAVED',host,role,flush=True)
 backup(mesh);slots=mesh.get_editor_property(prop)
 for i,s in enumerate(slots):
  if str(s.material_slot_name) in replacements:s.material_interface=replacements[str(s.material_slot_name)];slots[i]=s
 mesh.set_editor_property(prop,slots);save(mesh)
 report['meshes'][host]={'asset':mesh.get_path_name(),'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.get_editor_property(prop)},'saved':True,'geometry_reimported':False};record()

for name,path in tables.items():
 table=u.load_asset(path);backup(table);mapping=dict(table.get_editor_property('wet_materials'));mapping.update(newmaps[name]);table.set_editor_property('wet_materials',mapping);save(table)
 report['tables'][name]={'asset':path,'new_pairs':{k:v.get_path_name() for k,v in newmaps[name].items()},'saved':True};record()
report['completed']=True;record();print('PSO_MATTE_UPGRADE_SAVED',len(report['materials']),len(report['meshes']),flush=True)
