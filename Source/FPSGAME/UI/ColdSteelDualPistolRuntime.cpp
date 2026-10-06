#include "ColdSteelStatusModel.h"
#include "ColdSteelEnhancementSystem.h"
#include "../Weapons/WeaponReloadStages.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Engine/GameInstance.h"

namespace
{
bool Revolver(const FColdSteelItem& Item)
{
    return Item.Definition==TEXT("ue_dan_wesson715") || Item.Definition==TEXT("ue_rsh12");
}
void Cases(FColdSteelItem& Item,int32 Count)
{
    TSharedPtr<FJsonObject> O;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),O);
    if(O){O->SetNumberField(TEXT("revolver_case_count"),Count);Item.Data.Reset();FJsonSerializer::Serialize(O.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));}
}
bool EquippedPistol(const FColdSteelItem& Item,int32 Active)
{
    return ColdSteelInventory::IsDualPistol(Item) && Item.Place==1 && (Item.Cell==Active || Item.Cell==(Active==6?8:11));
}
}
FString UColdSteelStatusModel::AmmoDefinitionFor(const FColdSteelItem& Item) const
{
    if(ColdSteelInventory::IsBow(Item))
    {
        const auto* Selected = AmmoType(Item.LoadedAmmoType);
        if (Selected && Selected->Enabled && Selected->Group == AmmoGroupFor(Item)) return Selected->Id;
        const FString Arrow=ColdSteelInventory::Text(Item,TEXT("arrow_ammo"));
        return Arrow.IsEmpty()?FString(TEXT("arrow_wood")):Arrow;
    }
    return Item.LoadedAmmoType.IsEmpty()?AmmoGroupFor(Item):Item.LoadedAmmoType;
}
int32 UColdSteelStatusModel::AmmoCountFor(const FColdSteelItem& Item) const
{
    return int32(FMath::Min<int64>(PouchCount(AmmoDefinitionFor(Item)),MAX_int32));
}
int32 UColdSteelStatusModel::ReloadDualPistol(const FString& Id,int32 Requested,int32 Capacity,bool Completed,int32 NeedsCycle)
{
    if(!CurrentPawn.IsValid() || Requested<=0)return 0;
    SyncRuntime();auto P=Snapshot();auto* Gun=P.Items.FindByPredicate([&](const auto& I){return I.InstanceId==Id && EquippedPistol(I,P.ActiveWeaponSlot);});
    if(!Gun)return 0;
    const FString Def=AmmoDefinitionFor(*Gun);Requested=FMath::Clamp(Requested,0,Capacity-Gun->Magazine);
    const bool Infinite=CurrentPawn->HasInfiniteReserveAmmoFor(Def);
    const int32 Taken=Infinite?Requested:int32(FMath::Min<int64>(Requested,P.AmmoPouch.FindRef(Def)));if(Taken<=0)return 0;
    if(!Infinite)P.AmmoPouch.FindOrAdd(Def)-=Taken;
    Gun->Magazine+=Taken;
    if(!WeaponReloadStages::SetNeedsCycle(*Gun,NeedsCycle))return 0;
    if(Infinite)Gun->VirtualMagazineAmmo+=Taken;
    if(Revolver(*Gun))Cases(*Gun,FMath::Max(Gun->Magazine,int32(ColdSteelInventory::Number(*Gun,TEXT("revolver_case_count"),0))));
    P.Items.RemoveAll([](const auto& I){return I.Count<=0;});
    if(Completed)ColdSteelSkills::AddExperience(P,DexterousHandsSkill,DexterousHandsSkill.ReloadExperience);
    return CommitState(P)?Taken:0;
}
bool UColdSteelStatusModel::EjectDualPistolCases(const FString& Id,bool DiscardLive)
{
    if(!CurrentPawn.IsValid())return false;
    SyncRuntime();auto P=Snapshot();
    // RSH uses the same dual-hand ejection transaction. Rejecting it here
    // aborts AdvanceReload, then the empty-hand auto reload restarts the clip.
    for(auto& I:P.Items)if(I.InstanceId==Id && EquippedPistol(I,P.ActiveWeaponSlot) && Revolver(I))
    {
        if(DiscardLive){I.Magazine=0;I.VirtualMagazineAmmo=0;}Cases(I,I.Magazine);return CommitState(P);
    }
    return false;
}

int32 UColdSteelStatusModel::ReloadCowboyPistol(const FString& Id,int32 Capacity)
{
    if(!CurrentPawn.IsValid() || Capacity<=0)return 0;
    const auto* Item=FindItem(Id);
    const auto* Enchants=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();
    if(!Item || !EquippedPistol(*Item,Current.ActiveWeaponSlot) || !Enchants
        || Enchants->Effect(*Item,TEXT("cowboyReload"))<=0)return 0;

    SyncRuntime();
    auto State=Snapshot();
    auto* Gun=State.Items.FindByPredicate([&](const auto& I){return I.InstanceId==Id && EquippedPistol(I,State.ActiveWeaponSlot);});
    if(!Gun)return 0;
    const FString AmmoId=AmmoDefinitionFor(*Gun);
    const int32 Missing=FMath::Max(0,Capacity-Gun->Magazine);
    // Range/training infinite reserves must not manufacture Cowboy ammunition.
    const int32 Taken=int32(FMath::Min<int64>(Missing,State.AmmoPouch.FindRef(AmmoId)));
    if(Taken<=0)return 0;
    if(!WeaponReloadStages::SetNeedsCycle(*Gun,0))return 0;
    State.AmmoPouch.FindOrAdd(AmmoId)-=Taken;
    Gun->Magazine+=Taken;
    Gun->LoadedAmmoType=AmmoId;
    // Retain unfired rounds, replace spent cases, and leave the cylinder ready.
    if(Revolver(*Gun))Cases(*Gun,Gun->Magazine);
    // Automatic enchantment reloads do not train the manual reload skill.
    if(!CommitState(MoveTemp(State)))return 0;
    if(CurrentPawn.IsValid())CurrentPawn->NotifyCowboyReload();
    return Taken;
}
