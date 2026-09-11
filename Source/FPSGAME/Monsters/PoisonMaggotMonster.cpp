#include "PoisonMaggotMonster.h"
#include "PoisonMaggotProjectile.h"
#include "MonsterCombatComponent.h"
#include "MonsterAIController.h"
#include "FPSCombatHealthComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Engine/DamageEvents.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/Package.h"
#include "Misc/PackageName.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"
#if WITH_EDITOR
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "Materials/Material.h"
#include "ShaderCompiler.h"
#endif
APoisonMaggotMonster::APoisonMaggotMonster()
{
 PrimaryActorTick.bCanEverTick=true;Combat=CreateDefaultSubobject<UMonsterCombatComponent>(TEXT("CombatExecution"));
 Combat->PoiseThreshold=80;Combat->StaggerDuration=.45f;Combat->StunDuration=1;
 AIControllerClass=AMonsterAIController::StaticClass();AutoPossessAI=EAutoPossessAI::PlacedInWorldOrSpawned;
 GetCapsuleComponent()->InitCapsuleSize(70,70);GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Ignore);
 GetMesh()->SetRelativeLocation(FVector(0,0,-70));GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
 GetMesh()->SetCollisionResponseToAllChannels(ECR_Ignore);GetMesh()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
 GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
 auto* Move=GetCharacterMovement();Move->bOrientRotationToMovement=true;Move->RotationRate=FRotator(0,130,0);Move->bRunPhysicsWithNoController=true;Move->MaxStepHeight=25;Move->bCanWalkOffLedges=false;
 bUseControllerRotationYaw=false;Tags.Add(TEXT("Enemy"));Tags.Add(TEXT("PoisonMaggot"));
}
void APoisonMaggotMonster::OnConstruction(const FTransform& T){Super::OnConstruction(T);if(VisualMesh)GetMesh()->SetSkeletalMeshAsset(VisualMesh);}
void APoisonMaggotMonster::BeginPlay()
{
 Super::BeginPlay();Health=MaxHealth;Home=GetActorLocation();if(VisualMesh)GetMesh()->SetSkeletalMeshAsset(VisualMesh);GetCharacterMovement()->MaxWalkSpeed=WalkSpeed;
 if(!VisualMesh||!IdleClip||!MoveClip||!SpitClip||!DeathClip||!Combat->HitClip||!GetMesh()->GetPhysicsAsset())
 {UE_LOG(LogTemp,Error,TEXT("MAGGOT_ASSET_MISSING %s"),*GetName());SetActorTickEnabled(false);return;}
 SetState(EPoisonMaggotState::Idle);UE_LOG(LogTemp,Display,TEXT("MAGGOT_READY mesh=%s home=%s"),*VisualMesh->GetPathName(),*Home.ToString());
}
void APoisonMaggotMonster::SetState(EPoisonMaggotState New)
{
 State=New;StateSeconds=0;const bool Moving=New==EPoisonMaggotState::Chase||New==EPoisonMaggotState::Returning;
 if(!Moving)GetCharacterMovement()->StopMovementImmediately();GetCharacterMovement()->bOrientRotationToMovement=Moving;
 UAnimSequence* Clip=Moving?MoveClip:New==EPoisonMaggotState::Spitting?SpitClip:New==EPoisonMaggotState::Dying?DeathClip:IdleClip;
 if(Clip&&New!=EPoisonMaggotState::Stagger&&New!=EPoisonMaggotState::Ragdoll){GetMesh()->PlayAnimation(Clip,Moving||New==EPoisonMaggotState::Idle);GetMesh()->SetPlayRate(Moving||New==EPoisonMaggotState::Idle?1.f:0.f);}
 UE_LOG(LogTemp,Display,TEXT("MAGGOT_STATE %s %d"),*GetName(),int32(New));
}
FVector APoisonMaggotMonster::Mouth() const{return GetMesh()->GetSocketLocation(TEXT("mouth_socket"));}
bool APoisonMaggotMonster::CanSpit(APawn* Victim) const
{
 if(!IsValid(Victim)||Combat->IsBusy()||CooldownLeft>0||FVector::Dist2D(Victim->GetActorLocation(),GetActorLocation())>AttackRange)return false;
 auto* H=Victim->FindComponentByClass<UFPSCombatHealthComponent>();if(H&&H->IsDead())return false;
 FCollisionQueryParams Q(SCENE_QUERY_STAT(MaggotSight),false,this);Q.AddIgnoredActor(Victim);FHitResult Hit;
 return !GetWorld()->LineTraceSingleByChannel(Hit,Mouth(),Victim->GetActorLocation(),ECC_Visibility,Q);
}
bool APoisonMaggotMonster::StartSpit(APawn* Victim)
{
 if(!HasAuthority()||!CanSpit(Victim))return false;Target=Victim;
 LockedYaw=(Victim->GetActorLocation()-GetActorLocation()).Rotation().Yaw;SetActorRotation(FRotator(0,LockedYaw,0));
 LockedAim=(Victim->GetActorLocation()-Mouth()).GetSafeNormal();NextEmission=0;CooldownLeft=CooldownSeconds;EmissionTimes.Reset();SetState(EPoisonMaggotState::Spitting);
 if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}return true;
}
void APoisonMaggotMonster::Emit(float Scheduled)
{
 const FVector Direction=LockedAim.RotateAngleAxis(FMath::FRandRange(-FanDegrees*.5f,FanDegrees*.5f),FVector::UpVector);
 FActorSpawnParameters P;P.Owner=this;P.Instigator=this;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
 auto* Ball=GetWorld()->SpawnActor<APoisonMaggotProjectile>(Mouth(),Direction.Rotation(),P);
 if(Ball){Ball->Launch(this,Direction,ProjectileSpeed,ProjectileRange,FMath::RoundToFloat(MagicAttack*.33f),PoisonChance);Projectiles.Add(Ball);++ProjectilesFired;EmissionTimes.Add(Scheduled);}
 if(SpitSound&&NextEmission%3==0)UGameplayStatics::PlaySoundAtLocation(this,SpitSound,Mouth(),.3f);
}
void APoisonMaggotMonster::Tick(float Dt)
{
 Super::Tick(Dt);if(!HasAuthority())return;StateSeconds+=Dt;CooldownLeft=FMath::Max(0.f,CooldownLeft-Dt);
 if(State==EPoisonMaggotState::Spitting)
 {
  auto* H=Target.IsValid()?Target->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
  if(!Target.IsValid()||(H&&H->IsDead())){SetState(EPoisonMaggotState::Recovery);return;}
  SetActorRotation(FRotator(0,LockedYaw,0));GetCharacterMovement()->StopMovementImmediately();
  GetMesh()->SetPosition(FMath::Min(StateSeconds,Duration),false);GetMesh()->RefreshBoneTransforms();
  while(FirstEmission+NextEmission*EmissionInterval<EndEmission&&StateSeconds>=FirstEmission+NextEmission*EmissionInterval)
  {Emit(FirstEmission+NextEmission*EmissionInterval);++NextEmission;}
  if(StateSeconds>=Duration){SetState(EPoisonMaggotState::Recovery);if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();}return;
 }
 if(State==EPoisonMaggotState::Stagger){if(StateSeconds>=ReactionSeconds)Combat->FinishReaction();return;}
 if(State==EPoisonMaggotState::Dying){GetMesh()->SetPosition(FMath::Min(StateSeconds,DeathClip->GetPlayLength()),false);if(StateSeconds>=RagdollStartSeconds)EnterRagdoll();return;}
 if(State==EPoisonMaggotState::Ragdoll){if(StateSeconds>7)GetMesh()->PutAllRigidBodiesToSleep();return;}
 if(State==EPoisonMaggotState::Chase||State==EPoisonMaggotState::Returning)GetMesh()->SetPlayRate(FMath::Clamp(GetVelocity().Size2D()/WalkSpeed,0.f,1.5f));
 Projectiles.RemoveAll([](const auto& P){return !P.IsValid();});
}
void APoisonMaggotMonster::InterruptAttack(float Seconds)
{if(!HasAuthority()||Dead())return;ReactionSeconds=FMath::Max(.1f,Seconds);SetState(EPoisonMaggotState::Stagger);Combat->BeginReaction(ReactionSeconds);}
float APoisonMaggotMonster::TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer)
{
 if(!HasAuthority()||Dead()||Damage<=0)return 0;const float Applied=FMath::Min(Health,Damage);Health-=Applied;Super::TakeDamage(Applied,Event,EventInstigator,Causer);
 if(Health<=0)
 {
  ClearProjectiles();Target.Reset();SetState(EPoisonMaggotState::Dying);GetCharacterMovement()->DisableMovement();GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);SetLifeSpan(CorpseSeconds);
  if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();
  if(auto* PC=Cast<APlayerController>(EventInstigator))if(PC->IsLocalController()&&GetGameInstance()){GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->AwardKill(this,ExperienceReward);++RewardCount;}
 }
 else Combat->ReceiveHit(Applied,EventInstigator?EventInstigator->GetPawn().Get():Cast<APawn>(Causer));return Applied;
}
void APoisonMaggotMonster::ClearProjectiles(){for(auto& P:Projectiles)if(P.IsValid())P->Destroy();Projectiles.Reset();}
void APoisonMaggotMonster::EndPlay(const EEndPlayReason::Type Reason){ClearProjectiles();Super::EndPlay(Reason);}
void APoisonMaggotMonster::EnterRagdoll()
{
 GetMesh()->RefreshBoneTransforms();GetMesh()->bPauseAnims=true;GetMesh()->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
 GetMesh()->SetCollisionProfileName(TEXT("Ragdoll"));GetMesh()->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);GetMesh()->SetAllBodiesSimulatePhysics(true);GetMesh()->SetSimulatePhysics(true);GetMesh()->SetAllPhysicsLinearVelocity(FVector::ZeroVector);GetMesh()->WakeAllRigidBodies();SetState(EPoisonMaggotState::Ragdoll);
 // A non-colliding root body anchors component/physics space. Physical support
 // comes from the fitted segment hulls, not this bookkeeping body.
 if(auto* RootBody=GetMesh()->GetBodyInstance(TEXT("root")))RootBody->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
