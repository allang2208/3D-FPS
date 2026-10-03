#include "M10TissueNode.h"

FM10TissueNode::FM10TissueNode()
{
    Alpha=1.f;Jaw.BoneName=TEXT("jaw");Head.BoneName=TEXT("head");
    const TCHAR* Parents[]={TEXT("body_front"),TEXT("body_center"),TEXT("body_rear"),TEXT("rump")};
    for(int32 I=0;I<8;++I)
    {
        const FString Stem=FString::Printf(TEXT("leg_%02d_%s"),I%4+1,I<4?TEXT("L"):TEXT("R"));
        Sockets[I].Upper.BoneName=FName(Stem+TEXT("_upper"));Sockets[I].Tissue.BoneName=FName(Stem+TEXT("_socket"));Sockets[I].Body.BoneName=Parents[I%4];
    }
}
void FM10TissueNode::InitializeBoneReferences(const FBoneContainer& Bones)
{
    Jaw.Initialize(Bones);Head.Initialize(Bones);
    if(Jaw.IsValidToEvaluate(Bones))JawRest=Bones.GetRefPoseTransform(Jaw.GetCompactPoseIndex(Bones));
    for(auto& Socket:Sockets)
    {
        Socket.Upper.Initialize(Bones);Socket.Tissue.Initialize(Bones);Socket.Body.Initialize(Bones);
        if(Socket.Tissue.IsValidToEvaluate(Bones))Socket.Rest=Bones.GetRefPoseTransform(Socket.Tissue.GetCompactPoseIndex(Bones));
    }
}
bool FM10TissueNode::IsValidToEvaluate(const USkeleton*,const FBoneContainer& Bones)
{
    return Jaw.IsValidToEvaluate(Bones)&&Head.IsValidToEvaluate(Bones);
}
void FM10TissueNode::EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,TArray<FBoneTransform>& Out)
{
    const auto& Bones=Output.Pose.GetPose().GetBoneContainer();
    for(const auto& Socket:Sockets)
    {
        if(!Socket.Tissue.IsValidToEvaluate(Bones)||!Socket.Upper.IsValidToEvaluate(Bones)||!Socket.Body.IsValidToEvaluate(Bones))continue;
        const auto Index=Socket.Tissue.GetCompactPoseIndex(Bones);
        const FTransform& Upper=Output.Pose.GetComponentSpaceTransform(Socket.Upper.GetCompactPoseIndex(Bones));
        FTransform Tissue=Socket.Rest*Output.Pose.GetComponentSpaceTransform(Socket.Body.GetCompactPoseIndex(Bones));
        Tissue.SetLocation(Upper.GetLocation());
        Tissue.SetRotation(FQuat::Slerp(Tissue.GetRotation(),Upper.GetRotation(),.45f).GetNormalized());
        Out.Emplace(Index,Tissue);
    }
    const FTransform Neutral=JawRest*Output.Pose.GetComponentSpaceTransform(Head.GetCompactPoseIndex(Bones));
    const FQuat Current=Output.Pose.GetComponentSpaceTransform(Jaw.GetCompactPoseIndex(Bones)).GetRotation();
    const float Degrees=FMath::RadiansToDegrees(Neutral.GetRotation().AngularDistance(Current));
    auto Ramp=[](float A,float B,float X){const float T=FMath::Clamp((X-A)/(B-A),0.f,1.f);return T*T*(3.f-2.f*T);};
    const FName Open(TEXT("M10_MouthOpenTissue")),Wide(TEXT("M10_MouthWideTissue"));
    Output.Curve.Set(Open,Ramp(12.f,38.f,Degrees));Output.Curve.SetFlags(Open,UE::Anim::ECurveElementFlags::MorphTarget);
    Output.Curve.Set(Wide,Ramp(26.f,43.f,Degrees));Output.Curve.SetFlags(Wide,UE::Anim::ECurveElementFlags::MorphTarget);
    Out.Sort([](const FBoneTransform& A,const FBoneTransform& B){return A.BoneIndex.GetInt()<B.BoneIndex.GetInt();});
}
