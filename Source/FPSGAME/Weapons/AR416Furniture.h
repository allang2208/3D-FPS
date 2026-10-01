#pragma once
#include "HK416WeaponAssets.h"

namespace AR416Furniture
{
inline bool Supports(const FString& Definition)
{
    return Definition==TEXT("ue_m4a1") || Definition==TEXT("ue_m16a2") || Definition==TEXT("ue_qbz191") || Definition==HK416WeaponAssets::Definition;
}
inline bool IsPart(const FString& Part)
{
    return Part==HK416WeaponAssets::StockPart || Part==HK416WeaponAssets::RearGripPart;
}
inline FString MeshPath(const FString& Definition,const FString& Part)
{
    if(!Supports(Definition)||!IsPart(Part))return FString();
    if(Definition==HK416WeaponAssets::Definition)return HK416WeaponAssets::AttachmentPath(Part);
    const FString Family=Definition==TEXT("ue_qbz191")?TEXT("QBZ191"):Definition==TEXT("ue_m16a2")?TEXT("M16"):TEXT("M4");
    const FString Name=Part==HK416WeaponAssets::StockPart?TEXT("SM_416_Stock"):TEXT("SM_416_RearGrip");
    return TEXT("/Game/Weapons/HK416/ARParts20261001/")+Family+TEXT("/")+Name+TEXT(".")+Name;
}
}
