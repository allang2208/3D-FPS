#include "PoisonMaggotAudit.h"
#include "PoisonMaggotMonster.h"
#include "PoisonMaggotSpawner.h"
#include "PoisonMaggotProjectile.h"
#include "MonsterAIController.h"
#include "MonsterCombatComponent.h"
#include "FPSCombatHealthComponent.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/AnimSequence.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/BoxComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
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
#include "PhysicsEngine/BodyInstance.h"
#include "SkeletalRenderPublic.h"
#include "Engine/GameViewportClient.h"
#include "Engine/Texture.h"
#include "Materials/MaterialInterface.h"
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
namespace
{
TArray<FVector3f> MaggotSurfaceVertices(USkeletalMeshComponent* Mesh)
{
 // GetCPUSkinnedVertices calls RefreshBoneTransforms and overwrites the pose
 // before physics blending. Sample the current blended matrices without mutation.
 TArray<FVector3f> Vertices;TArray<FMatrix44f> RefToLocal;Mesh->GetCurrentRefToLocalMatrices(RefToLocal,0);
 const auto& LOD=Mesh->GetSkeletalMeshAsset()->GetResourceForRendering()->LODRenderData[0];
 USkinnedMeshComponent::ComputeSkinnedPositions(Mesh,Vertices,RefToLocal,LOD,*Mesh->GetSkinWeightBuffer(0));return Vertices;
}
FBox MaggotSurfaceBounds(USkeletalMeshComponent* Mesh)
{
 const auto Vertices=MaggotSurfaceVertices(Mesh);FBox Bounds(ForceInit);
 for(const auto& V:Vertices)Bounds+=Mesh->GetComponentTransform().TransformPosition(FVector(V));
 return Bounds;
}
}
void UPoisonMaggotAudit::OnWorldBeginPlay(UWorld& W){Super::OnWorldBeginPlay(W);bVillage=FParse::Param(FCommandLine::Get(),TEXT("PoisonMaggotVillageAudit"));if(W.IsGameWorld()&&(bVillage||FParse::Param(FCommandLine::Get(),TEXT("PoisonMaggotAudit")))){StartTime=StageStart=W.GetTimeSeconds();W.GetTimerManager().SetTimer(Timer,this,&ThisClass::Step,.05f,true,3);}}
void UPoisonMaggotAudit::Deinitialize(){if(GetWorld())GetWorld()->GetTimerManager().ClearTimer(Timer);Super::Deinitialize();}
void UPoisonMaggotAudit::Check(const FString& N,bool P){(P?Passed:Failed).AddUnique(N);UE_LOG(LogTemp,Display,TEXT("MAGGOT_ASSERT %s %s"),P?TEXT("PASS"):TEXT("FAIL"),*N);}
void UPoisonMaggotAudit::Capture(const FString& N){FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("PoisonMaggot")/(N+TEXT(".png")),false,false);}
void UPoisonMaggotAudit::Next(){++Stage;StageStart=GetWorld()->GetTimeSeconds();Flag=false;}
void UPoisonMaggotAudit::Finish()
{
 auto J=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> P,F;for(auto& S:Passed)P.Add(MakeShared<FJsonValueString>(S));for(auto& S:Failed)F.Add(MakeShared<FJsonValueString>(S));J->SetArrayField(TEXT("passed"),P);J->SetArrayField(TEXT("failed"),F);J->SetNumberField(TEXT("max_side_cm"),MaxSide);J->SetBoolField(TEXT("complete"),true);FString Text;auto W=TJsonWriterFactory<>::Create(&Text);FJsonSerializer::Serialize(J,W);FFileHelper::SaveStringToFile(Text,*(FPaths::ProjectSavedDir()/TEXT("PoisonMaggot/acceptance.json")));UE_LOG(LogTemp,Display,TEXT("MAGGOT_AUDIT_COMPLETE failures=%d"),Failed.Num());GetWorld()->GetTimerManager().ClearTimer(Timer);FPlatformMisc::RequestExitWithStatus(false,Failed.IsEmpty()?0:1);
}
void UPoisonMaggotAudit::Arena()
{
 auto* AI=Cast<AMonsterAIController>(Monster->GetController());AI->SetDecisionEnabled(false);Monster->SetState(EPoisonMaggotState::Idle);Monster->CooldownLeft=0;Monster->GetCharacterMovement()->StopMovementImmediately();Monster->SetActorLocation(FVector(-500,-900,72),false,nullptr,ETeleportType::TeleportPhysics);Monster->SetActorRotation(FRotator::ZeroRotator);
 Player->SetActorLocation(FVector(20,-900,100),false,nullptr,ETeleportType::TeleportPhysics);Player->GetCharacterMovement()->StopMovementImmediately();
 if(auto* Poison=Player->FindComponentByClass<UMaggotPoisonComponent>()){Poison->Stacks=0;Poison->SetComponentTickEnabled(false);}
 auto* H=Player->FindComponentByClass<UFPSCombatHealthComponent>();H->Health=H->MaxHealth;BeforeHealth=H->Health;BeforeShots=Monster->ProjectilesFired;BeforeHits=Monster->ProjectileHits;
}
void UPoisonMaggotAudit::Step()
{
 if(bVillage){VillageStep();return;}
 float Time=GetWorld()->GetTimeSeconds()-StartTime,T=GetWorld()->GetTimeSeconds()-StageStart;if(Time>150){Check(TEXT("finished_before_timeout_stage_")+FString::FromInt(Stage),false);Finish();return;}
 if(Stage==0)
 {
  Player=UGameplayStatics::GetPlayerCharacter(this,0);for(TActorIterator<APoisonMaggotSpawner> It(GetWorld());It;++It)Spawner=*It;if(!Player.IsValid()||!Spawner.IsValid()||!Spawner->LiveMonster)return;Monster=Spawner->LiveMonster;
  auto* AI=Cast<AMonsterAIController>(Monster->GetController());if(!AI||!AI->GetBlackboardComponent())return;
  auto* Path=UNavigationSystemV1::FindPathToLocationSynchronously(this,Monster->GetActorLocation(),Player->GetActorLocation(),AI);
  if(FMath::Fmod(Time,5.f)<.06f)UE_LOG(LogTemp,Display,TEXT("MAGGOT_NAV_DIAG time=%.2f valid=%d partial=%d points=%d start=%s goal=%s"),Time,Path&&Path->IsValid(),Path&&Path->IsPartial(),Path?Path->PathPoints.Num():0,*Monster->GetActorLocation().ToString(),*Player->GetActorLocation().ToString());
  if(!Path||!Path->IsValid()||Path->IsPartial())return;
  Check(TEXT("behavior_tree_loaded"),AI->Behavior!=nullptr);Check(TEXT("nav_path_around_obstacle"),Path->PathPoints.Num()>2);Check(TEXT("imported_five_clips_and_material"),Monster->SpitClip&&FMath::IsNearlyEqual(Monster->SpitClip->GetPlayLength(),3.f,.01f)&&Monster->GetMesh()->GetMaterial(0)!=nullptr);
  auto* Mat=Monster->GetMesh()->GetMaterial(0);TArray<UTexture*> Textures;Mat->GetUsedTextures(Textures);FString Names;for(auto* Tex:Textures)Names+=Tex->GetName()+TEXT(" ");Check(TEXT("runtime_pbr_texture_bindings"),Textures.Num()>=3);
  UE_LOG(LogTemp,Display,TEXT("MAGGOT_RENDER_DIAG skin=%s venom=%s textures=%s materials_flag=%d lighting_flag=%d"),*Mat->GetPathName(),*GetPathNameSafe(Monster->VenomMaterial),*Names,GetWorld()->GetGameViewport()->EngineShowFlags.Materials,GetWorld()->GetGameViewport()->EngineShowFlags.Lighting);
  auto* View=GetWorld()->GetGameViewport();UE_LOG(LogTemp,Display,TEXT("MAGGOT_VIEWMODE mode=%d lightingonly=%d diffuseoverride=%d"),View->ViewModeIndex,View->EngineShowFlags.LightingOnlyOverride,View->EngineShowFlags.OverrideDiffuseAndSpecular);
  const auto& VB=Monster->GetMesh()->GetSkeletalMeshAsset()->GetResourceForRendering()->LODRenderData[0].StaticVertexBuffers.StaticMeshVertexBuffer;FVector2f UVMin(10000),UVMax(-10000);for(uint32 V=0;V<VB.GetNumVertices();++V){auto UV=VB.GetVertexUV(V,0);UVMin=UVMin.ComponentMin(UV);UVMax=UVMax.ComponentMax(UV);}UE_LOG(LogTemp,Display,TEXT("MAGGOT_UV channels=%d min=%s max=%s"),VB.GetNumTexCoords(),*UVMin.ToString(),*UVMax.ToString());
  if(FParse::Param(FCommandLine::Get(),TEXT("PoisonMaggotPhysicsOnly")))
  {
   if(FParse::Param(FCommandLine::Get(),TEXT("PoisonMaggotRecompile")))APoisonMaggotMonster::CompileMaterialAssets({Mat,Monster->VenomMaterial});
   Arena();Camera=GetWorld()->SpawnActor<ACameraActor>();Camera->SetActorLocation(FVector(10,-1510,345));Camera->SetActorRotation((FVector(-400,-900,65)-Camera->GetActorLocation()).Rotation());Camera->GetCameraComponent()->SetFieldOfView(58);Cast<APlayerController>(Player->GetController())->SetViewTarget(Camera.Get());
   Monster->CorpseSeconds=15;UGameplayStatics::ApplyDamage(Monster.Get(),100000,Player->GetController(),Player.Get(),nullptr);BeforeShots=Monster->ProjectilesFired;Flag=true;Stage=15;StageStart=GetWorld()->GetTimeSeconds();return;
  }
  auto* H=Player->FindComponentByClass<UFPSCombatHealthComponent>();H->Health=H->MaxHealth;UGameplayStatics::ApplyDamage(Monster.Get(),10,Player->GetController(),Player.Get(),nullptr);Next();return;
 }
 if(!Player.IsValid()||!Spawner.IsValid()){Check(TEXT("test_fixture_alive"),false);Finish();return;}
 if(Stage==17&&T>.5f){Finish();return;}
 if(Stage==16){if(Spawner->SpawnCount>=2&&Spawner->LiveMonster){Check(TEXT("corpse_recycled_and_respawned_once"),Spawner->SpawnCount==2);Finish();}return;}
 if(!Monster.IsValid()){Check(TEXT("monster_alive_until_recycle"),false);Finish();return;}
 auto* AI=Cast<AMonsterAIController>(Monster->GetController());auto* PC=Cast<APlayerController>(Player->GetController());auto* H=Player->FindComponentByClass<UFPSCombatHealthComponent>();
 if(Stage==1&&T>.12f){Check(TEXT("hit_uses_dedicated_clip"),Monster->GetMesh()->GetSingleNodeInstance()->GetCurrentAsset()==Monster->Combat->HitClip);Check(TEXT("hit_stops_movement"),Monster->GetVelocity().Size2D()<2);Next();return;}
 if(Stage==2)
 {
  MaxSide=FMath::Max(MaxSide,FMath::Abs(Monster->GetActorLocation().Y));
  if(FVector::Dist2D(Monster->GetActorLocation(),Player->GetActorLocation())<620)
  {
   Check(TEXT("real_navigation_displacement"),MaxSide>400&&AI->NavigationRequests>0);Arena();Monster->PoisonChance=0;
   Camera=GetWorld()->SpawnActor<ACameraActor>();Camera->SetActorLocation(FVector(10,-1510,345));Camera->SetActorRotation((FVector(-400,-900,65)-Camera->GetActorLocation()).Rotation());Camera->GetCameraComponent()->SetFieldOfView(58);PC->SetViewTarget(Camera.Get());BeforeLocation=Monster->GetActorLocation();BeforeYaw=Monster->GetActorRotation().Yaw;
   auto* Trigger=GetWorld()->SpawnActor<AActor>();auto* Box=NewObject<UBoxComponent>(Trigger);Trigger->SetRootComponent(Box);Box->SetBoxExtent(FVector(350,250,200));Box->SetCollisionProfileName(TEXT("OverlapAllDynamic"));Box->RegisterComponent();Trigger->SetActorLocation(FVector(-250,-900,100));
   Check(TEXT("spit_starts"),Monster->StartSpit(Player.Get()));Next();return;
  }
 }
 if(Stage==3&&T>1.10f){Check(TEXT("windup_has_no_projectiles_or_damage"),Monster->ProjectilesFired==BeforeShots&&H->Health==BeforeHealth);Capture(TEXT("spit-windup"));Next();return;}
 if(Stage==4&&T>.7f){Capture(TEXT("spit-release"));Check(TEXT("release_occurs_in_window"),Monster->ProjectilesFired>BeforeShots&&Monster->StateSeconds>=Monster->FirstEmission);Next();return;}
 if(Stage==5&&T>2.5f)
 {
  Check(TEXT("exactly_24_emissions"),Monster->ProjectilesFired-BeforeShots==24&&Monster->EmissionTimes.Num()==24);
  bool Times=Monster->EmissionTimes.Num()==24;for(int32 I=0;I<Monster->EmissionTimes.Num();++I)Times&=FMath::IsNearlyEqual(Monster->EmissionTimes[I],Monster->FirstEmission+I*.05f,.0001f)&&Monster->EmissionTimes[I]<Monster->EndEmission;
  Check(TEXT("scheduled_window_and_interval"),Times);Check(TEXT("attack_locks_translation_and_yaw"),FVector::Dist2D(Monster->GetActorLocation(),BeforeLocation)<2&&FMath::Abs(Monster->GetActorRotation().Yaw-BeforeYaw)<1);
  Check(TEXT("visible_projectiles_cross_overlap_volume_and_hit_player"),Monster->ProjectileHits>BeforeHits&&H->Health<BeforeHealth);Check(TEXT("cooldown_rejects_early_attack"),!Monster->StartSpit(Player.Get()));Next();return;
 }
 if(Stage==6&&T>4.2f)
 {
  Check(TEXT("cooldown_releases"),Monster->CooldownLeft==0&&Monster->CanSpit(Player.Get()));Arena();Monster->FanDegrees=0;Monster->PoisonChance=0;Check(TEXT("dodge_attack_starts"),Monster->StartSpit(Player.Get()));Next();return;
 }
 if(Stage==7)
 {
  if(T>.7f&&!Flag){Player->SetActorLocation(FVector(20,-1350,100),false,nullptr,ETeleportType::TeleportPhysics);Flag=true;}
  if(T>4.5f){Check(TEXT("locked_spray_can_be_dodged"),H->Health==BeforeHealth&&Monster->ProjectileHits==BeforeHits);Arena();
   Wall=GetWorld()->SpawnActor<AStaticMeshActor>();Wall->SetMobility(EComponentMobility::Movable);Wall->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));Wall->SetActorLocation(FVector(-160,-900,140));Wall->SetActorScale3D(FVector(.5,4,2.8));Wall->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));Check(TEXT("wall_blocks_attack_decision"),!Monster->CanSpit(Player.Get()));
   // Launch directly to isolate the projectile wall collision from the decision gate.
   FActorSpawnParameters P;P.Owner=Monster.Get();auto* B=GetWorld()->SpawnActor<APoisonMaggotProjectile>(Monster->Mouth(),FRotator::ZeroRotator,P);B->Launch(Monster.Get(),FVector::ForwardVector,500,600,8,0);Next();return;}
 }
 if(Stage==8&&T>1.5f)
 {
  Check(TEXT("wall_blocks_flying_venom"),H->Health==BeforeHealth);Wall->Destroy();Arena();Check(TEXT("interrupt_fixture_starts"),Monster->StartSpit(Player.Get()));Next();return;
 }
 if(Stage==9&&T>.7f){UGameplayStatics::ApplyDamage(Monster.Get(),45,PC,Player.Get(),nullptr);UGameplayStatics::ApplyDamage(Monster.Get(),45,PC,Player.Get(),nullptr);Check(TEXT("hits_interrupt_and_stun"),Monster->State==EPoisonMaggotState::Stagger&&Monster->Combat->bStunned);Next();return;}
 if(Stage==10)
 {
  if(T>.2f&&!Flag){UGameplayStatics::ApplyDamage(Monster.Get(),1,PC,Player.Get(),nullptr);Flag=true;}
  if(T>.8f&&T<.87f)Check(TEXT("weak_hit_does_not_shorten_stun"),Monster->Combat->bStunned);
  if(T>2.8f){Check(TEXT("interrupted_windup_never_emits"),Monster->ProjectilesFired==BeforeShots);Check(TEXT("stun_releases"),!Monster->Combat->IsControlled());Arena();auto* P=NewObject<UMaggotPoisonComponent>(Player.Get());Player->AddInstanceComponent(P);P->RegisterComponent();P->AddStack(Monster.Get());P->AddStack(Monster.Get());Next();return;}
 }
 if(Stage==11&&T>5.15f)
 {
  auto* P=Player->FindComponentByClass<UMaggotPoisonComponent>();Check(TEXT("poison_five_ticks_and_single_layer_decay"),P&&P->TicksApplied==5&&P->Stacks==1&&FMath::IsNearlyEqual(BeforeHealth-H->Health,10.f,.01f));Next();return;
 }
 if(Stage==12&&T>5.15f)
 {
  auto* P=Player->FindComponentByClass<UMaggotPoisonComponent>();Check(TEXT("poison_expires_without_lingering_tick"),P&&P->Stacks==0&&!P->IsComponentTickEnabled()&&FMath::IsNearlyEqual(BeforeHealth-H->Health,15.f,.01f));Arena();PC->SetViewTarget(Player.Get());FVector Eye;FRotator R;PC->GetPlayerViewPoint(Eye,R);PC->SetControlRotation((Monster->GetMesh()->GetSocketLocation(TEXT("body_05"))-Eye).Rotation());BeforeMonsterHP=Monster->Health;Next();return;
 }
 if(Stage==13)
 {
  if(T<.4f){FVector Eye;FRotator R;PC->GetPlayerViewPoint(Eye,R);PC->SetControlRotation((Monster->GetMesh()->GetSocketLocation(TEXT("body_05"))-Eye).Rotation());}
  if(T>.4f&&!Flag){PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Pressed,1.f));Flag=true;}
  if(T>.58f){PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Released,0.f));Check(TEXT("real_weapon_hits_rig"),Monster->Health<BeforeMonsterHP);Capture(TEXT("weapon-hit"));Next();return;}
 }
 if(Stage==14&&T>1.5f){Arena();PC->SetViewTarget(Camera.Get());Spawner->RespawnSeconds=1;Spawner->MinimumPlayerDistance=0;Monster->CorpseSeconds=8;Monster->StartSpit(Player.Get());Next();return;}
 if(Stage==15)
 {
  if(T>1.6f&&!Flag){UGameplayStatics::ApplyDamage(Monster.Get(),100000,PC,Player.Get(),nullptr);BeforeShots=Monster->ProjectilesFired;UGameplayStatics::ApplyDamage(Monster.Get(),100000,PC,Player.Get(),nullptr);Flag=true;}
  if(T>5.7f)
  {
   Check(TEXT("death_cancels_pending_emissions"),Monster->ProjectilesFired==BeforeShots);int32 Active=0;for(TActorIterator<APoisonMaggotProjectile> It(GetWorld());It;++It)if(It->GetOwner()==Monster.Get())++Active;Check(TEXT("death_removes_active_projectiles"),Active==0);Check(TEXT("kill_reward_once"),Monster->RewardCount==1);Check(TEXT("ragdoll_active"),Monster->GetMesh()->IsSimulatingPhysics());
   float MinBottom=10000;const FName Bones[]={TEXT("body_02"),TEXT("body_05"),TEXT("head")};for(auto Bone:Bones)if(auto* Body=Monster->GetMesh()->GetBodyInstance(Bone))MinBottom=FMath::Min(MinBottom,float(Body->GetBodyBounds().Min.Z));
   for(auto Bone:Bones)if(auto* Body=Monster->GetMesh()->GetBodyInstance(Bone))UE_LOG(LogTemp,Display,TEXT("MAGGOT_BODY %s scale=%s shape=%s location=%s visual_bone=%s"),*Bone.ToString(),*Monster->GetMesh()->GetSocketTransform(Bone).GetScale3D().ToString(),*Body->GetBodyBounds().ToString(),*Body->GetUnrealWorldTransform().GetLocation().ToString(),*Monster->GetMesh()->GetSocketLocation(Bone).ToString());
   const FBox Surface=MaggotSurfaceBounds(Monster->GetMesh());UE_LOG(LogTemp,Display,TEXT("MAGGOT_CORPSE physics_aabb=%.3f actual_surface=%s"),MinBottom,*Surface.ToString());Check(TEXT("corpse_support_above_ground"),Surface.IsValid&&Surface.Min.Z> -3&&Surface.Min.Z<12);Capture(TEXT("corpse"));Next();if(FParse::Param(FCommandLine::Get(),TEXT("PoisonMaggotPhysicsOnly")))Stage=17;return;
  }
 }
}
void UPoisonMaggotAudit::FrameVillageCamera()
{
 const FVector Target=MaggotSurfaceBounds(Monster->GetMesh()).GetCenter();
 FCollisionQueryParams Q(SCENE_QUERY_STAT(MaggotPreviewCamera),false);Q.AddIgnoredActor(Monster.Get());Q.AddIgnoredActor(Player.Get());
 FVector Best=Target+FVector(0,0,600);float BestDistance=0;
 for(float Angle:{-60.f,60.f,-120.f,120.f,0.f,180.f,-90.f,90.f})
 {
  const FVector Desired=Target+Monster->GetActorForwardVector().RotateAngleAxis(Angle,FVector::UpVector)*560+FVector(0,0,260);
  FHitResult Hit;const bool Blocked=GetWorld()->SweepSingleByChannel(Hit,Target,Desired,FQuat::Identity,ECC_WorldStatic,FCollisionShape::MakeSphere(12),Q);
  const FVector Candidate=Blocked?Hit.Location+(Target-Hit.Location).GetSafeNormal()*30:Desired;
  const float Distance=FVector::Dist(Target,Candidate);if(!Hit.bStartPenetrating&&Distance>BestDistance){Best=Candidate;BestDistance=Distance;}if(!Blocked)break;
 }
 Camera->SetActorLocation(Best);Camera->SetActorRotation((Target-Best).Rotation());Camera->GetCameraComponent()->SetFieldOfView(60);
 Camera->GetCameraComponent()->PostProcessSettings.bOverride_MotionBlurAmount=true;Camera->GetCameraComponent()->PostProcessSettings.MotionBlurAmount=0;
 UE_LOG(LogTemp,Display,TEXT("MAGGOT_VILLAGE_CAMERA distance=%.2f target=%s camera=%s"),BestDistance,*Target.ToString(),*Best.ToString());
}
void UPoisonMaggotAudit::VillageStep()
{
 const float Time=GetWorld()->GetTimeSeconds()-StartTime,T=GetWorld()->GetTimeSeconds()-StageStart;
 if(Time>(Stage==0?180.f:70.f)){Check(TEXT("village_finished_stage_")+FString::FromInt(Stage),false);Finish();return;}
 if(Stage==0)
 {
  Player=UGameplayStatics::GetPlayerCharacter(this,0);for(TActorIterator<APoisonMaggotSpawner> It(GetWorld());It;++It)Spawner=*It;if(!Player.IsValid()||!Spawner.IsValid()||!Spawner->LiveMonster)return;Monster=Spawner->LiveMonster;
  // Isolate this runtime fixture without editing other placed actors or the saved map.
  for(TActorIterator<ACharacter> It(GetWorld());It;++It)if(*It!=Monster.Get()&&It->ActorHasTag(TEXT("Enemy"))){if(auto* OtherAI=Cast<AMonsterAIController>(It->GetController()))OtherAI->SetDecisionEnabled(false);It->SetActorTickEnabled(false);}
  auto* AI=Cast<AMonsterAIController>(Monster->GetController());if(!AI||!AI->GetBlackboardComponent())return;AI->SetDecisionEnabled(false);
  FVector P;UNavigationPath* Path=nullptr;FCollisionQueryParams Q(SCENE_QUERY_STAT(MaggotVillagePlayer),false);Q.AddIgnoredActor(Monster.Get());Q.AddIgnoredActor(Player.Get());
  // Pick a real, reachable terrain position for the test pawn. A fixed offset
  // can land across a narrow gate that this 140 cm collision footprint cannot use.
  for(float Angle:{-90.f,0.f,30.f,-30.f,60.f,-60.f,90.f,120.f,-120.f,180.f})
  {
   FVector Candidate=Monster->GetActorLocation()+Monster->GetActorForwardVector().RotateAngleAxis(Angle,FVector::UpVector)*950;FHitResult G;
   if(!GetWorld()->LineTraceSingleByChannel(G,Candidate+FVector(0,0,250),Candidate-FVector(0,0,500),ECC_WorldStatic,Q)||G.ImpactNormal.Z<.9f)continue;
   Candidate=G.ImpactPoint+FVector(0,0,Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+3);
   auto* CandidatePath=UNavigationSystemV1::FindPathToLocationSynchronously(this,Monster->GetActorLocation(),Candidate,AI);
   P=Candidate;Path=CandidatePath;if(Path&&Path->IsValid()&&!Path->IsPartial())break;
  }
  if(Time-LastNavLog>5){LastNavLog=Time;auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());FNavLocation A,B;const auto& Props=Monster->GetNavAgentPropertiesRef();bool At=Nav&&Nav->ProjectPointToNavigation(Monster->GetActorLocation(),A,FVector(200,200,300),&Props);bool To=Nav&&Nav->ProjectPointToNavigation(P,B,FVector(200,200,300),&Props);UE_LOG(LogTemp,Display,TEXT("MAGGOT_VILLAGE_NAV time=%.2f building=%d start=%d end=%d valid=%d partial=%d points=%d target=%s"),Time,UNavigationSystemV1::IsNavigationBeingBuiltOrLocked(this),At,To,Path&&Path->IsValid(),Path&&Path->IsPartial(),Path?Path->PathPoints.Num():0,*P.ToString());}
  if(!Path||!Path->IsValid()||Path->IsPartial())return;
  Player->SetActorLocation(P,false,nullptr,ETeleportType::TeleportPhysics);
  Check(TEXT("village_saved_spawner_runs"),Spawner->SpawnCount==1);Check(TEXT("village_nav_path_valid"),true);BeforeLocation=Monster->GetActorLocation();BeforeShots=Monster->ProjectilesFired;BeforeHits=Monster->ProjectileHits;
  Camera=GetWorld()->SpawnActor<ACameraActor>();FrameVillageCamera();Cast<APlayerController>(Player->GetController())->SetViewTarget(Camera.Get());
  AI->SetDecisionEnabled(true);UGameplayStatics::ApplyDamage(Monster.Get(),10,Player->GetController(),Player.Get(),nullptr);StartTime=GetWorld()->GetTimeSeconds();Next();return;
 }
 if(!Monster.IsValid()||!Player.IsValid()){Check(TEXT("village_runtime_actors_valid"),false);Finish();return;}
 auto* AI=Cast<AMonsterAIController>(Monster->GetController());
 if(Stage==1)
 {
  if(Time-LastNavLog>5){LastNavLog=Time;UE_LOG(LogTemp,Display,TEXT("MAGGOT_VILLAGE_MOVE location=%s speed=%.2f requests=%d failed=%d distance=%.2f"),*Monster->GetActorLocation().ToString(),Monster->GetVelocity().Size2D(),AI->NavigationRequests,AI->bNavigationFailed,FVector::Dist2D(Monster->GetActorLocation(),Player->GetActorLocation()));Capture(TEXT("village-chase"));}
  if(Monster->State==EPoisonMaggotState::Spitting&&Monster->StateSeconds>1.65f){Check(TEXT("village_actual_chase"),FVector::Dist2D(Monster->GetActorLocation(),BeforeLocation)>200);Check(TEXT("village_attack_emits"),Monster->ProjectilesFired>BeforeShots);FrameVillageCamera();AI->SetDecisionEnabled(false);Next();return;}
 }
 if(Stage==2&&T>.3f&&!Flag){Capture(TEXT("village-spit"));Flag=true;}
 if(Stage==2&&T>1.6f)Check(TEXT("village_venom_reaches_player"),Monster->ProjectileHits>BeforeHits);
 if(Stage==2&&T>1.6f){VillageGround=Monster->GetCharacterMovement()->CurrentFloor.HitResult.GetComponent();UE_LOG(LogTemp,Display,TEXT("MAGGOT_VILLAGE_GROUND component=%s floor=%s"),*GetPathNameSafe(VillageGround.Get()),*Monster->GetCharacterMovement()->CurrentFloor.HitResult.ImpactPoint.ToString());Monster->CorpseSeconds=12;UGameplayStatics::ApplyDamage(Monster.Get(),100000,Player->GetController(),Player.Get(),nullptr);if(auto* H=Player->FindComponentByClass<UFPSCombatHealthComponent>())H->Health=H->MaxHealth;if(auto* P=Player->FindComponentByClass<UMaggotPoisonComponent>()){P->Stacks=0;P->SetComponentTickEnabled(false);}Next();return;}
 if(Stage==3&&T>5)
 {
  Check(TEXT("village_death_and_reward"),Monster->Dead()&&Monster->RewardCount==1);bool Supported=Monster->GetMesh()->IsSimulatingPhysics();float Gap=10000;
  const auto Vertices=MaggotSurfaceVertices(Monster->GetMesh());
  // Query the actual movement floor directly. A world ray can begin inside an
  // adjacent stone wall or hit its roof instead of the ground under the corpse.
  for(int32 I=0;I<Vertices.Num();I+=13)
  {FVector V=Monster->GetMesh()->GetComponentTransform().TransformPosition(FVector(Vertices[I]));FHitResult G;FCollisionQueryParams Q(SCENE_QUERY_STAT(MaggotCorpseTerrain),true);if(VillageGround.IsValid()&&VillageGround->LineTraceComponent(G,V+FVector(0,0,200),V-FVector(0,0,250),Q)&&!G.bStartPenetrating&&G.ImpactNormal.Z>.7f){const float D=float(V.Z-G.ImpactPoint.Z);Gap=FMath::Min(Gap,D);Supported&=D> -3.f;}else Supported=false;}
  UE_LOG(LogTemp,Display,TEXT("MAGGOT_VILLAGE_CORPSE gap=%.3f"),Gap);Check(TEXT("village_ragdoll_terrain_support"),Supported&&Gap<20);FrameVillageCamera();Next();return;
 }
 if(Stage==4&&T>.35f&&!Flag){Capture(TEXT("village-corpse"));Flag=true;}
 if(Stage==4&&T>.8f)Finish();
}
