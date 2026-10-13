#include "MonsterAIController.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "MonsterNavigationCache.h"
#include "BoundCongregate.h"
#include "BellowSacLobber.h"
#include "MantisM27Monster.h"
#include "MonsterCombatComponent.h"
#include "../Skills/IceWallCombat.h"
#include "MonsterBTNodes.h"
#include "Mutant3.h"
#include "WolfMonster.h"
#include "BlindSupplicantMonster.h"
#include "HangingBellM09.h"
#include "VortexCofferM25.h"
#include "LurkerM08Monster.h"
#include "FPSCombatHealthComponent.h"
#include "../Dungeons/DungeonThemeEncounter.h"
#include "BehaviorTree/BehaviorTree.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "BehaviorTree/BlackboardData.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Bool.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Object.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Vector.h"
#include "BehaviorTree/Composites/BTComposite_Selector.h"
#include "Perception/AIPerceptionComponent.h"
#include "Perception/AISenseConfig_Sight.h"
#include "Perception/AISenseConfig_Hearing.h"
#include "Perception/AISenseConfig_Damage.h"
#include "Perception/AISense_Sight.h"
#include "Navigation/PathFollowingComponent.h"
#include "NavigationSystem.h"
#include "NavigationData.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "BrainComponent.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#if WITH_EDITOR
#include "Builders/CubeBuilder.h"
#include "Model.h"
#include "Engine/Polys.h"
#include "Components/BrushComponent.h"
#endif
AMonsterAIController::AMonsterAIController()
{
 Senses=CreateDefaultSubobject<UAIPerceptionComponent>(TEXT("MonsterPerception"));SetPerceptionComponent(*Senses);
 auto* Sight=CreateDefaultSubobject<UAISenseConfig_Sight>(TEXT("Sight"));Sight->SightRadius=1600;Sight->LoseSightRadius=1900;Sight->PeripheralVisionAngleDegrees=100;Sight->SetMaxAge(12);
 Sight->DetectionByAffiliation=FAISenseAffiliationFilter(true,true,false);
 auto* Hearing=CreateDefaultSubobject<UAISenseConfig_Hearing>(TEXT("Hearing"));Hearing->HearingRange=1800;Hearing->SetMaxAge(8);Hearing->DetectionByAffiliation=FAISenseAffiliationFilter(true,true,true);
 auto* Damage=CreateDefaultSubobject<UAISenseConfig_Damage>(TEXT("DamageSense"));Damage->SetMaxAge(12);
 Senses->ConfigureSense(*Sight);Senses->ConfigureSense(*Hearing);Senses->ConfigureSense(*Damage);Senses->SetDominantSense(Sight->GetSenseImplementation());
 Senses->OnTargetPerceptionUpdated.AddDynamic(this,&AMonsterAIController::Perceived);
}
ETeamAttitude::Type AMonsterAIController::GetTeamAttitudeTowards(const AActor& Other) const
{
 // Perceived/UpdateKnowledge only consume players. Reject fellow monsters
 // before native sight allocates observer-target queries for the whole crowd.
 // The combat component exists before possession; no global team IDs change.
 const auto* TargetPawn=Cast<APawn>(&Other);
 if(TargetPawn&&!TargetPawn->IsPlayerControlled()&&TargetPawn->FindComponentByClass<UMonsterCombatComponent>())
  return ETeamAttitude::Friendly;
 return Super::GetTeamAttitudeTowards(Other);
}
UMonsterCombatComponent* AMonsterAIController::Combat() const{return GetPawn()?GetPawn()->FindComponentByClass<UMonsterCombatComponent>():nullptr;}
void AMonsterAIController::OnPossess(APawn* P)
{
 Super::OnPossess(P);if(!HasAuthority())return;
 WanderRandom.Initialize(FMath::Rand());bWanderActive=bWanderMoving=false;WanderFailures=0;
 KnownTarget.Reset();EncounterTarget.Reset();EncounterArea.Reset();PendingDamageTarget.Reset();
 bConfirmedTarget=bPendingGroupAlert=bReturning=false;PassiveDiscoveryAt=-1.f;LastEvidence=-100.f;
 NextBroadcast=0.f;
 NextWanderUpdate=0.f;NextWanderMove=GetWorld()->GetTimeSeconds()+WanderRandom.FRandRange(.5f,3.f);
 const bool OmniSight=P->IsA<ALurkerM08Monster>()||P->IsA<AVortexCofferM25>();
 if(P->IsA<ALurkerM08Monster>())MemorySeconds=FMath::Max(MemorySeconds,30.f);
 auto* Sight=NewObject<UAISenseConfig_Sight>(this);
 // The monster's AggroRadius is the one active discovery range, including BP
 // overrides. Do not silently cap long-range species at the old default 16 m.
 Sight->SightRadius=Combat()?FMath::Max(0.f,Combat()->AggroRange()):1600.f;
 Sight->LoseSightRadius=Sight->SightRadius+(OmniSight?500.f:300.f);
 Sight->PeripheralVisionAngleDegrees=OmniSight?180.f:100.f;Sight->SetMaxAge(MemorySeconds);
 Sight->DetectionByAffiliation=FAISenseAffiliationFilter(true,true,false);
 Senses->ConfigureSense(*Sight);
 if(const auto* Bellow=Cast<ABellowSacLobber>(P);Bellow&&Bellow->bSoundSensitive)
 {
  auto* Hearing=NewObject<UAISenseConfig_Hearing>(this);
  Hearing->HearingRange=FMath::Max(0.f,Bellow->HearingRadius);Hearing->SetMaxAge(8.f);
  Hearing->DetectionByAffiliation=FAISenseAffiliationFilter(true,true,true);
  Senses->ConfigureSense(*Hearing);
 }
 Senses->RequestStimuliListenerUpdate();
 if(Behavior){RunBehaviorTree(Behavior);UpdateKnowledge();UE_LOG(LogTemp,Display,TEXT("MONSTER_BT_READY %s tree=%s"),*P->GetName(),*Behavior->GetPathName());}
 else UE_LOG(LogTemp,Error,TEXT("MONSTER_BT_MISSING %s"),*P->GetName());
}
void AMonsterAIController::OnUnPossess(){StopWander();StopMovement();if(BrainComponent)BrainComponent->StopLogic(TEXT("Unpossessed"));KnownTarget.Reset();EncounterTarget.Reset();EncounterArea.Reset();PendingDamageTarget.Reset();bPendingGroupAlert=false;PassiveDiscoveryAt=-1.f;Super::OnUnPossess();}
void AMonsterAIController::SetDecisionEnabled(bool Enabled){bDecisionEnabled=Enabled;if(!Enabled){StopWander();StopMovement();}UpdateKnowledge();}
void AMonsterAIController::SetEncounterTarget(APawn* P)
{
 EncounterTarget=P;bReturning=false;
 if(IsValid(P)){DiscoverPlayer(P,false);UpdateKnowledge();}
}
void AMonsterAIController::UpdateKnowledge()
{
 TRACE_CPUPROFILER_EVENT_SCOPE(MonsterAI_UpdateKnowledge);
 auto* C=Combat();auto* B=GetBlackboardComponent();if(!C||!B||!GetPawn())return;
 const bool Disabled=!bDecisionEnabled||!GetPawn()->IsActorTickEnabled();
 if(!Disabled)ConsumePassiveDiscovery();
 const bool HadTarget=B->GetValueAsBool(TEXT("HasTarget"));
 const bool ReactingToHit=PendingDamageTarget.IsValid();
 if(Disabled||C->IsBusy()||ReactingToHit)StopWander();
 const auto* Canine=Cast<AWolfMonster>(GetPawn());
 const auto* M07=Cast<ABlindSupplicantMonster>(GetPawn());
 const auto* M08=Cast<ALurkerM08Monster>(GetPawn());
 const auto* M09=Cast<AHangingBellM09>(GetPawn());
 const auto* M25=Cast<AVortexCofferM25>(GetPawn());
 const auto* M27=Cast<AMantisM27Monster>(GetPawn());
 const bool FeralPursuit=M27||GetPawn()->IsA<AMutant3>()||(Canine&&Canine->bUsePredictiveHunting);
 B->SetValueAsBool(TEXT("Hold"),Disabled||C->IsBusy()||ReactingToHit);
 if(C->IsDead()){PendingDamageTarget.Reset();bPendingGroupAlert=false;StopMovement();if(BrainComponent)BrainComponent->StopLogic(TEXT("Dead"));ActiveAction=TEXT("Dead");return;}
 if(EncounterTarget.IsValid())KnownTarget=EncounterTarget;
 // Perception updates report changes, not every visible frame. Reacquire from
 // its sight cache after a home/target reset without requiring a second event.
 if(!ReactingToHit&&!KnownTarget.IsValid()&&(!bReturning||FeralPursuit)&&C->AggroRange()>0)
 {
  TArray<AActor*> Seen;Senses->GetCurrentlyPerceivedActors(UAISense_Sight::StaticClass(),Seen);
  float Best=FMath::Square(C->AggroRange());
  for(auto* Actor:Seen)if(auto* P=Cast<APawn>(Actor))if(P->IsPlayerControlled())
  {
   auto* Health=P->FindComponentByClass<UFPSCombatHealthComponent>();
   const float D=FVector::DistSquared(P->GetActorLocation(),GetPawn()->GetActorLocation());
   if((!Health||!Health->IsDead())&&D<Best&&CanSeePlayer(P,true)){Best=D;DiscoverPlayer(P,true);}
  }
  // Sight perception samples the target center. M07 can acquire an exposed
  // upper body over low cover through the same segment used to select spells.
  // M25 also actively acquires visible players all around its back electrodes.
  // Reuse the existing 10 Hz knowledge service and enumerate only players.
  if((M07||M08||M25)&&!KnownTarget.IsValid())
  {
   const auto* Sight=Senses->GetSenseConfig<UAISenseConfig_Sight>();
   const float ConeCos=(M08||M25)?-1.f:FMath::Cos(FMath::DegreesToRadians(Sight?Sight->PeripheralVisionAngleDegrees:100.f));
   for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
   {
    const auto* PC=It->Get();APawn* P=PC?PC->GetPawn().Get():nullptr;
    if(!IsValid(P)||!P->IsPlayerControlled())continue;
    const auto* Health=P->FindComponentByClass<UFPSCombatHealthComponent>();
    const FVector Delta=P->GetActorLocation()-GetPawn()->GetActorLocation();
    const float D=Delta.SizeSquared();
    if((Health&&Health->IsDead())||D>=Best||
       FVector::DotProduct(GetPawn()->GetActorForwardVector().GetSafeNormal2D(),Delta.GetSafeNormal2D())<ConeCos||
       !(M08?M08->HasHuntingSight(P):M25?LineOfSightTo(P):M07->HasMagicSight(P)))continue;
    Best=D;DiscoverPlayer(P,true);
   }
  }
 }
 bool Valid=KnownTarget.IsValid();
 if(Valid){auto* H=KnownTarget->FindComponentByClass<UFPSCombatHealthComponent>();Valid=!H||!H->IsDead();}
 const float Now=GetWorld()->GetTimeSeconds();
 // Detection and retention are different distances. Once this hunter knows
 // a target, honor perception's lose-sight radius instead of expiring memory
 // just because the player stepped outside the initial 12 m aggro radius.
 bool Visible=!ReactingToHit&&Valid&&CanSeePlayer(KnownTarget.Get(),!bConfirmedTarget);
 if(Visible&&!bConfirmedTarget)DiscoverPlayer(KnownTarget.Get(),true);
 // Preserve explicit encounter locks for their existing callers. Hall area
 // membership alone never supplies a target or refreshes its memory.
 const bool Locked=Valid&&EncounterTarget.IsValid()&&KnownTarget==EncounterTarget;
 // Alerted monsters share a live target lock for the existing memory window.
 // Occlusion stops attacks, but does not immediately erase the pursuit target.
 if(Valid&&(bConfirmedTarget||Locked))LastKnown=KnownTarget->GetNavAgentLocation();
 if(Visible||Locked){LastEvidence=Now;EvidenceLifetime=MemorySeconds;}
 if(!Valid||C->AggroRange()<=0||Now-LastEvidence>EvidenceLifetime){KnownTarget.Reset();Valid=Visible=bConfirmedTarget=false;bPendingGroupAlert=false;}
 // A feral hunter keeps a living target while it is seen or remembered. The
 // shared 24 m home leash used to override sight, then reacquire the same
 // player at home forever. Other monsters retain their configured home leash.
 if(Valid&&FeralPursuit)bReturning=false;
 // The two halls share a large combat area. A confirmed chase inside this
 // area must not hit the ordinary 24 m home leash halfway across the hall.
 else if(const auto* Area=Cast<ADungeonThemeEncounter>(EncounterArea.Get());
     Valid&&bConfirmedTarget&&Area&&Area->ContainsLocation(LastKnown)&&
     Area->ContainsLocation(GetPawn()->GetActorLocation()))bReturning=false;
 else if(FVector::Dist2D(GetPawn()->GetActorLocation(),C->Home())>C->LeashRange())bReturning=true;
 const FVector HomeFeet=M08?M08->HomeSupportLocation():C->Home()-(GetPawn()->GetActorLocation()-GetPawn()->GetNavAgentLocation());
 // Losing a remembered enemy returns home; an unaware wanderer may move away
 // from home without the old 80 cm idle check cancelling every stroll.
 if(!Valid&&HadTarget&&!PendingDamageTarget.IsValid()&&(FVector::Dist2D(GetPawn()->GetNavAgentLocation(),HomeFeet)>80||FMath::Abs(GetPawn()->GetNavAgentLocation().Z-HomeFeet.Z)>50))bReturning=true;
 if(bReturning&&FVector::Dist2D(GetPawn()->GetNavAgentLocation(),HomeFeet)<80&&FMath::Abs(GetPawn()->GetNavAgentLocation().Z-HomeFeet.Z)<50){bReturning=false;KnownTarget.Reset();Valid=false;C->ReachedHome();LastEvidence=-100;}
 C->SetTarget(Valid&&bConfirmedTarget&&!bReturning?KnownTarget.Get():nullptr);
 if(Valid||bReturning)StopWander();
 if(!Disabled&&Valid&&bConfirmedTarget&&!bReturning)
  if(auto* EncounterMantis=Cast<AMantisM27Monster>(GetPawn()))EncounterMantis->NotifyCloakEncounter(KnownTarget.Get());
 B->SetValueAsObject(TEXT("Target"),Valid?KnownTarget.Get():nullptr);
 B->SetValueAsVector(TEXT("LastKnown"),LastKnown);B->SetValueAsVector(TEXT("Home"),HomeFeet);
 B->SetValueAsBool(TEXT("Visible"),Visible);B->SetValueAsBool(TEXT("Returning"),bReturning);
 const bool WallInWay=Valid&&bConfirmedTarget&&!Visible&&IceWallCombat::BlockingWall(GetPawn(),KnownTarget.Get(),C->AggroRange());
 B->SetValueAsBool(TEXT("CanAttack"),!bReturning&&(Visible||WallInWay)&&C->CanAttack(KnownTarget.Get()));
 B->SetValueAsBool(TEXT("HasTarget"),Valid&&!bReturning);
 if(!Disabled&&Valid&&!bReturning&&bPendingGroupAlert)BroadcastGroupAlert();
}
void AMonsterAIController::NavigateTo(FVector Destination,float Acceptance)
{
 TRACE_CPUPROFILER_EVENT_SCOPE(MonsterAI_NavigateAttempt);
 const float Now=GetWorld()->GetTimeSeconds();if(Now-LastMove<.65f)return;
 if(GetMoveStatus()==EPathFollowingStatus::Moving&&FVector::DistSquared(Destination,LastDestination)<FMath::Square(45.f))return;
 TRACE_CPUPROFILER_EVENT_SCOPE(MonsterAI_NavigateAdmitted);
 LastMove=Now;LastDestination=Destination;++NavigationRequests;
 auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
 const auto& Agent=GetNavAgentPropertiesRef();
 const auto* Data=Nav?Nav->GetNavDataForProps(Agent,GetNavAgentLocation()):nullptr;
 FNavLocation Goal;
 // Player capsules can stand nearer the railing than the boss's 62 cm radius.
 // Search laterally for its walkable interior, with a short vertical window so
 // a missing upper-floor polygon cannot silently select the ground floor.
 const float XY=FMath::Max(100.f,Agent.AgentRadius*2.f+30.f);
 if(!Data||!GetWorld()->GetSubsystem<UMonsterNavigationCache>()->Project(Nav,Data,Destination,FVector(XY,XY,100),Goal))
 {
  bNavigationFailed=true;
  UE_LOG(LogTemp,Warning,TEXT("MONSTER_NAV_FAILED %s reason=goal_projection feet=%s nav=%s"),*GetNameSafe(GetPawn()),*Destination.ToString(),*GetNameSafe(Data));
  return;
 }
 EPathFollowingRequestResult::Type Result;
 {
  TRACE_CPUPROFILER_EVENT_SCOPE(MonsterAI_MoveToLocation);
  Result=MoveToLocation(Goal.Location,Acceptance,false,true,false,false,nullptr,false);
 }
 bNavigationFailed=Result==EPathFollowingRequestResult::Failed;
 if(bNavigationFailed)UE_LOG(LogTemp,Warning,TEXT("MONSTER_NAV_FAILED %s reason=path start=%s goal=%s nav=%s"),*GetNameSafe(GetPawn()),*GetNavAgentLocation().ToString(),*Goal.Location.ToString(),*GetNameSafe(Data));
}
bool AMonsterAIController::BuildTree(UBehaviorTree* Tree)
{
 if(!Tree)return false;
 auto* Data=NewObject<UBlackboardData>(Tree,TEXT("MonsterKnowledge"));Tree->BlackboardAsset=Data;
 for(FName Name:{TEXT("Hold"),TEXT("Returning"),TEXT("CanAttack"),TEXT("HasTarget"),TEXT("Visible")}){FBlackboardEntry E;E.EntryName=Name;E.KeyType=NewObject<UBlackboardKeyType_Bool>(Data);Data->Keys.Add(E);}
 for(FName Name:{TEXT("LastKnown"),TEXT("Home")}){FBlackboardEntry E;E.EntryName=Name;E.KeyType=NewObject<UBlackboardKeyType_Vector>(Data);Data->Keys.Add(E);}
 FBlackboardEntry Target;Target.EntryName=TEXT("Target");auto* Object=NewObject<UBlackboardKeyType_Object>(Data);Object->BaseClass=APawn::StaticClass();Target.KeyType=Object;Data->Keys.Add(Target);
 auto* Root=NewObject<UBTComposite_Selector>(Tree,TEXT("PrioritySelector"));Root->NodeName=TEXT("Monster priorities");Tree->RootNode=Root;
 auto* Service=NewObject<UBTService_MonsterKnowledge>(Tree);Root->Services.Add(Service);
 const FName Keys[]={TEXT("Hold"),TEXT("Returning"),TEXT("CanAttack"),TEXT("HasTarget"),NAME_None};
 for(int32 I=0;I<5;++I)
 {
  FBTCompositeChild Child;auto* Task=NewObject<UBTTask_MonsterAction>(Tree);Task->Action=EMonsterAction(I);Task->NodeName=I==0?TEXT("Wait for combat / control"):I==1?TEXT("Return home"):I==2?TEXT("Execute attack"):I==3?TEXT("Pursue / investigate"):TEXT("Idle");Child.ChildTask=Task;
  if(!Keys[I].IsNone()){auto* Condition=NewObject<UBTDecorator_MonsterFlag>(Tree);Condition->Configure(Keys[I]);Child.Decorators.Add(Condition);}
  Root->Children.Add(Child);
 }
 Tree->MarkPackageDirty();return true;
}
bool AMonsterAIController::BuildNavigationBounds(UObject* Context,FVector Center,FVector Extent)
{
#if WITH_EDITOR
 UWorld* World=GEngine->GetWorldFromContextObject(Context,EGetWorldErrorMode::ReturnNull);if(!World)return false;
 ANavMeshBoundsVolume* Volume=nullptr;for(TActorIterator<ANavMeshBoundsVolume> It(World);It;++It)if(It->ActorHasTag(TEXT("MonsterNavigation")))Volume=*It;
 if(!Volume)Volume=World->SpawnActor<ANavMeshBoundsVolume>();if(!Volume)return false;
 Volume->Tags.AddUnique(TEXT("MonsterNavigation"));Volume->SetActorLabel(TEXT("MonsterNavigation"));
 if(!Volume->Brush){Volume->Brush=NewObject<UModel>(Volume,NAME_None,RF_Transactional);Volume->Brush->Initialize(Volume,false);Volume->Brush->Polys=NewObject<UPolys>(Volume->Brush,NAME_None,RF_Transactional);Volume->GetBrushComponent()->Brush=Volume->Brush;}
 auto* Cube=NewObject<UCubeBuilder>(Volume);Cube->X=Extent.X*2;Cube->Y=Extent.Y*2;Cube->Z=Extent.Z*2;if(!Cube->Build(World,Volume))return false;
 Volume->GetBrushComponent()->BuildSimpleBrushCollision();Volume->SetActorLocation(Center);Volume->ReregisterAllComponents();Volume->MarkPackageDirty();
 if(!FNavigationSystem::GetCurrent<UNavigationSystemV1>(World))FNavigationSystem::AddNavigationSystemToWorld(*World,FNavigationSystemRunMode::EditorMode);
 if(auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(World)){Nav->OnNavigationBoundsUpdated(Volume);Nav->Build();return true;}return false;
#else
 return false;
#endif
}
