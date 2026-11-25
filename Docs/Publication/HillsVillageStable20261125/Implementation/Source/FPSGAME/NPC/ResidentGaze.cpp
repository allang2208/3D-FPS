#include "ResidentGaze.h"
#include "BonePose.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/PlayerController.h"

namespace
{
const FName LeftEyes[]={TEXT("eye_l"),TEXT("LeftEye"),TEXT("FACIAL_L_Eye"),TEXT("CC_Base_L_Eye")};
const FName RightEyes[]={TEXT("eye_r"),TEXT("RightEye"),TEXT("FACIAL_R_Eye"),TEXT("CC_Base_R_Eye")};
const FName HeadNames[]={TEXT("head"),TEXT("CC_Base_Head")};
const FName NeckNames[]={TEXT("neck_01"),TEXT("neck"),TEXT("CC_Base_NeckTwist01")};

// Compute a roll-free correction relative to the *animated* gaze direction.
FQuat AimDelta(FVector Facing,FVector Towards,float YawLimit,float UpLimit,float DownLimit,float Amount)
{
    if (!Towards.Normalize() || Facing.IsNearlyZero()) return FQuat::Identity;
    const FRotator From=Facing.Rotation(), To=Towards.Rotation();
    const float Yaw=FMath::ClampAngle(To.Yaw-From.Yaw,-YawLimit,YawLimit);
    const float Pitch=FMath::Clamp(float(To.Pitch-From.Pitch),-DownLimit,UpLimit);
    const FVector ToClamped=FRotator(From.Pitch+Amount*Pitch,From.Yaw+Amount*Yaw,0.).Vector();
    return FQuat::FindBetweenNormals(Facing.GetSafeNormal(),ToClamped);
}
}

bool FResidentGaze::HasEyePair(const USkeletalMeshComponent& Mesh)
{
    const auto Has=[&Mesh](TConstArrayView<FName> Names)
    {
        for (FName Name:Names) if (Mesh.GetBoneIndex(Name)!=INDEX_NONE) return true;
        return false;
    };
    return Has(LeftEyes) && Has(RightEyes);
}

void FResidentGaze::UpdateTarget(const USkeletalMeshComponent& Mesh,const APlayerController* Viewer,float Delta)
{
    const bool Live=Viewer && Viewer->IsLocalController() && Viewer->GetPawn() && Viewer->GetWorld()==Mesh.GetWorld();
    if (Live)
    {
        FVector Eye; FRotator Rotation;
        Viewer->GetPlayerViewPoint(Eye,Rotation);
        SmoothedWorldTarget=IsActive() ? FMath::Lerp(SmoothedWorldTarget,Eye,1.-FMath::Exp(-16.*Delta)) : Eye;
    }
    Weight=FMath::FInterpConstantTo(Weight,Live?1.f:0.f,Delta,Live?4.5f:4.f);
    if (IsActive()) ComponentTarget=Mesh.GetComponentTransform().InverseTransformPosition(SmoothedWorldTarget);
}

void FResidentGaze::CacheBones(const FBoneContainer& Bones)
{
    if (Serial.IsSet() && Serial.GetValue()==Bones.GetSerialNumber()) return;
    Serial=Bones.GetSerialNumber();
    const auto Find=[&Bones](TConstArrayView<FName> Names)
    {
        FAimBone Result;
        for (FName Name:Names)
        {
            const int32 I=Bones.GetPoseBoneIndexForBoneName(Name);
            if (I==INDEX_NONE) continue;
            const auto Index=Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(I));
            if (Index==INDEX_NONE) continue;
            Result.Index=Index;
            for (auto B=Index;B!=INDEX_NONE;B=Bones.GetParentBoneIndex(B))
                Result.Reference=Result.Reference*Bones.GetRefPoseTransform(B);
            break;
        }
        return Result;
    };
    Head=Find(HeadNames); Neck=Find(NeckNames);
    LeftEye=Find(LeftEyes); RightEye=Find(RightEyes);
}

void FResidentGaze::Apply(FPoseContext& Output,bool EyesOnly)
{
    if (!IsActive()) return;
    CacheBones(Output.Pose.GetBoneContainer());
    const bool BothEyes=LeftEye.Index!=INDEX_NONE && RightEye.Index!=INDEX_NONE;
    if (Head.Index==INDEX_NONE || (EyesOnly && !BothEyes)) return;
    FCSPose<FCompactPose> Pose;
    Pose.InitPose(Output.Pose);
    const auto Rotate=[&Pose](const FAimBone& Bone,const FQuat& Delta)
    {
        FTransform T=Pose.GetComponentSpaceTransform(Bone.Index);
        T.SetRotation((Delta*T.GetRotation()).GetNormalized());
        TArray<FBoneTransform,TInlineAllocator<1>> Change;
        Change.Emplace(Bone.Index,T);
        Pose.LocalBlendCSBoneTransforms(Change,1.f);
    };
    // Both resident rigs face component +Y at bind, irrespective of head/eye bone roll.
    const auto Sight=[](const FAimBone& Bone,const FTransform& T)
    {
        return T.GetRotation().RotateVector(Bone.Reference.GetRotation().UnrotateVector(FVector::RightVector));
    };
    if (!EyesOnly)
    {
        const auto& T=Pose.GetComponentSpaceTransform(Head.Index);
        const FVector Eye=BothEyes ?
            (Pose.GetComponentSpaceTransform(LeftEye.Index).GetLocation()+Pose.GetComponentSpaceTransform(RightEye.Index).GetLocation())*.5 :
            T.GetLocation()+T.GetRotation().RotateVector(Head.Reference.GetRotation().UnrotateVector(FVector(0.,9.,10.5)));
        const FQuat Delta=AimDelta(Sight(Head,T),ComponentTarget-Eye,33.f,24.f,24.f,Weight);
        if (Neck.Index!=INDEX_NONE)
        {
            const FQuat NeckPart=FQuat::Slerp(FQuat::Identity,Delta,.32);
            Rotate(Neck,NeckPart);
            Rotate(Head,Delta*NeckPart.Inverse());
        }
        else Rotate(Head,Delta);
    }
    if (BothEyes)
    {
        for (const FAimBone* Bone:{&LeftEye,&RightEye})
        {
            const auto& T=Pose.GetComponentSpaceTransform(Bone->Index);
            Rotate(*Bone,AimDelta(Sight(*Bone,T),ComponentTarget-T.GetLocation(),10.f,8.f,8.f,Weight));
        }
    }
    FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Output.Pose);
}
