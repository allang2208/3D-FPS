#include "MonsterAIController.h"
#include "MonsterCombatComponent.h"
#include "MonsterBTNodes.h"
#include "Mutant3.h"
#include "WolfMonster.h"
#include "FPSCombatHealthComponent.h"
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
 Sight->DetectionByAffiliation.bDetectEnemies=Sight->DetectionByAffiliation.bDetectFriendlies=Sight->DetectionByAffiliation.bDetectNeutrals=true;
 auto* Hearing=CreateDefaultSubobject<UAISenseConfig_Hearing>(TEXT("Hearing"));Hearing->HearingRange=1800;Hearing->SetMaxAge(8);Hearing->DetectionByAffiliation=Sight->DetectionByAffiliation;
 auto* Damage=CreateDefaultSubobject<UAISenseConfig_Damage>(TEXT("DamageSense"));Damage->SetMaxAge(12);
 Senses->ConfigureSense(*Sight);Senses->ConfigureSense(*Hearing);Senses->ConfigureSense(*Damage);Senses->SetDominantSense(Sight->GetSenseImplementation());
 Senses->OnTargetPerceptionUpdated.AddDynamic(this,&AMonsterAIController::Perceived);
}
UMonsterCombatComponent* AMonsterAIController::Combat() const{return GetPawn()?GetPawn()->FindComponentByClass<UMonsterCombatComponent>():nullptr;}
void AMonsterAIController::OnPossess(APawn* P)
{
 Super::OnPossess(P);if(!HasAuthority())return;
 if(Behavior){RunBehaviorTree(Behavior);UpdateKnowledge();UE_LOG(LogTemp,Display,TEXT("MONSTER_BT_READY %s tree=%s"),*P->GetName(),*Behavior->GetPathName());}
 else UE_LOG(LogTemp,Error,TEXT("MONSTER_BT_MISSING %s"),*P->GetName());
}
void AMonsterAIController::OnUnPossess(){StopMovement();if(BrainComponent)BrainComponent->StopLogic(TEXT("Unpossessed"));KnownTarget.Reset();EncounterTarget.Reset();Super::OnUnPossess();}
void AMonsterAIController::SetDecisionEnabled(bool Enabled){bDecisionEnabled=Enabled;if(!Enabled)StopMovement();UpdateKnowledge();}
void AMonsterAIController::Perceived(AActor* Actor,FAIStimulus Stimulus)
{
 auto* P=Cast<APawn>(Actor);auto* C=Combat();
 if(!P||!P->IsPlayerControlled()||!C||C->IsDead()||C->AggroRange()<=0||!Stimulus.WasSuccessfullySensed())return;
 KnownTarget=P;
 // Stimuli are usually at torso/weapon height. Preserve their XY evidence,
 // but store a feet-height navigation goal for characters on stacked floors.
 LastKnown=Stimulus.StimulusLocation;
 LastKnown.Z-=P->GetActorLocation().Z-P->GetNavAgentLocation().Z;
 LastEvidence=GetWorld()->GetTimeSeconds();UpdateKnowledge();
}
void AMonsterAIController::RememberDamage(APawn* P)
{
 if(!IsValid(P)||P==GetPawn())return;KnownTarget=P;LastKnown=P->GetNavAgentLocation();LastEvidence=GetWorld()->GetTimeSeconds();UpdateKnowledge();
}
void AMonsterAIController::SetEncounterTarget(APawn* P)
{
 EncounterTarget=P;bReturning=false;
 if(IsValid(P))RememberDamage(P);
}
void AMonsterAIController::UpdateKnowledge()
{
 auto* C=Combat();auto* B=GetBlackboardComponent();if(!C||!B||!GetPawn())return;
 const bool Disabled=!bDecisionEnabled||!GetPawn()->IsActorTickEnabled();
 const auto* Canine=Cast<AWolfMonster>(GetPawn());
 const bool FeralPursuit=GetPawn()->IsA<AMutant3>()||(Canine&&Canine->bUsePredictiveHunting);
 B->SetValueAsBool(TEXT("Hold"),Disabled||C->IsBusy());
 if(C->IsDead()){StopMovement();if(BrainComponent)BrainComponent->StopLogic(TEXT("Dead"));ActiveAction=TEXT("Dead");return;}
 if(EncounterTarget.IsValid())KnownTarget=EncounterTarget;
 // Perception updates report changes, not every visible frame. Reacquire from
 // its sight cache after a home/target reset without requiring a second event.
 if(!KnownTarget.IsValid()&&(!bReturning||FeralPursuit)&&C->AggroRange()>0)
 {
  TArray<AActor*> Seen;Senses->GetCurrentlyPerceivedActors(UAISense_Sight::StaticClass(),Seen);
  float Best=FMath::Square(C->AggroRange());
  for(auto* Actor:Seen)if(auto* P=Cast<APawn>(Actor))if(P->IsPlayerControlled())
  {
   auto* Health=P->FindComponentByClass<UFPSCombatHealthComponent>();const float D=FVector::DistSquared2D(P->GetActorLocation(),GetPawn()->GetActorLocation());
   if((!Health||!Health->IsDead())&&D<Best){Best=D;KnownTarget=P;LastKnown=P->GetNavAgentLocation();LastEvidence=GetWorld()->GetTimeSeconds();}
  }
 }
 bool Valid=KnownTarget.IsValid();
 if(Valid){auto* H=KnownTarget->FindComponentByClass<UFPSCombatHealthComponent>();Valid=!H||!H->IsDead();}
 const float Now=GetWorld()->GetTimeSeconds();
 // Detection and retention are different distances. Once this hunter knows
 // a target, honor perception's lose-sight radius instead of expiring memory
 // just because the player stepped outside the initial 12 m aggro radius.
 float TrackingRange=C->AggroRange();
 if(FeralPursuit&&TrackingRange>0)
  if(const auto* Sight=Senses->GetSenseConfig<UAISenseConfig_Sight>())TrackingRange=FMath::Max(TrackingRange,Sight->LoseSightRadius);
 bool Visible=Valid&&C->AggroRange()>0&&FVector::Dist2D(KnownTarget->GetActorLocation(),GetPawn()->GetActorLocation())<=TrackingRange&&LineOfSightTo(KnownTarget.Get());
 // A sealed boss encounter tracks its living entrant through cover. Attacks
 // still require sight; ordinary monsters keep the existing perception memory.
 const bool Locked=Valid&&EncounterTarget.IsValid()&&KnownTarget==EncounterTarget;
 if(Visible||Locked){LastKnown=KnownTarget->GetNavAgentLocation();LastEvidence=Now;}
 if(!Valid||C->AggroRange()<=0||Now-LastEvidence>MemorySeconds){KnownTarget.Reset();Valid=false;}
 // A feral hunter keeps a living target while it is seen or remembered. The
 // shared 24 m home leash used to override sight, then reacquire the same
 // player at home forever. Other monsters retain their configured home leash.
 if(Valid&&FeralPursuit)bReturning=false;
 else if(FVector::Dist2D(GetPawn()->GetActorLocation(),C->Home())>C->LeashRange())bReturning=true;
 const FVector HomeFeet=C->Home()-(GetPawn()->GetActorLocation()-GetPawn()->GetNavAgentLocation());
 if(!Valid&&(FVector::Dist2D(GetPawn()->GetNavAgentLocation(),HomeFeet)>80||FMath::Abs(GetPawn()->GetNavAgentLocation().Z-HomeFeet.Z)>50))bReturning=true;
 if(bReturning&&FVector::Dist2D(GetPawn()->GetNavAgentLocation(),HomeFeet)<80&&FMath::Abs(GetPawn()->GetNavAgentLocation().Z-HomeFeet.Z)<50){bReturning=false;KnownTarget.Reset();Valid=false;C->ReachedHome();LastEvidence=-100;}
 C->SetTarget(Valid&&!bReturning?KnownTarget.Get():nullptr);
 B->SetValueAsObject(TEXT("Target"),Valid?KnownTarget.Get():nullptr);
 B->SetValueAsVector(TEXT("LastKnown"),LastKnown);B->SetValueAsVector(TEXT("Home"),HomeFeet);
 B->SetValueAsBool(TEXT("Visible"),Visible);B->SetValueAsBool(TEXT("Returning"),bReturning);
 B->SetValueAsBool(TEXT("CanAttack"),!bReturning&&Visible&&C->CanAttack(KnownTarget.Get()));
 B->SetValueAsBool(TEXT("HasTarget"),Valid&&!bReturning);
}
void AMonsterAIController::NavigateTo(FVector Destination,float Acceptance)
{
 const float Now=GetWorld()->GetTimeSeconds();if(Now-LastMove<.65f)return;
 if(GetMoveStatus()==EPathFollowingStatus::Moving&&FVector::DistSquared(Destination,LastDestination)<FMath::Square(45.f))return;
 LastMove=Now;LastDestination=Destination;++NavigationRequests;
 auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
 const auto& Agent=GetNavAgentPropertiesRef();
 const auto* Data=Nav?Nav->GetNavDataForProps(Agent,GetNavAgentLocation()):nullptr;
 FNavLocation Goal;
 // Player capsules can stand nearer the railing than the boss's 62 cm radius.
 // Search laterally for its walkable interior, with a short vertical window so
 // a missing upper-floor polygon cannot silently select the ground floor.
 const float XY=FMath::Max(100.f,Agent.AgentRadius*2.f+30.f);
 if(!Data||!Nav->ProjectPointToNavigation(Destination,Goal,FVector(XY,XY,100),Data))
 {
  bNavigationFailed=true;
  UE_LOG(LogTemp,Warning,TEXT("MONSTER_NAV_FAILED %s reason=goal_projection feet=%s nav=%s"),*GetNameSafe(GetPawn()),*Destination.ToString(),*GetNameSafe(Data));
  return;
 }
 const auto Result=MoveToLocation(Goal.Location,Acceptance,false,true,false,false,nullptr,false);
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
