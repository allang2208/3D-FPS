#include "TemperateHillsWorld.h"
#include "../Building/VillageBuildDefense.h"
#include "../Building/VoxelBuildWorld.h"
#include "VillageDefenseState.h"
#include "HillsCarpenterWorkshop.h"
#include "HillsHerbalistWorkshop.h"
#include "HillsWindmill.h"
#include "HillsVillageShopSite.h"
#include "../NPC/VillageBaker.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

namespace
{
uint16 VillagePlanBit(FName Plan)
{
    if(Plan==TEXT("wall"))return 1;
    if(Plan==TEXT("blacksmith"))return 2;
    if(Plan==TEXT("carpenter"))return UTemperateHillsSave::CarpenterPlan;
    if(Plan==TEXT("tavern"))return UTemperateHillsSave::TavernPlan;
    if(Plan==TEXT("herbalist"))return UTemperateHillsSave::HerbalistPlan;
    if(Plan==TEXT("windmill"))return UTemperateHillsSave::WindmillPlan;
    if(Plan==VillageBuildDefense::MechanicsPlan)return UTemperateHillsSave::GarrisonMechanicsPlan;
    if(Plan==TEXT("bakery"))return UTemperateHillsSave::BakeryPlan;
    if(Plan==TEXT("gunshop"))return UTemperateHillsSave::GunshopPlan;
    if(Plan==TEXT("village_construction"))return UTemperateHillsSave::ConstructionPlan;
    if(Plan==TEXT("high_wall"))return UTemperateHillsSave::HighWallPlan;
    return 0;
}
}
bool ATemperateHillsWorld::IsVillagePlanUnlocked(FName Plan) const
{
    const uint16 Bit=VillagePlanBit(Plan);
    // Older worlds may own the former all-recipes plan before rebuilding their perimeter.
    // Keep that purchase on disk and activate it as soon as the high wall is complete.
    if(Bit==UTemperateHillsSave::ConstructionPlan)return HasVillageHighWall()&&(VillagePlansUnlocked&Bit)!=0;
    if(Bit==UTemperateHillsSave::GarrisonMechanicsPlan)return bGarrisonMechanics && IsVillagePlanUnlocked(TEXT("village_construction"));
    if(Bit==UTemperateHillsSave::BakeryPlan)return IsBakeryRepaired();
    if(Bit==UTemperateHillsSave::GunshopPlan)return IsGunshopRepaired();
    return (VillagePlansUnlocked&Bit)!=0||(Bit==1&&bVillageWallRepaired)||(Bit==2&&bVillageBlacksmithRepaired);
}
bool ATemperateHillsWorld::UnlockVillagePlan(FName Plan,FText& FailureReason)
{
    const uint16 Bit=VillagePlanBit(Plan);FailureReason=FText::GetEmpty();
    if(!HasAuthority()||!Bit||Slot.IsEmpty()||!WorldId.IsValid()||!VillageSite.bPlaced)
    {FailureReason=FText::FromString(TEXT("当前村庄尚未准备好。"));return false;}
    if(Bit==UTemperateHillsSave::ConstructionPlan)
    {
        if(!HasVillageHighWall())
        {
            FailureReason=FText::FromString(TEXT("请先完成「升级高墙」，再解锁防御工事。"));
            return false;
        }
        if(IsVillagePlanUnlocked(Plan))return true;
        return CommitVillagePlanRepair(Bit,6,TEXT("防御工事未能保存，请重试。"),FailureReason);
    }
    if(Bit==UTemperateHillsSave::GarrisonMechanicsPlan)
    {
        if(!IsVillagePlanUnlocked(TEXT("village_construction")))
        {FailureReason=FText::FromString(TEXT("请先完成「防御工事」。"));return false;}
        if(bGarrisonMechanics)return true;
        if(!VillageSite.bPlaced || MechanicalWorkshopLotOccupied())
        {FailureReason=FText::FromString(TEXT("请先清空东门马厩对面的机械工坊用地。"));return false;}
        return CommitVillagePlanRepair(Bit,11,TEXT("守备机械未能保存，请重试。"),FailureReason);
    }
    // Unlock and repair share one durable commit. A legacy plan-only unlock must
    // still execute the replacement, rather than returning success early.
    if(Bit==1)return CompleteVillageWallRepair(FailureReason);
    if(Bit==UTemperateHillsSave::HighWallPlan)return CompleteVillageHighWallUpgrade(FailureReason);
    if(Bit==2)return CompleteVillageBlacksmithRepair(FailureReason);
    if(Bit==UTemperateHillsSave::CarpenterPlan)return CompleteVillageCarpenterRepair(FailureReason);
    if(Bit==UTemperateHillsSave::HerbalistPlan)
    {
        if(IsHerbalistRepaired())return true;
        TActorIterator<AHillsHerbalistWorkshop> Shop(GetWorld());
        if(!Shop)
        {
            FailureReason=FText::FromString(TEXT("草药铺还未准备好，请稍后重试。"));
            return false;
        }
        if(!Shop->CanRepair(FailureReason))return false;
        return CommitVillagePlanRepair(Bit,5,TEXT("草药铺修复未能保存，请重试。"),FailureReason);
    }

    if(Bit==UTemperateHillsSave::WindmillPlan)
    {
        if(IsWindmillRepaired())return true;
        const AHillsWindmill* Windmill=StreamedWindmill.Get();
        if(!Windmill)
        {
            FailureReason=FText::FromString(TEXT("风车尚未载入，请稍后重试。"));
            return false;
        }
        if(Windmill->IsRepairFootprintOccupied())
        {
            FailureReason=FText::FromString(TEXT("请让人员和动物离开风车施工区域，再完成修复。"));
            return false;
        }
        return CommitVillagePlanRepair(Bit,8,TEXT("风车修复未能保存，请重试。"),FailureReason);
    }
    if(Bit==UTemperateHillsSave::BakeryPlan)
    {
        if(IsBakeryRepaired())return true;
        if(!IsWindmillRepaired())
        {
            FailureReason=FText::FromString(TEXT("请先修复风车磨坊，再修复面包屋。"));
            return false;
        }
        const AActor* Shop=StreamedBakery.Get();
        if(!Shop)
        {
            FailureReason=FText::FromString(TEXT("面包屋尚未载入，请稍后重试。"));
            return false;
        }
        if(HillsVillageShopSite::IsOccupied(*Shop,HillsVillageShopSite::Bakery))
        {
            FailureReason=FText::FromString(TEXT("请让人员和动物离开面包屋施工区域，再完成修复。"));
            return false;
        }
        return CommitVillagePlanRepair(Bit,9,TEXT("面包屋修复未能保存，请重试。"),FailureReason);
    }
    if(Bit==UTemperateHillsSave::GunshopPlan)
    {
        if(IsGunshopRepaired())return true;
        if(!IsVillageBlacksmithRepaired())
        {
            FailureReason=FText::FromString(TEXT("请先重建铁匠铺，再修复枪店。"));
            return false;
        }
        const AActor* Shop=StreamedGunshop.Get();
        if(!Shop)
        {
            FailureReason=FText::FromString(TEXT("枪店尚未载入，请稍后重试。"));
            return false;
        }
        if(HillsVillageShopSite::IsOccupied(*Shop,HillsVillageShopSite::Gunshop))
        {
            FailureReason=FText::FromString(TEXT("请让人员和动物离开南侧长屋，再完成修复。"));
            return false;
        }
        return CommitVillagePlanRepair(Bit,10,TEXT("枪店修复未能保存，请重试。"),FailureReason);
    }
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

bool ATemperateHillsWorld::CommitVillagePlanRepair(uint16 PlanBit,int32 RequiredVersion,const TCHAR* SaveError,FText& FailureReason)
{
    auto* Save=Cast<UTemperateHillsSave>(UGameplayStatics::LoadGameFromSlot(Slot,0));
    if(!Save||Save->WorldId!=WorldId||Save->Seed!=Seed||Save->Version>6||
        Save->VillagePlanVersion>UTemperateHillsSave::CurrentVillagePlanVersion)
    {
        FailureReason=FText::FromString(TEXT("无法读取当前丘陵的村庄存档。"));
        return false;
    }
    Save->Version=6;
    Save->VillagePlansUnlocked=Save->SavedVillagePlans()|static_cast<uint8>(PlanBit);
    if(PlanBit==UTemperateHillsSave::BakeryPlan)Save->bVillageBakeryRepaired=true;
    if(PlanBit==UTemperateHillsSave::GunshopPlan)Save->bVillageGunshopRepaired=true;
    if(PlanBit==UTemperateHillsSave::GarrisonMechanicsPlan)Save->bGarrisonMechanics=true;
    Save->VillagePlanVersion=FMath::Max(RequiredVersion,Save->VillagePlanVersion);
    if(!UGameplayStatics::SaveGameToSlot(Save,Slot,0))
    {
        FailureReason=FText::FromString(SaveError);
        return false;
    }
    const uint8 PreviousPlans=VillagePlansUnlocked;
    VillagePlansUnlocked=Save->VillagePlansUnlocked;
    OnRep_VillagePlansUnlocked(PreviousPlans);
    if(bVillageBakeryRepaired!=Save->bVillageBakeryRepaired)
    {
        bVillageBakeryRepaired=Save->bVillageBakeryRepaired;
        OnRep_VillageBakery();
    }
    if(bGarrisonMechanics!=Save->bGarrisonMechanics)
    {
        bGarrisonMechanics=Save->bGarrisonMechanics;
        UpdateMechanicalWorkshop();
    }
    if(bVillageGunshopRepaired!=Save->bVillageGunshopRepaired)
    {
        bVillageGunshopRepaired=Save->bVillageGunshopRepaired;
        OnRep_VillageGunshop();
    }
    ForceNetUpdate();
    return true;
}

void ATemperateHillsWorld::OnRep_VillageBakery()
{
    AActor* Site = StreamedBakery.Get();
    if (Site) HillsVillageShopSite::Apply(*Site, HillsVillageShopSite::Bakery, bVillageBakeryRepaired);
    if (!HasAuthority()) return;

    if (AVillageBaker* Baker = BakeryResident.Get())
    {
        if (Site && bVillageBakeryRepaired && Baker->GetLevel() == Site->GetLevel()) return;
        Baker->Destroy();
        BakeryResident.Reset();
    }
    if (!Site || !bVillageBakeryRepaired) return;

    FActorSpawnParameters Spawn;
    Spawn.Owner = this;
    Spawn.OverrideLevel = Site->GetLevel();
    Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    BakeryResident = GetWorld()->SpawnActor<AVillageBaker>(AVillageBaker::StaticClass(),
        AVillageBaker::GetStandingTransform(*Site), Spawn);
}

void ATemperateHillsWorld::OnRep_VillageGunshop()
{
    if (AActor* Site=StreamedGunshop.Get())
        HillsVillageShopSite::Apply(*Site,HillsVillageShopSite::Gunshop,bVillageGunshopRepaired);
}

void ATemperateHillsWorld::OnRep_VillagePlansUnlocked(uint8 PreviousPlans)
{
    const uint8 Changed=PreviousPlans^VillagePlansUnlocked;
    if(Changed&UTemperateHillsSave::HighWallPlan)BuildVillagePerimeter();
    if(HasAuthority() && (Changed&(UTemperateHillsSave::HighWallPlan|UTemperateHillsSave::ConstructionPlan)))
        for(TActorIterator<AVoxelBuildWorld> It(GetWorld());It;++It)It->TryGrantWorkshopTower();
    if(Changed&UTemperateHillsSave::CarpenterPlan)
        for(TActorIterator<AHillsCarpenterWorkshop> It(GetWorld());It;++It)It->ApplyVillageState();
    if(Changed&UTemperateHillsSave::TavernPlan)
    {
        OnTavernRepairChanged.Broadcast();
        RefreshVillageStreetLighting();
    }
    if(Changed&UTemperateHillsSave::HerbalistPlan)
        for(TActorIterator<AHillsHerbalistWorkshop> It(GetWorld());It;++It)It->ApplyVillageState();
    if(Changed&UTemperateHillsSave::WindmillPlan)
        if(AHillsWindmill* Windmill=StreamedWindmill.Get())Windmill->ApplyRepairState(IsWindmillRepaired());
}

bool ATemperateHillsWorld::ResetVillageUpgrades(FText& FailureReason)
{
    FailureReason=FText::GetEmpty();
    if(!HasAuthority()||Slot.IsEmpty()||!WorldId.IsValid())
    {
        FailureReason=FText::FromString(TEXT("当前丘陵世界尚未准备好重置村庄。"));
        return false;
    }
    auto* Save=Cast<UTemperateHillsSave>(UGameplayStatics::LoadGameFromSlot(Slot,0));
    if(!Save||Save->WorldId!=WorldId||Save->Seed!=Seed||Save->Version>6||
        Save->VillagePlanVersion>UTemperateHillsSave::CurrentVillagePlanVersion)
    {
        FailureReason=FText::FromString(TEXT("无法读取当前丘陵的村庄存档。"));
        return false;
    }
    Save->bVillageWallRepaired=false;
    Save->bVillageBlacksmithRepaired=false;
    Save->bVillageBakeryRepaired=false;
    Save->bVillageGunshopRepaired=false;
    Save->bGarrisonMechanics=false;
    Save->VillagePlansUnlocked=0;
    Save->VillagePlanVersion=UTemperateHillsSave::CurrentVillagePlanVersion;
    Save->VillageDefenseGeneration=FGuid::NewGuid();
    if(!UGameplayStatics::SaveGameToSlot(Save,Slot,0))
    {
        FailureReason=FText::FromString(TEXT("村庄重置未能保存，请重试。"));
        return false;
    }

    const uint8 PreviousPlans=VillagePlansUnlocked;
    const bool HadBlacksmith=bVillageBlacksmithRepaired;
    bVillageWallRepaired=false;
    bVillageBlacksmithRepaired=false;
    if(bVillageBakeryRepaired)
    {
        bVillageBakeryRepaired=false;
        OnRep_VillageBakery();
    }
    if(bVillageGunshopRepaired)
    {
        bVillageGunshopRepaired=false;
        OnRep_VillageGunshop();
    }
    bGarrisonMechanics=false;
    UpdateMechanicalWorkshop();
    VillagePlansUnlocked=0;
    VillageDefenseGeneration=Save->VillageDefenseGeneration;
    SiegeRanks=GetWorld()->GetSubsystem<UVillageDefenseState>()->SelectGeneration(WorldId,VillageDefenseGeneration);
    // Even a ruined perimeter can have damaged or destroyed sections.
    if(!(PreviousPlans&UTemperateHillsSave::HighWallPlan))BuildVillagePerimeter();
    if(HadBlacksmith)OnRep_VillageBlacksmith();
    OnRep_VillagePlansUnlocked(PreviousPlans);
    ForceNetUpdate();
    return true;
}
