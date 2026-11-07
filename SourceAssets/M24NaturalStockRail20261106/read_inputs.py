from pathlib import Path
import unreal as u,json,hashlib
O=Path(__file__).resolve().parent
base='/Game/Weapons/M24/'
paths={
 'carbon_native':base+'CarbonSpine20261104/Meshes/SM_M24_CarbonSpine_Native',
 'carbon_advanced':base+'CarbonSpine20261104/Meshes/SM_M24_CarbonSpine_Advanced',
 'skeleton_native':base+'ReceiverGripRebuild20261031/Meshes/SM_M24_ReceiverStock_Native',
 'skeleton_advanced':base+'ReceiverGripRebuild20261031/Meshes/SM_M24_ReceiverStock_Advanced',
 'advanced_front':base+'ReceiverGripRebuild20261031/Meshes/SM_M24_AdvancedFront_ForIndependentGrip',
 'advanced_action':base+'AdvancedAction20261029/Meshes/SM_M24_m24_advanced_action',
 'host':base+'MotionMagazine20261027/SK_M24_MotionV9',
 'm24_custom_scope_6x':base+'Surface20261027/SM_M24_m24_custom_scope_6x',
 'm24_palma_iron':base+'MotionPolish20261027/SM_M24_m24_palma_iron'}
for k in ('holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','eoth_holographic','kv_scope_4x','thermal_scope'):
    paths[k]=base+'CommonOptics20261028/Meshes/SM_M24_'+k
rows={};dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for k,p in paths.items():
    obj=u.load_asset(p)
    if not obj:raise RuntimeError('Missing source '+p)
    if p in dirty:raise RuntimeError('Unsaved target retained: '+p)
    slots=obj.materials if k=='host' else obj.static_materials
    file=Path(u.Paths.project_content_dir())/(p[6:]+'.uasset')
    rows[k]={'path':p,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
        'slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in slots]}
    if k=='host':
        rows[k]['source_files']=list(obj.get_editor_property('asset_import_data').extract_filenames())
    elif not (O/'Inputs'/(k+'.fbx')).exists():
        t=u.AssetExportTask();t.object=obj;t.filename=str(O/'Inputs'/(k+'.fbx'));t.exporter=u.StaticMeshExporterFBX()
        t.options=u.FbxExportOption();t.options.level_of_detail=False;t.options.collision=False;t.automated=True;t.prompt=False;t.replace_identical=True
        if not u.Exporter.run_asset_export_task(t):raise RuntimeError('Export '+k)
    if k!='host':rows[k]['lods']=[obj.get_num_triangles(i) for i in range(obj.get_num_lods())]
    (O/'Inputs/current.json').write_text(json.dumps(rows,indent=2))
rows['_pie']=u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor() if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() else False
(O/'Inputs/current.json').write_text(json.dumps(rows,indent=2))
print('M24_INPUTS',list(paths),'PIE',rows['_pie'])
