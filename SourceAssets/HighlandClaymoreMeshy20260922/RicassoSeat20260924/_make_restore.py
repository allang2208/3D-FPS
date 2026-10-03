from pathlib import Path
p = Path(r"D:\FPS3D\FPSGAME\SourceAssets\HighlandClaymoreMeshy20260922\RicassoSeat20260924\import_ricasso.py")
t = p.read_text(encoding="utf-8-sig")
old = "for name, folder in JOBS:\n    fbx = P / \"Export\" / (name + \".fbx\")"
new = """BASE = P.parent
SOURCES = {
    "SM_Highland_Blade_factory": BASE / "Integration/Export/SM_Highland_Blade_factory.fbx",
    "SM_Highland_Blade_extended_edge": BASE / "Integration/Export/SM_Highland_Blade_extended_edge.fbx",
    "SM_Highland_Blade_heavy_spine": BASE / "Integration/Export/SM_Highland_Blade_heavy_spine.fbx",
    "SM_Highland_Blade_feather_edge": BASE / "Integration/Export/SM_Highland_Blade_feather_edge.fbx",
    "SM_Highland_Guard_factory": BASE / "Integration/Export/SM_Highland_Guard_factory.fbx",
    "SM_Highland_Guard_bastion_guard": BASE / "Integration/Export/SM_Highland_Guard_bastion_guard.fbx",
    "SM_Highland_Guard_riposte_guard": BASE / "Integration/Export/SM_Highland_Guard_riposte_guard.fbx",
    "SM_Highland_Guard_light_guard": BASE / "Integration/Export/SM_Highland_Guard_light_guard.fbx",
    "SM_Highland_Blade_Broadblade_ThickV2": BASE / "BroadbladeThicknessV2_20260922/Export/SM_Highland_Blade_Broadblade_ThickV2.fbx",
    "SM_Highland_Guard_Cloven": BASE / "ClovenGuard20260922/Export/SM_Highland_Guard_Cloven.fbx",
}
for name, folder in JOBS:
    fbx = SOURCES[name]"""
if old not in t:
    raise SystemExit("pattern missing")
out = p.with_name("restore_original.py")
text = t.replace(old, new, 1).replace("import_receipt.json", "restore_receipt.json")
out.write_text(text, encoding="utf-8", newline="\n")
print("wrote", out)
