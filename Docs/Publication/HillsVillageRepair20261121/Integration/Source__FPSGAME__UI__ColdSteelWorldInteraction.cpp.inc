// Source/FPSGAME/UI/ColdSteelWorldInteraction.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 2-5 | file scope
#include "../WorldGeneration/VillageDefenseSection.h"
#include "../WorldGeneration/VillageDefenseStairs.h"
#include "../WorldGeneration/HighVillageDefense.h"
#include "../WorldGeneration/VillageDefenseRepairTargets.h"

// Lines 77-77 | ColdSteelWorldInteraction::FUseTargets ColdSteelWorldInteraction::TraceUseTargets(const APlayerController* PC,float Reach,bool bFindNearbyBreach)
ColdSteelWorldInteraction::FUseTargets ColdSteelWorldInteraction::TraceUseTargets(const APlayerController* PC,float Reach,bool bFindNearbyBreach)

// Lines 101-103 | ColdSteelWorldInteraction::FUseTargets ColdSteelWorldInteraction::TraceUseTargets(const APlayerController* PC,float Reach,bool bFindNearbyBreach)
            Found.Target=Target;
            ClearReach=FMath::Min(ClearReach,Hit.Distance);
            break;

// Lines 107-109 | ColdSteelWorldInteraction::FUseTargets ColdSteelWorldInteraction::TraceUseTargets(const APlayerController* PC,float Reach,bool bFindNearbyBreach)
            // A standing portal or placed timber pier can still block this ray.
            // The breach trace below selects only the missing parts in front of it.
            if(const auto* Defense=Cast<AVillageDefenseSection>(Target); Defense && Defense->GetHealth()<=0.f)break;

// Lines 121-125 | ColdSteelWorldInteraction::FUseTargets ColdSteelWorldInteraction::TraceUseTargets(const APlayerController* PC,float Reach,bool bFindNearbyBreach)
    if (auto* Repair = PC->GetWorld()->GetSubsystem<UVillageDefenseRepairTargets>())
        if (auto* Breach = Repair->Trace(*PC->GetPawn(),Eye,Eye+View.Vector()*ClearReach,
                bFindNearbyBreach ? &Found.NearbyBreach : nullptr))
            Found.Target=Breach;
    return Found;

// Lines 417-417 | ColdSteelWorldInteraction::FInteractionHint ColdSteelWorldInteraction::ResolveInteractionHint(const AActor* Target,APawn* Viewer)
ColdSteelWorldInteraction::FInteractionHint ColdSteelWorldInteraction::ResolveInteractionHint(const AActor* Target,APawn* Viewer)

// Lines 423-438 | ColdSteelWorldInteraction::FInteractionHint ColdSteelWorldInteraction::ResolveInteractionHint(const AActor* Target,APawn* Viewer)
    if(const auto* Section=Cast<AVillageDefenseSection>(Target); Section && Section->GetHealth()<=0.f)
    {
        Hint.Title=Section->IsA<AHighVillageGate>()?TEXT("升降铁闸"):
            Section->IsA<AHighVillageWall>()?TEXT("石砌高墙"):Section->IsA<AVillageDefenseStairs>()?TEXT("城墙石阶"):
            Section->IsA<AVillageDefenseGate>()?TEXT("村门"):TEXT("围墙");
        if(Section->HasNearbyRepairEnemy(Viewer))
        {
            Hint.Text=TEXT("附近有敌方单位，无法修复");
            Hint.bAction=false;
            return Hint;
        }
        Hint.Text=FString::Printf(TEXT("修复 · %d 灵魂"),Section->GetRepairSoulCost());
        return Hint;
    }
    if(Target->IsA<AHighVillageGate>()){Hint.Title=TEXT("升降铁闸");Hint.Text=TEXT("开／关");return Hint;}
    if(Target->IsA<AVillageDefenseGate>()){Hint.Title=TEXT("村门");Hint.Text=TEXT("开／关");return Hint;}
