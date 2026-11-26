#include "VillageNetworkAudit.h"
#include "../FPSGAMECharacter.h"
#include "../Movement/FPSTraversalComponent.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../WorldGeneration/VillageDefenseSection.h"
#include "../WorldGeneration/ChapelShrine.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/MonsterAIController.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "NavigationSystem.h"
#include "NavigationData.h"

bool AVillageNetworkAudit::StartClimb()
{
    auto* C=Cast<AFPSGAMECharacter>(Guest->GetPawn());auto* T=C->FindComponentByClass<UFPSTraversalComponent>();
    const auto& V=Hills->GetVillageSite();int32 Tried=0;FString Reason;
    for(TActorIterator<AVillageDefenseSection> It(GetWorld());It;++It)
    {
        if(It->IsA<AVillageDefenseGate>()||It->GetHealth()<=0||!It->GetMasonry()->GetStaticMesh())continue;
        if(It->GetMasonry()->GetStaticMesh()->GetBoundingBox().GetSize().X<150.)continue;
        FVector Outward=It->GetActorRightVector();
        if(FVector::DotProduct(Outward,It->GetActorLocation()-V.Ground)<0)Outward*=-1.;
        const FVector Surface=It->TargetPoint(It->GetActorLocation()+Outward*500.+FVector(0,0,95));
        FVector P=Surface+Outward*(C->GetCapsuleComponent()->GetScaledCapsuleRadius()+5.);
        const float Ground=Hills->Height(P.X,P.Y);P.Z=Ground+C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+42.;
        VillageNetAudit::Place(Guest.Get(),P,P-Outward*100.);
        C->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
        const auto Probe=T->FindTarget(true,true);Reason=Probe.Reason;++Tried;
        if(Probe.Action==EFPSTraversalAction::None||Probe.Action==EFPSTraversalAction::Step)continue;
        Wall=*It;P.Z=Ground+C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.;
        Peer->Position=P;Peer->Aim=P-Outward*100.;
        VillageNetAudit::Place(Guest.Get(),P,Peer->Aim,true);
        RequestsAtStart=T->NetworkRequest;Guest->SetIgnoreMoveInput(true);
        Record(TEXT("real_village_wall_air_target"),true,FString::Printf(TEXT("section=%d probe_height=%.1f attempts=%d"),It->GetSectionId(),Probe.Probe.Height,Tried));
        Send(70,Wall.Get());return true;
    }
    Record(TEXT("real_village_wall_air_target"),false,FString::Printf(TEXT("attempts=%d last=%s"),Tried,*Reason));return false;
}
bool AVillageNetworkAudit::StartRaid()
{
    AChapelShrine* Shrine=nullptr;for(TActorIterator<AChapelShrine> It(GetWorld());It;++It){Shrine=*It;break;}
    auto* Class=LoadClass<ANurseZombie>(nullptr,TEXT("/Game/Monsters/NurseZombie/BP_NurseZombie.BP_NurseZombie_C"));
    if(!Shrine||!Class||!Wall.IsValid()){Record(TEXT("siege_fixture_ready"),false);return false;}
    Shrine->SetRaidNight(true,1800.f);
    FVector Outward=Wall->GetActorRightVector();
    if(FVector::DotProduct(Outward,Wall->GetActorLocation()-Hills->GetVillageSite().Ground)<0)Outward*=-1.;
    FVector P=Wall->TargetPoint(Wall->GetActorLocation()+Outward*500.+FVector(0,0,95))+Outward*350.;
    P.Z=Hills->Height(P.X,P.Y)+94.;RaidStart=P;
    const FTransform Transform((-Outward).Rotation(),P);
    auto* N=GetWorld()->SpawnActorDeferred<ANurseZombie>(Class,Transform,nullptr,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    if(!N){Record(TEXT("siege_monster_spawn"),false);return false;}
    // Speed up the endurance fixture without bypassing AI, pathfinding, attack
    // selection, authored contact time, collision or replicated damage.
    N->AttackDamage=400.f;N->Tags.Add(TEXT("HillsNightRaider"));N->AggroRadius=1200.f;
    N->FinishSpawning(Transform);Raider=N;
    auto* AI=Cast<AMonsterAIController>(N->GetController());
    Record(TEXT("siege_live_controller"),AI!=nullptr,TEXT("actual nurse blueprint; damage=400 for bounded duration; no manual TryAttack or damage calls"));
    if(!AI)return false;
    AI->SetNightRaidObjective(Shrine);AI->SetEncounterArea(Shrine);
    UNavigationSystemV1::RegisterNavigationInvoker(*N,6000,7500);
    return true;
}
FString AVillageNetworkAudit::RaidStatus() const
{
    auto* N=Raider.Get();auto* AI=N?Cast<AMonsterAIController>(N->GetController()):nullptr;
    if(!AI)return TEXT("missing raider/controller");
    auto* B=AI->GetBlackboardComponent();auto* C=AI->Combat();
    auto* T=B?Cast<APawn>(B->GetValueAsObject(TEXT("Target"))):nullptr;
    auto* W=Cast<AVillageDefenseSection>(T);
    const FVector Goal=B?B->GetValueAsVector(TEXT("LastKnown")):FVector::ZeroVector;
    auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    const auto* Data=Nav?Nav->GetNavDataForProps(AI->GetNavAgentPropertiesRef(),AI->GetNavAgentLocation()):nullptr;
    return FString::Printf(TEXT("pos=%s travel=%.1f action=%s target=%s wall_distance=%.1f goal_distance=%.1f visible=%d hold=%d can_attack=%d nav=%s requests=%d failed=%d velocity=%.1f"),
        *N->GetActorLocation().ToCompactString(),FVector::Dist2D(RaidStart,N->GetActorLocation()),*AI->ActiveAction,*GetNameSafe(T),
        W?FVector::Dist2D(N->GetActorLocation(),W->TargetPoint(N->GetActorLocation())):-1.,FVector::Dist2D(N->GetActorLocation(),Goal),
        B&&B->GetValueAsBool(TEXT("Visible")),B&&B->GetValueAsBool(TEXT("Hold")),C&&C->CanAttack(T),*GetNameSafe(Data),AI->NavigationRequests,AI->bNavigationFailed,N->GetVelocity().Size());
}
