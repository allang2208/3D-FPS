#include "KukriArmsMeshComponent.h"
#include "../../FPSGAMECharacter.h"
#include "Engine/SkeletalMesh.h"

namespace KukriGrip
{
    // Authored fist->grip relation (WPN_root relative to hand_r, component space, rig units), identical in
    // every Kukri clip: SourceAssets/Kukri20261020 kukri_rig.hand_rel and the Clips json files.
    inline FTransform HandToWeapon()
    {
        return FTransform(FQuat(-0.05378413,-0.02831518,0.98366476,-0.16943777).GetNormalized(),
            FVector(-0.07248964,0.02259467,-0.00225821),FVector::OneVector);
    }
    // Authored deviation from the grip (cm, 1 deg counts as 0.25 cm) below which the lock holds, and above which the
    // clip's own WPN_root plays: the toss-and-catch draw flies the knife out of the fist between release and catch.
    // Resampling drift between the two bone chains stays in the millimetres.
    inline constexpr float HoldBand=.6f, ReleaseBand=2.5f, DegreeToCm=.25f;
}

void UKukriArmsMeshComponent::CacheBones()
{
    auto* Mesh=GetSkeletalMeshAsset();
    if(!Mesh||CachedMesh.Get()==Mesh)return;
    CachedMesh=Mesh;EntryLocal.Reset();LeftChain.Reset();
    const auto& Ref=Mesh->GetRefSkeleton();
    HandR=Ref.FindBoneIndex(TEXT("hand_r"));
    Weapon=Ref.FindBoneIndex(TEXT("WPN_root"));
    ClavicleL=Ref.FindBoneIndex(TEXT("clavicle_l"));
    if(ClavicleL!=INDEX_NONE)
        for(int32 I=0;I<Ref.GetNum();++I)
            if(I==ClavicleL||Ref.BoneIsChildOf(I,ClavicleL))LeftChain.Add(I);
    WeaponChain.Reset();
    if(Weapon!=INDEX_NONE)
        for(int32 I=0;I<Ref.GetNum();++I)
            if(Ref.BoneIsChildOf(I,Weapon))WeaponChain.Add(I);
}

void UKukriArmsMeshComponent::CaptureEntry(float Seconds)
{
    CacheBones();
    const auto* Mesh=GetSkeletalMeshAsset();
    const auto& Pose=GetComponentSpaceTransforms();
    if(!Mesh||Pose.Num()!=Mesh->GetRefSkeleton().GetNum()){EntryLocal.Reset();return;}
    // Store the displayed pose in parent space: a local blend keeps every segment length.
    const auto& Ref=Mesh->GetRefSkeleton();
    EntryLocal.SetNum(Pose.Num());
    for(int32 I=0;I<Pose.Num();++I)
    {
        const int32 Parent=Ref.GetParentIndex(I);
        EntryLocal[I]=Parent>=0?Pose[I].GetRelativeTransform(Pose[Parent]):Pose[I];
    }
    EntryTime=0.f;EntryDuration=FMath::Max(.01f,Seconds);
}

void UKukriArmsMeshComponent::AdvanceEntry(float Delta)
{
    if(EntryLocal.IsEmpty())return;
    EntryTime+=FMath::Max(0.f,Delta);
    if(EntryTime>=EntryDuration)ClearEntry();
}

void UKukriArmsMeshComponent::FinalizeBoneTransform()
{
    CacheBones();
    const auto* Mesh=GetSkeletalMeshAsset();
    auto& Pose=GetEditableComponentSpaceTransforms();
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    const bool OffhandLeft=Player&&(Player->HasOffhandPistol()||Player->IsOffhandSpellbookPresented());
    bApplyLeftHandCast=!OffhandLeft;
    if(Mesh&&Pose.Num()==Mesh->GetRefSkeleton().GetNum())
    {
        const auto& Ref=Mesh->GetRefSkeleton();
        if(EntryLocal.Num()==Pose.Num()&&EntryDuration>0.f)
        {
            const float X=FMath::Clamp(EntryTime/EntryDuration,0.f,1.f);
            const float Alpha=X*X*X*(X*(X*6.f-15.f)+10.f);
            // The kukri is rigid in the right fist in every clip: carry it with the
            // blended hand instead of interpolating the weapon bone independently.
            const bool Grip=HandR!=INDEX_NONE&&Weapon!=INDEX_NONE;
            const FTransform HandToWeapon=Grip?Pose[Weapon].GetRelativeTransform(Pose[HandR]):FTransform::Identity;
            TArray<FTransform> Local;Local.SetNum(Pose.Num());
            for(int32 I=0;I<Pose.Num();++I)
            {
                const int32 Parent=Ref.GetParentIndex(I);
                const FTransform Target=Parent>=0?Pose[I].GetRelativeTransform(Pose[Parent]):Pose[I];
                FTransform Blend;Blend.Blend(EntryLocal[I],Target,Alpha);
                Local[I]=Blend;
            }
            for(int32 I=0;I<Pose.Num();++I)
            {
                const int32 Parent=Ref.GetParentIndex(I);
                Pose[I]=Parent>=0?Local[I]*Pose[Parent]:Local[I];
                if(Grip&&I==Weapon)Pose[I]=HandToWeapon*Pose[HandR];
            }
        }
        if(HandR!=INDEX_NONE&&Weapon!=INDEX_NONE)
        {
            // Grip lock: every authored clip holds the kukri with one constant fist->grip relation.
            // Re-impose it after sampling so resampling/compression of the two separate bone
            // chains (clavicle..hand_r vs root..ik_hand_gun..WPN_root) can never let the blade
            // swim against the fist.  The WPN subtree is carried rigidly.
            // Where the clip itself takes the knife out of the fist (the draw's toss), the lock fades out with the
            // authored deviation and the flight plays as authored; it fades back in as the catch closes on the grip.
            const FTransform Old=Pose[Weapon];
            const FTransform Locked=KukriGrip::HandToWeapon()*Pose[HandR];
            const float Deviation=FVector::Dist(Old.GetLocation(),Locked.GetLocation())
                +FMath::RadiansToDegrees(Old.GetRotation().AngularDistance(Locked.GetRotation()))*KukriGrip::DegreeToCm;
            const float Free=FMath::SmoothStep(KukriGrip::HoldBand,KukriGrip::ReleaseBand,Deviation);
            FTransform Final=Locked;
            if(Free>0.f)Final.Blend(Locked,Old,Free);
            for(const int32 I:WeaponChain)Pose[I]=Pose[I].GetRelativeTransform(Old)*Final;
            Pose[Weapon]=Final;
        }
        if(OffhandLeft&&!LeftChain.IsEmpty())
        {
            // Zero scale alone leaves weighted vertices spanning separated joints.
            // Collapse the chain onto the shoulder so outfit followers vanish too.
            const FTransform Hidden(FQuat::Identity,Pose[LeftChain[0]].GetLocation(),FVector::ZeroVector);
            for(const int32 I:LeftChain)Pose[I]=Hidden;
        }
    }
    Super::FinalizeBoneTransform();
}
