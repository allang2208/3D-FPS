#include "TemperateHillsWorld.h"
#include "HillsCarpenterWorkshop.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

namespace
{
uint8 VillagePlanBit(FName Plan)
{
    if(Plan==TEXT("wall"))return 1;
    if(Plan==TEXT("blacksmith"))return 2;
    if(Plan==TEXT("carpenter"))return UTemperateHillsSave::CarpenterPlan;
    if(Plan==TEXT("tavern"))return UTemperateHillsSave::TavernPlan;
    return 0;
}
}
bool ATemperateHillsWorld::IsVillagePlanUnlocked(FName Plan) const
{
    const uint8 Bit=VillagePlanBit(Plan);
    return (VillagePlansUnlocked&Bit)!=0||(Bit==1&&bVillageWallRepaired)||(Bit==2&&bVillageBlacksmithRepaired);
}
bool ATemperateHillsWorld::UnlockVillagePlan(FName Plan,FText& FailureReason)
{
    const uint8 Bit=VillagePlanBit(Plan);FailureReason=FText::GetEmpty();
    if(!HasAuthority()||!Bit||Slot.IsEmpty()||!WorldId.IsValid()||!VillageSite.bPlaced)
    {FailureReason=FText::FromString(TEXT("当前村庄尚未准备好。"));return false;}
    // Unlock and repair share one durable commit. A legacy plan-only unlock must
    // still execute the replacement, rather than returning success early.
    if(Bit==1)return CompleteVillageWallRepair(FailureReason);
    if(Bit==2)return CompleteVillageBlacksmithRepair(FailureReason);
    if(Bit==UTemperateHillsSave::CarpenterPlan)return CompleteVillageCarpenterRepair(FailureReason);
    if(IsTavernRepaired())return true;
    if(!TavernAreaOccupied.IsBound())
    {
        FailureReason=FText::FromString(TEXT("酒馆还未准备好，请稍后重试。"));
        return false;
    }
    if(TavernAreaOccupied.Execute())
    {
        FailureReason=FText::FromString(TEXT("请让人员和动物离开酒馆，再完成修复。"));
        return false;
    }
    return CommitVillagePlanRepair(Bit,4,TEXT("酒馆修复未能保存，请重试。"),FailureReason);
}

bool ATemperateHillsWorld::CommitVillagePlanRepair(uint8 PlanBit,int32 RequiredVersion,const TCHAR* SaveError,FText& FailureReason)
{
    auto* Save=Cast<UTemperateHillsSave>(UGameplayStatics::LoadGameFromSlot(Slot,0));
    if(!Save||Save->WorldId!=WorldId||Save->Seed!=Seed||Save->Version>6||
        Save->VillagePlanVersion>UTemperateHillsSave::CurrentVillagePlanVersion)
    {
        FailureReason=FText::FromString(TEXT("无法读取当前丘陵的村庄存档。"));
        return false;
    }
    Save->Version=6;
    Save->VillagePlansUnlocked=Save->SavedVillagePlans()|PlanBit;
    Save->VillagePlanVersion=FMath::Max(RequiredVersion,Save->VillagePlanVersion);
    if(!UGameplayStatics::SaveGameToSlot(Save,Slot,0))
    {
        FailureReason=FText::FromString(SaveError);
        return false;
    }
    const uint8 PreviousPlans=VillagePlansUnlocked;
    VillagePlansUnlocked=Save->VillagePlansUnlocked;
    OnRep_VillagePlansUnlocked(PreviousPlans);
    ForceNetUpdate();
    return true;
}

void ATemperateHillsWorld::OnRep_VillagePlansUnlocked(uint8 PreviousPlans)
{
    const uint8 Changed=PreviousPlans^VillagePlansUnlocked;
    if(Changed&UTemperateHillsSave::CarpenterPlan)
        for(TActorIterator<AHillsCarpenterWorkshop> It(GetWorld());It;++It)It->ApplyVillageState();
    if(Changed&UTemperateHillsSave::TavernPlan)
        OnTavernRepairChanged.Broadcast();
}
