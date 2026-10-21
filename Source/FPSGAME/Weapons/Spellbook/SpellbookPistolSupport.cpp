#include "SpellbookComponent.h"
#include "SpellbookCarryTuning.h"
#include "SpellbookPistolSupportTuning.h"
#include "SpellbookPistolArmSolver.h"
#include "SpellbookPistolThumbPose.h"
#include "../../FPSGAMECharacter.h"
#include "../../Characters/FPSPlayerBodyComponent.h"
#include "../../Items/FPSPotionUseComponent.h"
#include "../../Skills/FPSFireballComponent.h"
#include "Camera/CameraComponent.h"
#include "Engine/SkeletalMesh.h"

void USpellbookArmsMeshComponent::CachePistolSupport()
{
    PistolSupportBase=CarryKeys[0];PistolSupportLocal=CarryKeys[0];
    const auto& Ref=GetSkeletalMeshAsset()->GetRefSkeleton();
    for(int32 I=0;I<PistolSupportBase.Num();++I)
        if(const int32 P=Ref.GetParentIndex(I);P>=0)PistolSupportBase[I]*=PistolSupportBase[P];
    PistolSupportComponent=PistolSupportBase;PistolSupportSource=PistolSupportBase;
    PistolSupportGun.Reset();PistolRightHand=PistolRightLower=INDEX_NONE;
    PistolSupportWeight=PistolRightWeight=PistolAimWeight=0.f;PistolContactAlpha=1.f;
    bPistolSupportAnchor=bPistolSupportPair=bPistolSupportHold=false;
    PistolTwist01=Ref.FindBoneIndex(TEXT("lowerarm_twist_01_l"));
    PistolTwist02=Ref.FindBoneIndex(TEXT("lowerarm_twist_02_l"));
    for(int32 B=0;B<3;++B)PistolThumbBones[B]=Ref.FindBoneIndex(SpellbookPistolThumbPose::Names[B]);
    const int32 H=Ref.FindBoneIndex(TEXT("hand_l")),M=Ref.FindBoneIndex(TEXT("middle_01_l"));
    const int32 I=Ref.FindBoneIndex(TEXT("index_01_l")),P=Ref.FindBoneIndex(TEXT("pinky_01_l"));
    if(H<0||M<0||I<0||P<0)return;
    const FVector Origin=Reference[H].GetLocation();
    const FVector Forward=Reference[M].GetLocation()-Origin;
    const FVector Dorsal=-((Reference[I].GetLocation()-Origin)^(Reference[P].GetLocation()-Origin));
    namespace T=SpellbookPistolSupport;
    const FQuat Palm=FRotationMatrix::MakeFromXZ(Forward,Dorsal).ToQuat();
    const FQuat ToNative=Palm.Inverse()*Reference[H].GetRotation();
    PistolHipHandRotation=(FRotationMatrix::MakeFromXZ(T::HipFingerDirection,T::HipDorsalDirection).ToQuat()*ToNative).GetNormalized();
    PistolAimHandRotation=(FRotationMatrix::MakeFromXZ(T::AimFingerDirection,T::AimDorsalDirection).ToQuat()*ToNative).GetNormalized();
}

