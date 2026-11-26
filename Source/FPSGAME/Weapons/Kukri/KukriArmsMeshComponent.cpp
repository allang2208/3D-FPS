#include "KukriArmsMeshComponent.h"
#include "KukriLeftRest.h"
#include "../../FPSGAMECharacter.h"
#include "../../Items/FPSPotionUseComponent.h"
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
    CachedMesh=Mesh;EntryLocal.Reset();LeftChain.Reset();RightChain.Reset();
    const auto& Ref=Mesh->GetRefSkeleton();
    HandR=Ref.FindBoneIndex(TEXT("hand_r"));
    HandL=Ref.FindBoneIndex(TEXT("hand_l"));
    Weapon=Ref.FindBoneIndex(TEXT("WPN_root"));
    ClavicleL=Ref.FindBoneIndex(TEXT("clavicle_l"));
    const int32 ClavicleR=Ref.FindBoneIndex(TEXT("clavicle_r"));
    if(ClavicleR!=INDEX_NONE)
        for(int32 I=0;I<Ref.GetNum();++I)
            if(I==ClavicleR||Ref.BoneIsChildOf(I,ClavicleR))RightChain.Add(I);
    if(ClavicleL!=INDEX_NONE)
        for(int32 I=0;I<Ref.GetNum();++I)
            if(I==ClavicleL||Ref.BoneIsChildOf(I,ClavicleL))LeftChain.Add(I);
    // Mesh X is camera left/right (this rig is attached with yaw 90). Conjugate rotations
    // through that plane, then restore each left bone's native binding and segment length.
    MirrorReferenceLocal=Ref.GetRefBonePose();
    TArray<FTransform> Bind=MirrorReferenceLocal;
    for(int32 I=0;I<Bind.Num();++I)
    {const int32 Parent=Ref.GetParentIndex(I);if(Parent>=0)Bind[I]=Bind[I]*Bind[Parent];}
    MirrorSources.Reset();MirrorBindCorrection.Reset();
    for(const int32 L:LeftChain)
    {
        const FString Name=Ref.GetBoneName(L).ToString();
        const int32 R=Name.EndsWith(TEXT("_l"))?Ref.FindBoneIndex(FName(Name.LeftChop(2)+TEXT("_r"))):INDEX_NONE;
        MirrorSources.Add(R);
        const FQuat Q=R>=0?Bind[R].GetRotation():FQuat::Identity;
        const FQuat Mirrored(Q.X,-Q.Y,-Q.Z,Q.W);
        MirrorBindCorrection.Add(R>=0?(Mirrored.Inverse()*Bind[L].GetRotation()).GetNormalized():FQuat::Identity);
        if(L==ClavicleL&&R>=0)
        {
            const FVector RP=Bind[R].GetLocation();
            MirrorClavicleOffset=Bind[L].GetLocation()-FVector(-RP.X,RP.Y,RP.Z);
        }
    }
    WeaponChain.Reset();
    if(Weapon!=INDEX_NONE)
        for(int32 I=0;I<Ref.GetNum();++I)
            if(Ref.BoneIsChildOf(I,Weapon))WeaponChain.Add(I);
    MirrorHandL=LeftChain.IndexOfByKey(HandL);
    // Hidden on a left-hand-only rig: the right arm and the right weapon chain.
    HiddenRight.Init(false,Ref.GetNum());
    for(const int32 I:RightChain)HiddenRight[I]=true;
    if(Weapon!=INDEX_NONE)HiddenRight[Weapon]=true;
    for(const int32 I:WeaponChain)HiddenRight[I]=true;
}

