import unreal as u
p="/Game/Weapons/SVCH/Integrated20261017/Materials/MI_SVCH_Material"
if u.EditorAssetLibrary.does_asset_exist(p):
    ok=u.EditorAssetLibrary.delete_asset(p)
    print("DELETED stale MI_SVCH_Material", ok)
else:
    print("no stale asset")
# confirm the seven real instances
for part in ("Body","Magazine","BoltCarrier","MagRelease","Selector","Cartridge"):
    q="/Game/Weapons/SVCH/Integrated20261017/Materials/MI_SVCH_"+part
    print(part, u.EditorAssetLibrary.does_asset_exist(q))
