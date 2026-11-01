"""Save factory-derived seat revisions and complete the requested icon asset audit."""
import unreal as u,json,shutil,datetime,re,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2];D='/Game/Weapons/ThunderGodHammer20261028/SeatRefineV3';IC='/Game/ColdSteelData/AttachmentIcons20260913'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S');B=P/'Backups'/stamp;B.mkdir(parents=True)
A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt={'complete':False,'saved':[],'models':[],'icons':[],'runtime_tested':False,'backup':str(B)}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
 asset.modify()
 if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed '+str(asset))
 receipt['saved'].append(asset.get_path_name());record();return asset
def imp(path,name,folder,options=None):
 t=u.AssetImportTask();t.filename=str(path);t.destination_name=name;t.destination_path=folder;t.automated=True;t.save=False;t.replace_existing=False
 if options:t.options=options
 A.import_asset_tasks([t]);asset=u.load_asset(folder+'/'+name)
 if not asset:raise RuntimeError('Import failed '+name)
 return asset
record()
materials={
 'M_ThunderGodHammerSurface':u.load_asset('/Game/Weapons/ThunderGodHammer20261028/Materials/M_ThunderGodHammerSurface'),
 'M_CommonHammerHeadSteel':u.load_asset('/Game/Weapons/CommonHammerHeads20261014/Materials/M_CommonHammerHeadSteel'),
 'M_CommonHammerSeatDarkSteel':u.load_asset('/Game/Weapons/CommonHammerSeats20261014/BuildV1/Materials/M_CommonHammerSeatDarkSteel'),
 'M_CommonHammerSeatDamping':u.load_asset('/Game/Weapons/CommonHammerSeats20261014/BuildV1/Materials/M_CommonHammerSeatDamping')}
