from pathlib import Path
import unreal as u
root=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonFaceRepair20261003')
for name in ['M_skin_unified_baked','M_headDown']:
    mat=u.load_asset('/Game/AsianMale_Jason/Demo/MetaHumans/Common/Lookdev_UHM/Skin/Materials/'+name)
    task=u.AssetExportTask();task.object=mat;task.filename=str(root/(name+'.t3d'))
    task.exporter=u.ObjectExporterT3D();task.automated=True;task.prompt=False;task.replace_identical=True
    print(name+' export '+str(u.Exporter.run_asset_export_task(task)))
    print('opacity '+str(u.MaterialEditingLibrary.get_material_property_input_node(mat,u.MaterialProperty.MP_OPACITY_MASK)))
head=u.load_asset('/Game/AsianMale_Jason/Mesh/Head/SKM_Jason_head')
dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(head,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
_,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
import json
out=[]
for b in bones:
    p=b.world_transform.translation
    out.append({'name':str(b.name),'parent':b.parent_index,'position':[p.x,p.y,p.z],
                'local':str(b.local_transform) if hasattr(b,'local_transform') else ''})
(root/'head_bones.json').write_text(json.dumps(out))
