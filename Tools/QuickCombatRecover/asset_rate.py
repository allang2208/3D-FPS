import unreal, json, os
OUT=r"D:\FPS3D\FPSGAME\Saved\QuickCombatRecover\asset_rate.json"
paths=[
 "/Game/Weapons/AzureRunesword20260913/A_RuneSword_PommelStrike",
 "/Game/Weapons/AzureRunesword20260913/A_RuneSword_Idle",
 "/Game/Weapons/AzureRunesword20260913/A_RuneSword_Slash1",
 "/Game/Weapons/DanWesson715/QuickCombat20260918/Animations/A_DW715_quickcombat",
 "/Game/Weapons/M1911/QuickCombat20260919/Animations/A_M1911_quickcombat",
 "/Game/Weapons/M4StockMelee20260918/Base/A_M4_QuickCombat_Base",
]
res={}
for p in paths:
    a=unreal.load_asset(p)
    if not a: res[p]="missing"; continue
    e={"length":round(float(a.get_play_length()),4)}
    for prop in ("sampling_frame_rate","number_of_frames","num_frames","interpolation","compression_scheme","enable_root_motion"):
        try:
            v=a.get_editor_property(prop)
            e[prop]=str(v)
        except Exception as ex:
            e[prop]="n/a"
    try:
        e["num_frames"]=unreal.AnimationLibrary.get_num_frames(a)
    except Exception: pass
    try:
        e["skeleton"]=a.get_editor_property("skeleton").get_name() if a.get_editor_property("skeleton") else None
    except Exception: pass
    res[p]=e
json.dump(res,open(OUT,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
unreal.log("ASSET_RATE_DONE")
print("WROTE",OUT)
