"""Export poster RGB textures to PNGs, with file-based logging (print is not
captured in commandlet logs). Run via UnrealEditor-Cmd -run=pythonscript."""
from pathlib import Path
import json
import unreal as u

OUT = Path(r"D:/FPS3D/FPSGAME/SourceAssets/HospitalCorridor/PosterPreviews")
OUT.mkdir(parents=True, exist_ok=True)
log = {"found": [], "export_return": None, "exported_files": [], "errors": []}

AR = u.AssetRegistryHelpers.get_asset_registry()
assets = AR.get_assets_by_path("/Game/HospitalCorridor/Textures", recursive=True)
poster_paths = []
for a in assets:
    name = str(a.asset_name)
    cls = str(a.asset_class_path.asset_name)
    if cls == "Texture2D" and name.startswith("T_HospitalPosters") :
        poster_paths.append(str(a.package_name))
poster_paths.sort()
log["found"] = [p.split("/")[-1] for p in poster_paths]

if poster_paths:
    A = u.AssetToolsHelpers.get_asset_tools()
    try:
        ret = A.export_assets(poster_paths, str(OUT))
        log["export_return"] = str(ret)
    except Exception as e:
        log["errors"].append("export_assets: " + repr(e))
        # signature variant: (assets, export_path) as two lists? try keyword form
        try:
            ret = A.export_assets(assets_to_export=poster_paths, export_path=str(OUT))
            log["export_return"] = "kw:" + str(ret)
        except Exception as e2:
            log["errors"].append("kw variant: " + repr(e2))

log["exported_files"] = sorted(p.name for p in OUT.glob("*.png"))
(OUT / "_export_log.json").write_text(json.dumps(log, indent=1, ensure_ascii=False),
                                      encoding="utf-8")
