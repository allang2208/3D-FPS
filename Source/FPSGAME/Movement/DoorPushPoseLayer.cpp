#include "DoorPushPoseLayer.h"
#include "DoorPushAuthored20261002.h"
#include "../Weapons/ASH12WeaponAssets.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

namespace
{
namespace Motion=DoorPushAuthored20261002;
bool IsFistBone(const FString& Name)
{return Name.EndsWith(TEXT("_l"))&&(Name.StartsWith(TEXT("index_"))||Name.StartsWith(TEXT("middle_"))||
    Name.StartsWith(TEXT("ring_"))||Name.StartsWith(TEXT("pinky_"))||Name.StartsWith(TEXT("thumb_")));}
FQuat PalmFrame(const TArray<FTransform>& Pose,const FReferenceSkeleton& Ref)
{
    const FVector H=Pose[Ref.FindBoneIndex(TEXT("hand_l"))].GetLocation();
    return FRotationMatrix::MakeFromXZ(Pose[Ref.FindBoneIndex(TEXT("middle_01_l"))].GetLocation()-H,
        (Pose[Ref.FindBoneIndex(TEXT("index_01_l"))].GetLocation()-H)^
        (Pose[Ref.FindBoneIndex(TEXT("pinky_01_l"))].GetLocation()-H)).ToQuat();
}
}

void FDoorPushPoseLayer::Reset()
{
    CachedMesh.Reset();Bones.Reset();Reference.Reset();EntryCamera.Reset();LastCamera.Reset();RecoveryCamera.Reset();
    EntryLocal.Reset();SourcePose.Reset();AuthoredLocal.Reset();bRecovering=false;bSelfFallback=false;
    ExternalSource.Reset();ExternalReference.Reset();ExternalBoneMap.Reset();
}

