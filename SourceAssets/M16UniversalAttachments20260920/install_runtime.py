"""Scoped textual edits: retain concurrent changes outside these exact fragments."""
from pathlib import Path
ROOT=Path(__file__).parents[2];S=ROOT/'Source/FPSGAME'
def edit(file,pairs,include=True):
 p=S/file;t=p.read_bytes().decode('utf-8')
 if include and '#include "M16Attachments.h"' not in t:
  anchor='#include "../FPSGAMECharacter.h"'
  t=t.replace(anchor,anchor+'\n#include "M16Attachments.h"',1)
 for old,new in pairs:
  if old not in t:
   old=old.replace('\n','\r\n');new=new.replace('\n','\r\n')
  if old not in t:raise RuntimeError(file+' missing edit '+repr(old[:100]))
  t=t.replace(old,new,1)
 p.write_bytes(t.encode('utf-8'))
for file,family,field in [('M4VerticalForegrip.cpp','vertical','VerticalForegrip'),('M4CantedForegrip.cpp','canted','CantedForegrip'),('M4AngledForegrip.cpp','angled','AngledForegrip'),('M4HandstopVisual.cpp','prism','PrismHandstop')]:
 pairs=[('(bUseQBZ191||bUseASH12)&&!Pair.Key','(bUseQBZ191||bUseASH12||bUseM16)&&!Pair.Key'),
 ('bUseASH12?ASH12WeaponAssets::GripAnimationPath',f'bUseM16?M16Attachments::AnimationPath(TEXT("{family}"),Pair.Value):bUseASH12?ASH12WeaponAssets::GripAnimationPath')]
 # Prism is configured inside SetGunsmithHandstop after the other families.
 anchor=f'    if(bUseASH12){{{field}=ASH12Attachments::Configure'
 if file=='M4HandstopVisual.cpp':
  field='PrismHandstop';anchor='    if(bUseASH12){PrismHandstop=ASH12Attachments::Configure'
 pairs.append((anchor,f'    if(bUseM16){{{field}=M16Attachments::Configure(this,AKMViewmodel,{field},TEXT("{family}"),bEnabled&&bInventoryWeaponReady);return;}}\n'+anchor))
 edit('Weapons/'+file,pairs)
edit('Weapons/M4HandstopVisual.cpp',[
 ('const FString Path=FString::Printf(TEXT("/Game/Weapons/TacticalVerticalForegrip20260919/%s/SM_TacticalVerticalForegrip"),Rifle);','const FString Path=bUseM16?M16Attachments::MeshPath(TEXT("tactical_vertical")):FString::Printf(TEXT("/Game/Weapons/TacticalVerticalForegrip20260919/%s/SM_TacticalVerticalForegrip"),Rifle);')])
edit('Weapons/M4GunsmithVisual.cpp',[
 ('const FString SelectedMeshPath = bUseASH12','const FString SelectedMeshPath = bUseM16 ? M16Attachments::MeshPath(Variant) : bUseASH12'),
 ('HolographicMount=bUseQBZ191?','HolographicMount=bUseM16?M16Attachments::OpticMount():bUseQBZ191?'),
 ('const FString RingMeshPath = bUseASH12','const FString RingMeshPath = bUseM16 ? M16Attachments::MeshPath(TEXT("lpvo_ring")) : bUseASH12')])
edit('Weapons/M4MuzzleVisual.cpp',[
 ('const FString Path=bASH12Tactical?','const FString Path=bUseM16?M16Attachments::MeshPath(Key):bASH12Tactical?')])
edit('Weapons/SkeletonStockVisual.cpp',[
 ('Name.Contains(TEXT("FactoryStock"))','Name.Contains(TEXT("FactoryStock"))||Name==TEXT("M_M16_Stock")'),
 ('CheekRest?ASH12WeaponAssets::CheekRestMeshPath:','bUseM16?*M16Attachments::MeshPath(Variant):CheekRest?ASH12WeaponAssets::CheekRestMeshPath:'),
 ('StockMount=bUseQBZ191?','StockMount=(bUseM16||bUseQBZ191)?')])
edit('Weapons/PhantomRearGripVisual.cpp',[
 ('Name.Contains(TEXT("FactoryRearGrip"))','Name.Contains(TEXT("FactoryRearGrip"))||Name==TEXT("M_M16_PistolGrip")'),
 ('const FString Path=StableGrip','const FString Path=bUseM16?M16Attachments::MeshPath(Variant):StableGrip')])
edit('Weapons/M4DrumVisual.cpp',[
 ('LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_M4_LargeDrum"))','LoadObject<UStaticMesh>(nullptr,bUseM16?*M16Attachments::MeshPath(TEXT("large_drum")):TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_M4_LargeDrum"))'),
 ('LoadObject<UStaticMesh>(nullptr,bUseASH12','LoadObject<UStaticMesh>(nullptr,bUseM16?*M16Attachments::MeshPath(TEXT("ext_mag")):bUseASH12'),
 ('WeaponMesh->GetMaterials()[M].MaterialSlotName.ToString().Contains(TEXT("Magazine")))\n                    AKMViewmodel','(bUseM16?WeaponMesh->GetMaterials()[M].MaterialSlotName==TEXT("M_M16_Magazine"):WeaponMesh->GetMaterials()[M].MaterialSlotName.ToString().Contains(TEXT("Magazine"))))\n                    AKMViewmodel')])
edit('Weapons/TacticalDeviceComponent.cpp',[
 ('const FString Path=ASH','const FString Path=Family==TEXT("M16")?M16Attachments::MeshPath(Variant):ASH'),
 ('if(!Pistol&&!ASH&&Variant==TEXT("laser"))','if(!Pistol&&!ASH&&Family!=TEXT("M16")&&Variant==TEXT("laser"))'),
 ('if(!Pistol&&!ASH&&Variant==TEXT("flashlight"))','if(!Pistol&&!ASH&&Family!=TEXT("M16")&&Variant==TEXT("flashlight"))'),
 ('const FString Family=bUseASH12?','const FString Family=bUseM16?TEXT("M16"):bUseASH12?')])
print('M16_RUNTIME_VISUAL_BRANCHES_INSTALLED')