void USpellbookArmsMeshComponent::AdvancePistolSupport(float Delta,bool Equipped)
{
    CachePose();
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* Body=Pawn?Pawn->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    const auto* Gun=Pawn?Pawn->AKMViewmodel.Get():nullptr;
    bPistolSupportPair=Equipped&&GetSkeletalMeshAsset()&&Pawn&&Pawn->IsLocallyControlled()&&Pawn->HasInventoryWeapon()&&
        Pawn->IsPistolWeapon()&&!Pawn->HasOffhandPistol()&&!Pawn->IsSwitchingWeapon()&&!Pawn->IsTraversing()&&
        Pawn->GetWeaponState()!=EAKMWeaponState::Equipping&&Gun&&Gun->GetSkeletalMeshAsset()&&
        !(Body&&Body->IsThirdPersonViewEnabled());
    if(!bPistolSupportPair)
    {
        PistolSupportWeight=PistolRightWeight=PistolAimWeight=0.f;
        bPistolSupportAnchor=bPistolSupportHold=false;PistolSupportGun.Reset();return;
    }
    if(PistolSupportGun.Get()!=Gun->GetSkeletalMeshAsset())
    {
        PistolSupportGun=Gun->GetSkeletalMeshAsset();
        const auto& Ref=PistolSupportGun->GetRefSkeleton();
        PistolRightClavicle=Ref.FindBoneIndex(TEXT("clavicle_r"));
        PistolRightUpper=Ref.FindBoneIndex(TEXT("upperarm_r"));
        PistolRightLower=Ref.FindBoneIndex(TEXT("lowerarm_r"));
        PistolRightHand=Ref.FindBoneIndex(TEXT("hand_r"));
        PistolRightTwist01=Ref.FindBoneIndex(TEXT("lowerarm_twist_01_r"));
        PistolRightTwist02=Ref.FindBoneIndex(TEXT("lowerarm_twist_02_r"));
        PistolRightReference=Ref.GetRefBonePose();PistolRightBones.Reset();
        for(int32 I=0;I<Ref.GetNum();++I)
        {
            if(const int32 P=Ref.GetParentIndex(I);P>=0)PistolRightReference[I]*=PistolRightReference[P];
            if(PistolRightClavicle>=0&&(I==PistolRightClavicle||Ref.BoneIsChildOf(I,PistolRightClavicle)))PistolRightBones.Add(I);
        }
        PistolRightSource=PistolRightReference;PistolRightTarget=PistolRightReference;
        bPistolSupportAnchor=false;PistolSupportWeight=PistolRightWeight=PistolAimWeight=0.f;
    }
    const auto Phase=Pawn->GetOffhandReloadPhase();
    const auto* Potion=Pawn->FindComponentByClass<UFPSPotionUseComponent>();
    const auto* Magic=Pawn->FindComponentByClass<UFPSFireballComponent>();
    const auto* Book=Pawn->FindComponentByClass<USpellbookComponent>();
    bPistolSupportHold=Phase==EOffhandReloadPhase::Lower||Phase==EOffhandReloadPhase::Reload||
        (Potion&&Potion->IsStowingOffhand()&&!Potion->IsOffhandWeaponHidden())||
        (Pawn->GetWeaponState()!=EAKMWeaponState::Idle&&Phase!=EOffhandReloadPhase::Raise);
    const bool Ready=Pawn->GetWeaponState()==EAKMWeaponState::Idle&&!Pawn->IsSprinting()&&
        !Pawn->IsOffhandReloadActive()&&!(Potion&&Potion->IsActive())&&!Pawn->IsDoorPushActive()&&
        !(Magic&&Magic->IsOccupyingLeftHand())&&!(Book&&Book->IsQuickCombatActive());
    namespace T=SpellbookPistolSupport;
    // One clock before the viewmodel and both mesh evaluations. Action overlays
    // still own their hands; framing fades back to the native action anchor.
    PistolRightWeight=FMath::FInterpConstantTo(PistolRightWeight,Ready?1.f:0.f,Delta,1.f/T::ContactReturnSeconds);
    if(bPistolSupportHold)return;
    const bool Aim=Ready&&Pawn->IsAiming();
    PistolAimWeight=FMath::FInterpConstantTo(PistolAimWeight,Aim?1.f:0.f,Delta,
        1.f/(Aim?T::AimInSeconds:T::AimOutSeconds));
    PistolSupportWeight=FMath::FInterpConstantTo(PistolSupportWeight,Pawn->IsSprinting()?0.f:1.f,Delta,1.f/T::BlendSeconds);
}

