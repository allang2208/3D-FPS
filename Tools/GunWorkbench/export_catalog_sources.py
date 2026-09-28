"""Export the installed weapon meshes for authoring workbench assembly parts."""
import json,re
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');ROOT=P/'SourceAssets/GunAssemblyCatalog20260928'
OUT=ROOT/'Sources';OUT.mkdir(parents=True,exist_ok=True)
sources={
 'akm':('ue_akm','/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative'),
 'qbz191':('ue_qbz191','/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny'),
 'm1911':('ue_m1911','/Game/Weapons/M1911/RearFinish20260913/SK_M1911_Manny')}
for key,header in [('dan_wesson715','DanWesson715'),('ash12','ASH12'),('m16a2','M16'),('a762','A762'),('svd','SVD'),('pkm_lowpoly','PKMLowpoly'),('lmg201','LMG201')]:
    text=(P/('Source/FPSGAME/Weapons/'+header+'WeaponAssets.h')).read_text(encoding='utf-8-sig')
    path=re.search(r'\bMeshPath\s*=\s*TEXT\("([^"]+)"\)',text).group(1).split('.')[0]
    sources[key]=('ue_'+key,path)
result={'weapons':[]}
for key,(definition,path) in sources.items():
    mesh=u.load_asset(path)
    if not isinstance(mesh,u.SkeletalMesh):raise RuntimeError('Installed weapon mesh missing: '+path)
    fbx=OUT/(key+'.fbx')
    task=u.AssetExportTask();task.object=mesh;task.filename=str(fbx);task.automated=True
    task.prompt=False;task.replace_identical=True;task.exporter=u.SkeletalMeshExporterFBX()
    options=u.FbxExportOption();options.ascii=False;options.level_of_detail=False;options.collision=False
    task.options=options
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed: '+path)
    materials=[{'slot':str(s.material_slot_name),'asset':s.material_interface.get_path_name() if s.material_interface else None,
        'name':s.material_interface.get_name() if s.material_interface else None} for s in mesh.get_editor_property('materials')]
    result['weapons'].append({'key':key,'definition':definition,'source_mesh':path,'fbx':str(fbx),
        'source_files':list(mesh.get_editor_property('asset_import_data').extract_filenames()),'materials':materials})
    (ROOT/'sources.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('ASSEMBLY_WEAPON_SOURCES_EXPORTED '+str(len(result['weapons'])))
