"""Save a native 201 mail sleeve repair and publish only its equipment profile."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;PROJECT=O.parents[2]
E=u.EditorAssetLibrary;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
DEST='/Game/Characters/ModularOutfit20260924/LMG201ADS34/SK_LMG201_Chainmail_ADS34'
data=json.loads((O/'sources.json').read_text())['meshes'];source=data['shirt']['mesh'];body=data['201']['mesh'];edits=json.loads((O/'weight_edits.json').read_text())
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; preserve loaded assets')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.split('.')[0] in dirty for p in [source,body,DEST]):raise RuntimeError('A relevant asset has unsaved changes')
def dynamic(path):
 a=u.load_asset(path)
 dm,status=G.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+path)
 return a,dm
shirt,dm=dynamic(source);native,native_dm=dynamic(body)
_,bones=B.get_all_bones_info(dm);ids={str(b.name):b.index for b in bones}
for row in edits:
 _,valid=B.set_vertex_bone_weights(dm,row['vertex_id'],[u.GeometryScriptBoneWeight(bone_index=ids[n],weight=w) for n,w in row['weights'].items()])
 if not valid:raise RuntimeError('Invalid sleeve vertex '+str(row['vertex_id']))
# Only the skin's bone table changes; the current garment's UVs, tangent data,
# vertex colours, triangles, lining and shared sway masks stay on the source mesh.
B.copy_bones_from_mesh(native_dm,dm,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=True))
asset=u.load_asset(DEST) or E.duplicate_asset(body,DEST)
if not asset:raise RuntimeError('Cannot create native 201 garment')
slots=[s.copy() for s in shirt.materials]
opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
_,res=G.copy_mesh_to_skeletal_mesh(dm,asset,opts,u.GeometryScriptMeshWriteLOD())
if res!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write repaired garment')
asset.set_editor_property('materials',slots);asset.set_editor_property('physics_asset',None)
settings=S.get_lod_build_settings(asset,0);settings.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(asset,0,settings)
if not u.FPSModularOutfitComponent.configure_outfit_lods(asset):raise RuntimeError('Cannot configure garment LODs')
if not S.regenerate_lod(asset,3,True,False):raise RuntimeError('Cannot build garment LODs')
for k,v in {'EquipmentDefinition':'ue_chainmail_shirt','201ADSRevision':'ADS34: right shoulder/upper sleeve follows accepted native 201 arm; old torso weights replaced by corresponding surface interpolation','201ADSSource':source,'201ADSWeightEdits':str(O/'weight_edits.json'),'SecondaryMotion':'Original shared outer/inner vertex mask; max 0.12 cm; no clothing assets'}.items():E.set_metadata_tag(asset,k,v)
if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save repaired asset')
ex=u.AssetExportTask();ex.object=asset;ex.filename=str(O/'SK_LMG201_Chainmail_ADS34.fbx');ex.automated=True;ex.prompt=False;ex.replace_identical=True;ex.options=u.FbxExportOption();ex.options.level_of_detail=False;ex.options.export_morph_targets=False;ex.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
if not u.Exporter.run_asset_export_task(ex):raise RuntimeError('Cannot save editable interchange source')
# The component resolves item variants by rig_profile. Add 201 explicitly for
# existing items, keeping their current supported PKM variants except this shirt.
cfg=PROJECT/'Content/ColdSteelData/modular_outfits.json';before=cfg.read_bytes();catalog=json.loads(before.decode('utf-8-sig'));profile_key=body
if profile_key not in catalog['profiles']:raise RuntimeError('Current source profile no longer exists')
profile=catalog['profiles'][profile_key]
if profile['rig_profile'] not in ['PKM','LMG201']:raise RuntimeError('201 profile changed concurrently')
(O/'Before').mkdir(exist_ok=True)
backup=O/'Before/modular_outfits.json'
if not backup.exists():backup.write_bytes(before)
modified=[]
for item,recipe in catalog['items'].items():
 for field in ['rig_meshes','skin_meshes']:
  maps=recipe.get(field)
  if not maps or 'PKM' not in maps:continue
  expected=asset.get_path_name() if item=='ue_chainmail_shirt' and field=='rig_meshes' else maps['PKM']
  if 'LMG201' in maps and maps['LMG201']!=expected:raise RuntimeError('Concurrent 201 item mapping '+item)
  if not u.load_asset(expected):raise RuntimeError('Missing equipment dependency '+expected)
  maps['LMG201']=expected;modified.append(item+'.'+field+'.LMG201')
profile['rig_profile']='LMG201'
if cfg.read_bytes()!=before:raise RuntimeError('Equipment catalog changed during asset save')
cfg.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
file=PROJECT/'Content'/(DEST.removeprefix('/Game/')+'.uasset')
report={'status':'asset_and_equipment_configuration_saved','asset':asset.get_path_name(),'asset_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'source_unchanged':source,'vertices_reweighted':len(edits),'new_native_profile':'LMG201','configuration_fields':modified,'profile':profile_key,'animation_changes':0,'weapon_mesh_changes':0,'left_sleeve_changes':0,'geometry_position_changes':0,'old_assets_deleted':False,'in_game_tested':False}
(O/'delivery.json').write_text(json.dumps(report,indent=2));print('ADS34_INSTALLED',json.dumps(report),flush=True)