void USpellbookArmsMeshComponent::UpdatePistolSupport(float Delta,bool Equipped)
{
    if(!Equipped||!bPistolSupportPair)return;
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* Gun=Pawn?Pawn->AKMViewmodel.Get():nullptr;
    if(!Gun||PistolRightHand<0||!Pawn->FirstPersonCamera)return;
    if(bPistolSupportHold)
    {
        if(bPistolSupportAnchor){PistolSupportEntry=PistolSupportWrist;PistolContactAlpha=0.f;}
        return;
    }
    namespace T=SpellbookPistolSupport;
    const FVector Right=Pawn->FirstPersonCamera->GetComponentTransform().InverseTransformPosition(
        Gun->GetBoneTransform(PistolRightHand).GetLocation());
    const FVector AimWrist=Right+T::WristFromGunHand;
    const float Cross=FMath::SmoothStep(.18f,.9f,PistolAimWeight);
    const float Lift=FMath::SmoothStep(0.f,.72f,PistolAimWeight);
    const float Arc=FMath::Sin(PI*PistolAimWeight);
    FVector Target=FMath::Lerp(T::HipWrist,AimWrist,Cross);
    Target.Z=FMath::Lerp(T::HipWrist.Z,AimWrist.Z,Lift)+T::TransferLiftCm*Arc;
    Target.X+=T::TransferForwardCm*Arc;
    // This layer runs before the shared carry/stow translation.
    Target.Z+=SpellbookCarryTuning::LowerCm;
    if(!bPistolSupportAnchor){PistolSupportEntry=Target;PistolContactAlpha=1.f;bPistolSupportAnchor=true;}
    PistolContactAlpha=FMath::Min(1.f,PistolContactAlpha+Delta/T::ContactReturnSeconds);
    PistolSupportWrist=FMath::Lerp(PistolSupportEntry,Target,T::Ease(PistolContactAlpha));
}

void USpellbookArmsMeshComponent::ApplyPistolSupport(TArray<FTransform>& LocalPose)
{
    // Outside ADS leave the original book carry and its live gait untouched.
    // The paired arm, downward book and thumb correction belong to ADS only.
    if(!bPistolSupportAnchor||PistolSupportWeight<=UE_SMALL_NUMBER||PistolAimWeight<=UE_SMALL_NUMBER||LeftBones.Num()<6||
        PistolSupportBase.Num()!=LocalPose.Num())return;
    const int32 C=LeftBones[0],U=LeftBones[1],E=LeftBones[2],H=LeftBones[5];
    if(C<0||U<0||E<0||H<0)return;
    const auto& Ref=GetSkeletalMeshAsset()->GetRefSkeleton();
    PistolSupportSource=LocalPose;
    for(int32 I=0;I<LocalPose.Num();++I)
        if(const int32 P=Ref.GetParentIndex(I);P>=0)PistolSupportSource[I]*=PistolSupportSource[P];
    namespace T=SpellbookPistolSupport;
    const float Aim=T::Ease(PistolAimWeight);
    const FVector Low(0,0,SpellbookCarryTuning::LowerCm);
    const FVector Gait=(PistolSupportSource[H].GetLocation()-PistolSupportBase[H].GetLocation())*(1.f-Aim);
    const FVector Wrist=PistolSupportWrist+Gait;
    const FVector Shoulder=FMath::Lerp(T::HipShoulder,T::AimShoulder,Aim)+Low;
    const FVector Pole=FMath::Lerp(T::HipPole+Low,Wrist+T::AimPoleFromWrist,Aim);
    const FQuat Hand=FQuat::Slerp(PistolHipHandRotation,PistolAimHandRotation,Aim).GetNormalized();
    const SpellbookPistolArm::FJoints J{C,U,E,H,PistolTwist01,PistolTwist02};
    SpellbookPistolArm::Solve(Ref,Reference,PistolSupportSource,LeftBones,J,Shoulder,Wrist,Pole,
        Hand,T::AimHandRollDegrees*Aim,1.f,PistolSupportComponent);
    // The old book clamp twisted the thumb root and counter-bent its tip.
    // Correct only these three native local rotations. Keep the accepted palm,
    // wrist, book mount and every other finger exactly on their existing path.
    for(int32 B=0;B<3;++B)if(const int32 I=PistolThumbBones[B];I>=0)
    {
        const int32 Parent=Ref.GetParentIndex(I);
        FTransform ThumbLocal=PistolSupportSource[I].GetRelativeTransform(PistolSupportSource[Parent]);
        ThumbLocal.SetRotation(SpellbookPistolThumbPose::Rotations[B]);
        PistolSupportComponent[I]=ThumbLocal*PistolSupportComponent[Parent];
    }
    // Fade the whole local chain from the original carry. At full ADS this is
    // the same V5 endpoint; releasing ADS returns exactly to the original pose.
    const float Weight=PistolSupportBlend()*Aim;
    for(const int32 I:LeftBones)if(I>=0)
    {
        const int32 Parent=Ref.GetParentIndex(I);
        PistolSupportLocal[I]=Parent>=0?PistolSupportComponent[I].GetRelativeTransform(PistolSupportComponent[Parent]):PistolSupportComponent[I];
        FTransform Mixed;Mixed.Blend(LocalPose[I],PistolSupportLocal[I],Weight);LocalPose[I]=Mixed;
    }
}

