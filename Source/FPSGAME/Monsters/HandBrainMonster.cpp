#include "HandBrainMonster.h"
#include "MonsterCombatComponent.h"
#include "MonsterAIController.h"
#include "HandBrainFearComponent.h"
#include "FPSCombatHealthComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Engine/DamageEvents.h"
#include "Engine/GameInstance.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"
#include "UObject/Package.h"
#include "Misc/PackageName.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"
#include "PhysicsEngine/BodyInstance.h"
#if WITH_EDITOR
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#endif

AHandBrainMonster::AHandBrainMonster()
{
 Combat=CreateDefaultSubobject<UMonsterCombatComponent>(TEXT("CombatExecution"));Combat->PoiseThreshold=150;Combat->StaggerDuration=.6f;Combat->StunDuration=.9f;
 AIControllerClass=AMonsterAIController::StaticClass();AutoPossessAI=EAutoPossessAI::PlacedInWorldOrSpawned;
 GetCharacterMovement()->bOrientRotationToMovement=true;GetCharacterMovement()->RotationRate=FRotator(0,180,0);
 PrimaryActorTick.bCanEverTick=true;GetCapsuleComponent()->InitCapsuleSize(62,102);
 GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Ignore);
 GetMesh()->SetRelativeLocation(FVector(0,0,-102));GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
 GetMesh()->SetCollisionResponseToAllChannels(ECR_Ignore);GetMesh()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
 GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
 GetCharacterMovement()->bRunPhysicsWithNoController=true;GetCharacterMovement()->MaxStepHeight=35;
 GetCharacterMovement()->bCanWalkOffLedges=false;bUseControllerRotationYaw=false;
 Tags.Add(TEXT("Enemy"));Tags.Add(TEXT("HandBrain"));
 SlamRing=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("SlamWarning"));HowlRing=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("HowlWave"));
 static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
 for(auto* Ring:{SlamRing.Get(),HowlRing.Get()}){Ring->SetupAttachment(GetRootComponent());Ring->SetAbsolute(true,true,true);Ring->SetCollisionEnabled(ECollisionEnabled::NoCollision);Ring->SetCastShadow(false);Ring->SetVisibility(false);if(Plane.Succeeded())Ring->SetStaticMesh(Plane.Object);}
 Voice=CreateDefaultSubobject<UAudioComponent>(TEXT("HowlVoice"));Voice->SetupAttachment(GetMesh());Voice->bAutoActivate=false;
 Voice->bOverrideAttenuation=true;Voice->AttenuationOverrides.bAttenuate=true;Voice->AttenuationOverrides.bSpatialize=true;Voice->AttenuationOverrides.FalloffDistance=1800;
}
void AHandBrainMonster::OnConstruction(const FTransform& T){Super::OnConstruction(T);if(VisualMesh)GetMesh()->SetSkeletalMeshAsset(VisualMesh);}
void AHandBrainMonster::BeginPlay()
{
 Super::BeginPlay();Health=MaxHealth;Home=GetActorLocation();if(VisualMesh)GetMesh()->SetSkeletalMeshAsset(VisualMesh);
 GetCharacterMovement()->MaxWalkSpeed=WalkSpeed;
 if(!VisualMesh||!IdleClip||!MoveClip||!SlamClip||!HowlClip||!DeathClip||!GetMesh()->GetPhysicsAsset()){UE_LOG(LogTemp,Error,TEXT("HANDBRAIN_ASSET_MISSING %s"),*GetName());SetActorTickEnabled(false);return;}
 if(GroundRingMaterial){SlamMaterial=UMaterialInstanceDynamic::Create(GroundRingMaterial,this);HowlMaterial=UMaterialInstanceDynamic::Create(GroundRingMaterial,this);SlamRing->SetMaterial(0,SlamMaterial);HowlRing->SetMaterial(0,HowlMaterial);}
 SetState(EHandBrainState::Idle);UE_LOG(LogTemp,Display,TEXT("HANDBRAIN_READY hp=%.0f home=%s physics=%s"),Health,*Home.ToString(),*GetMesh()->GetPhysicsAsset()->GetName());
}
void AHandBrainMonster::SetState(EHandBrainState New)
{
 State=New;StateSeconds=0;SlamRing->SetVisibility(false);HowlRing->SetVisibility(false);
 if(New!=EHandBrainState::Howl)Voice->Stop();
 UAnimSequence* Clip=New==EHandBrainState::Slam?SlamClip:New==EHandBrainState::Howl?HowlClip:New==EHandBrainState::Dying?DeathClip:(New==EHandBrainState::Chase||New==EHandBrainState::Returning)?MoveClip:IdleClip;
 const bool Loop=New==EHandBrainState::Idle||New==EHandBrainState::Chase||New==EHandBrainState::Returning||New==EHandBrainState::Stagger;
 if(Clip&&New!=EHandBrainState::Ragdoll&&New!=EHandBrainState::Stagger){GetMesh()->PlayAnimation(Clip,Loop);GetMesh()->SetPlayRate(Loop?1.f:0.f);}
 if(New!=EHandBrainState::Chase&&New!=EHandBrainState::Returning)GetCharacterMovement()->StopMovementImmediately();
 UE_LOG(LogTemp,Display,TEXT("HANDBRAIN_STATE %s %d"),*GetName(),int32(State));
}
FVector AHandBrainMonster::GroundPoint(FVector P) const
{
 FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(HandBrainGround),false,this);
 if(GetWorld()->LineTraceSingleByChannel(Hit,P+FVector(0,0,160),P-FVector(0,0,500),ECC_WorldStatic,Q))return Hit.ImpactPoint+FVector(0,0,3);
 return P-FVector(0,0,99);
}
bool AHandBrainMonster::CanSee(const AActor* A,FVector From) const
{
 if(!IsValid(A))return false;FHitResult H;FCollisionQueryParams Q(SCENE_QUERY_STAT(HandBrainSight),false,this);Q.AddIgnoredActor(A);
 return !GetWorld()->LineTraceSingleByChannel(H,From,A->GetActorLocation(),ECC_Visibility,Q);
}
void AHandBrainMonster::ShowRing(UStaticMeshComponent* Ring,FVector P,float Radius,FLinearColor Color,float Opacity)
{
 Ring->SetWorldLocation(P);Ring->SetWorldRotation(FRotator::ZeroRotator);Ring->SetWorldScale3D(FVector(Radius*.02f,Radius*.02f,1));Ring->SetVisibility(true);
 if(auto* M=Cast<UMaterialInstanceDynamic>(Ring->GetMaterial(0))){M->SetVectorParameterValue(TEXT("Tint"),Color);M->SetScalarParameterValue(TEXT("Opacity"),Opacity);}
}
bool AHandBrainMonster::StartAttack(bool bHowl)
{
 if(!HasAuthority()||Dead()||State==EHandBrainState::Slam||State==EHandBrainState::Howl||State==EHandBrainState::Stagger)return false;
 if((bHowl?HowlLeft:SlamLeft)>0)return false;
 if(!Target.IsValid())Target=UGameplayStatics::GetPlayerPawn(this,0);
 if(Target.IsValid())SetActorRotation(FRotator(0,(Target->GetActorLocation()-GetActorLocation()).Rotation().Yaw,0));
 if(bHowl){HowlLeft=HowlCooldown;NextHowlTick=.5f;SetState(EHandBrainState::Howl);Voice->SetSound(HowlSound);Voice->Play();DealHowl();}
 else{SlamLeft=SlamCooldown;bSlamConsumed=false;SlamCenter=GroundPoint(GetActorLocation()+GetActorForwardVector()*SlamReach);SetState(EHandBrainState::Slam);}
 return true;
}
void AHandBrainMonster::DealSlam()
{
 if(bSlamConsumed||Dead())return;bSlamConsumed=true;
 if(SlamSound)UGameplayStatics::PlaySoundAtLocation(this,SlamSound,SlamCenter,.9f);
 for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
 {
  APawn* P=It->Get()?It->Get()->GetPawn():nullptr;if(!P)continue;
  auto* H=P->FindComponentByClass<UFPSCombatHealthComponent>();if(H&&H->IsDead())continue;
  FVector Delta=P->GetActorLocation()-SlamCenter;
  if(Delta.Size2D()>SlamRadius||FMath::Abs(Delta.Z)>170||!CanSee(P,SlamCenter+FVector(0,0,60)))continue;
  UGameplayStatics::ApplyDamage(P,PhysicalAttack*2,GetController(),this,UDamageType::StaticClass());++SlamHits;
 }
 UE_LOG(LogTemp,Display,TEXT("HANDBRAIN_SLAM time=%.3f hits=%d center=%s"),StateSeconds,SlamHits,*SlamCenter.ToString());
}
void AHandBrainMonster::DealHowl()
{
 if(Dead())return;
 for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
 {
  APawn* P=It->Get()?It->Get()->GetPawn():nullptr;if(!P)continue;auto* H=P->FindComponentByClass<UFPSCombatHealthComponent>();if(H&&H->IsDead())continue;
  FVector Delta=P->GetActorLocation()-GetActorLocation();
  if(Delta.Size2D()>HowlRadius||FMath::Abs(Delta.Z)>170||!CanSee(P,GetActorLocation()+FVector(0,0,30)))continue;
  UGameplayStatics::ApplyDamage(P,MagicAttack*.5f,GetController(),this,UHandBrainMagicDamage::StaticClass());++HowlHits;
  if(!H||!H->IsDead()){auto* Fear=P->FindComponentByClass<UHandBrainFearComponent>();if(!Fear){Fear=NewObject<UHandBrainFearComponent>(P);P->AddInstanceComponent(Fear);Fear->RegisterComponent();}Fear->Apply(this);}
 }
 UE_LOG(LogTemp,Display,TEXT("HANDBRAIN_HOWL time=%.3f hits=%d"),StateSeconds,HowlHits);
}
void AHandBrainMonster::Tick(float Dt)
{
 Super::Tick(Dt);if(!HasAuthority())return;StateSeconds+=Dt;SlamLeft=FMath::Max(0.f,SlamLeft-Dt);HowlLeft=FMath::Max(0.f,HowlLeft-Dt);
 if(State==EHandBrainState::Ragdoll){if(StateSeconds>8)GetMesh()->PutAllRigidBodiesToSleep();return;}
 if(State==EHandBrainState::Dying){GetMesh()->SetPosition(FMath::Min(StateSeconds,DeathClip->GetPlayLength()),false);if(StateSeconds>=RagdollStartSeconds)EnterRagdoll();return;}
 if(State==EHandBrainState::Slam)
 {
  GetMesh()->SetPosition(FMath::Min(StateSeconds,2.f),false);
  if(StateSeconds>=1.f)DealSlam();
  ShowRing(SlamRing,SlamCenter,SlamRadius,StateSeconds<1?FLinearColor(1,.12f,.015f):FLinearColor(1,.75f,.2f),StateSeconds<1?.8f:FMath::Max(0.f,1-(StateSeconds-1)*3));
  if(StateSeconds>=2){State=EHandBrainState::Recovery;StateSeconds=0;SlamRing->SetVisibility(false);}return;
 }
 if(State==EHandBrainState::Howl)
 {
  GetMesh()->SetPosition(FMath::Min(StateSeconds,3.f),false);
  while(NextHowlTick<3.f&&StateSeconds>=NextHowlTick){DealHowl();NextHowlTick+=.5f;}
  const float Pulse=FMath::Fmod(StateSeconds,.5f)/.5f;ShowRing(HowlRing,GroundPoint(GetActorLocation()),HowlRadius*FMath::Max(.02f,Pulse),FLinearColor(.65f,.05f,1),1-Pulse);
  if(StateSeconds>=3){State=EHandBrainState::Recovery;StateSeconds=0;HowlRing->SetVisibility(false);Voice->Stop();}return;
 }
 if(State==EHandBrainState::Stagger){if(StateSeconds>=StaggerSeconds)Combat->FinishReaction();return;}
 if(State==EHandBrainState::Chase||State==EHandBrainState::Returning){GetMesh()->SetPlayRate(FMath::Clamp(GetVelocity().Size2D()/WalkSpeed,.2f,1.5f));StepClock+=Dt;if(StepClock>=.5f&&GetVelocity().Size2D()>10){StepClock=0;if(MoveSound)UGameplayStatics::PlaySoundAtLocation(this,MoveSound,GetActorLocation(),.35f);}}

}
void AHandBrainMonster::InterruptAttack(float Seconds){if(!HasAuthority()||Dead())return;bSlamConsumed=true;StaggerSeconds=FMath::Max(.1f,Seconds);SetState(EHandBrainState::Stagger);Combat->BeginReaction(StaggerSeconds);}
float AHandBrainMonster::TakeDamage(float Damage,const FDamageEvent& Event,AController* DamageInstigator,AActor* Causer)
{
 if(!HasAuthority()||Dead()||Damage<=0)return 0;
 const bool Magic=Event.DamageTypeClass&&Event.DamageTypeClass->IsChildOf(UHandBrainMagicDamage::StaticClass());
 float Applied=FMath::Min(Health,Magic?FMath::Max(1.f,Damage-MagicDefense):Damage);Health-=Applied;Super::TakeDamage(Applied,Event,DamageInstigator,Causer);
 if(Causer)LastImpulse=(GetActorLocation()-Causer->GetActorLocation()).GetSafeNormal2D()*60;
 if(Health<=0)
 {
  SetState(EHandBrainState::Dying);if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();Target.Reset();bSlamConsumed=true;GetCharacterMovement()->DisableMovement();GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);SetLifeSpan(CorpseSeconds);
  if(auto* PC=Cast<APlayerController>(DamageInstigator))if(PC->IsLocalController()&&GetGameInstance())GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->AwardKill(this,ExperienceReward);
  UE_LOG(LogTemp,Display,TEXT("HANDBRAIN_KILLED %s"),*GetName());
 }
 else Combat->ReceiveHit(Applied,DamageInstigator?DamageInstigator->GetPawn().Get():Cast<APawn>(Causer));
 return Applied;
}
void AHandBrainMonster::EnterRagdoll()
{
 GetMesh()->RefreshBoneTransforms();GetMesh()->bPauseAnims=true;GetMesh()->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
 GetMesh()->SetCollisionProfileName(TEXT("Ragdoll"));GetMesh()->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);
 GetMesh()->SetAllBodiesSimulatePhysics(true);GetMesh()->SetSimulatePhysics(true);GetMesh()->SetAllPhysicsLinearVelocity(FVector::ZeroVector);GetMesh()->WakeAllRigidBodies();GetMesh()->AddImpulse(LastImpulse,TEXT("cranium"),true);
 // The animated death_pivot is above the old first physics bone. A root body
 // keeps component and simulation space aligned after that pivot has moved.
 if(auto* RootBody=GetMesh()->GetBodyInstance(TEXT("root")))RootBody->SetCollisionEnabled(ECollisionEnabled::NoCollision);
 SetState(EHandBrainState::Ragdoll);UE_LOG(LogTemp,Display,TEXT("HANDBRAIN_RAGDOLL active=%d"),GetMesh()->IsSimulatingPhysics());
}
UPhysicsAsset* AHandBrainMonster::CreatePhysicsAsset(USkeletalMesh* InMesh)
{
#if WITH_EDITOR
 if(!InMesh)return nullptr;const FString Path=FPackageName::GetLongPackagePath(InMesh->GetOutermost()->GetName())/TEXT("PA_HandBrain");
 auto* Package=CreatePackage(*Path);auto* Asset=FindObject<UPhysicsAsset>(Package,TEXT("PA_HandBrain"));
 if(!Asset)Asset=NewObject<UPhysicsAsset>(Package,TEXT("PA_HandBrain"),RF_Public|RF_Standalone|RF_Transactional);
 return BuildPhysicsAsset(InMesh,Asset)?Asset:nullptr;
#else
 return nullptr;
#endif
}
bool AHandBrainMonster::BuildPhysicsAsset(USkeletalMesh* Mesh,UPhysicsAsset* Asset)
{
#if WITH_EDITOR
 if(!Mesh||!Asset)return false;Asset->Modify();Asset->SkeletalBodySetups.Empty();Asset->ConstraintSetup.Empty();Asset->CollisionDisableTable.Empty();
 const auto& Ref=Mesh->GetRefSkeleton();TArray<FTransform> CS=Ref.GetRefBonePose();for(int32 I=0;I<CS.Num();++I)if(Ref.GetParentIndex(I)>=0)CS[I]=CS[I]*CS[Ref.GetParentIndex(I)];
 const FName Names[]={TEXT("root"),TEXT("base"),TEXT("neck"),TEXT("cranium")};const float Z[]={0,27,85,152};const float Radius[]={2,32,42,46};const float Length[]={0,20,25,32};
 TArray<TArray<FVector>> HullPoints;HullPoints.SetNum(4);
 // The visible body includes broad palms outside the old axial capsules.
 // Alternate attack/fan meshes shrink in Death, so they must not enlarge the
 // persistent body hulls to their full attack-pose extent.
 if(auto* Model=Mesh->GetImportedModel())if(Model->LODModels.Num())
 for(const auto& Section:Model->LODModels[0].Sections)for(const auto& Vertex:Section.SoftVertices)
 {
  int32 Influence=0;for(int32 J=1;J<MAX_TOTAL_INFLUENCES;++J)if(Vertex.InfluenceWeights[J]>Vertex.InfluenceWeights[Influence])Influence=J;
  int32 Bone=Section.BoneMap[Vertex.InfluenceBones[Influence]],Region=INDEX_NONE;bool Alternate=false;
  while(Bone>=0&&Region==INDEX_NONE)
  {
   const FName Name=Ref.GetBoneName(Bone);if(Name==TEXT("arm_mount")||Name==TEXT("fan_mount")){Alternate=true;break;}
   for(int32 J=1;J<4;++J)if(Name==Names[J]){Region=J;break;}
   if(Region==INDEX_NONE)Bone=Ref.GetParentIndex(Bone);
  }
  if(!Alternate&&Region!=INDEX_NONE)HullPoints[Region].Add(CS[Bone].InverseTransformPosition(FVector(Vertex.Position)));
 }
 for(int32 I=0;I<4;++I)
 {
  int32 B=Ref.FindBoneIndex(Names[I]);if(B==INDEX_NONE)return false;auto* Setup=NewObject<USkeletalBodySetup>(Asset,NAME_None,RF_Transactional);Setup->BoneName=Names[I];Setup->PhysicsType=PhysType_Default;Setup->CollisionTraceFlag=CTF_UseSimpleAsComplex;
  // Dimensions are specified in component-space centimetres; Chaos applies the
  // imported bone scale to the local shape, just as it does to its centre.
  const float BoneScale=CS[B].GetScale3D().GetAbsMax();
  if(BoneScale<=UE_SMALL_NUMBER)return false;
  if(I>0&&HullPoints[I].Num()>8)
  {
   FKConvexElem Hull;Hull.VertexData=HullPoints[I];Hull.UpdateElemBox();
   // Two centimetres cover the small crown relaxation and blended joint skin.
   const FVector Center=Hull.ElemBox.GetCenter();for(auto& V:Hull.VertexData)V+=(V-Center).GetSafeNormal()*(2.f/BoneScale);
   Hull.UpdateElemBox();Setup->AggGeom.ConvexElems.Add(Hull);
  }
  else{FKSphylElem Capsule;Capsule.Center=CS[B].InverseTransformPosition(FVector(0,0,Z[I]));Capsule.Rotation=CS[B].GetRotation().Inverse().Rotator();Capsule.Radius=Radius[I]/BoneScale;Capsule.Length=Length[I]/BoneScale;Setup->AggGeom.SphylElems.Add(Capsule);}
  Setup->DefaultInstance.SetCollisionProfileName(TEXT("Ragdoll"));Setup->DefaultInstance.LinearDamping=1.2f;Setup->DefaultInstance.AngularDamping=4.f;Setup->DefaultInstance.SetMassOverride(I==0?.1f:I==3?90:45);
  // Keep the three heavy, constrained bodies stable through the death handoff.
  Setup->DefaultInstance.bUseCCD=true;
  Setup->DefaultInstance.PositionSolverIterationCount=16;
  Setup->DefaultInstance.VelocitySolverIterationCount=8;
  Setup->InvalidatePhysicsData();Setup->CreatePhysicsMeshes();Asset->SkeletalBodySetups.Add(Setup);
  if(I>0)
  {
   auto* C=NewObject<UPhysicsConstraintTemplate>(Asset,NAME_None,RF_Transactional);auto& D=C->DefaultInstance;D.JointName=Names[I];D.ConstraintBone1=Names[I];D.ConstraintBone2=Names[I-1];
   FTransform Anchor(FQuat::Identity,CS[B].GetLocation());D.SetRefFrame(EConstraintFrame::Frame1,Anchor.GetRelativeTransform(CS[B]));D.SetRefFrame(EConstraintFrame::Frame2,Anchor.GetRelativeTransform(CS[Ref.FindBoneIndex(Names[I-1])]));
   D.SetLinearXLimit(LCM_Locked,0);D.SetLinearYLimit(LCM_Locked,0);D.SetLinearZLimit(LCM_Locked,0);D.SetAngularSwing1Limit(ACM_Limited,12);D.SetAngularSwing2Limit(ACM_Limited,12);D.SetAngularTwistLimit(ACM_Limited,8);D.SetDisableCollision(true);Asset->ConstraintSetup.Add(C);
  }
 }
 for(int32 I=0;I<4;++I)for(int32 J=I+1;J<4;++J)Asset->DisableCollision(I,J);
 Asset->UpdateBodySetupIndexMap();Asset->UpdateBoundsBodiesArray();Asset->MarkPackageDirty();Mesh->SetPhysicsAsset(Asset);Mesh->MarkPackageDirty();return true;
#else
 return false;
#endif
}
bool AHandBrainMonster::FindVillageSpawn(UObject* Context,FVector Origin,FRotator Facing,FVector& Location)
{
 UWorld* W=GEngine->GetWorldFromContextObject(Context,EGetWorldErrorMode::ReturnNull);if(!W)return false;FCollisionQueryParams Q(SCENE_QUERY_STAT(HandBrainPlace),false);
 for(float Dist:{1700.f,1400.f,1100.f,900.f})for(float Angle:{0.f,30.f,-30.f,60.f,-60.f,90.f,-90.f,180.f})
 {
  FVector Near=Origin+FRotator(0,Facing.Yaw+Angle,0).Vector()*Dist;FHitResult H;
  if(!W->LineTraceSingleByChannel(H,Near+FVector(0,0,400),Near-FVector(0,0,700),ECC_WorldStatic,Q)||H.ImpactNormal.Z<.9f)continue;
  FVector P=H.ImpactPoint+FVector(0,0,104);if(FMath::Abs(P.Z-Origin.Z)>180)continue;
  if(W->OverlapBlockingTestByChannel(P,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(70,103),Q))continue;
  if(W->LineTraceSingleByChannel(H,Origin+FVector(0,0,45),P+FVector(0,0,45),ECC_Visibility,Q))continue;
  Location=P;return true;
 }return false;
}
