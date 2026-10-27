#include "FoodSpoilage.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "Engine/World.h"

FFoodClockSample UColdSteelStatusModel::FoodClockSnapshot() const
{return {Current.FoodClockId,Current.FoodClockDay};}

void UColdSteelStatusModel::ObserveFoodClock(const FFoodClockSample& Sample)
{
    if(!Sample.Id.IsValid()||!FMath::IsFinite(Sample.Day)||Sample.Day<0.)return;
    if(GetWorld()&&GetWorld()->GetNetMode()==NM_Client)
    {
        // Owner-only time samples update presentation, never client item ages.
        // A delayed full profile may arrive behind this lightweight sample.
        Current.FoodClockDay=Current.FoodClockId==Sample.Id?FMath::Max(Current.FoodClockDay,Sample.Day):Sample.Day;
        Current.FoodClockId=Sample.Id;Current.FoodVersion=1;return;
    }
    if(ColdSteelFood::RebaseProfile(Current,Sample))bTrainingDirty=true;
}
double UColdSteelStatusModel::FoodRemainingDays(const FColdSteelItem& Item) const
{
    const auto Now=ColdSteelFood::Clock(this);
    return FMath::Max(0.,ColdSteelFood::LifetimeDays(Item)-ColdSteelFood::AgeDays(Item,Now));
}
bool UColdSteelStatusModel::SettleFoodSpoilage(bool Force)
{
    UWorld* W=GetWorld();
    if(!W||W->bIsTearingDown||W->GetNetMode()==NM_Client||bSettlingFood||bStagingNetworkContainer
        ||bCampfireInventoryPending||bTransactionSaveUnconfirmed)return false;
    const double Time=W->GetTimeSeconds();if(!Force&&Time<NextFoodSettlement)return true;
    NextFoodSettlement=Time+1.;TGuardValue<bool> Guard(bSettlingFood,true);
    const auto Now=ColdSteelFood::Clock(this);if(!Now.Id.IsValid())return false;
    const bool Migration=Current.FoodVersion!=1||Current.FoodClockId!=Now.Id||Current.FoodClockDay>Now.Day||Current.Items.ContainsByPredicate([&](const auto& I)
    {return !I.Container.StartsWith(TEXT("NetView."))&&ColdSteelFood::LifetimeDays(I)>0.
        &&(I.FoodVersion==0||I.FoodClockId!=Now.Id);});
    if(!Migration&&!Current.Items.ContainsByPredicate([&](const auto& I)
        {return !I.Container.StartsWith(TEXT("NetView."))&&ColdSteelFood::IsExpired(I,Now);}))
    {ObserveFoodClock(Now);return true;}
    auto P=Snapshot();
    ColdSteelFood::RebaseProfile(P,Now);
    const bool Expired=P.Items.ContainsByPredicate([&](const auto& I)
    {return !I.Container.StartsWith(TEXT("NetView."))&&ColdSteelFood::IsExpired(I,Now);});
    FString Reason;ColdSteelFood::SettleGrid(P.Items,this,Now,Reason);
    if(!Reason.IsEmpty()){Message=Reason;return false;}
    if(!Migration&&!Expired){ObserveFoodClock(Now);return true;}
    if(P.CampfireInventoryRevision==MAX_int64){Message=TEXT("库存版本达到上限，食物结算暂停");return false;}
    ++P.CampfireInventoryRevision;P.CampfireWorldReceipts.FindOrAdd(TEXT("FoodSpoilage"))=P.CampfireInventoryRevision;
    const auto* Pawn=RuntimePawn();const auto* PS=Pawn?Pawn->GetPlayerState<AColdSteelPlayerState>():nullptr;
    const FString GuestSlot=bNetShadowProfile&&PS?PS->CampfireGuestSlot():FString();
    if(bNetShadowProfile&&GuestSlot.IsEmpty())return false;
    bool Saved=false;
    {
        TGuardValue<FString> SlotGuard(CampfireGuestSaveSlot,GuestSlot);
        TGuardValue<bool> TransactionGuard(bSavingTransaction,true);
        // Food aging never re-equips weapons or interrupts unrelated hand actions.
        Saved=PersistState(MoveTemp(P),false);
    }
    if(Saved&&Expired)RefreshDrops();
    return Saved;
}
