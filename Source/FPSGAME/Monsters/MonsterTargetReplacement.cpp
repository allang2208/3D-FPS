#include "MonsterAIController.h"
#include "MonsterTargeting.h"
#include "Perception/AIPerceptionComponent.h"
#include "Perception/AISense_Sight.h"
#include "MonsterCombatComponent.h"
#include "UnknownHumanoid.h"
#include "BlindSupplicantMonster.h"
#include "HangingBellM09.h"
#include "LurkerM08Monster.h"
#include "MantisM27Monster.h"
#include "../Dungeons/DungeonThemeEncounter.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "NavigationSystem.h"
#include "NavigationData.h"
#include "NavigationPath.h"
#include "CoreGlobals.h"

void AMonsterAIController::RememberAlternate(APawn* Player)
{
    const double Now=GetWorld()->GetTimeSeconds();
    for(auto It=AlternateEvidence.CreateIterator();It;++It)
        if(!It.Key().IsValid()||It.Value()<=Now)It.RemoveCurrent();
    AlternateEvidence.Add(Player,Now+MemorySeconds);
}

// Called only when the BT actually wants to close distance (including a
// projected endpoint that is still short of the player), not during a firing hold.
void AMonsterAIController::NotePursuitAttempt()
{
    if(!bConfirmedTarget||bReturning||!KnownTarget.IsValid()||!GetPawn())return;
    // A retreat or a peek follows a position, so closing on the opponent is not
    // a useful measure of progress. The owner monitors the actual path for stalls.
    if(const auto* Unknown=Cast<AUnknownHumanoid>(GetPawn());Unknown && Unknown->FollowingRangedPlan())
    {ProgressTarget.Reset();return;}
    const double Now=GetWorld()->GetTimeSeconds();
    if(ProgressTarget!=KnownTarget||Now-LastAttempt>.65)
    {
        ProgressTarget=KnownTarget;
        ProgressPosition=GetPawn()->GetActorLocation();
        BestDistance=FVector::Distance(ProgressPosition,KnownTarget->GetActorLocation());
        LastClosure=LastTravel=Now;
    }
    LastAttempt=Now;
}

void AMonsterAIController::CheckForStalledPursuit(double Now)
{
    if(!KnownTarget.IsValid()||ProgressTarget!=KnownTarget||Now-LastAttempt>.65)return;
    const FVector Position=GetPawn()->GetActorLocation();
    if(FVector::DistSquared(Position,ProgressPosition)>FMath::Square(50.))
    {ProgressPosition=Position;LastTravel=Now;}
    const double Distance=FVector::Distance(Position,KnownTarget->GetActorLocation());
    if(Distance<BestDistance-60.){BestDistance=Distance;LastClosure=Now;}
    const bool Stopped=Now-LastTravel>=3.;
    // A moving hunter on a long detour may switch only to an immediately usable attack.
    if((!Stopped&&Now-LastClosure<7.)||Now<NextAlternativeCheck)return;
    NextAlternativeCheck=Now+1.;
    if(GetWorld()->GetNumPlayerControllers()<2&&!bHillsPursuitRecovery&&AlternateEvidence.IsEmpty()&&
        !MonsterTargeting::IsActiveArtisan(KnownTarget.Get()))return;
    if(const auto* Mantis=Cast<AMantisM27Monster>(GetPawn());Mantis&&Mantis->bCloaked)return;
    if(CanSeePlayer(KnownTarget.Get(),false)&&Combat()->CanAttack(KnownTarget.Get()))return;
    if(APawn* Next=FindReplacement(true,!Stopped))
    {
        FailedPlayers.Add(KnownTarget,Now+12.);
        if(EncounterTarget==KnownTarget)EncounterTarget=Next;
        // Retire the previous request before committing the new goal. Aborting
        // it is not an obstacle receipt for the new player.
        PursuitRequest=FAIRequestID::InvalidRequest;StopMovement();
        FailedPursuitUntil=0.;LastMove=-100.f;bNavigationFailed=false;
        DiscoverPlayer(Next,false);
    }
}

