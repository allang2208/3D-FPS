#include "HangingBellM09.h"
#include "M09GazeParameters.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
float Ease(float T){T=FMath::Clamp(T,0.f,1.f);return T*T*(3.f-2.f*T);}
const FName EyeNames[M09Gaze::Eyes]={TEXT("eye_01"),TEXT("eye_02"),TEXT("eye_03"),TEXT("eye_04"),TEXT("eye_05")};
const float IrisRadius[M09Gaze::Eyes]={4.2f,4.f,3.1f,3.2f,2.6f};
FTransform Ribbon(FVector A,FVector B,float Radius)
{
 const FVector D=B-A;
 return FTransform(FRotationMatrix::MakeFromZ(D.GetSafeNormal()).ToQuat(),(A+B)*.5f,FVector(Radius,Radius,FMath::Max(.001f,float(D.Size()))/100.f));
}
}

void AHangingBellM09::CreateGazeFX()
{
 GazeIrises=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("GazeIrises"));
 GazeFilaments=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("GazeConvergence"));
 for(auto* FX:{GazeIrises.Get(),GazeFilaments.Get()})
 {
  FX->SetupAttachment(GetRootComponent());FX->SetAbsolute(true,true,true);
  FX->SetCollisionEnabled(ECollisionEnabled::NoCollision);FX->SetGenerateOverlapEvents(false);
  FX->SetCanEverAffectNavigation(false);FX->SetCastShadow(false);FX->SetVisibility(false);
  FX->NumCustomDataFloats=1;FX->SetCullDistances(2700,3000);
 }
 static ConstructorHelpers::FObjectFinder<UStaticMesh> RibbonMesh(TEXT("/Game/Monsters/HangingBellM09/V08/FX/SM_M09_GazeRibbon_V08.SM_M09_GazeRibbon_V08"));
 static ConstructorHelpers::FObjectFinder<UStaticMesh> IrisMesh(TEXT("/Game/Monsters/HangingBellM09/V08/FX/SM_M09_IrisVeil_V08.SM_M09_IrisVeil_V08"));
 static ConstructorHelpers::FObjectFinder<UMaterialInterface> BeamMat(TEXT("/Game/Monsters/HangingBellM09/V08/Materials/M_M09_GazeBeam_V08.M_M09_GazeBeam_V08"));
 static ConstructorHelpers::FObjectFinder<UMaterialInterface> IrisMat(TEXT("/Game/Monsters/HangingBellM09/V08/Materials/M_M09_GazeIris_V08.M_M09_GazeIris_V08"));
 static ConstructorHelpers::FObjectFinder<UMaterialInterface> StrandMat(TEXT("/Game/Monsters/HangingBellM09/V08/Materials/M_M09_GazeFilament_V08.M_M09_GazeFilament_V08"));
 Beam->SetStaticMesh(RibbonMesh.Object);Beam->SetMaterial(0,BeamMat.Object);
 Charge->SetStaticMesh(IrisMesh.Object);Charge->SetMaterial(0,IrisMat.Object);
 GazeIrises->SetStaticMesh(IrisMesh.Object);GazeIrises->SetMaterial(0,IrisMat.Object);
 GazeFilaments->SetStaticMesh(RibbonMesh.Object);GazeFilaments->SetMaterial(0,StrandMat.Object);
 Beam->SetCullDistance(3000.f);Charge->SetCullDistance(3000.f);
 static ConstructorHelpers::FObjectFinder<UNiagaraSystem> Gather(TEXT("/Game/Monsters/HangingBellM09/V10/NS_M09_EyeGather_V10.NS_M09_EyeGather_V10"));
 for(int32 I=0;I<M09Gaze::Eyes;++I)
 {
  auto* FX=CreateDefaultSubobject<UNiagaraComponent>(*FString::Printf(TEXT("EyeParticleGather%d"),I));
  FX->SetupAttachment(GetMesh());FX->SetAsset(Gather.Object);FX->SetAutoActivate(false);
  FX->SetCollisionEnabled(ECollisionEnabled::NoCollision);FX->SetCastShadow(false);
  FX->SetCanEverAffectNavigation(false);FX->SetVisibility(false);FX->SetComponentTickEnabled(false);
  GazeGatherSystems.Add(FX);
 }
}

