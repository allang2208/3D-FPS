#include "HandBrainAudit.h"
#include "MonsterSurfaceAudit.h"
#include "HandBrainMonster.h"
#include "HandBrainVillageSpawner.h"
#include "HandBrainFearComponent.h"
#include "NurseZombie.h"
#include "FPSCombatHealthComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/BodyInstance.h"
#include "../FPSGAMECharacter.h"
#include "Animation/AnimSequence.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Camera/CameraActor.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HighResScreenshot.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "TimerManager.h"
#include "Serialization/JsonWriter.h"
#include "Serialization/JsonSerializer.h"
void UHandBrainAudit::OnWorldBeginPlay(UWorld& W){Super::OnWorldBeginPlay(W);if(W.IsGameWorld()&&FParse::Param(FCommandLine::Get(),TEXT("HandBrainAudit")))W.GetTimerManager().SetTimer(Timer,this,&UHandBrainAudit::Step,.05f,true,4.f);}
void UHandBrainAudit::Deinitialize(){if(GetWorld())GetWorld()->GetTimerManager().ClearTimer(Timer);Super::Deinitialize();}
void UHandBrainAudit::Check(const FString& Name,bool Pass){(Pass?Passed:Failed).Add(Name);UE_LOG(LogTemp,Display,TEXT("HANDBRAIN_ASSERT %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),*Name);}
void UHandBrainAudit::Capture(const FString& Name){FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("HandBrain")/(Name+TEXT(".png")),false,false);}
void UHandBrainAudit::PlacePlayer(float Distance)
{
 FVector P=Brain->GetActorLocation()+Brain->GetActorForwardVector()*Distance;FHitResult H;FCollisionQueryParams Q(SCENE_QUERY_STAT(HandBrainAuditPlace),false);Q.AddIgnoredActor(Brain.Get());Q.AddIgnoredActor(Player.Get());
 if(GetWorld()->LineTraceSingleByChannel(H,P+FVector(0,0,250),P-FVector(0,0,500),ECC_WorldStatic,Q))P=H.ImpactPoint+FVector(0,0,Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+3);
 Player->SetActorLocation(P,false,nullptr,ETeleportType::TeleportPhysics);Player->GetCharacterMovement()->StopMovementImmediately();
 if(auto* PC=Cast<APlayerController>(Player->GetController()))PC->SetControlRotation((Brain->GetActorLocation()+FVector(0,0,15)-(P+FVector(0,0,60))).Rotation());
}
void UHandBrainAudit::Finish()
{
 TSharedRef<FJsonObject> J=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> P,F;for(auto& N:Passed)P.Add(MakeShared<FJsonValueString>(N));for(auto& N:Failed)F.Add(MakeShared<FJsonValueString>(N));J->SetArrayField(TEXT("passed"),P);J->SetArrayField(TEXT("failed"),F);J->SetBoolField(TEXT("complete"),true);J->SetStringField(TEXT("map"),GetWorld()->GetMapName());
 FString Text;auto Writer=TJsonWriterFactory<>::Create(&Text);FJsonSerializer::Serialize(J,Writer);FFileHelper::SaveStringToFile(Text,*(FPaths::ProjectSavedDir()/TEXT("HandBrain/acceptance.json")));
 UE_LOG(LogTemp,Display,TEXT("HANDBRAIN_ACCEPTANCE_COMPLETE failures=%d"),Failed.Num());GetWorld()->GetTimerManager().ClearTimer(Timer);FPlatformMisc::RequestExitWithStatus(false,Failed.IsEmpty()?0:1);
}
void UHandBrainAudit::Step()
{
 Clock+=.05f;StageClock+=.05f;if(Clock>100){Check(TEXT("completed_in_time"),false);Finish();return;}
 if(Stage==0)
 {
  Player=UGameplayStatics::GetPlayerCharacter(this,0);if(!Player.IsValid())return;
  for(TActorIterator<AHandBrainVillageSpawner> I(GetWorld());I;++I)Spawner=*I;
  if(!Spawner.IsValid()||!IsValid(Spawner->LiveMonster))return;Brain=Spawner->LiveMonster;Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();if(!Health.IsValid())return;
  for(TActorIterator<ANurseZombie> I(GetWorld());I;++I)I->SetActorTickEnabled(false);
  Check(TEXT("village_spawner_created_one"),Spawner->SpawnCount==1);Check(TEXT("default_respawn_300s"),Spawner->RespawnSeconds==300);
  Check(TEXT("lord_stats"),Brain->MaxHealth==1500&&Brain->PhysicalAttack==50&&Brain->MagicAttack==55&&Brain->SlamCooldown==6&&Brain->HowlCooldown==30);
  Check(TEXT("five_clips_loaded"),Brain->IdleClip&&Brain->MoveClip&&Brain->SlamClip&&Brain->HowlClip&&Brain->DeathClip);
  Check(TEXT("root_and_three_fitted_ragdoll_bodies"),Brain->GetMesh()->GetPhysicsAsset()&&Brain->GetMesh()->GetPhysicsAsset()->SkeletalBodySetups.Num()==4);
  Health->MaxHealth=10000;Health->Health=10000;Brain->AggroRadius=3000;Brain->HowlRadius=0;PlacePlayer(400);Start=Brain->GetActorLocation();BeforeHealth=Brain->Health;
  if(auto* FPS=Cast<AFPSGAMECharacter>(Player.Get())){BeforeAmmo=FPS->GetMagazineAmmo();}
  Brain->SetActorTickEnabled(false);Stage=18;StageClock=0;return;
 }
 // Teleporting the player and firing in the same callback used a stale camera.
 // Aim from the updated view, then allow the camera tick before pressing fire.
 if(Stage==18&&StageClock>.3f){if(auto* PC=Cast<APlayerController>(Player->GetController())){FVector Eye;FRotator Rot;PC->GetPlayerViewPoint(Eye,Rot);PC->SetControlRotation((Brain->GetMesh()->GetSocketLocation(TEXT("cranium"))+FVector(0,0,35)-Eye).Rotation());}Stage=19;StageClock=0;return;}
 if(Stage==19&&StageClock>.3f){Capture(TEXT("village-idle"));if(auto* PC=Cast<APlayerController>(Player->GetController())){FVector Eye;FRotator Rot;PC->GetPlayerViewPoint(Eye,Rot);FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(HandBrainGunProbe),true,Player.Get());GetWorld()->LineTraceSingleByChannel(Hit,Eye,Eye+Rot.Vector()*2000,ECC_Visibility,Q);UE_LOG(LogTemp,Display,TEXT("HANDBRAIN_GUN_PROBE hit=%s bone=%s eye=%s"),*GetNameSafe(Hit.GetActor()),*Hit.BoneName.ToString(),*Eye.ToString());if(auto* FPS=Cast<AFPSGAMECharacter>(Player.Get())){GetWorld()->LineTraceSingleByChannel(Hit,Eye,FPS->GetEffectiveMuzzleLocation(),ECC_Visibility,Q);UE_LOG(LogTemp,Display,TEXT("HANDBRAIN_MUZZLE_PROBE hit=%s"),*GetNameSafe(Hit.GetActor()));}PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Pressed,1.f));}Stage=1;StageClock=0;return;}
 if(!Brain.IsValid()&&Stage<16){Check(TEXT("monster_survived_test_setup"),false);Finish();return;}
 if(Stage==1&&!bGunReleased&&StageClock>1.f){if(auto* PC=Cast<APlayerController>(Player->GetController()))PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Released,0.f));if(auto* FPS=Cast<AFPSGAMECharacter>(Player.Get())){UE_LOG(LogTemp,Display,TEXT("HANDBRAIN_GUN_RESULT ammo_before=%d after=%d hp_before=%.1f after=%.1f"),BeforeAmmo,FPS->GetMagazineAmmo(),BeforeHealth,Brain->Health);}bGunReleased=true;Check(TEXT("real_gun_input_damages_handbrain"),Brain->Health<BeforeHealth);PlacePlayer(850);Brain->SetActorTickEnabled(true);}
 if(Stage==1&&StageClock>3)
 {
  Check(TEXT("chase_displaces_monster"),FVector::Dist2D(Start,Brain->GetActorLocation())>50);Brain->AggroRadius=0;Brain->HowlRadius=600;Brain->InterruptAttack(.1f);Stage=2;StageClock=0;return;
 }
 if(Stage==2&&StageClock>.3f)
 {
  PlacePlayer(160);BeforeHits=Brain->SlamHits;BeforeHealth=Health->Health;Check(TEXT("slam_started"),Brain->StartAttack(false));Stage=3;StageClock=0;return;
 }
 if(Stage==3&&StageClock>.5f){Check(TEXT("slam_windup_no_damage"),Health->Health==BeforeHealth);Capture(TEXT("village-slam-warning"));Stage=4;StageClock=0;return;}
 if(Stage==4&&StageClock>.7f){Check(TEXT("slam_exact_contact_hit"),Brain->SlamHits==BeforeHits+1&&Health->Health<BeforeHealth);Capture(TEXT("village-slam-impact"));Stage=5;StageClock=0;return;}
 if(Stage==5&&StageClock>1.f){Check(TEXT("slam_no_duplicate_hit"),Brain->SlamHits==BeforeHits+1);Check(TEXT("slam_cooldown_blocks_restart"),!Brain->StartAttack(false));Stage=6;StageClock=0;return;}
 if(Stage==6&&StageClock>4.2f){PlacePlayer(160);BeforeHits=Brain->SlamHits;Check(TEXT("slam_restart_after_cooldown"),Brain->StartAttack(false));Brain->InterruptAttack();Stage=7;StageClock=0;return;}
 if(Stage==7&&StageClock>1.3f)
 {
  Check(TEXT("interrupted_slam_cannot_hit"),Brain->SlamHits==BeforeHits);PlacePlayer(350);BeforeHowl=Brain->HowlHits;PlayerBefore=Player->GetActorLocation();Brain->HowlCooldown=1;
  Check(TEXT("howl_started"),Brain->StartAttack(true));Check(TEXT("howl_immediate_first_tick"),Brain->HowlHits==BeforeHowl+1);Stage=8;StageClock=0;return;
 }
 if(Stage==8&&StageClock>1.1f)
 {
  auto* Fear=Player->FindComponentByClass<UHandBrainFearComponent>();
  UE_LOG(LogTemp,Display,TEXT("HANDBRAIN_FEAR_DIAGNOSTIC stacks=%d displacement=%.3f speed=%.3f mode=%d start=%s end=%s"),Fear?Fear->Stacks:-1,FVector::Dist2D(PlayerBefore,Player->GetActorLocation()),Player->GetCharacterMovement()->MaxWalkSpeed,int32(Player->GetCharacterMovement()->MovementMode),*PlayerBefore.ToString(),*Player->GetActorLocation().ToString());
  Check(TEXT("fear_stacks_and_moves_away"),Fear&&Fear->Stacks==3&&FVector::Dist2D(PlayerBefore,Player->GetActorLocation())>1);Capture(TEXT("village-howl"));Stage=9;StageClock=0;return;
 }
 if(Stage==9&&StageClock>2.1f){Check(TEXT("howl_six_ticks_without_end_duplicate"),Brain->HowlHits==BeforeHowl+6);Stage=10;StageClock=0;return;}
 if(Stage==10&&StageClock>3.2f)
 {
  auto* Fear=Player->FindComponentByClass<UHandBrainFearComponent>();Check(TEXT("fear_expires_and_releases_input"),Fear&&Fear->Stacks==0&&!Player->GetController()->IsMoveInputIgnored());PlacePlayer(350);
  Wall=GetWorld()->SpawnActor<AActor>();auto* Box=NewObject<UBoxComponent>(Wall.Get());Wall->SetRootComponent(Box);Box->SetBoxExtent(FVector(40,250,250));Box->SetCollisionProfileName(TEXT("BlockAll"));Box->RegisterComponent();Wall->SetActorLocation((Brain->GetActorLocation()+Player->GetActorLocation())*.5f);Wall->SetActorRotation(Brain->GetActorRotation());
  BeforeHowl=Brain->HowlHits;Check(TEXT("occlusion_howl_started"),Brain->StartAttack(true));Stage=11;StageClock=0;return;
 }
 if(Stage==11&&StageClock>3.2f){Check(TEXT("wall_blocks_howl_damage"),Brain->HowlHits==BeforeHowl);Wall->Destroy();PlacePlayer(160);BeforeHits=Brain->SlamHits;Check(TEXT("dodge_slam_started"),Brain->StartAttack(false));PlacePlayer(1000);Stage=12;StageClock=0;return;}
 if(Stage==12&&StageClock>2.2f)
 {
  Check(TEXT("leaving_slam_area_avoids_hit"),Brain->SlamHits==BeforeHits);PlacePlayer(420);BeforeHowl=Brain->HowlHits;Brain->CorpseSeconds=5;Spawner->RespawnSeconds=2;
  auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();BeforeKills=Model->Kills();Brain->StartAttack(true);DeathFloor=Brain->GetCharacterMovement()->CurrentFloor.HitResult.GetComponent();
  float CorpseYaw=0;FParse::Value(FCommandLine::Get(),TEXT("HandBrainCorpseYaw="),CorpseYaw);Brain->AddActorWorldRotation(FRotator(0,CorpseYaw,0));
  UGameplayStatics::ApplyDamage(Brain.Get(),10000,Player->GetController(),Player.Get(),nullptr);UGameplayStatics::ApplyDamage(Brain.Get(),10000,Player->GetController(),Player.Get(),nullptr);
  Check(TEXT("death_once_and_kill_reward_once"),Brain->State==EHandBrainState::Dying&&Model->Kills()==BeforeKills+1);BeforeHowl=Brain->HowlHits;Stage=13;StageClock=0;return;
 }
 if(Stage==13&&StageClock>.8f){Capture(TEXT("village-death-animation"));Stage=14;StageClock=0;return;}
 if(Stage==14&&StageClock>.6f){Check(TEXT("death_transitions_to_ragdoll"),Brain->State==EHandBrainState::Ragdoll&&Brain->GetMesh()->IsSimulatingPhysics());Check(TEXT("death_cancels_howl_damage"),Brain->HowlHits==BeforeHowl);Stage=15;StageClock=0;return;}
 if(Stage==15&&StageClock>2.f)
 {
  FVector P=Brain->GetMesh()->GetSocketLocation(TEXT("cranium"));Check(TEXT("ragdoll_finite_near_spawn"),!P.ContainsNaN()&&FVector::Dist(P,Brain->GetActorLocation())<1200);
  auto* Body=Brain->GetMesh()->GetBodyInstance(TEXT("cranium"));
  Check(TEXT("ragdoll_physics_matches_render_bones"),Body&&(Body->GetUnrealWorldTransform().GetLocation()-P).Size()<.5f);
  const auto Surface=MonsterSurfaceAudit::Ground(Brain->GetMesh(),DeathFloor.Get());
  Check(TEXT("ragdoll_visible_surface_above_terrain"),Surface.Samples>100&&Surface.Missing==0&&Surface.Minimum> -3&&Surface.Minimum<20);
  UE_LOG(LogTemp,Display,TEXT("HANDBRAIN_SURFACE min=%.3f below=%d sampled=%d missing=%d bounds=%s body_delta=%s"),Surface.Minimum,Surface.Underground,Surface.Samples,Surface.Missing,*Surface.Bounds.ToString(),*(Body->GetUnrealWorldTransform().GetLocation()-Brain->GetMesh()->GetSocketLocation(TEXT("cranium"))).ToString());
  const FVector Look=Surface.Bounds.GetCenter();FVector CameraPos=Look+FVector(300,250,450);
  auto* Camera=GetWorld()->SpawnActor<ACameraActor>(CameraPos,(Look-CameraPos).Rotation());if(auto* PC=Cast<APlayerController>(Player->GetController()))PC->SetViewTarget(Camera);
  Stage=16;StageClock=0;return;
 }
 if(Stage==16&&StageClock>.15f&&StageClock<.22f)Capture(TEXT("village-ragdoll"));
 if(Stage==16&&StageClock>2.f){Check(TEXT("corpse_removed"),!Brain.IsValid());Stage=17;StageClock=0;return;}
 if(Stage==17&&StageClock>2.5f){Check(TEXT("village_respawns_one_new_monster"),Spawner.IsValid()&&Spawner->SpawnCount==2&&IsValid(Spawner->LiveMonster));Finish();}
}
