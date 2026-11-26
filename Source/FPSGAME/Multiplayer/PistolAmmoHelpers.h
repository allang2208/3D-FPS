#pragma once
#include "../UI/ColdSteelInventoryTypes.h"
#include "../Weapons/WeaponReloadStages.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

namespace PistolAmmo
{
inline bool Revolver(const FColdSteelItem& Gun)
{return Gun.Definition==TEXT("ue_dan_wesson715")||Gun.Definition==TEXT("ue_rsh12");}
inline int32 Cases(const FColdSteelItem& Gun)
{return Revolver(Gun)?FMath::Max(Gun.Magazine,int32(ColdSteelInventory::Number(Gun,TEXT("revolver_case_count"),Gun.Magazine))):Gun.Magazine;}
inline void SetCases(FColdSteelItem& Gun,int32 Count)
{
    if(!Revolver(Gun)||int32(ColdSteelInventory::Number(Gun,TEXT("revolver_case_count"),-1))==Count)return;
    TSharedPtr<FJsonObject> Data;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Gun.Data),Data)||!Data)return;
    Data->SetNumberField(TEXT("revolver_case_count"),Count);Gun.Data.Reset();
    FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Gun.Data));
}
inline void CopyMagazine(FColdSteelItem& To,const FColdSteelItem& From)
{
    const int32 Count=Cases(From);
    To.Magazine=From.Magazine;To.VirtualMagazineAmmo=From.VirtualMagazineAmmo;To.LoadedAmmoType=From.LoadedAmmoType;
    const bool Pending=WeaponReloadStages::NeedsCycle(From),Empty=WeaponReloadStages::UsesEmptyCycle(From);
    if(WeaponReloadStages::NeedsCycle(To)!=Pending||(Pending&&WeaponReloadStages::UsesEmptyCycle(To)!=Empty))
        WeaponReloadStages::SetNeedsCycle(To,Pending?(Empty?1:2):0);
    SetCases(To,Count);
}
}