bool FDoorPushPoseLayer::Capture(USkeletalMeshComponent& Mesh,const USkeletalMeshComponent& Source,
    const USkeletalMesh& FistRig,bool bNoNativeArms)
{
    Reset();auto* Asset=Mesh.GetSkeletalMeshAsset();const auto* SourceAsset=Source.GetSkeletalMeshAsset();
    const auto* Camera=Mesh.GetOwner()?Mesh.GetOwner()->FindComponentByClass<UCameraComponent>():nullptr;
    if(!Asset||!SourceAsset||!Camera)return false;
    const auto& Ref=Asset->GetRefSkeleton();const auto& SourceRef=SourceAsset->GetRefSkeleton();
    const auto& SourceCS=Source.GetComponentSpaceTransforms();
    if(SourceCS.Num()!=SourceRef.GetNum())return false;
    CachedMesh=Asset;Reference=Ref.GetRefBonePose();auto SourceRest=SourceRef.GetRefBonePose();
    for(int32 I=0;I<SourceRest.Num();++I)
    {const int32 P=SourceRef.GetParentIndex(I);if(P>=0)SourceRest[I]=SourceRest[I]*SourceRest[P];}
    if(&Source!=&Mesh)
    {
        ExternalSource=&Source;ExternalReference=SourceRest;ExternalBoneMap.SetNum(Reference.Num());
        for(int32 I=0;I<Reference.Num();++I)ExternalBoneMap[I]=SourceRef.FindBoneIndex(Ref.GetBoneName(I));
    }
    Clavicle=Ref.FindBoneIndex(TEXT("clavicle_l"));Upper=Ref.FindBoneIndex(TEXT("upperarm_l"));
    Lower=Ref.FindBoneIndex(TEXT("lowerarm_l"));Hand=Ref.FindBoneIndex(TEXT("hand_l"));
    if(Clavicle<0||Upper<0||Lower<0||Hand<0||Ref.FindBoneIndex(TEXT("index_01_l"))<0||
        Ref.FindBoneIndex(TEXT("middle_01_l"))<0||Ref.FindBoneIndex(TEXT("pinky_01_l"))<0)return false;
    const int32 WeaponRoot=Ref.FindBoneIndex(TEXT("WPN_root"));
    const int32 BowRoot=Ref.FindBoneIndex(TEXT("bow_grip"));
    for(int32 I=0;I<Reference.Num();++I)
    {
        const int32 P=Ref.GetParentIndex(I);if(P>=0)Reference[I]=Reference[I]*Reference[P];
        const FString Name=Ref.GetBoneName(I).ToString();
        const bool Weapon=Name.StartsWith(TEXT("WPN_"))||
            (WeaponRoot>=0&&(I==WeaponRoot||Ref.BoneIsChildOf(I,WeaponRoot)))||
            (BowRoot>=0&&(I==BowRoot||Ref.BoneIsChildOf(I,BowRoot)));
        if(!Weapon&&(I==Clavicle||Ref.BoneIsChildOf(I,Clavicle))&&Name.EndsWith(TEXT("_l")))Bones.Add(I);
    }
    const auto& Donor=FistRig.GetRefSkeleton();auto DonorRest=Donor.GetRefBonePose();
    for(int32 I=0;I<DonorRest.Num();++I)
    {const int32 P=Donor.GetParentIndex(I);if(P>=0)DonorRest[I]=DonorRest[I]*DonorRest[P];}
    const int32 DonorHand=Donor.FindBoneIndex(TEXT("hand_l"));
    if(DonorHand<0||Donor.FindBoneIndex(TEXT("index_01_l"))<0||Donor.FindBoneIndex(TEXT("middle_01_l"))<0||
        Donor.FindBoneIndex(TEXT("pinky_01_l"))<0)return false;
    const bool bNative=Asset==&FistRig;
    const FString RigPath=Asset->GetPathName();
    // M16 retains its native arm binding, with the wrist and digits rebound
    // to the common V7 locals. Reuse the complete donor chain, including its
    // rigid forearm helpers; do not add a second wrist twist compensation.
    const bool bM16=
        RigPath.StartsWith(TEXT("/Game/Weapons/M16A2/Gameplay20260919/"))||
        RigPath.StartsWith(TEXT("/Game/Characters/ModularOutfit20260924/BarePalmV7/M16/"));
    // ASH-12 has the same Manny joint offsets and bone frames as the donor.
    // Its different reference rotations describe the factory holding pose,
    // not different retarget axes. Applying donor rotation deltas preserves
    // that holding bias and sends the elbow/wrist behind the camera. Use the
    // complete authored chain, including the wrist, digits and twist helpers,
    // while retaining this mesh's native translations, scales and binding.
    const bool bASH12=
        RigPath==ASH12WeaponAssets::MeshPath||
        RigPath.StartsWith(TEXT("/Game/Characters/ModularOutfit20260924/BarePalmV7/ASH12/"));
    const bool bUseAuthoredLocals=bNative||bM16||bASH12;
    const FQuat PalmAlign=bUseAuthoredLocals?FQuat::Identity:
        PalmFrame(Reference,Ref)*PalmFrame(DonorRest,Donor).Inverse();
    // The guard stays at its authored camera-space placement until recovery.
    // Door distance selects the interaction, without shifting the held fist.
    AuthoredLocal.SetNum(Motion::KeyCount*Reference.Num());
    for(int32 Key=0;Key<Motion::KeyCount;++Key)
    {
        auto DonorPose=Donor.GetRefBonePose();
        for(int32 B=0;B<Motion::BoneCount;++B)
        {
            const int32 I=Donor.FindBoneIndex(Motion::Names[B]);if(I<0)continue;
            const int32 P=Donor.GetParentIndex(I);
            DonorPose[I].SetLocation(Motion::Poses[Key][B].Position/(P>=0?DonorRest[P].GetScale3D():FVector::OneVector));
            DonorPose[I].SetRotation(Motion::Poses[Key][B].Rotation.GetNormalized());
        }
        for(int32 I=0;I<DonorPose.Num();++I)
        {const int32 P=Donor.GetParentIndex(I);if(P>=0)DonorPose[I]=DonorPose[I]*DonorPose[P];}
        TArray<FQuat> KeyRotations;KeyRotations.SetNum(Reference.Num());
        const FQuat DonorHandDeform=DonorPose[DonorHand].GetRotation()*DonorRest[DonorHand].GetRotation().Inverse();
        const FQuat HandRotation=(DonorHandDeform*Reference[Hand].GetRotation()).GetNormalized();
        const FQuat TargetHandDeform=HandRotation*Reference[Hand].GetRotation().Inverse();
        for(int32 I:Bones)
        {
            const int32 J=Donor.FindBoneIndex(Ref.GetBoneName(I));if(J<0)return false;
            if(bUseAuthoredLocals)KeyRotations[I]=DonorPose[J].GetRotation();
            else if(IsFistBone(Ref.GetBoneName(I).ToString()))
            {
                const FQuat FistDeform=DonorHandDeform.Inverse()*DonorPose[J].GetRotation()*DonorRest[J].GetRotation().Inverse();
                KeyRotations[I]=(TargetHandDeform*PalmAlign*FistDeform*PalmAlign.Inverse()*Reference[I].GetRotation()).GetNormalized();
            }
            else KeyRotations[I]=(DonorPose[J].GetRotation()*DonorRest[J].GetRotation().Inverse()*Reference[I].GetRotation()).GetNormalized();
        }
        for(int32 I:Bones)
        {
            const int32 P=Ref.GetParentIndex(I);FTransform& Local=AuthoredLocal[Key*Reference.Num()+I];
            Local=Ref.GetRefBonePose()[I];
            if(I==Clavicle)
            {
                // Clavicle is the camera-space root of this independently
                // authored chain; all remaining transforms are parent local.
                Local=FTransform(KeyRotations[I],Motion::Contacts[Key].Shoulder-
                    KeyRotations[I].RotateVector(Ref.GetRefBonePose()[Upper].GetLocation()*Reference[I].GetScale3D()),
                    Reference[I].GetScale3D());
            }
            else
            {
                Local.SetRotation((KeyRotations[P].Inverse()*KeyRotations[I]).GetNormalized());
                if(bNative)Local.SetTranslation(DonorPose[Donor.FindBoneIndex(Ref.GetBoneName(I))].GetRelativeTransform(
                    DonorPose[Donor.FindBoneIndex(Ref.GetBoneName(P))]).GetTranslation());
            }
        }
    }
    EntryCamera=Reference;
    // Bow and canonical arms share their parent-local joint axes. The source
    // pose plus component transform already include the bow's root basis and
    // presentation pivot. Keep the evaluated camera-space rotation: another
    // reference-space correction changes the native-offset FK directions.
    for(int32 I=0;I<EntryCamera.Num();++I)
    {
        const int32 S=SourceRef.FindBoneIndex(Ref.GetBoneName(I));
        if(S>=0)
        {
            EntryCamera[I]=(SourceCS[S]*Source.GetComponentTransform()).GetRelativeTransform(Camera->GetComponentTransform());
        }
    }
    bSelfFallback=bNoNativeArms;
    if(bSelfFallback)
    {
        // Key zero is the accepted empty-hand idle example. Lower the entire
        // chain below the frame; never expose the canonical rifle rest pose.
        for(int32 I:Bones)
        {
            const int32 P=Ref.GetParentIndex(I);
            EntryCamera[I]=I==Clavicle?AuthoredLocal[I]:AuthoredLocal[I]*EntryCamera[P];
        }
        for(int32 I:Bones)EntryCamera[I].AddToTranslation(FVector(-2.f,0.f,-6.f));
    }
    EntryLocal=Ref.GetRefBonePose();
    for(int32 I:Bones)
    {
        const int32 P=Ref.GetParentIndex(I);EntryLocal[I]=EntryCamera[I].GetRelativeTransform(EntryCamera[P]);
        if(SourceAsset!=Asset&&I!=Clavicle)EntryLocal[I].SetTranslation(Ref.GetRefBonePose()[I].GetTranslation());
    }
    LastCamera=EntryCamera;return true;
}

