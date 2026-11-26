#include "../WorldGeneration/VillageDefenseCombat.h"
#include "../WorldGeneration/VillageDefenseSection.h"
#include "MonsterAIController.h"
#include "MonsterCombatComponent.h"
#include "../WorldGeneration/ChapelShrine.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "Engine/World.h"
#include "NavigationSystem.h"

void AMonsterAIController::SetNightRaidObjective(AChapelShrine* Shrine)
{
    if(!HasAuthority())return;
    NightRaidObjective=Shrine;RaidSearchStep=uint8(GetUniqueID()%8);NextRaidSearch=0.;
    bReturning=false;UpdateKnowledge();
}

void AMonsterAIController::PublishNightRaidObjective()
{
    auto* Shrine=NightRaidObjective.Get();auto* B=GetBlackboardComponent();auto* C=Combat();
    if(!Shrine||!B||!C||!GetPawn()||C->IsDead())return;
    const bool Attackable=Shrine->CanBeSieged();
    FVector Goal=Shrine->GetNavAgentLocation();
    bool Visible=false;
    if(Attackable)
    {
        const FVector Surface=Shrine->GetRaidTargetPoint(GetPawn()->GetActorLocation());
        // Navigate within the existing attack stop range of the near surface,
        // not the inaccessible center. Keep the destination at floor height.
        Goal=FVector(Surface.X,Surface.Y,Shrine->GetNavAgentLocation().Z);
        FCollisionQueryParams Query(SCENE_QUERY_STAT(RaidShrineSight),false,GetPawn());
        Query.AddIgnoredActor(Shrine);
        FHitResult Hit;
        Visible=!GetWorld()->LineTraceSingleByChannel(Hit,GetPawn()->GetActorLocation()+FVector(0,0,35),
            Surface,ECC_Visibility,Query);
    }
    else
    {
        // Search physical waypoints around the last objective, never reveal unseen player coordinates.
        const double Now=GetWorld()->GetTimeSeconds();
        if(Now>=NextRaidSearch)
        {
            NextRaidSearch=Now+10.;
            const double Angle=double(RaidSearchStep++%8)*PI*.25;
            const FVector Desired=Goal+FVector(FMath::Cos(Angle),FMath::Sin(Angle),0)*1400.;
            FNavLocation Point;
            auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
            const auto* Data=Nav?Nav->GetNavDataForProps(GetNavAgentPropertiesRef(),GetNavAgentLocation()):nullptr;
            RaidSearchPoint=Nav&&Data&&Nav->ProjectPointToNavigation(Desired,Point,FVector(400,400,400),Data)?Point.Location:Goal;
        }
        Goal=RaidSearchPoint;
    }
    APawn* AttackTarget=Attackable?static_cast<APawn*>(Shrine):nullptr;
    if(Attackable)
    {
        const double Now=GetWorld()->GetTimeSeconds();
        if(RaidBarrier.IsValid()&&!RaidBarrier->BlocksPassage()){RaidBarrier.Reset();NextBarrierSearch=0.;}
        if(Now>=NextBarrierSearch)
        {
            NextBarrierSearch=Now+1.5;
            auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
            const auto* Data=Nav?Nav->GetNavDataForProps(GetNavAgentPropertiesRef(),GetNavAgentLocation()):nullptr;
            bool Connected=false;
            if(Nav&&Data){FPathFindingQuery Q(nullptr,*Data,GetNavAgentLocation(),Goal);Q.SetAllowPartialPaths(false);Connected=Nav->TestPathSync(Q);}
            RaidBarrier=Connected?nullptr:VillageDefenseCombat::Reachable(GetWorld(),GetNavAgentLocation(),Goal,Nav,Data,RaidBarrierApproach);
        }
        if(auto* Wall=RaidBarrier.Get())
        {
            AttackTarget=Wall;Goal=RaidBarrierApproach;
            FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(RaidWallSight),false,GetPawn());Q.AddIgnoredActor(Wall);
            Visible=!GetWorld()->LineTraceSingleByChannel(Hit,GetPawn()->GetActorLocation(),Wall->TargetPoint(GetPawn()->GetActorLocation()),ECC_Visibility,Q);
        }
    }
    C->SetTarget(AttackTarget);
    B->SetValueAsObject(TEXT("Target"),AttackTarget);
    B->SetValueAsVector(TEXT("LastKnown"),Goal);
    B->SetValueAsBool(TEXT("Returning"),false);
    B->SetValueAsBool(TEXT("Visible"),Visible);
    B->SetValueAsBool(TEXT("HasTarget"),true);
    B->SetValueAsBool(TEXT("CanAttack"),Attackable&&Visible&&C->CanAttack(AttackTarget));
    StopWander();
}