void AHangingBellM09::InitializeGazeFX()
{
 if(GetNetMode()==NM_DedicatedServer)return;
 GazeBeamMID=Beam->CreateDynamicMaterialInstance(0);
 GazeImpactMID=Charge->CreateDynamicMaterialInstance(0);
 GazeIrisMID=GazeIrises->CreateDynamicMaterialInstance(0);
 GazeFilamentMID=GazeFilaments->CreateDynamicMaterialInstance(0);
 GazeIrises->ClearInstances();GazeFilaments->ClearInstances();
 for(const auto& FX:GazeGatherSystems)FX->AddTickPrerequisiteComponent(GetMesh());
 const FVector Forward=GetMesh()->GetComponentTransform().InverseTransformVectorNoScale(GetActorForwardVector());
 if(VisualMesh)
 {
  const auto& Ref=VisualMesh->GetRefSkeleton();TArray<FTransform> Frames=Ref.GetRefBonePose();
  for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
  for(int32 I=0;I<M09Gaze::Eyes;++I)
  {
   const int32 B=Ref.FindBoneIndex(EyeNames[I]);
   GazeEyeLocalForward[I]=B>=0?Frames[B].InverseTransformVectorNoScale(Forward):FVector::ForwardVector;
  }
 }
 // Fixed pools: five attached irises, four curved segments per eye.
 for(int32 I=0;I<M09Gaze::Eyes;++I)GazeIrises->AddInstance(FTransform::Identity);
 for(int32 I=0;I<M09Gaze::Eyes*M09Gaze::SegmentsPerEye;++I)GazeFilaments->AddInstance(FTransform::Identity);
}

void AHangingBellM09::ClearGazeFX()
{
 Beam->SetVisibility(false);Charge->SetVisibility(false);
 GazeIrises->SetVisibility(false);GazeFilaments->SetVisibility(false);
 for(const auto& FX:GazeGatherSystems)
 {
  FX->SetVisibility(false);if(FX->IsActive())FX->DeactivateImmediate();FX->SetComponentTickEnabled(false);
 }
}

void AHangingBellM09::CaptureGazeAim()
{
 if(Target.IsValid())LockedAim=Target->GetActorLocation()+FVector(0,0,35);
 GazeDirection=(LockedAim-Eye()).GetSafeNormal();
 if(GazeDirection.IsNearlyZero())GazeDirection=GetActorForwardVector();
}

void AHangingBellM09::QueryGazeBeam(FVector& From,FVector& End,FHitResult& Hit) const
{
 From=Eye();
 const FVector Direction=StateSeconds<M09Gaze::Lock?(LockedAim-From).GetSafeNormal():GazeDirection;
 End=From+Direction*M09Gaze::Range;
 FCollisionQueryParams Q(SCENE_QUERY_STAT(M09GazeBeam),false,this);
 const auto Shape=FCollisionShape::MakeSphere(M09Gaze::Radius);
 FHitResult Cover,Pawn;
 // Cover may block Visibility without blocking Pawn. Use the same nearest
 // blocker for the visible ray and all three damage samples.
 const bool WallHit=GetWorld()->SweepSingleByChannel(Cover,From,End,FQuat::Identity,ECC_Visibility,Shape,Q);
 const bool PawnHit=GetWorld()->SweepSingleByChannel(Pawn,From,End,FQuat::Identity,ECC_Pawn,Shape,Q);
 if(WallHit)Hit=Cover;
 if(PawnHit&&(!WallHit||Pawn.Distance<Cover.Distance))Hit=Pawn;
 if(Hit.bBlockingHit)End=Hit.Location;
}

void AHangingBellM09::GazePulse()
{
 if(!HasAuthority()||Dead()||State!=EM09State::Gaze)return;
 FVector From,End;FHitResult Hit;QueryGazeBeam(From,End,Hit);
 if(auto* Victim=Cast<APawn>(Hit.GetActor()))Deal(Victim,MagicAttack*M09Gaze::DamageMultiplier,true,Hit.ImpactPoint);
}