bool FDoorPushPoseLayer::Apply(USkeletalMeshComponent& Mesh,float Age)
{
    const auto* Asset=Mesh.GetSkeletalMeshAsset();
    const auto* Camera=Mesh.GetOwner()?Mesh.GetOwner()->FindComponentByClass<UCameraComponent>():nullptr;
    auto& Pose=Mesh.GetEditableComponentSpaceTransforms();
    if(!Asset||CachedMesh.Get()!=Asset||!Camera||Bones.IsEmpty()||Pose.Num()!=Reference.Num())return false;
    const auto& Ref=Asset->GetRefSkeleton();const auto& RestLocal=Ref.GetRefBonePose();
    SourcePose=Pose;
    const FTransform MW=Mesh.GetComponentTransform(),CW=Camera->GetComponentTransform();
    const auto FromCamera=[&](const FTransform& T){return (T*CW).GetRelativeTransform(MW);};
    const auto ToCamera=[&](const FTransform& T){return (T*MW).GetRelativeTransform(CW);};
    if(bSelfFallback)
    {
        for(int32 I:Bones)
        {
            const int32 P=Ref.GetParentIndex(I);
            SourcePose[I]=I==Clavicle?FromCamera(EntryCamera[I]):EntryLocal[I]*SourcePose[P];
        }
        Pose=SourcePose;
    }
    else if(const auto* Other=ExternalSource.Get())
    {
        // The bow supplies its live stow/return pose to the canonical left arm.
        // Preserve the evaluated rotation after changing component space,
        // matching capture; the shared local joint axes need no rest delta.
        const auto& OtherPose=Other->GetComponentSpaceTransforms();
        if(OtherPose.Num()==ExternalReference.Num())
        {
            for(int32 I=0;I<SourcePose.Num();++I)
            {
                const int32 J=ExternalBoneMap[I];if(J<0)continue;
                SourcePose[I]=(OtherPose[J]*Other->GetComponentTransform()).GetRelativeTransform(MW);
            }
            const auto Mapped=SourcePose;
            for(int32 I:Bones)if(I!=Clavicle)
            {
                const int32 P=Ref.GetParentIndex(I);FTransform Local=Mapped[I].GetRelativeTransform(Mapped[P]);
                Local.SetTranslation(RestLocal[I].GetTranslation());SourcePose[I]=Local*SourcePose[P];
            }
            Pose=SourcePose;
        }
    }
    if(Age>=Motion::RecoverStartSeconds)
    {
        if(!bRecovering){bRecovering=true;RecoveryCamera=LastCamera;}
        const float Return=Motion::Ease((Age-Motion::RecoverStartSeconds)/Motion::RecoverySeconds);
        for(int32 I:Bones)
        {
            const int32 P=Ref.GetParentIndex(I);
            FTransform From=RecoveryCamera[I].GetRelativeTransform(RecoveryCamera[P]);
            if(I==Clavicle)From=FromCamera(RecoveryCamera[I]).GetRelativeTransform(SourcePose[P]);
            const FTransform To=SourcePose[I].GetRelativeTransform(SourcePose[P]);
            FTransform Mixed;Mixed.Blend(From,To,Return);
            Mixed.SetRotation(FQuat::Slerp(From.GetRotation(),To.GetRotation(),Return).GetNormalized());
            Pose[I]=Mixed*Pose[P];
        }
    }
    else
    {
        const float Sample=Motion::MotionBlend(Age);
        const int32 A=FMath::Clamp(FMath::FloorToInt(Sample),0,Motion::KeyCount-2),B=A+1;
        const float Weight=FMath::Clamp(Sample-A,0.f,1.f);
        for(int32 I:Bones)
        {
            const int32 P=Ref.GetParentIndex(I);
            // One local interpolation and one FK, including the whole wrist,
            // closed fingers, metacarpals and helpers. No runtime arm/fist IK.
            const FTransform From=A==0?(I==Clavicle?EntryCamera[I]:EntryLocal[I]):AuthoredLocal[A*Reference.Num()+I];
            const FTransform& To=AuthoredLocal[B*Reference.Num()+I];
            FTransform Mixed;Mixed.Blend(From,To,Weight);
            Mixed.SetRotation(FQuat::Slerp(From.GetRotation(),To.GetRotation(),Weight).GetNormalized());
            Pose[I]=I==Clavicle?FromCamera(Mixed):Mixed*Pose[P];
        }
    }
    for(int32 I=0;I<Pose.Num();++I)LastCamera[I]=ToCamera(Pose[I]);
    return true;
}