APawn* AMonsterAIController::FindReplacement(bool Stalled,bool AttackOnly)
{
    auto* C=Combat();
    if(!HasAuthority()||!GetPawn()||!C||C->AggroRange()<=0.f)return nullptr;
    const double Now=GetWorld()->GetTimeSeconds();
    for(auto It=FailedPlayers.CreateIterator();It;++It)
        if(!It.Key().IsValid()||It.Value()<=Now)It.RemoveCurrent();
    const auto* Area=bEncounterOwnsTarget?Cast<ADungeonThemeEncounter>(EncounterArea.Get()):nullptr;
    const bool Blind=GetPawn()->IsA<ABlindSupplicantMonster>();
    const FVector Origin=GetPawn()->GetActorLocation();
    TArray<APawn*,TInlineAllocator<4>> Candidates;
    auto Consider=[&](APawn* P)
    {
        if(!IsCombatOpponent(P)||P==KnownTarget.Get()||Candidates.Contains(P)||
            (Stalled&&FailedPlayers.Contains(P))||(Area&&!Area->ContainsLocation(P->GetActorLocation())))return;
        // A remembered hit / species-qualified gunshot is real discovery evidence.
        // A silent bystander never becomes visible to M07 simply because A died.
        const double* Until=AlternateEvidence.Find(P);
        if(!(Area&&!Stalled)&&!(Until&&*Until>Now)&&(Blind||!CanSeePlayer(P,true)))return;
        Candidates.Add(P);
    };
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
    {
        auto* PC=It->Get();
        Consider(PC?PC->GetPawn().Get():nullptr);
    }
    if(!Area)
    {
        TArray<AActor*> Seen;
        Senses->GetCurrentlyPerceivedActors(UAISense_Sight::StaticClass(),Seen);
        for(AActor* Actor:Seen)
            if(auto* P=Cast<APawn>(Actor);MonsterTargeting::IsActiveArtisan(P))Consider(P);
        for(const auto& Evidence:AlternateEvidence)
            if(auto* P=Evidence.Key.Get();Evidence.Value>Now&&MonsterTargeting::IsActiveArtisan(P))Consider(P);
    }
    Candidates.Sort([&](const APawn& A,const APawn& B)
    {
        return FVector::DistSquared(Origin,A.GetActorLocation())<FVector::DistSquared(Origin,B.GetActorLocation());
    });
    if(!Stalled||Candidates.IsEmpty())return Candidates.IsEmpty()?nullptr:Candidates[0];
    for(APawn* P:Candidates)
        if(CanSeePlayer(P,false)&&C->CanAttack(P))return P;
    if(AttackOnly)return nullptr;
    if(GetPawn()->IsA<ALurkerM08Monster>()||GetPawn()->IsA<AHangingBellM09>())
    {
        // Their travel graph is made of walls/ceilings. Give the nearest sensed
        // alternative a trial on its native solver; never ask floor NavMesh to veto it.
        return Candidates[0];
    }
    // Probe one candidate per retry. Rotate even after a bad endpoint; do not
    // starve player C because nearer player B is on a disconnected balcony.
    static uint64 LastProbeFrame=MAX_uint64;
    if(LastProbeFrame==GFrameCounter)
    {
        NextAlternativeCheck=Now+WanderRandom.FRandRange(.15f,.55f);
        return nullptr;
    }
    LastProbeFrame=GFrameCounter;
    APawn* P=Candidates[AlternativeRouteCursor++%Candidates.Num()];
    auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    const auto& Agent=GetNavAgentPropertiesRef();
    const FVector Feet=GetNavAgentLocation(),Goal=P->GetNavAgentLocation();
    const auto* Data=Nav?Nav->GetNavDataForProps(Agent,Feet):nullptr;
    // Match NavigateTo: while Hills tiles register, a smaller fallback mesh
    // must not make an unreachable alternative player look like a valid route.
    if(!Data||(bHillsPursuitRecovery&&(Data->GetConfig().AgentRadius+KINDA_SMALL_NUMBER<Agent.AgentRadius
        ||Data->GetConfig().AgentHeight+KINDA_SMALL_NUMBER<Agent.AgentHeight)))return nullptr;
    FNavLocation Point;
    const float ProjectionXY=FMath::Max(100.f,Agent.AgentRadius*2.f+30.f);
    if(!Nav->ProjectPointToNavigation(Goal,Point,FVector(ProjectionXY,ProjectionXY,65.),Data)
        ||FMath::Abs(Point.Location.Z-Goal.Z)>50.||FVector::Dist2D(Goal,Point.Location)>C->StopRange())return nullptr;
    FPathFindingQuery Query(this,*Data,Feet,Point.Location,Data->GetDefaultQueryFilter());
    Query.SetAllowPartialPaths(false);
    const auto Path=Nav->FindPathSync(Agent,Query);
    return Path.IsSuccessful()&&Path.Path.IsValid()&&!Path.Path->IsPartial()?P:nullptr;
}