void UKukriArmsMeshComponent::MirrorRightPose(TArray<FTransform>& Pose) const
{
    const auto& Ref=GetSkeletalMeshAsset()->GetRefSkeleton();
    for(int32 K=0;K<LeftChain.Num();++K)
    {
        const int32 L=LeftChain[K],R=MirrorSources[K],Parent=Ref.GetParentIndex(L);
        if(R==INDEX_NONE)continue;
        const FQuat Q=Pose[R].GetRotation();
        const FQuat Goal=(FQuat(Q.X,-Q.Y,-Q.Z,Q.W)*MirrorBindCorrection[K]).GetNormalized();
        FTransform Local=MirrorReferenceLocal[L];
        Local.SetRotation(Parent>=0?(Pose[Parent].GetRotation().Inverse()*Goal).GetNormalized():Goal);
        Pose[L]=Parent>=0?Local*Pose[Parent]:Local;
        if(L==ClavicleL)
        {
            const FVector RP=Pose[R].GetLocation();
            Pose[L].SetLocation(FVector(-RP.X,RP.Y,RP.Z)+MirrorClavicleOffset);
        }
    }
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

void UKukriArmsMeshComponent::CaptureLeftEntry(float Seconds)
{
    CacheBones();
    const auto* Mesh=GetSkeletalMeshAsset();
    const auto& Pose=GetComponentSpaceTransforms();
    LeftEntryLocal.Reset();
    if(!Mesh||Pose.Num()!=Mesh->GetRefSkeleton().GetNum()||LeftChain.IsEmpty())return;
    const auto& Ref=Mesh->GetRefSkeleton();
    for(const int32 I:LeftChain)
    {
        const int32 Parent=Ref.GetParentIndex(I);
        LeftEntryLocal.Add(Parent>=0?Pose[I].GetRelativeTransform(Pose[Parent]):Pose[I]);
    }
    LeftEntryTime=0.f;LeftEntryDuration=FMath::Max(.01f,Seconds);
}

void UKukriArmsMeshComponent::SetLeftArmRest(float Weight,float Seconds)
{
    Weight=FMath::Clamp(Weight,0.f,1.f);
    if(FMath::IsNearlyEqual(Weight,LeftRestTarget,1e-4f))return;
    LeftRestFrom=LeftRestWeight;LeftRestTarget=Weight;
    LeftRestSeconds=FMath::Max(.01f,Seconds);LeftRestTime=0.f;
}

void UKukriArmsMeshComponent::AdvanceEntry(float Delta)
{
    if(FMath::IsNearlyEqual(LeftRestWeight,LeftRestTarget,1e-4f)==false)
    {
        LeftRestTime+=FMath::Max(0.f,Delta);
        const float X=FMath::Clamp(LeftRestTime/FMath::Max(.01f,LeftRestSeconds),0.f,1.f);
        const float E=X*X*X*(X*(X*6.f-15.f)+10.f);
        LeftRestWeight=FMath::Lerp(LeftRestFrom,LeftRestTarget,E);
        if(X>=1.f){LeftRestWeight=LeftRestTarget;LeftRestTime=0.f;LeftRestSeconds=.01f;}
    }
    if(!LeftEntryLocal.IsEmpty())
    {
        LeftEntryTime+=FMath::Max(0.f,Delta);
        if(LeftEntryTime>=LeftEntryDuration){LeftEntryLocal.Reset();LeftEntryTime=LeftEntryDuration=0.f;}
    }
    if(EntryLocal.IsEmpty())return;
    EntryTime+=FMath::Max(0.f,Delta);
    if(EntryTime>=EntryDuration){EntryLocal.Reset();EntryTime=EntryDuration=0.f;}
}

void UKukriArmsMeshComponent::FinalizeBoneTransform()
{
    CacheBones();
    const auto* Mesh=GetSkeletalMeshAsset();
    auto& Pose=GetEditableComponentSpaceTransforms();
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    const bool OffhandLeft=!bLeftHandOnly&&(bRightHandOnly||(Player&&(Player->HasOffhandPistol()||Player->IsOffhandSpellbookPresented())));
    bApplyLeftHandCast=!OffhandLeft;
    if(Mesh&&Pose.Num()==Mesh->GetRefSkeleton().GetNum())
    {
        const auto& Ref=Mesh->GetRefSkeleton();
        if(bMirrorRightToLeft)
        {
            MirrorRightPose(Pose);
            if(HandR!=INDEX_NONE&&Weapon!=INDEX_NONE&&MirrorHandL!=INDEX_NONE)
            {
                // Lone off-hand blade (2026-11-04): the clip's right weapon in its fist -- the grip lock below, applied to the
                // sampled pose -- mirrored into the left fist.  hand_l = mirror(hand_r) * bind correction (MirrorRightPose),
                // the blade = mirror(weapon) turned half about its grip Z (the blade-plane flip, dual_rig.left_kukri), so the
                // relation follows from the right one alone (SourceAssets/HatchetPairs20261104/Work/probe_lone_mirror.py: the
                // accepted left grip to 0.001 cm).  Taken before the entry blend: blending from the hidden, collapsed right
                // arm carried the blade off the left fist for the length of every clip change.
                const FTransform Old=Pose[Weapon];
                const FTransform Locked=FTransform(FQuat(GripFlipAxis,GripFlipAngle))*KukriGrip::HandToWeapon()*Pose[HandR];
                const float Deviation=FVector::Dist(Old.GetLocation(),Locked.GetLocation())
                    +FMath::RadiansToDegrees(Old.GetRotation().AngularDistance(Locked.GetRotation()))*KukriGrip::DegreeToCm;
                const float Free=bGripFlipHold?0.f:FMath::SmoothStep(KukriGrip::HoldBand,KukriGrip::ReleaseBand,Deviation);
                FTransform Held=Locked;
                if(Free>0.f)Held.Blend(Locked,Old,Free);
                const FTransform Right=Held.GetRelativeTransform(Pose[HandR]);
                const FQuat Q=Right.GetRotation();const FVector L=Right.GetLocation();
                const FQuat Unbind=MirrorBindCorrection[MirrorHandL].Inverse();
                MirroredWeaponRelative=FTransform((Unbind*FQuat(Q.X,-Q.Y,-Q.Z,Q.W)*FQuat(FVector::ZAxisVector,PI)).GetNormalized(),
                    Unbind.RotateVector(FVector(-L.X,L.Y,L.Z)),FVector::OneVector);
            }
        }
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
                // A left-hand-only rig captured its right arm collapsed (zero scale): that arm and the weapon chain keep the
                // clip instead of growing out of the shoulder.
                if(bLeftHandOnly&&HiddenRight.IsValidIndex(I)&&HiddenRight[I]){Local[I]=Target;continue;}
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
            // Dual kukri run: the same fist holds the kukri turned about its grip-frame axis (reverse grip); while the
            // dual hold drives the flip the lock never releases, so the blade turns in the fist during the change.
            const FTransform Old=Pose[Weapon];
            const FTransform Flip(FQuat(GripFlipAxis,GripFlipAngle));
            const FTransform Locked=Flip*KukriGrip::HandToWeapon()*Pose[HandR];
            const float Deviation=FVector::Dist(Old.GetLocation(),Locked.GetLocation())
                +FMath::RadiansToDegrees(Old.GetRotation().AngularDistance(Locked.GetRotation()))*KukriGrip::DegreeToCm;
            const float Free=bGripFlipHold?0.f:FMath::SmoothStep(KukriGrip::HoldBand,KukriGrip::ReleaseBand,Deviation);
            FTransform Final=Locked;
            if(Free>0.f)Final.Blend(Locked,Old,Free);
            for(const int32 I:WeaponChain)Pose[I]=Pose[I].GetRelativeTransform(Old)*Final;
            Pose[Weapon]=Final;
        }
        if(LeftEntryLocal.Num()==LeftChain.Num()&&LeftEntryDuration>0.f)
        {
            // Dual kukri hold in/out: the left arm and the kukri on hand_l travel in parent space over their own time.
            // LeftChain is in bone order (parents first) and rooted at clavicle_l, whose parent is outside it.
            const float X=FMath::Clamp(LeftEntryTime/LeftEntryDuration,0.f,1.f);
            const float Alpha=X*X*X*(X*(X*6.f-15.f)+10.f);
            TArray<FTransform> Local;Local.SetNum(LeftChain.Num());
            for(int32 K=0;K<LeftChain.Num();++K)
            {
                const int32 Parent=Ref.GetParentIndex(LeftChain[K]);
                const FTransform Target=Parent>=0?Pose[LeftChain[K]].GetRelativeTransform(Pose[Parent]):Pose[LeftChain[K]];
                Local[K].Blend(LeftEntryLocal[K],Target,Alpha);
            }
            for(int32 K=0;K<LeftChain.Num();++K)
            {
                const int32 Parent=Ref.GetParentIndex(LeftChain[K]);
                Pose[LeftChain[K]]=Parent>=0?Local[K]*Pose[Parent]:Local[K];
            }
        }
        if(bLeftHandOnly&&!RightChain.IsEmpty())
        {
            const FTransform Hidden(FQuat::Identity,Pose[RightChain[0]].GetLocation(),FVector::ZeroVector);
            for(const int32 I:RightChain)Pose[I]=Hidden;
        }
        if(OffhandLeft&&!LeftChain.IsEmpty())
        {
            // Zero scale alone leaves weighted vertices spanning separated joints.
            // Collapse the chain onto the shoulder so outfit followers vanish too.
            const FTransform Hidden(FQuat::Identity,Pose[LeftChain[0]].GetLocation(),FVector::ZeroVector);
            for(const int32 I:LeftChain)Pose[I]=Hidden;
        }
        const auto* Use=GetOwner()->FindComponentByClass<UFPSPotionUseComponent>();
        // The main kukri/hatchet rig owns both arms. Lower only its left chain;
        // staff pairs have a separate left rig with their own component offset.
        const bool ConsumeStow=Use&&Use->UsesHandMesh(this)&&Use->IsStowingOffhand()&&!Use->IsTwoHanded()
            &&(!bLeftHandOnly||bMirrorRightToLeft);
        const float LowerWeight=ConsumeStow?Use->OffhandLowerWeight():0.f;
        if(FMath::Max(FMath::Abs(LeftRestWeight),LowerWeight)>UE_KINDA_SMALL_NUMBER&&!LeftChain.IsEmpty())
        {
            // Dual-wield whirlwind: the clip raises the free left arm as a guard fist, and a dual-wield off-hand weapon
            // rides hand_l -- it filled the upper view.  Blend the whole left chain to the single-hand Idle's hanging arm
            // (KukriLeftRest.h), in parent space so every segment keeps its length and the shoulder stays anchored.
            const float W=FMath::Clamp(FMath::Max(LeftRestWeight,LowerWeight),0.f,1.f);
            TArray<FTransform> Local;Local.SetNum(Pose.Num());
            for(const int32 I:LeftChain)
            {
                const int32 Parent=Ref.GetParentIndex(I);
                Local[I]=Parent>=0?Pose[I].GetRelativeTransform(Pose[Parent]):Pose[I];
            }
            for(const KukriLeftRest::FBone& Bone:KukriLeftRest::Bones)
            {
                const int32 I=Ref.FindBoneIndex(Bone.Name);
                if(I==INDEX_NONE||!LeftChain.Contains(I))continue;
                // Keep the actual weapon grasp until it is outside the frame.
                // Shoulder/elbow/wrist rotate together; fingers and segment
                // lengths retain the sampled native binding and weapon fit.
                if(ConsumeStow&&I!=HandL&&Ref.BoneIsChildOf(I,HandL))continue;
                const FTransform Rest(FQuat(Bone.Q[0],Bone.Q[1],Bone.Q[2],Bone.Q[3]).GetNormalized(),
                    ConsumeStow?Local[I].GetLocation():FVector(Bone.P[0],Bone.P[1],Bone.P[2]),
                    ConsumeStow?Local[I].GetScale3D():FVector::OneVector);
                FTransform Blend;Blend.Blend(Local[I],Rest,W);
                Local[I]=Blend;
            }
            for(const int32 I:LeftChain)
            {
                const int32 Parent=Ref.GetParentIndex(I);
                Pose[I]=Parent>=0?Local[I]*Pose[Parent]:Local[I];
            }
        }
    }
    Super::FinalizeBoneTransform();
}
