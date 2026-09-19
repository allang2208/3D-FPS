"""Headless: export baluster + column to OBJ and dump the M_RomanStone_V2 expression graph.

Forensics (degenerate faces, flipped normals, UV issues) are done offline in numpy from the OBJ.
"""

import unreal

D = "/Game/Props/RomanColumn20260915"
BALUSTER = D + "/SM_RomanBaluster_Small"
COLUMN = D + "/SM_RomanColumn_Detailed"
STONE = D + "/M_RomanStone_V2"
OUT = r"D:\FPS3D\FPSGAME\SourceAssets\RomanColumn20260915\preview_20260917"


def log(m):
    print("[diag] " + m)


tools = unreal.AssetToolsHelpers.get_asset_tools()
ok = tools.export_assets([BALUSTER, COLUMN], OUT)
log("export_assets=%s" % ok)

mat = unreal.EditorAssetLibrary.load_asset(STONE)
if mat:
    log("material expressions:")
    for expr in unreal.MaterialEditingLibrary.get_material_expressions(mat) or []:
        info = "  " + type(expr).__name__
        try:
            info += " name=%s" % expr.get_editor_property("parameter_name")
        except Exception:
            pass
        try:
            info += " texture=%s" % expr.get_editor_property("texture").get_name()
        except Exception:
            pass
        try:
            info += " default=%s" % expr.get_editor_property("default_value")
        except Exception:
            pass
        log(info)