void USpellbookArmsMeshComponent::ApplyPistolRightArm(USkeletalMeshComponent& Gun,TArray<FTransform>& Pose)
{
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    const float Weight=PistolRightBlend();
    if(!bPistolSupportPair||Weight<=UE_SMALL_NUMBER||!Pawn||Pawn->AKMViewmodel.Get()!=&Gun||
        !Pawn->FirstPersonCamera||PistolSupportGun.Get()!=Gun.GetSkeletalMeshAsset()||
        PistolRightClavicle<0||PistolRightUpper<0||PistolRightLower<0||PistolRightHand<0||
        Pose.Num()!=PistolRightReference.Num())return;
    const FTransform ToCamera=Gun.GetComponentTransform().GetRelativeTransform(Pawn->FirstPersonCamera->GetComponentTransform());
    const FTransform ToMesh=Pawn->FirstPersonCamera->GetComponentTransform().GetRelativeTransform(Gun.GetComponentTransform());
    for(int32 I=0;I<Pose.Num();++I)PistolRightSource[I]=Pose[I]*ToCamera;
    namespace T=SpellbookPistolSupport;
    const FVector Shoulder=FMath::Lerp(PistolRightSource[PistolRightUpper].GetLocation(),T::RightShoulder,Weight);
    const FVector Pole=FMath::Lerp(PistolRightSource[PistolRightLower].GetLocation(),
        FMath::Lerp(T::RightHipPole,T::RightAimPole,T::Ease(PistolAimWeight)),Weight);
    const auto& Ref=Gun.GetSkeletalMeshAsset()->GetRefSkeleton();
    const SpellbookPistolArm::FJoints J{PistolRightClavicle,PistolRightUpper,PistolRightLower,PistolRightHand,PistolRightTwist01,PistolRightTwist02};
    SpellbookPistolArm::Solve(Ref,PistolRightReference,PistolRightSource,PistolRightBones,J,Shoulder,
        PistolRightSource[PistolRightHand].GetLocation(),Pole,PistolRightSource[PistolRightHand].GetRotation(),
        0.f,Weight,PistolRightTarget);
    for(const int32 I:PistolRightBones)
    {
        // Exact original hand/fingers and gun transforms survive even during
        // entry/exit. Only the shoulder, elbow and arm helpers are recomposed.
        if(I==PistolRightHand||Ref.BoneIsChildOf(I,PistolRightHand))continue;
        Pose[I]=PistolRightTarget[I]*ToMesh;
    }
}
