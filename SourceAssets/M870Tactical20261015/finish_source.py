from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
f=P/'Source/FPSGAME/UI/ColdSteelPickupStudio.cpp';s=f.read_text(encoding='utf-8-sig');old='Item.Definition!=TEXT("ue_super90")&&';new=old+'Item.Definition!=TEXT("ue_m870")&&'
if new not in s:
 if old not in s:raise RuntimeError('Missing pickup warm allowlist')
 backup=O/'Before/Source/FPSGAME/UI/ColdSteelPickupStudio.cpp';backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():backup.write_bytes(f.read_bytes())
 f.write_text(s.replace(old,new),encoding='utf-8')
print('M870_PICKUP_WARM_REGISTERED')
f=P/'Source/FPSGAME/UI/ColdSteelWeaponIconCatalogCommandlet.cpp';s=f.read_text(encoding='utf-8-sig');old='TArray<FString>{TEXT("ue_super90"),';new='TArray<FString>{TEXT("ue_m870"),TEXT("ue_super90"),'
if new not in s:
 if old not in s:raise RuntimeError('Missing catalog production default list')
 backup=O/'Before/Source/FPSGAME/UI/ColdSteelWeaponIconCatalogCommandlet.cpp';backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():backup.write_bytes(f.read_bytes())
 f.write_text(s.replace(old,new,1),encoding='utf-8')
