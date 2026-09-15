#include "ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Engine/GameInstance.h"

namespace
{
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
    if(auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>())if(const auto* W=G->Weapon(Item.Definition))return W->Ammo;
    return FString();
}
int32 UColdSteelStatusModel::AmmoCountFor(const FColdSteelItem& Item) const
{
    const FString Def=AmmoDefinitionFor(Item);int64 Total=0;
    for(const auto& I:Current.Items)if(I.Place==0 && I.Definition==Def)Total+=I.Count;
    return int32(FMath::Min<int64>(Total,MAX_int32));
}
int32 UColdSteelStatusModel::ReloadDualPistol(const FString& Id,int32 Requested,int32 Capacity,bool Completed)
{
    if(!CurrentPawn.IsValid() || Requested<=0)return 0;
    SyncRuntime();auto P=Snapshot();auto* Gun=P.Items.FindByPredicate([&](const auto& I){return I.InstanceId==Id && EquippedPistol(I,P.ActiveWeaponSlot);});
    if(!Gun)return 0;
    const FString Def=AmmoDefinitionFor(*Gun);Requested=FMath::Clamp(Requested,0,Capacity-Gun->Magazine);
    int32 Left=CurrentPawn->HasInfiniteReserveAmmo()?0:Requested;
    for(auto& I:P.Items)if(I.Place==0 && I.Definition==Def){const int32 N=int32(FMath::Min<int64>(Left,I.Count));I.Count-=N;Left-=N;}
    const int32 Taken=Requested-Left;if(Taken<=0)return 0;
    Gun->Magazine+=Taken;
    if(Gun->Definition==TEXT("ue_dan_wesson715"))Cases(*Gun,FMath::Max(Gun->Magazine,int32(ColdSteelInventory::Number(*Gun,TEXT("revolver_case_count"),0))));
    P.Items.RemoveAll([](const auto& I){return I.Count<=0;});
    if(Completed)ColdSteelSkills::AddExperience(P,DexterousHandsSkill,DexterousHandsSkill.ReloadExperience);
    return CommitState(P)?Taken:0;
}
bool UColdSteelStatusModel::EjectDualPistolCases(const FString& Id,bool DiscardLive)
{
    if(!CurrentPawn.IsValid())return false;
    SyncRuntime();auto P=Snapshot();
    for(auto& I:P.Items)if(I.InstanceId==Id && EquippedPistol(I,P.ActiveWeaponSlot) && I.Definition==TEXT("ue_dan_wesson715"))
    {
        if(DiscardLive)I.Magazine=0;Cases(I,I.Magazine);return CommitState(P);
    }
    return false;
}
