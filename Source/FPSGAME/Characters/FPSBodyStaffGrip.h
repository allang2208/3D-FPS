#pragma once
#include "FPSPlayerBodyGrip.h"
#include "FPSBodyStaffContactFit.h"

namespace FPSBodyStaffGrip
{
// Reuse the first-person staff grip or free-hand fist, including thumb and palm fan.
// Preserve the authored FPS grasp, native lengths and anatomical palm frame.
// Jason's thicker equipped hand needs only bounded local clearance deltas.
inline bool HasJasonFit(const FFPSBodyGripRig& Rig)
{
    return Rig.IsValid()&&Rig.Digits.Num()==5&&Rig.TargetLocal.Num()==342&&
        FMath::IsNearlyEqual(Rig.TargetLocal[Rig.Digits[0].Target[1]].GetLocation().Size(),4.43,.02);
}
inline void AdaptMount(FFPSBodyGripRig& Rig,int32 Variant)
{
    if(HasJasonFit(Rig))Rig.Mount.AddToTranslation(FPSBodyStaffContactFit::Offset[FMath::Clamp(Variant,0,3)]);
}
inline bool Transfer(const FFPSBodyGripRig& Rig,const FReferenceSkeleton& Source,
    const TArray<FTransform>& SourcePose,TArray<FTransform>& Pose,int32 Variant=0)
{
    if(!Rig.IsValid()||SourcePose.Num()!=Rig.SourceBind.Num())return false;
    if(Pose.Num()!=Rig.TargetLocal.Num())Pose=Rig.TargetLocal;
    TArray<FQuat,TInlineAllocator<342>> World,Desired;
    TArray<bool,TInlineAllocator<342>> Driven;
    World.SetNum(Rig.TargetLocal.Num());Desired.SetNum(Rig.TargetLocal.Num());
    Driven.Init(false,Rig.TargetLocal.Num());
    const FQuat SourceRestHand=Rig.SourceBind[Rig.SourceHand].GetRotation();
    const FQuat SourceHand=SourcePose[Rig.SourceHand].GetRotation();
    const FQuat Frame=(Rig.TargetBind[Rig.TargetHand].GetRotation()*Rig.Mount.GetRotation()).GetNormalized();
    const bool Right=Source.GetBoneName(Rig.SourceHand)==TEXT("hand_r");
    const auto Copy=[&](int32 From,int32 To)
    {
        const FQuat Rest=SourceRestHand.Inverse()*Rig.SourceBind[From].GetRotation();
        const FQuat Authored=SourceHand.Inverse()*SourcePose[From].GetRotation();
        Desired[To]=(Frame*Authored*Rest.Inverse()*Frame.Inverse()*Rig.TargetBind[To].GetRotation()).GetNormalized();
        Driven[To]=true;
    };
    for(const auto& Digit:Rig.Digits)
    {
        for(int32 J=0;J<3;++J)
        {
            Copy(Digit.Source[J],Digit.Target[J]);
            if(Right)
            {
                const int32 A=J<2?J:1,B=J<2?J+1:2;
                const FVector TargetAxis=Rig.TargetBind[Digit.Target[J]].GetRotation().UnrotateVector(
                    Rig.TargetBind[Digit.Target[B]].GetLocation()-Rig.TargetBind[Digit.Target[A]].GetLocation()).GetSafeNormal();
                const FVector SourceAxis=Rig.SourceBind[Digit.Source[J]].GetRotation().UnrotateVector(
                    Rig.SourceBind[Digit.Source[B]].GetLocation()-Rig.SourceBind[Digit.Source[A]].GetLocation()).GetSafeNormal();
                // Copy the actual segment direction, including the source's
                // pre-bent reference hand, rather than its delta alone.
                Desired[Digit.Target[J]]=(Frame*SourceHand.Inverse()*SourcePose[Digit.Source[J]].GetRotation()*
                    FQuat::FindBetweenNormals(TargetAxis,SourceAxis)).GetNormalized();
            }
        }
        const int32 From=Source.GetParentIndex(Digit.Source[0]),To=Rig.Parents[Digit.Target[0]];
        if(From!=INDEX_NONE&&From!=Rig.SourceHand&&To!=INDEX_NONE&&To!=Rig.TargetHand)Copy(From,To);
    }
    for(int32 Bone=0;Bone<Rig.TargetLocal.Num();++Bone)
    {
        const int32 Parent=Rig.Parents[Bone];
        const FQuat ParentPose=Parent>=0?World[Parent]:FQuat::Identity;
        FQuat Local=Rig.TargetLocal[Bone].GetRotation();
        if(Driven[Bone])Local=(ParentPose.Inverse()*Desired[Bone]).GetNormalized();
        else if(Rig.HalfJoint[Bone]&&Parent>=0&&Driven[Parent])
        {
            const FQuat Delta=Rig.TargetLocal[Parent].GetRotation().Inverse()*Pose[Parent].GetRotation();
            Local=(FQuat::Slerp(FQuat::Identity,Delta.Inverse(),.5f)*Local).GetNormalized();
        }
        World[Bone]=(ParentPose*Local).GetNormalized();
        if(Rig.IsFinger[Bone]){Pose[Bone]=Rig.TargetLocal[Bone];Pose[Bone].SetRotation(Local);}
    }
    if(Right&&HasJasonFit(Rig))
    {
        const int32 V=FMath::Clamp(Variant,0,3);
        for(int32 D=0;D<Rig.Digits.Num();++D)for(int32 J=0;J<3;++J)
        {
            auto& Bone=Pose[Rig.Digits[D].Target[J]];
            Bone.SetRotation((Bone.GetRotation()*FPSBodyStaffContactFit::Fingers[V][D*3+J]).GetNormalized());
        }
        for(int32 Bone:Rig.Descendants)if(Rig.HalfJoint[Bone])
        {
            const int32 Parent=Rig.Parents[Bone];
            const FQuat Delta=Rig.TargetLocal[Parent].GetRotation().Inverse()*Pose[Parent].GetRotation();
            Pose[Bone].SetRotation((FQuat::Slerp(FQuat::Identity,Delta.Inverse(),.5f)*Rig.TargetLocal[Bone].GetRotation()).GetNormalized());
        }
    }
    return true;
}
}
