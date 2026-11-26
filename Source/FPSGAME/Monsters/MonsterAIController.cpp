#include "MonsterAIController.h"
#include "MonsterTargeting.h"
#include "../WorldGeneration/VillageDefenseCombat.h"
#include "WildlifeSubsystem.h"
#include "../WorldGeneration/ChapelShrine.h"
#include "UnknownHumanoid.h"
#include "HeQueMonster.h"
#include "RootCrownRigPreview.h"
#include "M66IncineratorMonster.h"
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
#include "WitchMonster.h"
#include "PoisonMaggotMonster.h"
#include "SpiralPillarM14.h"
#include "M10Mawcrawler.h"
#include "HundredEyedSlagMonster.h"
#include "HandBrainMonster.h"
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
 // Defenses are explicit path obstacles, not 150 additional perception targets.
 if(Other.ActorHasTag(TEXT("VillageDefense")))return ETeamAttitude::Friendly;
 // Native sight keeps artisan sources subscribed across knockdown and rescue.
 // Live status is checked when acquiring, retaining or damaging a target.
 const auto* TargetPawn=Cast<APawn>(&Other);
 if(TargetPawn && (Other.ActorHasTag(TEXT("VillageBlacksmith")) || Other.ActorHasTag(TEXT("VillageCarpenter"))))
  return CanHuntArtisans()?ETeamAttitude::Hostile:ETeamAttitude::Friendly;
 // Reject fellow monsters before native sight allocates queries for the crowd.
 // The combat component exists before possession; no global team IDs change.
 if(TargetPawn&&!TargetPawn->IsPlayerControlled()&&TargetPawn->FindComponentByClass<UMonsterCombatComponent>())
  return ETeamAttitude::Friendly;
 return Super::GetTeamAttitudeTowards(Other);
}
bool AMonsterAIController::CanHuntArtisans() const
{
 const APawn* Hunter=GetPawn();
 return Hunter&&!Hunter->ActorHasTag(TEXT("Friendly"))&&!Hunter->ActorHasTag(TEXT("Wildlife"));
}
bool AMonsterAIController::IsCombatOpponent(const APawn* Candidate) const
{
 return MonsterTargeting::IsLivingOpponent(Candidate)&&(Candidate->IsPlayerControlled()||CanHuntArtisans());
}
UMonsterCombatComponent* AMonsterAIController::Combat() const{return GetPawn()?GetPawn()->FindComponentByClass<UMonsterCombatComponent>():nullptr;}
void AMonsterAIController::OnPossess(APawn* P)
{
 Super::OnPossess(P);if(!HasAuthority())return;
 PursuitRequest=FAIRequestID::InvalidRequest;FailedPursuitUntil=0.;LastPursuitAcceptance=-1.f;
 LastMove=-100.f;bNavigationFailed=false;ApproachSearchOffset=0;
 bHillsPursuitRecovery=UWildlifeSubsystem::IsWildlifeMap(GetWorld());
 PursuitProgressPosition=P->GetActorLocation();PursuitProgressTime=GetWorld()->GetTimeSeconds();
 // Wildlife wolves can spawn 82 m away while the player only invokes 60 m.
 // M08 also uses optional floor corridors to guide its physical surface search.
 // Only the ceiling-only solver has no use for ground navigation tiles.
 bHillsPawnInvoker=bHillsPursuitRecovery&&!P->IsA<AHangingBellM09>();
 if(bHillsPawnInvoker)UNavigationSystemV1::RegisterNavigationInvoker(*P,5000.f,6500.f);
 WanderRandom.Initialize(FMath::Rand());bWanderActive=bWanderMoving=false;WanderFailures=0;
 KnownTarget.Reset();EncounterTarget.Reset();EncounterArea.Reset();PendingDamageTarget.Reset();NightRaidObjective.Reset();
 AlternateEvidence.Reset();FailedPlayers.Reset();ProgressTarget.Reset();LastAttempt=-100.;NextAlternativeCheck=0.;AlternativeRouteCursor=0;
 bAwaitingReplacement=bEncounterOwnsTarget=false;
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
 // 盲祷者目盲：视觉半径归零，发现完全依赖听觉与受击。
 if(P->IsA<ABlindSupplicantMonster>()){Sight->SightRadius=0.f;Sight->LoseSightRadius=0.f;}
 Senses->ConfigureSense(*Sight);
 if(const auto* Wolf=Cast<AWolfMonster>(P); Wolf && Wolf->IsWildlifeWolf())
 {
  auto* Hearing=NewObject<UAISenseConfig_Hearing>(this);
  Hearing->HearingRange=3600.f; Hearing->SetMaxAge(2.f);
  Hearing->DetectionByAffiliation=FAISenseAffiliationFilter(true,true,true);
  Senses->ConfigureSense(*Hearing);
 }
 if(const auto* Bellow=Cast<ABellowSacLobber>(P);Bellow&&Bellow->bSoundSensitive)
 {
  auto* Hearing=NewObject<UAISenseConfig_Hearing>(this);
  Hearing->HearingRange=FMath::Max(0.f,Bellow->HearingRadius);Hearing->SetMaxAge(8.f);
  Hearing->DetectionByAffiliation=FAISenseAffiliationFilter(true,true,true);
  Senses->ConfigureSense(*Hearing);
 }
 if(const auto* Mantis=Cast<AMantisM27Monster>(P))
 {
  auto* Hearing=NewObject<UAISenseConfig_Hearing>(this);
  Hearing->HearingRange=FMath::Max(0.f,Mantis->GunshotHearingRadius);Hearing->SetMaxAge(8.f);
  Hearing->DetectionByAffiliation=FAISenseAffiliationFilter(true,true,true);
  Senses->ConfigureSense(*Hearing);
  MemorySeconds=FMath::Max(MemorySeconds,30.f);
 }
 if(const auto* M07=Cast<ABlindSupplicantMonster>(P))
 {
  auto* Hearing=NewObject<UAISenseConfig_Hearing>(this);
  Hearing->HearingRange=FMath::Max(0.f,M07->HearingRadius);Hearing->SetMaxAge(8.f);
  Hearing->DetectionByAffiliation=FAISenseAffiliationFilter(true,true,true);
  Senses->ConfigureSense(*Hearing);
  MemorySeconds=FMath::Max(MemorySeconds,30.f);
 }
 Senses->RequestStimuliListenerUpdate();
 if(Behavior){RunBehaviorTree(Behavior);UpdateKnowledge();UE_LOG(LogTemp,Display,TEXT("MONSTER_BT_READY %s tree=%s"),*P->GetName(),*Behavior->GetPathName());}
 else UE_LOG(LogTemp,Error,TEXT("MONSTER_BT_MISSING %s"),*P->GetName());
}
void AMonsterAIController::OnUnPossess()
{
 if(bHillsPawnInvoker&&GetPawn())UNavigationSystemV1::UnregisterNavigationInvoker(*GetPawn());
 bHillsPawnInvoker=false;
 StopWander();StopMovement();if(BrainComponent)BrainComponent->StopLogic(TEXT("Unpossessed"));
 KnownTarget.Reset();EncounterTarget.Reset();EncounterArea.Reset();PendingDamageTarget.Reset();
 bPendingGroupAlert=false;PassiveDiscoveryAt=-1.f;Super::OnUnPossess();
}
void AMonsterAIController::SetDecisionEnabled(bool Enabled)
{
 bDecisionEnabled=Enabled;
 if(!Enabled)
 {
  StopWander();StopMovement();
  if(auto* HeQue=Cast<AHeQueMonster>(GetPawn()))HeQue->CancelAttack();
  if(auto* M66=Cast<AM66IncineratorMonster>(GetPawn()))M66->CancelAttack();
 }
 UpdateKnowledge();
}
void AMonsterAIController::SetEncounterTarget(APawn* P)
{
 if(!HasAuthority())return;
 EncounterTarget=IsCombatOpponent(P)&&P->IsPlayerControlled()?P:nullptr;
 bEncounterOwnsTarget=EncounterTarget.IsValid();
 UpdateKnowledge();
}
void AMonsterAIController::UpdateKnowledge()
{
 TRACE_CPUPROFILER_EVENT_SCOPE(MonsterAI_UpdateKnowledge);
 auto* C=Combat();auto* B=GetBlackboardComponent();if(!C||!B||!GetPawn())return;
 const bool Disabled=!bDecisionEnabled||!GetPawn()->IsActorTickEnabled();
 if(!Disabled)ConsumePassiveDiscovery();
 const bool HadTarget=B->GetValueAsBool(TEXT("HasTarget"))&&(KnownTarget.IsValid()||!NightRaidObjective.IsValid());
 const bool ReactingToHit=PendingDamageTarget.IsValid();
 const bool Busy=C->IsBusy();
 if(Disabled||Busy||ReactingToHit){ProgressTarget.Reset();StopWander();}
 const auto* Canine=Cast<AWolfMonster>(GetPawn());
 const auto* M07=Cast<ABlindSupplicantMonster>(GetPawn());
 const auto* M08=Cast<ALurkerM08Monster>(GetPawn());
 const auto* M09=Cast<AHangingBellM09>(GetPawn());
 const auto* M25=Cast<AVortexCofferM25>(GetPawn());
 const auto* M27=Cast<AMantisM27Monster>(GetPawn());
 const bool FeralPursuit=M27||GetPawn()->IsA<AMutant3>()||(Canine&&Canine->bUsePredictiveHunting);
 auto* TacticalHumanoid=Cast<AUnknownHumanoid>(GetPawn());
 if(!TacticalHumanoid)B->SetValueAsBool(TEXT("Hold"),Disabled||Busy||ReactingToHit);
 if(Canine && Canine->State==EWolfState::Flee) return;
 if(C->IsDead()){PendingDamageTarget.Reset();bPendingGroupAlert=false;StopMovement();if(BrainComponent)BrainComponent->StopLogic(TEXT("Dead"));ActiveAction=TEXT("Dead");return;}
 const float Now=GetWorld()->GetTimeSeconds();
 if(!IsCombatOpponent(EncounterTarget.Get()))EncounterTarget.Reset();
 if(!IsCombatOpponent(KnownTarget.Get()))
 {
  bAwaitingReplacement|=bConfirmedTarget||HadTarget;
  KnownTarget.Reset();bConfirmedTarget=false;bPendingGroupAlert=false;
 }
 if(!Disabled&&!Busy&&EncounterTarget.IsValid()&&
    (KnownTarget!=EncounterTarget||!bConfirmedTarget))DiscoverPlayer(EncounterTarget.Get(),false);
 bool bLostTargetThisUpdate=false;
 auto ReplaceLost=[&]()
 {
  if(!bAwaitingReplacement||Disabled||ReactingToHit||Busy)return;
  bAwaitingReplacement=false;bLostTargetThisUpdate=true;
  if(APawn* Next=FindReplacement(false))
  {
   if(bEncounterOwnsTarget)EncounterTarget=Next;
   DiscoverPlayer(Next,!bEncounterOwnsTarget);
  }
  else if(!EncounterTarget.IsValid())bEncounterOwnsTarget=false;
 };
 ReplaceLost();
 // Perception updates report changes, not every visible frame. Reacquire from
 // its sight cache after a home/target reset without requiring a second event.
 if(!Disabled&&!M07&&!bLostTargetThisUpdate&&!bAwaitingReplacement&&!ReactingToHit&&!KnownTarget.IsValid()&&(!bReturning||FeralPursuit)&&C->AggroRange()>0)
 {
  TArray<AActor*> Seen;Senses->GetCurrentlyPerceivedActors(UAISense_Sight::StaticClass(),Seen);
  float Best=FMath::Square(C->AggroRange());
  APawn* BestPlayer=nullptr;
  for(auto* Actor:Seen)if(auto* P=Cast<APawn>(MonsterTargeting::DamageRecipient(Actor));IsCombatOpponent(P))
  {
   const float D=FVector::DistSquared(P->GetActorLocation(),GetPawn()->GetActorLocation());
   if(D<Best&&CanSeePlayer(P,true)){Best=D;BestPlayer=P;}
  }
  // Native perception can miss players behind allied bodies. All ranged
  // archetypes use the same friend-transparent sight as their firing lanes.
  // Retain M08/M25 all-around acquisition and the others' original view cone.
  // Reuse the existing 10 Hz service; enumerate players, never all monsters.
  const auto* Unknown=Cast<AUnknownHumanoid>(GetPawn());
  const bool RangedSight=!M07&&((Unknown&&Unknown->IsRanged())||M08||M09||M25||GetPawn()->IsA<ABellowSacLobber>()
   ||GetPawn()->IsA<AWitchMonster>()||GetPawn()->IsA<APoisonMaggotMonster>()
   ||GetPawn()->IsA<ASpiralPillarM14>()||GetPawn()->IsA<AM10Mawcrawler>()||GetPawn()->IsA<ARootCrownRigPreview>()
   ||GetPawn()->IsA<AHundredEyedSlagMonster>()||GetPawn()->IsA<AHandBrainMonster>()
   ||GetPawn()->IsA<ABoundCongregate>()||GetPawn()->IsA<AM66IncineratorMonster>()||GetPawn()->IsA<AHeQueMonster>());
  if(!BestPlayer)
  {
   const auto* Sight=Senses->GetSenseConfig<UAISenseConfig_Sight>();
   const float ConeCos=(M08||M25)?-1.f:FMath::Cos(FMath::DegreesToRadians(Sight?Sight->PeripheralVisionAngleDegrees:100.f));
   for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
   {
    const auto* PC=It->Get();APawn* P=PC?PC->GetPawn().Get():nullptr;
    if(!IsValid(P)||!P->IsPlayerControlled()||(!RangedSight&&MonsterTargeting::ContactBody(P)==P))continue;
    const auto* Health=P->FindComponentByClass<UFPSCombatHealthComponent>();
    const FVector Delta=P->GetActorLocation()-GetPawn()->GetActorLocation();
    const float D=Delta.SizeSquared();
    if((Health&&Health->IsDead())||D>=Best||
       FVector::DotProduct(GetPawn()->GetActorForwardVector().GetSafeNormal2D(),Delta.GetSafeNormal2D())<ConeCos||
       !CanSeePlayer(P,false))continue;
    Best=D;BestPlayer=P;
   }
  }
  if(BestPlayer)DiscoverPlayer(BestPlayer,true);
 }
 if(!Disabled&&!ReactingToHit&&!Busy&&bConfirmedTarget&&!bReturning)
  CheckForStalledPursuit(Now);
 bool Valid=KnownTarget.IsValid();
 // Detection and retention are different distances. Once this hunter knows
 // a target, honor perception's lose-sight radius instead of expiring memory
 // just because the player stepped outside the initial 12 m aggro radius.
 bool Visible=!ReactingToHit&&Valid&&CanSeePlayer(KnownTarget.Get(),!bConfirmedTarget);
 // HeQue defends against an exposed close player before continuing a distant
 // engagement. Publish the same target to facing, navigation and attack choice.
 if(!ReactingToHit&&Valid&&bConfirmedTarget&&!bReturning)
  if(const auto* HeQue=Cast<AHeQueMonster>(GetPawn());HeQue&&!HeQue->Busy())
   if(APawn* Close=HeQue->PreferredCombatTarget(KnownTarget.Get());Close!=KnownTarget.Get()&&CanSeePlayer(Close,false))
   {KnownTarget=Close;Visible=true;}
 if(TacticalHumanoid && Valid && bConfirmedTarget && !bReturning && !Disabled && !ReactingToHit)
 {
  if(auto* Other=TacticalHumanoid->ConsiderVisibleOpponent(*this,KnownTarget.Get(),Visible,
      !Busy&&!EncounterTarget.IsValid()&&!EncounterArea.IsValid());Other!=KnownTarget.Get())
  {
   DiscoverPlayer(Other,false);
   Visible=true;
  }
 }
 if(Visible&&!bConfirmedTarget)DiscoverPlayer(KnownTarget.Get(),true);
 // Preserve explicit encounter locks for their existing callers. Hall area
 // membership alone never supplies a target or refreshes its memory.
 const bool Locked=Valid&&EncounterTarget.IsValid()&&KnownTarget==EncounterTarget;
 // Alerted monsters share a live target lock for the existing memory window.
 // Occlusion stops attacks, but does not immediately erase the pursuit target.
 if(Valid&&(bConfirmedTarget||Locked)&&(!TacticalHumanoid||Visible))LastKnown=KnownTarget->GetNavAgentLocation();
 if(Visible||Locked){LastEvidence=Now;EvidenceLifetime=MemorySeconds;}
 if(Valid&&(C->AggroRange()<=0||Now-LastEvidence>EvidenceLifetime))
 {
  bAwaitingReplacement=bConfirmedTarget&&C->AggroRange()>0;KnownTarget.Reset();
  Valid=Visible=bConfirmedTarget=bPendingGroupAlert=false;
  ReplaceLost();Valid=KnownTarget.IsValid();Visible=Valid&&CanSeePlayer(KnownTarget.Get(),false);
 }
 // A feral hunter keeps a living target while it is seen or remembered. The
 // shared 24 m home leash used to override sight, then reacquire the same
 // player at home forever. Other monsters retain their configured home leash.
 if(NightRaidObjective.IsValid()||(Valid&&FeralPursuit))bReturning=false;
 // The two halls share a large combat area. A confirmed chase inside this
 // area must not hit the ordinary 24 m home leash halfway across the hall.
 else if(const auto* Area=Cast<ADungeonThemeEncounter>(EncounterArea.Get());
     Valid&&bConfirmedTarget&&Area&&Area->ContainsLocation(LastKnown)&&
     Area->ContainsLocation(GetPawn()->GetActorLocation()))bReturning=false;
 else if(FVector::Dist2D(GetPawn()->GetActorLocation(),C->Home())>C->LeashRange())bReturning=true;
 const FVector HomeFeet=M08?M08->HomeSupportLocation():C->Home()-(GetPawn()->GetActorLocation()-GetPawn()->GetNavAgentLocation());
 // Losing a remembered enemy returns home; an unaware wanderer may move away
 // from home without the old 80 cm idle check cancelling every stroll.
 if(!NightRaidObjective.IsValid()&&!Valid&&(HadTarget||bLostTargetThisUpdate)&&!bAwaitingReplacement&&!PendingDamageTarget.IsValid()&&(FVector::Dist2D(GetPawn()->GetNavAgentLocation(),HomeFeet)>80||FMath::Abs(GetPawn()->GetNavAgentLocation().Z-HomeFeet.Z)>50))bReturning=true;
 if(bReturning&&FVector::Dist2D(GetPawn()->GetNavAgentLocation(),HomeFeet)<80&&FMath::Abs(GetPawn()->GetNavAgentLocation().Z-HomeFeet.Z)<50){bReturning=false;KnownTarget.Reset();Valid=false;C->ReachedHome();LastEvidence=-100;}
 // Publish the raid objective atomically. Clearing HasTarget/Target first on
 // every knowledge tick aborts its active pursuit before restoring the same
 // shrine/wall target, so raiders only take a few centimetres per update.
 if(!Valid&&NightRaidObjective.IsValid())
 {B->SetValueAsVector(TEXT("Home"),HomeFeet);PublishNightRaidObjective();return;}
 C->SetTarget(Valid&&bConfirmedTarget&&!bReturning?KnownTarget.Get():nullptr);
 if(Valid||bReturning)StopWander();
 if(!Disabled&&Valid&&bConfirmedTarget&&!bReturning)
  if(auto* EncounterMantis=Cast<AMantisM27Monster>(GetPawn()))EncounterMantis->NotifyCloakEncounter(KnownTarget.Get());
 B->SetValueAsObject(TEXT("Target"),Valid?KnownTarget.Get():nullptr);
 B->SetValueAsVector(TEXT("LastKnown"),LastKnown);B->SetValueAsVector(TEXT("Home"),HomeFeet);
 B->SetValueAsBool(TEXT("Visible"),Visible);B->SetValueAsBool(TEXT("Returning"),bReturning);
 if(TacticalHumanoid)
 {
  TacticalHumanoid->UpdateTactics(Valid&&bConfirmedTarget&&!bReturning&&!Disabled?KnownTarget.Get():nullptr,Visible,LastKnown);
  const bool MovingAction=bConfirmedTarget && !bReturning && TacticalHumanoid->CanPursueDuringAction(KnownTarget.Get(),Visible);
  B->SetValueAsBool(TEXT("Hold"),Disabled||ReactingToHit||(C->IsBusy()&&!MovingAction));
 }
 const bool WallInWay=Valid&&bConfirmedTarget&&!Visible&&(IceWallCombat::BlockingWall(GetPawn(),KnownTarget.Get(),C->AggroRange())||VillageDefenseCombat::Blocking(GetPawn(),KnownTarget.Get()));
 // Keep one movement task across ranged attacks, archer blade counters and swaps.
 // The task still enters the same authoritative attack executor; the tree's
 // higher-priority hold/return branches continue to own interruptions.
 const bool MobileCombat=TacticalHumanoid && TacticalHumanoid->UsesMobileCombatTask() && bConfirmedTarget;
 B->SetValueAsBool(TEXT("CanAttack"),!MobileCombat&&!bReturning&&(Visible||WallInWay||(TacticalHumanoid&&TacticalHumanoid->CanActOutOfSight()))&&C->CanAttack(KnownTarget.Get()));
 B->SetValueAsBool(TEXT("HasTarget"),Valid&&!bReturning);
 if(!Disabled&&Valid&&!bReturning&&bPendingGroupAlert)BroadcastGroupAlert();
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
