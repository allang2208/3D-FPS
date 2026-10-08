"""Save six fitted grips, PBR and UI icons, then publish the approved catalog entries.

Run with UE Python commandlet when the editor is closed, or the existing mutex
bridge when already open. No PIE, tests, preview scene, or editor launch.
"""
import unreal as u, json, shutil, sys
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
sys.path.insert(0,str(P))
from grip_materials import build_material
D='/Game/Weapons/SharedSwordGrips20260927'
I='/Game/ColdSteelData/AttachmentIcons20260913'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
models=json.loads((P/'models.json').read_text());receipts=[]
level_editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
if level_editor and level_editor.is_in_play_in_editor():
 raise RuntimeError('End Play before importing: the engine blocks asset saving during PIE.')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
def save(asset):
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
def task(file,name,folder,options=None):
 # Own new asset names only. A resumed run keeps already-created meshes rather
 # than invoking FBX reimport, which can reuse and compound old unit settings.
 asset=u.load_asset(folder+'/'+name)
 if not asset:
  t=u.AssetImportTask();t.filename=str(file);t.destination_name=name;t.destination_path=folder
  t.automated=True;t.replace_existing=False;t.save=False
  if options:t.options=options
  A.import_asset_tasks([t]);asset=u.load_asset(folder+'/'+name)
  if not asset or not t.imported_object_paths:raise RuntimeError('Import failed: '+str(file))
 receipts.append({'source':str(file),'asset':asset.get_path_name()});return asset
def texture(file,name,kind,folder=D+'/Textures'):
 tex=task(file,name,folder);tex.srgb=kind in ['BaseColor','Icon']
 tex.compression_settings={'Normal':u.TextureCompressionSettings.TC_NORMALMAP,'BaseColor':u.TextureCompressionSettings.TC_DEFAULT,'Roughness':u.TextureCompressionSettings.TC_MASKS,'Icon':u.TextureCompressionSettings.TC_EDITOR_ICON}[kind]
 if kind=='Normal':tex.flip_green_channel=True
 if kind=='Icon':
  tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
 save(tex);return tex
materials={}
for key in ['Leather','Steel','Textile']:
 name='M_SharedGrip_'+key;mat=u.load_asset(D+'/Materials/'+name)
 maps={suffix:texture(P/'Textures'/(key+'_'+suffix+'.png'),'T_SharedGrip_'+key+'_'+suffix,suffix) for suffix in ['BaseColor','Normal','Roughness']}
 if not mat:
  mat=A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
 build_material(mat,key,maps)
 E.set_metadata_tag(mat,'SharedSwordGrip.Source','Original authored PBR surfaces, 20260927')
 save(mat);materials[key]=mat
editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
entries={}
for row in models:
 name=row['mesh'];folder=D+'/'+row['host'];file=Path(row['folder'])/(name+'.fbx')
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
 opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_mesh=True
 opt.import_materials=False;opt.import_textures=False
 data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
 data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
 data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
 data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
 mesh=task(file,name,folder,opt)
 settings=editor.get_lod_build_settings(mesh,0);settings.recompute_normals=False;settings.recompute_tangents=True
 settings.use_mikk_t_space=True;settings.remove_degenerates=True;settings.use_full_precision_u_vs=True
 editor.set_lod_build_settings(mesh,0,settings)
 stock=u.load_asset(row['stock_mesh'])
 if not stock:raise RuntimeError('Missing stock mounting material '+row['stock_mesh'])
 for index,slot in enumerate(mesh.static_materials):
  slotname=str(slot.material_slot_name)
  if row['stock_material_slot'] in slotname:material=stock.get_material(0)
  else:
   kind=next((k for k in materials if 'M_SharedGrip_'+k in slotname),None)
   if kind is None:raise RuntimeError('Unmapped authored material slot '+slotname)
   material=materials[kind]
  mesh.set_material(index,material)
 E.set_metadata_tag(mesh,'SharedSwordGrip.Source','Approved design; per-host original mounting rims, 20260927')
 E.set_metadata_tag(mesh,'SharedSwordGrip.HandContact','Stock length and hand positions; no pommel offset or animation replacement')
 save(mesh)
 key=row['weapon']+'_grip_'+row['id'];png=P/'Icons'/(key+'.png')
 deployed=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/png.name
 shutil.copy2(png,deployed)
 texture(deployed,key,'Icon',I)
 entries.setdefault(row['catalog'],{})[row['id']]={'mesh':mesh.get_path_name(),
  'location_cm':row['location_cm'],'interface':row['interface'],'pommel_offset_cm':[0,0,0],
  'appearance':'贴平钢脊 · 三段人字纹皮革' if row['id']=='iron_spine_power_grip' else '交错锁纹织带 · 柔韧稳握'}
 u.log('SHARED_GRIP_SAVED '+name)
# All packages are saved before exposing options to runtime and saved equipment.
before=P/'Before';before.mkdir(exist_ok=True)
def load_live(name):
 file=ROOT/'Content/ColdSteelData'/name
 if not (before/name).exists():shutil.copy2(file,before/name)
 return file,json.loads(file.read_text(encoding='utf-8-sig'))
def write(file,content):
 temporary=file.with_suffix('.shared-grips.tmp')
 temporary.write_text(json.dumps(content,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temporary.replace(file)
for name,new in entries.items():
 file,live=load_live(name);live['slots']['grip'].update(new);write(file,live)
file,live=load_live('melee-gunsmith.json')
column=next(c for c in live['columns'] if c['key']=='grip')
weapons=['ue_rune_sword','ue_frost_crystal_sword','ue_highland_claymore','ue_xuanchi_zhenyue']
new_options=[
 {'id':'iron_spine_power_grip','name':'铁脊强攻柄','weapons':weapons,
  'description':'贴平钢脊支撑三段皮革握区，偏重重击破韧，出手稍慢。伤害与削韧增益仅作用于重击，包含护手转换的重击。',
  'effects':[{'text':'重击伤害 +20%','benefit':1},{'text':'重击韧性伤害 +30%','benefit':1},{'text':'攻击速度 -8%','benefit':-1}],
  'stats':{'heavy_damage_mult':1.2,'heavy_toughness_mult':1.3,'attack_speed_mult':.92}},
 {'id':'lockweave_guard_grip','name':'锁纹稳握柄','weapons':weapons,
  'description':'交错锁纹织带贴合握区，提升格挡稳定性与受击续航。格挡减伤沿原有上限计算。',
  'effects':[{'text':'格挡受击耐力消耗 -25%','benefit':1},{'text':'格挡减伤倍率 ×1.10','benefit':1}],
  'stats':{'block_stamina_mult':.75,'block_reduction_mult':1.1}}
]
for option in new_options:
 index=next((i for i,o in enumerate(column['options']) if o['id']==option['id']),None)
 if index is None:column['options'].append(option)
 else:column['options'][index]=option
column['description']='双手接触的握柄区域。原装握把保留原握持位置；可选吸震、速握、长柄、重击破韧与格挡稳握配置。长柄同步移动柄尾并适配左手。'
write(file,live)
(P/'import_receipt.json').write_text(json.dumps({'saved_assets':receipts,'materials':[m.get_path_name() for m in materials.values()],
 'catalogs':entries,'options':new_options,'testing':'Not run; user will test'},ensure_ascii=False,indent=2),encoding='utf-8')
u.log('SHARED_SWORD_GRIPS_IMPORTED_AND_SAVED')