UPhysicsAsset* APoisonMaggotMonster::CreatePhysicsAsset(USkeletalMesh* Mesh)
{
#if WITH_EDITOR
 if(!Mesh)return nullptr;const FString Path=FPackageName::GetLongPackagePath(Mesh->GetOutermost()->GetName())/TEXT("PA_PoisonMaggot");auto* Package=CreatePackage(*Path);
 auto* Asset=FindObject<UPhysicsAsset>(Package,TEXT("PA_PoisonMaggot"));if(!Asset)Asset=NewObject<UPhysicsAsset>(Package,TEXT("PA_PoisonMaggot"),RF_Public|RF_Standalone|RF_Transactional);
 Asset->Modify();Asset->SkeletalBodySetups.Empty();Asset->ConstraintSetup.Empty();Asset->CollisionDisableTable.Empty();
 const auto& Ref=Mesh->GetRefSkeleton();TArray<FTransform> CS=Ref.GetRefBonePose();for(int32 I=0;I<CS.Num();++I)if(Ref.GetParentIndex(I)>=0)CS[I]=CS[I]*CS[Ref.GetParentIndex(I)];
 // Every fleshy segment needs physical support. Leaving intermediate body bones
 // animated after a side collapse lets their weighted surface pass through terrain.
 const FName Names[]={TEXT("root"),TEXT("body_00"),TEXT("body_01"),TEXT("body_02"),TEXT("body_03"),TEXT("body_04"),TEXT("body_05"),TEXT("body_06"),TEXT("body_07"),TEXT("head")};
 const float Radii[]={2,27,35,39,41,41,40,36,31,24};
 TArray<TArray<FVector>> HullPoints;HullPoints.SetNum(UE_ARRAY_COUNT(Names));
 if(auto* Model=Mesh->GetImportedModel())if(Model->LODModels.Num())
 {
  for(const auto& Section:Model->LODModels[0].Sections)for(const auto& Vertex:Section.SoftVertices)
  {
   int32 MaxInfluence=0;for(int32 J=1;J<MAX_TOTAL_INFLUENCES;++J)if(Vertex.InfluenceWeights[J]>Vertex.InfluenceWeights[MaxInfluence])MaxInfluence=J;
   int32 Bone=Section.BoneMap[Vertex.InfluenceBones[MaxInfluence]];int32 Region=INDEX_NONE;
   while(Bone>=0&&Region==INDEX_NONE){for(int32 J=0;J<UE_ARRAY_COUNT(Names);++J)if(Ref.GetBoneName(Bone)==Names[J]){Region=J;break;}if(Region==INDEX_NONE)Bone=Ref.GetParentIndex(Bone);}
   if(Region!=INDEX_NONE)HullPoints[Region].Add(CS[Bone].InverseTransformPosition(FVector(Vertex.Position)));
  }
 }
 if(auto* Skeleton=Mesh->GetSkeleton()){Skeleton->SetBoneTranslationRetargetingMode(0,EBoneTranslationRetargetingMode::Animation,true);Skeleton->MarkPackageDirty();}
 for(int32 I=0;I<UE_ARRAY_COUNT(Names);++I)
 {
  int32 B=Ref.FindBoneIndex(Names[I]);if(B==INDEX_NONE)return nullptr;auto* Setup=NewObject<USkeletalBodySetup>(Asset,NAME_None,RF_Transactional);Setup->BoneName=Names[I];Setup->PhysicsType=PhysType_Default;Setup->CollisionTraceFlag=CTF_UseSimpleAsComplex;
  const float Scale=CS[B].GetScale3D().GetAbsMax();
  // Fit each region's actual rest surface, including its attached short legs.
  // A sphere misses the broad flanks when this non-humanoid rolls onto its side.
  if(HullPoints[I].Num()>8){FKConvexElem Hull;Hull.VertexData=HullPoints[I];Hull.UpdateElemBox();Setup->AggGeom.ConvexElems.Add(Hull);}
  else{FKSphereElem Sphere;Sphere.Center=FVector::ZeroVector;Sphere.Radius=Radii[I]/Scale;Setup->AggGeom.SphereElems.Add(Sphere);}
  Setup->DefaultInstance.SetCollisionProfileName(TEXT("Ragdoll"));Setup->DefaultInstance.LinearDamping=2;Setup->DefaultInstance.AngularDamping=5;Setup->DefaultInstance.SetMassOverride(I==0?.1f:I==9?5:9);Setup->DefaultInstance.bUseCCD=true;Setup->DefaultInstance.PositionSolverIterationCount=16;Setup->DefaultInstance.VelocitySolverIterationCount=8;
  Setup->InvalidatePhysicsData();Setup->CreatePhysicsMeshes();Asset->SkeletalBodySetups.Add(Setup);
  if(I>0){auto* C=NewObject<UPhysicsConstraintTemplate>(Asset,NAME_None,RF_Transactional);auto& D=C->DefaultInstance;D.JointName=Names[I];D.ConstraintBone1=Names[I];D.ConstraintBone2=Names[I-1];FTransform Anchor(FQuat::Identity,CS[B].GetLocation());D.SetRefFrame(EConstraintFrame::Frame1,Anchor.GetRelativeTransform(CS[B]));D.SetRefFrame(EConstraintFrame::Frame2,Anchor.GetRelativeTransform(CS[Ref.FindBoneIndex(Names[I-1])]));D.SetLinearXLimit(LCM_Locked,0);D.SetLinearYLimit(LCM_Locked,0);D.SetLinearZLimit(LCM_Locked,0);D.SetAngularSwing1Limit(ACM_Limited,22);D.SetAngularSwing2Limit(ACM_Limited,22);D.SetAngularTwistLimit(ACM_Limited,15);D.SetDisableCollision(true);Asset->ConstraintSetup.Add(C);}
 }
 for(int32 I=0;I<UE_ARRAY_COUNT(Names);++I)for(int32 J=I+1;J<UE_ARRAY_COUNT(Names);++J)Asset->DisableCollision(I,J);
 Asset->UpdateBodySetupIndexMap();Asset->UpdateBoundsBodiesArray();Asset->MarkPackageDirty();Mesh->SetPhysicsAsset(Asset);Mesh->MarkPackageDirty();return Asset;
#else
 return nullptr;
#endif
}
bool APoisonMaggotMonster::CompileMaterialAssets(const TArray<UMaterialInterface*>& Materials)
{
#if WITH_EDITOR
 for(auto* Interface:Materials)if(Interface){auto* M=Interface->GetMaterial();M->PreEditChange(nullptr);M->PostEditChange();M->UpdateCachedExpressionData();M->ForceRecompileForRendering();M->MarkPackageDirty();}
 GShaderCompilingManager->FinishAllCompilation();
 bool Valid=true;for(auto* Interface:Materials)if(Interface){TArray<UTexture*> Textures;Interface->GetUsedTextures(Textures);UE_LOG(LogTemp,Display,TEXT("MAGGOT_COMPILED_MATERIAL %s textures=%d"),*Interface->GetName(),Textures.Num());if(Interface->GetName()==TEXT("M_PoisonMaggot_Skin"))Valid&=Textures.Num()>=3;}
 return Valid;
#else
 return false;
#endif
}
