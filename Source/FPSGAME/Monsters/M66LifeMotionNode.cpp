#include "M66LifeMotionNode.h"
#include "Animation/AnimInstanceProxy.h"

FM66LifeMotionNode::FM66LifeMotionNode()
{
    Eyes.SetNum(7);
    for(int32 I=0;I<Eyes.Num();++I)Eyes[I].BoneName=FName(*FString::Printf(TEXT("M66_Eye_%02d"),I+1));
    for(const TCHAR* Name:{TEXT("M66_SacUpper_L"),TEXT("M66_SacLower_L"),TEXT("M66_SacLower_R"),TEXT("M66_SacUpper_R")})
    {FBoneReference Bone;Bone.BoneName=Name;Sacs.Add(Bone);}
}
void FM66LifeMotionNode::Initialize_AnyThread(const FAnimationInitializeContext& Context)
{FAnimNode_Base::Initialize_AnyThread(Context);Source.Initialize(Context);}
void FM66LifeMotionNode::CacheBones_AnyThread(const FAnimationCacheBonesContext& Context)
{
    Source.CacheBones(Context);const auto& Bones=Context.AnimInstanceProxy->GetRequiredBones();
    for(auto& Eye:Eyes)Eye.Initialize(Bones);
    const auto& Ref=Bones.GetReferenceSkeleton();InverseSacScale.Init(0.f,Sacs.Num());
    for(int32 I=0;I<Sacs.Num();++I)
    {
        Sacs[I].Initialize(Bones);int32 Index=Ref.FindBoneIndex(Sacs[I].BoneName);
        if(Index==INDEX_NONE)continue;
        FTransform Frame=Ref.GetRefBonePose()[Index];
        while((Index=Ref.GetParentIndex(Index))!=INDEX_NONE)Frame*=Ref.GetRefBonePose()[Index];
        InverseSacScale[I]=1.f/FMath::Max(.001f,float(Frame.GetScale3D().GetAbsMax()));
    }
}
void FM66LifeMotionNode::Update_AnyThread(const FAnimationUpdateContext& Context){Source.Update(Context);}
void FM66LifeMotionNode::Evaluate_AnyThread(FPoseContext& Output)
{
    Source.Evaluate(Output);if(Alpha<=KINDA_SMALL_NUMBER)return;
    const auto& Bones=Output.Pose.GetBoneContainer();
    // Each globe makes a short eased saccade, holds, then drifts slightly.
    // Shared server time keeps this deterministic without extra replication.
    auto Gaze=[](int64 Segment,int32 Eye,int32 Axis)
    {return FMath::Sin(double(Segment)*2.173+Eye*1.713+Axis*2.417)*.75+FMath::Sin(double(Segment)*.681+Eye*.47+Axis)*.25;};
    for(int32 I=0;I<Eyes.Num();++I)
    {
        if(!Eyes[I].IsValidToEvaluate(Bones))continue;
        const double Clock=(Seconds+I*.41)/(2.6+I*.13);
        const int64 Segment=FMath::FloorToInt64(Clock);const float Part=float(Clock-Segment);
        const float Blend=FMath::SmoothStep(0.f,.10f,Part);
        const double Yaw=FMath::Lerp(Gaze(Segment-1,I,0),Gaze(Segment,I,0),Blend)*8.+FMath::Sin(Seconds*.9+I)*.6;
        const double Pitch=FMath::Lerp(Gaze(Segment-1,I,1),Gaze(Segment,I,1),Blend)*5.;
        auto& Pose=Output.Pose[Eyes[I].GetCompactPoseIndex(Bones)];
        const FQuat Delta=FQuat(FVector::UpVector,FMath::DegreesToRadians(Yaw)*Alpha)
            *FQuat(FVector::ForwardVector,FMath::DegreesToRadians(Pitch)*Alpha);
        Pose.SetRotation((Pose.GetRotation()*Delta).GetNormalized());
    }
    for(int32 I=0;I<Sacs.Num();++I)
    {
        if(!Sacs[I].IsValidToEvaluate(Bones))continue;
        const double Phase=Seconds*(2.*PI/3.4)-I*.95;
        const float Wave=float(FMath::Sin(Phase));
        const float Ripple=float(FMath::Sin(Seconds*3.7-I*1.3)*FMath::Pow(FMath::Max(0.,FMath::Sin(Seconds*.8-I)),3.));
        const float Weight=Alpha*FMath::Lerp(1.f,.8f,Movement);
        auto& Pose=Output.Pose[Sacs[I].GetCompactPoseIndex(Bones)];
        Pose.SetScale3D(Pose.GetScale3D()*FVector(1.f+.023f*Wave*Weight,1.f-.012f*Wave*Weight,
            1.f+(.018f*float(FMath::Sin(Phase+.5))+.006f*Ripple)*Weight));
        // Local translation is in the imported rig's units (container scale 100).
        Pose.AddToTranslation(FVector(.65f*Wave,.45f*Ripple,.8f*Wave)*InverseSacScale[I]*Weight);
    }
}
void FM66LifeMotionNode::GatherDebugData(FNodeDebugData& DebugData){Source.GatherDebugData(DebugData);}
