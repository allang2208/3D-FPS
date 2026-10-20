import unreal as u
from pathlib import Path
X=Path(r"D:\FPS3D\FPSGAME\SourceAssets\SVCHSketchfab20261017\Donor"); X.mkdir(exist_ok=True)
mesh=u.load_asset("/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock")
out=str(X/"SK_SVD_Arms_Donor.fbx")
t=u.AssetExportTask()
t.object=mesh
t.filename=out
t.automated=True
t.prompt=False
t.exporter=u.SkeletalMeshExporterFBX()
o=u.FbxExportOption()
for name,val in (("level_of_detail",False),("collision",False),("vertex_color",True),
                 ("export_morph_targets",False),("export_preview_mesh",False),("ascii",False)):
    try: o.set_editor_property(name,val)
    except Exception as e: print("OPTFAIL",name,e)
t.options=o
ok=u.Exporter.run_asset_export_task(t)
print("EXPORT_OK",ok,"errors",[str(e) for e in t.errors], Path(out).exists(), Path(out).stat().st_size if Path(out).exists() else 0)
