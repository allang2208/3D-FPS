"""Export factory sights and the default LMG bipod with their native mounts."""
import unreal as u,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');ROOT=P/'SourceAssets/GunAssemblyCatalog20260928'
sources=json.loads((ROOT/'sources.json').read_text(encoding='utf-8'))
specs={
 'qbz191':[(f'/Game/Weapons/QBZ191/Attachments20260913/SM_QBZ191_{n}Sight',[.000688,y,.1],'body') for n,y in [('Rear',-.009231),('Front',.343514)]],
 'a762':[(f'/Game/Weapons/A762/Accessories05/Meshes/SM_A762_{n}Sight',[.00056,y,z],'body') for n,y,z in [('Rear',-.05576,.1065),('Front',.49144,.0935)]],
 'lmg201':[(f'/Game/Weapons/LMG201/Production20260927/SM_LMG201_{n}Sight',[.0008,y,z],'body') for n,y,z in [('Rear',-.04252,.0855),('Front',.54212,.0648)]]+[
 ('/Game/Weapons/LMG201/Production20260927/SM_LMG201_BipodBase',[0,0,0],'bipod'),
 ('/Game/Weapons/LMG201/Production20260927/SM_LMG201_BipodLegA',[.01356,.46498,-.01398],'bipod'),
 ('/Game/Weapons/LMG201/Production20260927/SM_LMG201_BipodLegB',[-.01196,.46498,-.01398],'bipod')]}
result={}
def vec(v):return [v.x,v.y,v.z]
for source in sources['weapons']:
    key=source['key']
    if key not in specs:continue
    mesh=u.load_asset(source['source_mesh']);skeleton=u.SkeletonModifier()
    skeleton.set_skeletal_mesh(mesh)
    root=skeleton.get_bone_transform('WPN_root',True)
    anchors={name:vec(skeleton.get_bone_transform(name,True).translation)
        for name in ['root','hand_l','hand_r','WPN_root','WPN_SOCKET_Magazine','WPN_Trigger']}
    row={'anchors':anchors,'root_basis':[vec(root.transform_location(u.Vector(*p))) for p in [(0,0,0),(1,0,0),(0,1,0),(0,0,1)]],'extras':[]}
    for path,location,group in specs[key]:
        asset=u.load_asset(path)
        if not asset:raise RuntimeError('Factory part missing: '+path)
        fbx=ROOT/'Sources'/(key+'_'+asset.get_name()+'.fbx')
        task=u.AssetExportTask();task.object=asset;task.filename=str(fbx);task.automated=True;task.prompt=False
        task.replace_identical=True;task.exporter=u.StaticMeshExporterFBX();options=u.FbxExportOption()
        options.ascii=False;options.level_of_detail=False;options.collision=False;task.options=options
        if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed: '+path)
        row['extras'].append({'mesh':path,'fbx':str(fbx),'location':location,'group':group,
            'materials':[{'slot':str(s.material_slot_name),'asset':s.material_interface.get_path_name() if s.material_interface else None} for s in asset.get_editor_property('static_materials')]})
    result[key]=row
(ROOT/'extras.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('ASSEMBLY_FACTORY_PARTS_EXPORTED '+str(sum(len(r['extras']) for r in result.values())))
