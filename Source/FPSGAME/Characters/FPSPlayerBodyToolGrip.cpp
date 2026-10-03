#include "FPSPlayerBodyComponent.h"
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSBodyWeaponMeshComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Math/RotationMatrix.h"

namespace
{
TArray<FTransform> Compose(const FReferenceSkeleton& Ref,const TArray<FTransform>& Local)
{
    auto Result=Local;
    for(int32 B=0;B<Result.Num();++B)if(Ref.GetParentIndex(B)>=0)Result[B]=Result[B]*Result[Ref.GetParentIndex(B)];
    return Result;
}
// One equipment-time fit. Keep native segment lengths and the donor's bend
// plane; move distal joint centers onto the shaft plus soft-tissue clearance.
FTransform FitShaft(const FReferenceSkeleton& Ref,const FFPSBodyGripRig& Rig,TArray<FTransform>& Local,
    const FVector& ModelPoint,const FVector& Scale,const FQuat& Preferred)
{
    auto Pose=Compose(Ref,Local);FTransform Hand=Pose[Rig.TargetHand];Hand.SetScale3D(FVector::OneVector);
    const auto Point=[&](int32 B){return Hand.InverseTransformPosition(Pose[B].GetLocation());};
    FVector Axis=(Point(Rig.Digits[1].Target[0])-Point(Rig.Digits[4].Target[0])).GetSafeNormal();
    if(FVector::DotProduct(Axis,Preferred.GetAxisX())<0.f)Axis=-Axis;
    FVector Center=FVector::ZeroVector;
    for(int32 D=1;D<5;++D)Center+=(Point(Rig.Digits[D].Target[0])+Point(Rig.Digits[D].Target[2]))*.125;
    const FVector Palm=Point(Rig.Digits[2].Target[0]);
    // Source shaft radius is about 1.8 cm; the active mesh uses scale 0.8.
    const double Radius=1.8*FMath::Max(Scale.Y,Scale.Z)+.55;
    const FVector Away=(Center-Palm-Axis*FVector::DotProduct(Center-Palm,Axis)).GetSafeNormal();
    Center=Palm+Away*Radius;
    for(const auto& Digit:Rig.Digits)
    {
        const FVector Root=Point(Digit.Target[0]),Pole=Point(Digit.Target[1]),Tip=Point(Digit.Target[2]);
        const FVector OnAxis=Center+Axis*FVector::DotProduct(Tip-Center,Axis);
        const FVector Radial=(Tip-OnAxis).GetSafeNormal();
        const FVector Goal=OnAxis+Radial*Radius;
        const double L1=FVector::Distance(Root,Pole),L2=FVector::Distance(Pole,Tip);
        const FVector Direction=(Goal-Root).GetSafeNormal();
        const double Reach=FMath::Clamp(FVector::Distance(Root,Goal),FMath::Abs(L1-L2)+.001,L1+L2-.001);
        FVector Bend=(Pole-Root-Direction*FVector::DotProduct(Pole-Root,Direction)).GetSafeNormal();
        if(Bend.IsNearlyZero())Bend=Away;
        const double Along=(L1*L1-L2*L2+Reach*Reach)/(2.*Reach);
        const FVector Elbow=Root+Direction*Along+Bend*FMath::Sqrt(FMath::Max(0.,L1*L1-Along*Along));
        const FVector Segments[]={Elbow-Root,Root+Direction*Reach-Elbow};
        for(int32 J=0;J<2;++J)
        {
            const int32 Bone=Digit.Target[J],Child=Digit.Target[J+1],Parent=Ref.GetParentIndex(Bone);
            const FVector Before=Hand.GetRotation().UnrotateVector(Pose[Child].GetLocation()-Pose[Bone].GetLocation());
            const FQuat Change=FQuat::FindBetweenNormals(Before.GetSafeNormal(),Segments[J].GetSafeNormal());
            const FQuat Desired=Hand.GetRotation()*Change*Hand.GetRotation().Inverse()*Pose[Bone].GetRotation();
            Local[Bone].SetRotation((Pose[Parent].GetRotation().Inverse()*Desired).GetNormalized());
            Pose=Compose(Ref,Local);
        }
    }
    // Native half-joints retain their inverse half correction after the fit.
    for(int32 B:Rig.Descendants)if(Rig.HalfJoint[B])
    {
        const int32 P=Ref.GetParentIndex(B);
        const FQuat Delta=Ref.GetRefBonePose()[P].GetRotation().Inverse()*Local[P].GetRotation();
        Local[B].SetRotation((FQuat::Slerp(FQuat::Identity,Delta.Inverse(),.5f)*Ref.GetRefBonePose()[B].GetRotation()).GetNormalized());
    }
    const FQuat Rotation=FRotationMatrix::MakeFromXZ(Axis,Preferred.GetAxisZ()).ToQuat();
    return FTransform(Rotation,Center-Rotation.RotateVector(ModelPoint*Scale),Scale);
}
}

