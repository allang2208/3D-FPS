#include "../GunsmithSystem.h"
#include "StaffCatalog.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"

void UGunsmithSystem::LoadStaffCatalog()
{
    const auto C=ColdSteelStaff::Catalog();if(!C)return;
    TMap<FString,TArray<FGunsmithOption>> Options;
    for(const auto& V:C->GetArrayField(TEXT("columns")))
    {
        const auto Col=V->AsObject();const FString Key=Col->GetStringField(TEXT("key"));
        StaffSlotKeys.Add(Key);StaffCategoryNames.Add(Col->GetStringField(TEXT("name")));StaffDefaultNames.Add(Col->GetStringField(TEXT("default")));
        FGunsmithOption Factory;Factory.Id=TEXT("false");Factory.Name=Col->GetStringField(TEXT("default"));Factory.Description=Col->GetStringField(TEXT("description"));Options.Add(Key,{Factory});
        for(const auto& O:Col->GetArrayField(TEXT("options")))
        {
            const auto D=O->AsObject();FGunsmithOption Part;Part.Id=D->GetStringField(TEXT("id"));Part.Name=D->GetStringField(TEXT("name"));
            Part.Description=D->GetStringField(TEXT("description"));Part.Appearance=TEXT("独立长杖部件");Part.Effects.Emplace(Part.Description,1);
            Part.ReadSpecialEffects(D);
            Options.FindChecked(Key).Add(MoveTemp(Part));
        }
    }
    for(const auto& V:C->GetArrayField(TEXT("weapons")))
    {
        const auto D=V->AsObject();FGunsmithWeapon W;W.Id=D->GetStringField(TEXT("id"));
        const auto I=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->CreateItem(W.Id);
        W.Model=TEXT("staff");W.Name=ColdSteelInventory::Text(I,TEXT("name"));W.Source=D;W.Allowed=StaffSlotKeys;W.Options=Options;
        W.Base.Damage=ColdSteelInventory::Number(I,TEXT("melee_damage"),3);W.Base.Interval=.5;
        W.Base.Range=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->QuickCombatDefinition().QuickCombat.RangeCM/100.f;
        W.Base.Capacity=0;W.Base.Speed=W.Base.ADS=W.Base.Reload=W.Base.EmptyReload=0;
        StaffWeapons.Add(W.Id,MoveTemp(W));
    }
}
