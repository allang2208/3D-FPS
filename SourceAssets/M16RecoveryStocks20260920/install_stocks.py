"""Reimport only the four M16 stock variants, retaining their runtime slots."""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parent.parent;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
spec=json.loads((O/'repairs.json').read_text());baseline=json.loads((O/'runtime_sources.json').read_text())['stocks'];report={}
for key,row in spec['stocks'].items():
 old_info=baseline[key];path=old_info['asset'];old=u.load_asset(path)
 if not old:raise RuntimeError('Missing stock '+path)
 previous=list(old.get_editor_property('asset_import_data').extract_filenames())
 already_imported=len(previous)==1 and Path(previous[0])==Path(row['file'])
 if previous!=old_info['source'] and not already_imported:raise RuntimeError('Stock edited since source read: '+path)
 src=P/'Content'/(path.removeprefix('/Game/')+'.uasset');backup=O/'PreviousAssets'/(path.removeprefix('/Game/')+'.uasset')
 if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,backup)
 options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;options.import_as_skeletal=False;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
 data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
 task=u.AssetImportTask();task.filename=row['file'];task.destination_path=path.rsplit('/',1)[0];task.destination_name=path.rsplit('/',1)[1];task.automated=True;task.replace_existing=True;task.save=False;task.options=options
 if not already_imported:
  A.import_asset_tasks([task])
  if not task.imported_object_paths:raise RuntimeError('No imported stock '+path)
 asset=u.load_asset(path);bindings={s['slot']:s['material'] for s in old_info['slots']}
 for index,slot in enumerate(asset.static_materials):
  material=bindings.get(str(slot.material_slot_name))
  if not material:raise RuntimeError('Unknown stock material slot '+str(slot.material_slot_name))
  asset.set_material(index,u.load_asset(material))
 E.set_metadata_tag(asset,'M16InterfaceSource','M16RecoveryStocks20260920: closed actual 106-vertex receiver cut and solid stem shoulder; preserved donor UV0..3')
 saved=E.save_loaded_asset(asset,False)
 if not saved:raise RuntimeError('Could not save '+path)
 report[key]={'asset':asset.get_path_name(),'source':row['file'],'saved':saved,'slots':[str(s.material_slot_name) for s in asset.static_materials]}
 (O/'installation.json').write_text(json.dumps(report,indent=2));print('M16_STOCK_IMPORTED',key,flush=True)
state={'dirty_maps':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()], 'dirty_content':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
(O/'editor_build_state.json').write_text(json.dumps(state,indent=2))
print('M16_STOCK_INSTALL_COMPLETE',len(report),'dirty_maps',len(state['dirty_maps']),'dirty_content',len(state['dirty_content']),flush=True)