void UFPSPlayerBodyComponent::BuildShovelGrip(const FFPSBodyWeapon& Definition,UStaticMeshComponent& Part)
{
    if(!BodyAnimation||!GetBodyMesh()||!GetBodyMesh()->GetSkeletalMeshAsset())return;
    auto* Donor=Definition.Mesh.LoadSynchronous();auto* Clip=Definition.HoldClip.LoadSynchronous();if(!Donor||!Clip)return;
    auto* Sampler=NewObject<UFPSBodyWeaponMeshComponent>(GetOwner(),NAME_None,RF_Transient);
    Sampler->SetVisibility(false);Sampler->SetCollisionEnabled(ECollisionEnabled::NoCollision);Sampler->SetSkeletalMeshAsset(Donor);
    Sampler->RegisterComponent();Sampler->SetAnimationMode(EAnimationMode::AnimationSingleNode);
    Sampler->PlayAnimation(Clip,false);Sampler->SetPosition(0.f,false);Sampler->SetPlayRate(0.f);
    Sampler->TickAnimation(0.f,false);Sampler->RefreshBoneTransforms();
    const auto SourcePose=Sampler->GetComponentSpaceTransforms();Sampler->DestroyComponent();
    const auto& Ref=GetBodyMesh()->GetSkeletalMeshAsset()->GetRefSkeleton();
    FFPSBodyGripRig Rigs[2];FTransform Mounts[2];
    for(int32 Side=0;Side<2;++Side)
    {
        const FName Hand=Side==0?TEXT("hand_r"):TEXT("hand_l");
        Rigs[Side].Initialize(Donor->GetRefSkeleton(),Ref,Hand,Hand);if(!Rigs[Side].IsValid())return;
        Rigs[Side].Transfer(SourcePose,BodyAnimation->EquipmentFingers);
        // Geometry source: shovel-vertices.json. X is the shaft; both positions
        // stay between the D handle and the metal blade, 25 cm apart unscaled.
        const FVector Contact=Side==0?FVector(-31,.4,1.9):FVector(-6,.55,2.1);
        FQuat Preferred=Definition.StaticGrip.GetRotation();
        if(Side==1)
        {
            const auto& Right=Rigs[0];
            Preferred=(Rigs[Side].TargetBind[Rigs[Side].TargetHand].GetRotation().Inverse()
                *Right.TargetBind[Right.TargetHand].GetRotation()*Preferred).GetNormalized();
        }
        Mounts[Side]=FitShaft(Ref,Rigs[Side],BodyAnimation->EquipmentFingers,Contact,Definition.StaticGrip.GetScale3D(),Preferred);
    }
    Part.SetRelativeTransform(Mounts[0]);
    BodyAnimation->EquipmentGripHands=3;BodyAnimation->bHasLeftGrip=true;
    BodyAnimation->LeftGripFromRight=Mounts[1].Inverse()*Mounts[0];
    BodyAnimation->LeftGripFromRight.SetScale3D(FVector::OneVector);
}
