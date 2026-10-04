#include "M09HitSurfaceAuditCommandlet.h"
#include "HangingBellM09.h"
#include "MonsterCombatComponent.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/FireballDamage.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Combat/CoreCombatFormula.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "Engine/DamageEvents.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

int32 UM09HitSurfaceAuditCommandlet::Main(const FString& Params)
{
 int32 Passed=0,Failed=0;TArray<TSharedPtr<FJsonValue>> Failures;
 auto Check=[&](bool OK,const FString& Label){if(OK)++Passed;else{++Failed;Failures.Add(MakeShared<FJsonValueString>(Label));UE_LOG(LogTemp,Error,TEXT("M09_HIT_AUDIT_FAIL %s"),*Label);}};
 const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
  .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
 UWorld* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("M09HitSurfaceAuditWorld"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
 if(!World)return 2;
 auto* M=World->SpawnActor<AHangingBellM09>();if(!M){World->DestroyWorld(false);return 2;}
 // No map BeginPlay, player subsystem initialization or user save access.
 M->Tags.Add(TEXT("NoSkillTraining"));M->Health=100000.f;
 auto* Mesh=M->GetMesh();auto* CorpseAsset=M->VisualMesh->GetPhysicsAsset();auto* HitAsset=Mesh->GetPhysicsAsset();
 Check(HitAsset&&HitAsset!=CorpseAsset,TEXT("independent live hit asset"));
 Check(HitAsset&&HitAsset->ConstraintSetup.IsEmpty(),TEXT("live hit asset has no ragdoll constraints"));
 Check(CorpseAsset&&!CorpseAsset->ConstraintSetup.IsEmpty(),TEXT("original corpse constraints retained"));
 int32 Membranes=0;
 for(const USkeletalBodySetup* Body:HitAsset->SkeletalBodySetups)if(Body->BoneName.ToString().StartsWith(TEXT("membrane_")))
 {++Membranes;Check(Body->PhysicsType==PhysType_Kinematic&&Body->DefaultInstance.GetCollisionEnabled()==ECollisionEnabled::QueryOnly,Body->BoneName.ToString()+TEXT(" query only"));}
 Check(Membranes==24,TEXT("24 membrane segments"));
 for(const USkeletalBodySetup* Body:CorpseAsset->SkeletalBodySetups)Check(!Body->BoneName.ToString().StartsWith(TEXT("membrane_")),TEXT("corpse excludes new membrane bodies"));
 const TCHAR* Roles[]={TEXT("Idle"),TEXT("Resonance"),TEXT("Claw")};const float Times[]={.25f,1.1f,.43f};
 for(int32 Pose=0;Pose<3;++Pose)
 {
  UAnimSequence* Clip=M->Clips.FindRef(FName(Roles[Pose]));Check(Clip!=nullptr,FString(Roles[Pose])+TEXT(" clip available"));if(!Clip)continue;
  Mesh->SetAnimationMode(EAnimationMode::AnimationSingleNode);Mesh->PlayAnimation(Clip,false);Mesh->SetPosition(Times[Pose],false);
  Mesh->TickAnimation(0.f,false);Mesh->RefreshBoneTransforms();
  Mesh->UpdateKinematicBonesToAnim(Mesh->GetComponentSpaceTransforms(),ETeleportType::TeleportPhysics,false,EAllowKinematicDeferral::DisallowDeferral);
  // Exercise the real exposed eye-crown surface, not only a synthetic bone receipt.
  if(auto* Crown=Mesh->GetBodyInstance(TEXT("eye_crown")))
  {
   const FVector Center=Crown->GetBodyBounds().GetCenter();
   const FVector Start=Center-FVector(0,0,150.f);
   FCollisionQueryParams Query(SCENE_QUERY_STAT(M09HeadSurfaceAudit),true);FHitResult Hit;
   const bool Found=World->LineTraceSingleByChannel(Hit,Start,Center,ECC_Visibility,Query);
   Check(Found&&ColdSteelSkills::IsCriticalHit(Hit),FString(Roles[Pose])+TEXT(" actual head surface ray is critical"));
   const bool Swept=World->SweepSingleByChannel(Hit,Start,Center,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(2.f),Query);
   Check(Swept&&ColdSteelSkills::IsCriticalHit(Hit),FString(Roles[Pose])+TEXT(" actual head surface sweep is critical"));
  }
  else Check(false,FString(Roles[Pose])+TEXT(" head physics body exists"));
  for(const USkeletalBodySetup* Setup:HitAsset->SkeletalBodySetups)
  {
   if(!Setup->BoneName.ToString().StartsWith(TEXT("membrane_")))continue;
   const FString Label=FString(Roles[Pose])+TEXT(" ")+Setup->BoneName.ToString();
   auto* Body=Mesh->GetBodyInstance(Setup->BoneName);Check(Body&&Body->IsValidBodyInstance(),Label+TEXT(" live body"));if(!Body||Setup->AggGeom.ConvexElems.IsEmpty())continue;
   const auto& Hull=Setup->AggGeom.ConvexElems[0];const FTransform Bone=Mesh->GetSocketTransform(Setup->BoneName);
   const FVector Extent=Hull.ElemBox.GetExtent();int32 Axis=0;if(Extent.Y<Extent.X)Axis=1;if(Extent.Z<Extent[Axis])Axis=2;
   FVector Delta=FVector::ZeroVector;Delta[Axis]=Extent[Axis]+.3;
   FVector Center=FVector::ZeroVector;for(const auto& Vertex:Hull.VertexData)Center+=Vertex;Center/=Hull.VertexData.Num();
   const FVector Start=Bone.TransformPosition(Center-Delta),End=Bone.TransformPosition(Center+Delta);
   for(bool Complex:{false,true}){FHitResult Hit;Check(Body->LineTrace(Hit,Start,End,Complex),Label+(Complex?TEXT(" complex ray"):TEXT(" simple ray")));}
   if(Setup->BoneName.ToString().EndsWith(TEXT("_04")))
   {
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M09HitSurfaceAudit),true);FHitResult Hit;
    const bool Found=World->LineTraceSingleByChannel(Hit,Start,End,ECC_Visibility,Query);
    Check(Found&&Hit.GetActor()==M&&Hit.BoneName.ToString().StartsWith(TEXT("membrane_")),Label+TEXT(" world weapon trace"));
    Check(!ColdSteelSkills::IsCriticalHit(Hit),Label+TEXT(" membrane is not guaranteed critical"));
    const bool Sweep=World->SweepSingleByChannel(Hit,Start,End,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(2.f),Query);
    Check(Sweep&&Hit.GetActor()==M,Label+TEXT(" arrow/spell sweep"));
   }
  }
 }
 FHitResult Head(M,Mesh,Mesh->GetSocketLocation(TEXT("eye_crown")),FVector::ForwardVector);Head.bBlockingHit=true;Head.BoneName=TEXT("eye_crown");
 FHitResult Membrane=Head;Membrane.BoneName=TEXT("membrane_L1_02");
 FHitResult Body=Head;Body.BoneName=TEXT("spine_02");
 FHitResult NetHead=Head;NetHead.Component=nullptr;
 Check(ColdSteelSkills::IsCriticalHit(NetHead),TEXT("component-less authoritative network head receipt"));
 for(const auto State:{EM09State::Idle,EM09State::Travel,EM09State::Resonance,EM09State::Gaze,EM09State::Claw,EM09State::SwingLeft,EM09State::SwingRight})
 {
  M->State=State;Check(ColdSteelSkills::IsCriticalHit(Head),TEXT("head guaranteed critical in state ")+FString::FromInt(int32(State)));
  Check(!ColdSteelSkills::IsCriticalHit(Membrane)&&!ColdSteelSkills::IsCriticalHit(Body),TEXT("body and membrane are ordinary hits"));
 }
 M->State=EM09State::Idle;
 auto* GameInstance=NewObject<UGameInstance>();auto* Model=NewObject<UColdSteelStatusModel>(GameInstance);
 auto* Shooter=World->SpawnActor<AActor>();
 for(bool Melee:{false,true})
 {
  FColdSteelSkillShot Shot;Shot.bMelee=Melee;Shot.bMeleeStrike=true;Shot.CriticalChance=0;Shot.CriticalDamageBonus=.5f;
  for(const FHitResult* Hit:{&Head,&Membrane,&Body})
  {
   const bool Critical=Hit==&Head;FWeaponDamageResult Result;
   const float Applied=M->Combat->ApplyHitWithReactionScale(0.f,[&](){return Model->ApplySkillWeaponHit(Shooter,*Hit,1000.f,FVector::ForwardVector,Shot,&Result);});
   const double Expected=CoreCombatFormula::Defense(Critical?1500:1000,CombatFormulaRuntime::MonsterDefense(M,false),false,0,0,1);
   Check(Result.bCritical==Critical,TEXT("weapon critical receipt"));
   Check(Result.bResolved&&FMath::IsNearlyEqual(double(Applied),Expected,.01),TEXT("weapon damage once, no legacy 1.5x stack"));
  }
 }
 for(const FHitResult* Hit:{&Head,&Membrane})
 {
  bool Critical=false;const bool Weak=ColdSteelSkills::IsCriticalHit(*Hit);
  const CombatFormulaRuntime::MagicHit Context{0,.5,0,0,&Critical,Weak};
  TGuardValue<const CombatFormulaRuntime::MagicHit*> Scope(CombatFormulaRuntime::ActiveMagicHit,&Context);
  FPointDamageEvent Event;Event.HitInfo=*Hit;Event.DamageTypeClass=UFireballDamage::StaticClass();
  const float Applied=M->Combat->ApplyHitWithReactionScale(0.f,[&](){return M->TakeDamage(1000.f,Event,nullptr,nullptr);});
  double Expected=CoreCombatFormula::Defense(1000,CombatFormulaRuntime::MonsterDefense(M,true),true,0,0,1);if(Weak)Expected=CoreCombatFormula::CriticalDamage(Expected,.5);
  Check(Critical==Weak&&FMath::IsNearlyEqual(double(Applied),Expected,.01),TEXT("direct magic head critical / ordinary membrane"));
 }
 M->Health=1.f;FDamageEvent Death(UCombatDirectDamage::StaticClass());M->TakeDamage(2.f,Death,nullptr,nullptr);
 Check(M->Dead()&&Mesh->GetPhysicsAsset()==CorpseAsset,TEXT("death restores original physics before ragdoll"));
 Check(ColdSteelSkills::IsCriticalHit(Head),TEXT("lethal headshot classification retained for feedback"));
 for(const auto& Slot:M->VisualMesh->GetMaterials())Check(Slot.MaterialInterface!=nullptr,TEXT("surface material binding retained"));
 TSharedRef<FJsonObject> Report=MakeShared<FJsonObject>();Report->SetNumberField(TEXT("passed"),Passed);Report->SetNumberField(TEXT("failed"),Failed);
 Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("map_begin_play"),false);Report->SetBoolField(TEXT("visual_acceptance"),false);
 FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));
 FFileHelper::SaveStringToFile(Text,*(FPaths::ProjectDir()/TEXT("SourceAssets/HangingBellM09Meshy20261003/HitSurfaceV23/Records/audit.json")));
 Shooter->Destroy();M->Destroy();World->DestroyWorld(false);UE_LOG(LogTemp,Display,TEXT("M09_HIT_SURFACE_AUDIT %s"),*Text);return Failed?1:0;
}
