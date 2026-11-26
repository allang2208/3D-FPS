#include "ColdSteelStatusModel.h"
#include "../Movement/StableHorseGear.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Movement/HorseRiderComponent.h"
#include "../Movement/StableRidingHorse.h"
#include "EngineUtils.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

FGuid UColdSteelStatusModel::CreditPresentMountExperience(FColdSteelProfile& State,int64 Amount) const
{
    if(Amount<=0 || !State.MountRoster.Deployed.IsValid())return {};
    const auto* Pawn=RuntimePawn();
    if(!IsValid(Pawn) || !Pawn->HasAuthority())return {};
    const auto* Ride=Pawn->FindComponentByClass<UHorseRiderComponent>();
    const auto* Horse=Ride?Ride->GetOwnedHorse():nullptr;
    if(!IsValid(Horse) || Horse->IsActorBeingDestroyed() || Horse->IsRetreating() ||
       Horse->Visit()==EStableHorseVisit::Departing || !Horse->HasActiveKeeper() ||
       Horse->Keeper()!=State.NetworkProfileId || Horse->Identity()!=State.MountRoster.Deployed)return {};
    auto* Entry=State.MountRoster.Find(Horse->Identity());
    if(!Entry || Entry->Level>=FStableHorseTraits::MaxLevel)return {};

    const int32 Previous=Entry->Level;
    const auto Vitals=Horse->Condition();
    Entry->Health=Vitals.Health;
    Entry->Stamina=Vitals.Stamina;
    Entry->bExhausted=Vitals.bExhausted;
    Entry->GainExperience(Amount);
    ++State.MountRoster.Revision;
    // The ordinary owner-only profile mirror already carries XP and this revision.
    // Only a new level needs to change the live movement and vital limits.
    return Previous!=Entry->Level?Entry->HorseId:FGuid();
}

void UColdSteelStatusModel::ApplyCommittedMountLevel(FGuid HorseId) const
{
    if(!HorseId.IsValid())return;
    const auto* Pawn=RuntimePawn();
    const auto* Ride=IsValid(Pawn)?Pawn->FindComponentByClass<UHorseRiderComponent>():nullptr;
    auto* Horse=Ride?Ride->GetOwnedHorse():nullptr;
    if(IsValid(Horse) && Horse->Identity()==HorseId && Horse->Keeper()==Current.NetworkProfileId)
        if(const auto* Entry=Current.MountRoster.Find(HorseId))Horse->ApplyEarnedLevel(*Entry);
}

bool UColdSteelStatusModel::CommitMountRoster(FStableMountRoster Roster)
{
    if(!RuntimePawn() || !RuntimePawn()->HasAuthority())return false;
    Roster.Revision=Current.MountRoster.Revision+1;
    auto Next=Snapshot();
    Next.MountRoster=MoveTemp(Roster);
    FString GuestSlot;
    if(bNetShadowProfile)
    {
        const auto* PS=RuntimePawn()->GetPlayerState<AColdSteelPlayerState>();
        if(!PS || PS->CampfireGuestSlot().IsEmpty())return false;
        GuestSlot=PS->CampfireGuestSlot();
    }
    TGuardValue<FString> SlotGuard(CampfireGuestSaveSlot,GuestSlot);
    if(!PersistState(MoveTemp(Next),false))return false;
    if(bNetShadowProfile)
        if(auto* Ride=RuntimePawn()->FindComponentByClass<UHorseRiderComponent>())
        {
            // Gear already travels atomically with its inventory receipt. This RPC carries roster changes only.
            auto Updates=Current.MountRoster;
            for(auto& Entry:Updates.Horses)Entry.Equipment.Empty();
            Ride->ClientMountRoster(Current.NetworkProfileId,Updates);
        }
    return true;
}

void UColdSteelStatusModel::ReceiveMountRoster(FGuid Profile,const FStableMountRoster& Roster)
{
    if(Profile==Current.NetworkProfileId && Roster.Revision>Current.MountRoster.Revision)
    {
        auto Next=Roster;
        StableHorseGear::CopyEquipment(Next,Current.MountRoster);
        Current.MountRoster=MoveTemp(Next);
    }
}

void UColdSteelStatusModel::StageMountCondition(const FStableMountRecord& Horse)
{
    if(auto* Previous=Current.MountRoster.Find(Horse.HorseId))
    {
        // Movement samples must not shorten an escape cooldown or erase progress made in the journal.
        Previous->Health=Horse.Health;Previous->Stamina=Horse.Stamina;Previous->bExhausted=Horse.bExhausted;
        Previous->RecallAfterUtc=FMath::Max(Previous->RecallAfterUtc,Horse.RecallAfterUtc);
    }
}

bool UColdSteelStatusModel::GiveMountPotion(FGuid HorseId,const FString& ItemId,FString& Reason)
{
    auto* Pawn=RuntimePawn();
    if(!Pawn||!Pawn->HasAuthority())return false;
    auto P=Snapshot();
    auto* Horse=P.MountRoster.Find(HorseId);
    if(!Horse){Reason=TEXT("马匹不在当前角色的马匹栏");return false;}
    AStableRidingHorse* Live=nullptr;
    for(TActorIterator<AStableRidingHorse> It(Pawn->GetWorld());It;++It)
    {
        if(It->Identity()!=HorseId||It->Keeper()!=P.NetworkProfileId||!It->HasActiveKeeper()||It->IsRetreating())continue;
        Live=*It;break;
    }
    const float Health=Live?Live->GetHealth():Horse->Health;
    if(Health>=Horse->MaxHealth){Reason=TEXT("马匹生命已满");return false;}
    const int32 I=P.Items.IndexOfByPredicate([&](const auto& Item){return Item.InstanceId==ItemId;});
    if(!P.Items.IsValidIndex(I)){Reason=TEXT("药水已用完");return false;}
    auto& Item=P.Items[I];
    if((Item.Place!=0&&Item.Place!=ColdSteelInventory::ColdSteelCompartment::Place)||Item.Count<1||Item.Cooldown>0.f||
        !(Item.Definition==TEXT("hp_potion")||Item.Definition.StartsWith(TEXT("hp_potion_"))))
    {Reason=TEXT("请选择随身携带的可用生命药水");return false;}
    const auto* Def=Definitions.Find(Item.Definition);
    TSharedPtr<FJsonObject> Json;
    const TSharedPtr<FJsonObject>* Effect=nullptr;
    if(!Def||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(*Def),Json)||!Json||
        !Json->TryGetObjectField(TEXT("useEffect"),Effect)){Reason=TEXT("生命药水没有治疗配置");return false;}
    double Flat=0.,Percent=0.;(*Effect)->TryGetNumberField(TEXT("hp"),Flat);(*Effect)->TryGetNumberField(TEXT("maxHpPercent"),Percent);
    const float Restored=FMath::Min(Horse->MaxHealth-Health,float(Flat+.01*Percent*Horse->MaxHealth));
    if(Restored<=0.f){Reason=TEXT("药水当前无法使用");return false;}
    Horse->Health=Health+Restored;
    const float After=Horse->Health;
    if(--Item.Count==0)P.Items.RemoveAt(I);
    ++P.MountRoster.Revision;
    const auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>();
    const FString Slot=bNetShadowProfile&&PS?PS->CampfireGuestSlot():FString();
    if(!CommitCampfireState(MoveTemp(P),TEXT("MountPotion"),Slot))
    {Reason=ResultMessage();return false;}
    if(Live)Live->ApplyPotionHealth(After);
    Reason=FString::Printf(TEXT("马匹恢复 %.0f 点生命"),Restored);
    return true;
}
