// Source/FPSGAME/WorldGeneration/TemperateVillagePlans.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 40-45 | bool ATemperateHillsWorld::UnlockVillagePlan(FName Plan,FText& FailureReason)
    {FailureReason=FText::FromString(TEXT("当前村庄尚未准备好。"));return false;}
    if(Bit==UTemperateHillsSave::ConstructionPlan)
    {
        if(IsVillagePlanUnlocked(Plan))return true;
        return CommitVillagePlanRepair(Bit,6,TEXT("村庄修建未能保存，请重试。"),FailureReason);
    }

// Lines 48-49 | bool ATemperateHillsWorld::UnlockVillagePlan(FName Plan,FText& FailureReason)
    if(Bit==1)return CompleteVillageWallRepair(FailureReason);
    if(Bit==UTemperateHillsSave::HighWallPlan)return CompleteVillageHighWallUpgrade(FailureReason);

// Lines 201-204 | void ATemperateHillsWorld::OnRep_VillagePlansUnlocked(uint8 PreviousPlans)
void ATemperateHillsWorld::OnRep_VillagePlansUnlocked(uint8 PreviousPlans)
{
    const uint8 Changed=PreviousPlans^VillagePlansUnlocked;
    if(Changed&UTemperateHillsSave::HighWallPlan)BuildVillagePerimeter();

// Lines 257-261 | bool ATemperateHillsWorld::ResetVillageUpgrades(FText& FailureReason)
    VillagePlansUnlocked=0;
    VillageDefenseGeneration=Save->VillageDefenseGeneration;
    GetWorld()->GetSubsystem<UVillageDefenseState>()->SelectGeneration(WorldId,VillageDefenseGeneration);
    // Even a ruined perimeter can have damaged or destroyed sections.
    if(!(PreviousPlans&UTemperateHillsSave::HighWallPlan))BuildVillagePerimeter();
