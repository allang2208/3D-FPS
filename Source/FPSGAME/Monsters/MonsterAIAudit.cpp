#include "MonsterAIAudit.h"
#include "NurseZombie.h"
#include "MonsterAIController.h"
#include "MonsterCombatComponent.h"
#include "FPSCombatHealthComponent.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/AnimSequence.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonSerializer.h"
#include "HighResScreenshot.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "TimerManager.h"
void UMonsterAIAudit::OnWorldBeginPlay(UWorld& W){Super::OnWorldBeginPlay(W);if(W.IsGameWorld()&&FParse::Param(FCommandLine::Get(),TEXT("MonsterAIAudit")))W.GetTimerManager().SetTimer(Timer,this,&UMonsterAIAudit::Step,.05f,true,3);}
void UMonsterAIAudit::Deinitialize(){if(GetWorld())GetWorld()->GetTimerManager().ClearTimer(Timer);Super::Deinitialize();}
void UMonsterAIAudit::Check(const FString& N,bool P){(P?Passed:Failed).Add(N);UE_LOG(LogTemp,Display,TEXT("MONSTER_AI_ASSERT %s %s"),P?TEXT("PASS"):TEXT("FAIL"),*N);}
void UMonsterAIAudit::Capture(const FString& N){FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("MonsterAI")/(N+TEXT(".png")),false,false);}
void UMonsterAIAudit::Finish(){auto J=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> P,F;for(auto& S:Passed)P.Add(MakeShared<FJsonValueString>(S));for(auto& S:Failed)F.Add(MakeShared<FJsonValueString>(S));J->SetArrayField(TEXT("passed"),P);J->SetArrayField(TEXT("failed"),F);J->SetNumberField(TEXT("max_side_cm"),MaxSide);FString Text;auto W=TJsonWriterFactory<>::Create(&Text);FJsonSerializer::Serialize(J,W);FFileHelper::SaveStringToFile(Text,*(FPaths::ProjectSavedDir()/TEXT("MonsterAI/acceptance.json")));UE_LOG(LogTemp,Display,TEXT("MONSTER_AI_COMPLETE failures=%d"),Failed.Num());GetWorld()->GetTimerManager().ClearTimer(Timer);FPlatformMisc::RequestExitWithStatus(false,Failed.IsEmpty()?0:1);}
void UMonsterAIAudit::Step()
{
 Time+=.05f;StageTime+=.05f;if(Time>65){Check(TEXT("finished_before_timeout"),false);Finish();return;}
 if(Stage==0)
 {
  Player=UGameplayStatics::GetPlayerCharacter(this,0);for(TActorIterator<ANurseZombie> It(GetWorld());It;++It)Nurse=*It;
  if(!Player.IsValid()||!Nurse.IsValid())return;auto* AI=Cast<AMonsterAIController>(Nurse->GetController());if(!AI||!AI->GetBlackboardComponent())return;
  auto* Path=UNavigationSystemV1::FindPathToLocationSynchronously(this,Nurse->GetActorLocation(),Player->GetActorLocation(),AI);
  if(FMath::Fmod(Time,5.f)<.051f){auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());UE_LOG(LogTemp,Display,TEXT("MONSTER_NAV_DIAG nav=%s path=%s valid=%d partial=%d points=%d start=%s goal=%s radius=%.1f height=%.1f"),*GetNameSafe(Nav),*GetNameSafe(Path),Path&&Path->IsValid(),Path&&Path->IsPartial(),Path?Path->PathPoints.Num():0,*Nurse->GetActorLocation().ToString(),*Player->GetActorLocation().ToString(),Nurse->GetNavAgentPropertiesRef().AgentRadius,Nurse->GetNavAgentPropertiesRef().AgentHeight);}
  if(!Path||!Path->IsValid()||Path->IsPartial())return;
  Check(TEXT("behavior_tree_controller_loaded"),AI->Behavior!=nullptr);Check(TEXT("path_routes_around_wall"),Path->PathPoints.Num()>2);
  auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();if(Health){Health->MaxHealth=10000;Health->Health=10000;}
  // Damage supplies a last-known target through the wall; visibility must not be faked.
  UGameplayStatics::ApplyDamage(Nurse.Get(),10,Player->GetController(),Player.Get(),nullptr);
  Check(TEXT("hit_enters_stagger"),Nurse->State==ENurseState::Stagger);Stage=1;StageTime=0;return;
 }
 if(!Nurse.IsValid()||!Player.IsValid()){Check(TEXT("actors_remain_valid"),false);Finish();return;}
 auto* AI=Cast<AMonsterAIController>(Nurse->GetController());
 if(Stage==1&&StageTime>.12f)
 {
  Check(TEXT("stagger_uses_hit_clip"),Nurse->GetMesh()->GetSingleNodeInstance()->GetCurrentAsset()==Nurse->Combat->HitClip);
  Check(TEXT("stagger_stops_motion"),Nurse->GetVelocity().Size2D()<2);Capture(TEXT("hit-reaction"));Stage=2;StageTime=0;return;
 }
 if(Stage==2)
 {
  MaxSide=FMath::Max(MaxSide,FMath::Abs(Nurse->GetActorLocation().Y));SawChase|=Nurse->State==ENurseState::Chase;
  if(StageTime>1&&Nurse->State==ENurseState::Idle)UE_LOG(LogTemp,Display,TEXT("MONSTER_AI_IDLE_DIAG action=%s requests=%d"),*AI->ActiveAction,AI->NavigationRequests);
  if(FVector::Dist2D(Nurse->GetActorLocation(),Player->GetActorLocation())<170)
  {
   Check(TEXT("recovers_to_chase"),SawChase);Check(TEXT("actual_motion_around_wall"),MaxSide>430);Check(TEXT("navigation_requests_used"),AI->NavigationRequests>0&&!AI->bNavigationFailed);Capture(TEXT("after-navigation"));
   AI->SetDecisionEnabled(false);UGameplayStatics::ApplyDamage(Nurse.Get(),35,Player->GetController(),Player.Get(),nullptr);UGameplayStatics::ApplyDamage(Nurse.Get(),35,Player->GetController(),Player.Get(),nullptr);
   Check(TEXT("accumulated_hits_stun"),Nurse->Combat->bStunned);Stage=3;StageTime=0;return;
  }
 }
 if(Stage==3&&StageTime>.2f&&!FollowupHit){FollowupHit=true;UGameplayStatics::ApplyDamage(Nurse.Get(),1,Player->GetController(),Player.Get(),nullptr);Check(TEXT("weak_followup_retains_stun"),Nurse->Combat->bStunned);}
 if(Stage==3&&StageTime>.8f){Check(TEXT("stun_outlasts_short_stagger"),Nurse->State==ENurseState::Stagger);Stage=4;StageTime=0;return;}
 if(Stage==4&&StageTime>.65f)
 {
  Check(TEXT("stun_releases"),!Nurse->Combat->IsControlled()&&!Nurse->Combat->bStunned);
  // Actual FPS firing input on an unobstructed setup verifies weapon -> reaction.
  Nurse->SetActorLocation(Player->GetActorLocation()+FVector(-280,0,0),false,nullptr,ETeleportType::TeleportPhysics);Nurse->SetActorRotation(FRotator::ZeroRotator);
  auto* PC=Cast<APlayerController>(Player->GetController());FVector Eye;FRotator Rot;PC->GetPlayerViewPoint(Eye,Rot);PC->SetControlRotation((Nurse->GetMesh()->GetSocketLocation(TEXT("spine_03"))-Eye).Rotation());Before=Nurse->Health;Stage=5;StageTime=0;return;
 }
 if(Stage==5&&StageTime>.4f){Cast<APlayerController>(Player->GetController())->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Pressed,1.f));Stage=6;StageTime=0;return;}
 if(Stage==6&&StageTime>.12f)
 {
  Cast<APlayerController>(Player->GetController())->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Released,0.f));Check(TEXT("real_gun_damage"),Nurse->Health<Before);Check(TEXT("real_gun_stagger"),Nurse->State==ENurseState::Stagger);Capture(TEXT("gun-stagger"));Stage=7;StageTime=0;return;
 }
 if(Stage==7&&StageTime>.16f&&StageTime<.23f)Capture(TEXT("gun-recoil-peak"));
 if(Stage==7&&StageTime>1.5f){Check(TEXT("post_gun_control_released"),!Nurse->Combat->IsControlled());AI->SetDecisionEnabled(true);Stage=8;StageTime=0;return;}
 if(Stage==8&&StageTime>2.5f){Check(TEXT("can_attack_after_recovery"),Nurse->State==ENurseState::Attack||Nurse->SuccessfulHits>0);Finish();}
}
