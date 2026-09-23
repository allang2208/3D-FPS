import unreal as u,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/SVDReloadHandRepair20260923')
mesh=u.load_asset('/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock')
anim=u.load_asset('/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_reload')
rows={}
for name,asset,exporter in [('Mesh',mesh,u.SkeletalMeshExporterFBX()),('Reload',anim,u.AnimSequenceExporterFBX())]:
    opt=u.FbxExportOption();opt.ascii=False;opt.level_of_detail=False;opt.collision=False
    task=u.AssetExportTask();task.object=asset;task.filename=str(O/('UE_'+name+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=exporter;task.options=opt
    ok=u.Exporter.run_asset_export_task(task)
    rows[name]={'asset':asset.get_path_name(),'exported':bool(ok),'filename':task.filename}
    if not ok:raise RuntimeError('SVD export failed '+name)
opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,220/120,opt)
rows['pose_methods']=[n for n in dir(u.AnimPoseExtensions) if 'ref' in n or 'bone' in n]
rows['worlds']=[]
for world in u.EditorLevelLibrary.get_pie_worlds(False):
    actors=u.GameplayStatics.get_all_actors_of_class(world,u.Character)
    row={'world':world.get_path_name(),'characters':[]}
    for a in actors:
        d={'name':a.get_name(),'meshes':[]}
        for comp in a.get_components_by_class(u.SkeletalMeshComponent):
            sk=comp.get_skinned_asset()
            if sk:d['meshes'].append({'name':comp.get_name(),'asset':sk.get_path_name(),'animation_data':str(comp.get_editor_property('animation_data'))})
        row['characters'].append(d)
    rows['worlds'].append(row)
(O/'ue_export.json').write_text(json.dumps(rows,indent=2))
print('SVD_RUNTIME_EXPORT',json.dumps(rows))
