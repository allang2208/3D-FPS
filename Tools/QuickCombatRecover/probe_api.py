import unreal
print("=== AnimationLibrary funcs ===")
for f in dir(unreal.AnimationLibrary):
    if not f.startswith("_"):
        print(" ", f)
print("=== Skeleton props ===")
sk = unreal.load_asset("/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny_Skeleton")
print("skel:", sk)
if sk:
    for p in dir(sk):
        if not p.startswith("_"): print("  ", p)