void AHangingBellM09::UpdateGazeFX()
{
 if(State!=EM09State::Gaze)return;
 const float T=StateSeconds;
 const bool Firing=T>=M09Gaze::FirstPulse&&T<M09Gaze::FireEnd;
 const float Fade=1.f-Ease((T-1.92f)/.55f);
 const float Energy=Ease(T/.85f)*Fade;
 const float Discharge=Firing?(.65f+.35f*Ease((T-M09Gaze::FirstPulse)/.035f))*(1.f-Ease((T-1.76f)/.09f)):0.f;
 const float GatherProgress=Ease((T-.08f)/(M09Gaze::FirstPulse-.08f));
 const float GatherFocus=T<M09Gaze::FirstPulse?FMath::Pow(GatherProgress,6.f):0.f;
 const float ReleaseFlash=Firing?1.f-Ease((T-M09Gaze::FirstPulse)/.10f):0.f;
 const auto* PC=GetWorld()->GetFirstPlayerController();
 const bool ChargeInViewRange=PC&&PC->PlayerCameraManager&&
  FVector::DistSquared(PC->PlayerCameraManager->GetCameraLocation(),GetActorLocation())<FMath::Square(3000.f);
 FVector From,End;FHitResult Hit;QueryGazeBeam(From,End,Hit);
 const FVector Delta=End-From,Direction=Delta.GetSafeNormal();
 const float Length=Delta.Size();
 const float MergeDistance=FMath::Min(24.f,Length*.35f);
 const FVector Merge=From+Direction*MergeDistance;
 const float Preview=Ease((T-.30f)/.25f)*.16f;
 const bool BeamVisible=T>=.30f&&T<M09Gaze::FireEnd&&Length>1.f;
 Beam->SetVisibility(BeamVisible);
 if(BeamVisible)Beam->SetWorldTransform(Ribbon(Merge,End,Firing?M09Gaze::Radius:2.8f));
 if(GazeBeamMID)
 {
  GazeBeamMID->SetScalarParameterValue(TEXT("Strength"),Firing?Discharge:Preview);
  GazeBeamMID->SetScalarParameterValue(TEXT("Clock"),T);
  GazeBeamMID->SetScalarParameterValue(TEXT("FirePower"),Discharge);
 }
 GazeIrises->SetVisibility(Energy>.001f);GazeFilaments->SetVisibility(Energy>.001f&&T<M09Gaze::FireEnd&&Length>1.f);
 for(auto* Mat:{GazeIrisMID.Get(),GazeFilamentMID.Get(),GazeImpactMID.Get()})if(Mat)
 {
  Mat->SetScalarParameterValue(TEXT("Strength"),Energy);
  Mat->SetScalarParameterValue(TEXT("Clock"),T);
  Mat->SetScalarParameterValue(TEXT("FirePower"),Discharge);
 }
 if(GazeIrisMID)GazeIrisMID->SetScalarParameterValue(TEXT("Strength"),Energy*(1.f+.65f*GatherFocus+.65f*ReleaseFlash));
 for(int32 I=0;I<M09Gaze::Eyes;++I)
 {
  const FTransform EyeFrame=GetMesh()->GetSocketTransform(EyeNames[I]);
  const FVector Normal=EyeFrame.TransformVectorNoScale(GazeEyeLocalForward[I]).GetSafeNormal();
  const FVector Iris=EyeFrame.GetLocation()+Normal*2.f;
  const float EyeAlpha=Ease((T-.06f-I*.055f)/.38f);
  const float Radius=IrisRadius[I]*(.82f+.18f*Energy);
  GazeIrises->UpdateInstanceTransform(I,FTransform(FRotationMatrix::MakeFromZ(Normal).ToQuat(),Iris,FVector(Radius)),true,false,true);
  GazeIrises->SetCustomDataValue(I,0,EyeAlpha,false);
  if(GazeGatherSystems.IsValidIndex(I))
  {
   auto* Gather=GazeGatherSystems[I].Get();
   const float Begin=.08f+I*.035f;
   const bool Gathering=ChargeInViewRange&&T>=Begin&&T<M09Gaze::FirstPulse;
   if(Gathering)
   {
    // Local +X faces out from the actual iris. All five fields collapse at
    // the same release time; auxiliary eyes remain smaller than the main eye.
    const float Scale=I==0?.90f:.38f;
    Gather->SetWorldTransform(FTransform(FRotationMatrix::MakeFromX(Normal).ToQuat(),Iris,FVector(Scale)));
    Gather->SetVariableFloat(TEXT("User.Charge"),Ease((T-Begin)/(M09Gaze::FirstPulse-Begin)));
    Gather->SetVisibility(true);
    if(!Gather->IsActive()){Gather->SetComponentTickEnabled(true);Gather->Activate(true);}
   }
   else
   {
    Gather->SetVisibility(false);if(Gather->IsActive())Gather->DeactivateImmediate();Gather->SetComponentTickEnabled(false);
   }
  }
  // Curved decorative inflow stays close to the organ and shares the one
  // gameplay beam. It creates neither projectiles nor extra damage tasks.
  const FVector Control=(Iris+Merge)*.5f+Normal*5.f+GetActorRightVector()*((I%2==0?1.f:-1.f)*3.f);
  FVector A=Iris;
  for(int32 Segment=0;Segment<M09Gaze::SegmentsPerEye;++Segment)
  {
   const float U=float(Segment+1)/M09Gaze::SegmentsPerEye;
   const FVector B=FMath::Square(1.f-U)*Iris+2.f*(1.f-U)*U*Control+U*U*Merge;
   const int32 Index=I*M09Gaze::SegmentsPerEye+Segment;
   GazeFilaments->UpdateInstanceTransform(Index,Ribbon(A,B,Firing?1.7f:1.15f),true,false,true);
   GazeFilaments->SetCustomDataValue(Index,0,EyeAlpha*Ease((T-.22f)/.4f)*(Firing?1.f:.32f),false);
   A=B;
  }
 }
 GazeIrises->MarkRenderStateDirty();GazeFilaments->MarkRenderStateDirty();
 const bool Impact=Firing&&Hit.bBlockingHit&&!Hit.bStartPenetrating;
 Charge->SetVisibility(Impact);
 if(Impact)
 {
  Charge->SetWorldTransform(FTransform(FRotationMatrix::MakeFromZ(Hit.ImpactNormal).ToQuat(),Hit.ImpactPoint+Hit.ImpactNormal*.7f,FVector(12.f)));
  if(GazeImpactMID)GazeImpactMID->SetScalarParameterValue(TEXT("Strength"),Discharge*.8f);
 }
}