if any(not m for m in materials.values()):raise RuntimeError('Missing original/shared material')
for alias,suffix,tint_rgb,is_pad in [('M_CommonHammerHeadSteel','Steel',(1,1,1),False),('M_CommonHammerSeatDarkSteel','Dark',(.38,.38,.38),False),('M_CommonHammerSeatDamping','Damping',(.025,.025,.025),True),('M_ThorSeatV3_Bronze','Bronze',(.95,.51,.22),False)]:
 name='M_ThorSeatV3_'+suffix;mat=u.load_asset(D+'/'+name) or A.create_asset(name,D,u.Material,u.MaterialFactoryNew())
 L.delete_all_material_expressions(mat);mat.set_editor_property('used_with_nanite',True)
 surface=L.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels);surface.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
 uv=L.create_material_expression(mat,u.MaterialExpressionTextureCoordinate);uv.set_editor_property('coordinate_index',1)
 nodes={}
 for key in ['BaseColor','MetallicRoughness','Normal']:
  tex=u.load_asset('/Game/Weapons/CommonHammerHeads20261014/Textures/T_CommonHammerSteel_'+key)
  if not tex:raise RuntimeError('Missing shared steel texture '+key)
  n=L.create_material_expression(mat,u.MaterialExpressionTextureSample);n.set_editor_property('texture',tex);n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if key=='MetallicRoughness' else u.MaterialSamplerType.SAMPLERTYPE_COLOR);L.connect_material_expressions(uv,'',n,'UVs');nodes[key]=n
 tint=L.create_material_expression(mat,u.MaterialExpressionConstant3Vector);tint.set_editor_property('constant',u.LinearColor(*tint_rgb,1))
 color=L.create_material_expression(mat,u.MaterialExpressionMultiply);L.connect_material_expressions(nodes['BaseColor'],'RGB',color,'A');L.connect_material_expressions(tint,'',color,'B')
 flat=L.create_material_expression(mat,u.MaterialExpressionConstant3Vector);flat.set_editor_property('constant',u.LinearColor(0,0,1,1))
 lerp=L.create_material_expression(mat,u.MaterialExpressionLinearInterpolate);lerp.set_editor_property('const_alpha',.18);L.connect_material_expressions(flat,'',lerp,'A');L.connect_material_expressions(nodes['Normal'],'RGB',lerp,'B')
 normal=L.create_material_expression(mat,u.MaterialExpressionNormalize);L.connect_material_expressions(lerp,'',normal,'VectorInput')
 rough=L.create_material_expression(mat,u.MaterialExpressionConstant);rough.set_editor_property('r',.74)
 metal=L.create_material_expression(mat,u.MaterialExpressionConstant);metal.set_editor_property('r',0)
 for node,ch,pin,prop in [(tint if is_pad else color,'','BaseColor',u.MaterialProperty.MP_BASE_COLOR),(rough if is_pad else nodes['MetallicRoughness'],'' if is_pad else 'G','Roughness',u.MaterialProperty.MP_ROUGHNESS),(metal if is_pad else nodes['MetallicRoughness'],'' if is_pad else 'B','Metallic',u.MaterialProperty.MP_METALLIC),(normal,'','Normal',u.MaterialProperty.MP_NORMAL)]:
  if not L.connect_material_expressions(node,ch,surface,pin):raise RuntimeError('Material pin '+pin)
  L.connect_material_property(node,ch,prop)
 L.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL);L.layout_material_expressions(mat)
 errors=L.recompile_material(mat)
 if errors:raise RuntimeError(str(errors))
 save(mat)
 materials[alias]=mat
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
for row in json.loads((P/'model_manifest.json').read_text(encoding='utf-8'))['parts']:
 name=row['mesh'];mesh=u.load_asset(D+'/'+name)
 if not mesh:mesh=imp(P/'Export'/(name+'.fbx'),name,D,opt)
 for i,s in enumerate(mesh.get_editor_property('static_materials')):
  key=re.sub(r'(?:[._]\d{3})+$','',str(s.material_slot_name))
  if key not in materials:raise RuntimeError('Unknown material '+key)
  mesh.set_material(i,materials[key])
 n=mesh.get_editor_property('nanite_settings');n.enabled=True;n.explicit_tangents=True;n.fallback_percent_triangles=1.;n.fallback_relative_error=0.;mesh.set_editor_property('nanite_settings',n)
 box=mesh.get_bounding_box();size=box.max-box.min;expected=[(row['bounds_m'][1][i]-row['bounds_m'][0][i])*100 for i in range(3)]
 got=[size.x,size.y,size.z]
 if any(abs(a-b)>.05 for a,b in zip(expected,got)):raise RuntimeError('Model scale mismatch '+name+str(got))
 save(mesh);receipt['models'].append({'id':row['id'],'mesh':mesh.get_path_name(),'size_cm':got,'material_paths':[s.material_interface.get_path_name() for s in mesh.get_editor_property('static_materials')],'nanite':True,'explicit_tangents':True,'fbx_sha256':hashlib.sha256((P/'Export'/(name+'.fbx')).read_bytes()).hexdigest()});record()
settings={'lod_group':u.TextureGroup.TEXTUREGROUP_UI,'compression_settings':u.TextureCompressionSettings.TC_EDITOR_ICON,'srgb':True,'never_stream':True,'mip_gen_settings':u.TextureMipGenSettings.TMGS_NO_MIPMAPS}
for row in json.loads((P/'icon_audit.json').read_text(encoding='utf-8'))['unique']:
 name=row['key'];tex=u.load_asset(IC+'/'+name);created=not bool(tex);before={};changed=[]
 if not tex:tex=imp(Path(row['path']),name,IC)
 else:before={k:str(tex.get_editor_property(k)) for k in settings}
 for key,val in settings.items():
  if tex.get_editor_property(key)!=val:changed.append(key)
 if changed or created:
  disk=R/'Content/ColdSteelData/AttachmentIcons20260913'/(name+'.uasset')
  if disk.exists():shutil.copy2(disk,B/disk.name)
  for key,val in settings.items():tex.set_editor_property(key,val)
  save(tex)
 receipt['icons'].append({'key':name,'created':created,'settings_changed':changed,'before':before,'after':{k:str(tex.get_editor_property(k)) for k in settings},'png_sha256':row['sha256'],'source_png_size':row['size']});record()
receipt['complete']=True;record();print('THOR_SEATS_V3_AND_ICON_AUDIT_SAVED')
