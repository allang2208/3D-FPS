// Source/FPSGAME/FPSGAMEPlayerController.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 29-30 | file scope
#include "WorldGeneration/VillageDefenseSection.h"
#include "Monsters/FPSCombatHealthComponent.h"

// Lines 561-567 | bool AFPSGAMEPlayerController::InputKey(const FInputKeyEventArgs& Params)
            const auto Focus=ColdSteelWorldInteraction::TraceUseTargets(this);
            auto* Target=Focus.Target;
            if(auto* Section=Cast<AVillageDefenseSection>(Target); Section && Section->GetHealth()<=0.f)
            {
                RequestVillageRepair(Section);
                return true;
            }

// Lines 782-856 | bool AFPSGAMEPlayerController::IsInBuildMode() const
bool AFPSGAMEPlayerController::IsInBuildMode() const
{
    return VoxelBuilder && VoxelBuilder->IsBuilding();
}

void AFPSGAMEPlayerController::RequestVillageRepair(AVillageDefenseSection* Section)
{
    APawn* Payer=GetPawn();
    if (!IsValid(Section) || Section->GetHealth()>0.f || !Payer || bShowMouseCursor || BlocksOngoingActions(this)) return;
    auto* RepairCharacter=Cast<AFPSGAMECharacter>(Payer);
    if (RepairCharacter && RepairCharacter->IsAmmoWheelOpen()) return;
    const auto* Health=Payer->FindComponentByClass<UFPSCombatHealthComponent>();
    if (Health && Health->IsDead()) return;
    if (VillageRepairPawn.Get()!=Payer)
    {
        PendingVillageRepairs.Reset();
        RecentlyRepairedSection.Reset();
        VillageRepairPawn=Payer;
    }
    if (PendingVillageRepairs.FindKey(Section) ||
        (RecentlyRepairedSection.Get()==Section && FPlatformTime::Seconds()<RepairedSectionRetryTime)) return;
    // The prompt's cached enemy sample can lag the server when a hostile dies or moves away.
    if (RepairCharacter && !Section->HasNearbyRepairEnemy(Payer)) RepairCharacter->InterruptWeaponInspection();
    const uint32 RequestId=++VillageRepairRequestId;
    PendingVillageRepairs.Add(RequestId,Section);
    ServerRepairVillageDefense(Section,Payer,RequestId);
}

void AFPSGAMEPlayerController::ServerRepairVillageDefense_Implementation(AVillageDefenseSection* Section,APawn* RequestPawn,uint32 RequestId)
{
    APawn* Payer=GetPawn();
    if (!IsValid(Section) || !IsValid(Payer) || Payer!=RequestPawn || Section->GetWorld()!=GetWorld() || BlocksOngoingActions(this))
    {
        ClientVillageRepairResult(RequestId,false,FText::GetEmpty());
        return;
    }
    if (const auto* Health=Payer->FindComponentByClass<UFPSCombatHealthComponent>(); Health && Health->IsDead())
    {
        ClientVillageRepairResult(RequestId,false,FText::GetEmpty());
        return;
    }
    if (Section->GetHealth()>0.f)
    {
        // Another player or an earlier request may have repaired it before replication arrived.
        ClientVillageRepairResult(RequestId,false,FText::GetEmpty());
        return;
    }
    if (ColdSteelWorldInteraction::TraceUseTargets(this).Target!=Section)
    {
        ClientVillageRepairResult(RequestId,false,FText::FromString(TEXT("请靠近并对准尚未修复的缺口。")));
        return;
    }
    FText Reason;
    const bool bRepaired=Section->TryRepair(Payer,Reason);
    if (bRepaired)
        Reason=FText::Format(NSLOCTEXT("VillageDefense","RepairPaid","已消耗 {0} 灵魂。"),FText::AsNumber(Section->GetRepairSoulCost()));
    ClientVillageRepairResult(RequestId,bRepaired,Reason);
}

void AFPSGAMEPlayerController::ClientVillageRepairResult_Implementation(uint32 RequestId,bool bRepaired,const FText& Message)
{
    TWeakObjectPtr<AVillageDefenseSection> Section;
    if (!PendingVillageRepairs.RemoveAndCopyValue(RequestId,Section) || !Section.IsValid() ||
        Section->GetWorld()!=GetWorld() || !VillageRepairPawn.IsValid() || VillageRepairPawn.Get()!=GetPawn()) return;
    if (bRepaired && Section->GetHealth()<=0.f)
    {
        // The receipt can beat health replication. A fresh collapse can also coalesce with that update.
        RecentlyRepairedSection=Section;
        RepairedSectionRetryTime=FPlatformTime::Seconds()+0.75;
    }
    if (Message.IsEmpty()) return;
    if(auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        Model->PostNotice(bRepaired?TEXT("城防已修复"):TEXT("无法修复"),Message.ToString());
}
