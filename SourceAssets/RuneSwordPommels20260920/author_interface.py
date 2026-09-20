"""Extract the production collar in the open editor with Vibe3D; no render or test."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).parent; E=P/'Interface'; E.mkdir(exist_ok=True)
S=u.ModelingService;L=u.EditorAssetLibrary
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before authoring pommel assets; leave the editor open.')
source='/Game/Weapons/AzureRunesword20260913/Modules20260919/SM_RuneSword_Pommel_factory'
dest='/Game/Weapons/AzureRunesword20260913/Pommels20260920/Source/SM_RunePommel_StockCollar'
def done(r):
    if not r.success:raise RuntimeError(r.message)
    return r
h=done(S.load_mesh_from_static_mesh(source)).handle
try:
    info=S.get_mesh_info(h)
    print('FACTORY_MESH_INFO',info)
    done(S.plane_cut(h,u.Transform(location=u.Vector(0,0,-.9)),True,True))
    done(S.save_mesh_to_static_mesh(h,dest,False,False,False,False))
    src=u.load_asset(source); mat=src.get_material(0)
    done(S.set_asset_materials(dest,mat.get_path_name(),True))
    asset=u.load_asset(dest)
    export=u.AssetExportTask();export.object=asset;export.filename=str(E/'StockCollar.fbx')
    export.automated=True;export.prompt=False;export.replace_identical=True
    export.exporter=u.StaticMeshExporterFBX();export.options=u.FbxExportOption()
    export.options.ascii=False;export.options.level_of_detail=False;export.options.collision=False
    if not u.Exporter.run_asset_export_task(export):raise RuntimeError('Collar export failed')
    receipt={'source':source,'collar_asset':asset.get_path_name(),'material':mat.get_path_name(),
      'cut_z_cm':-.9,'placement_cm':[0,0,-19.5],'units':'centimetres; blade +Z, width X, thickness Y',
      'interface':'azure_hilt_v1','export':export.filename}
    (P/'interface_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('POMMEL_INTERFACE_AUTHORED',json.dumps(receipt))
finally:S.release_mesh(h)
