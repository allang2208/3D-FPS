#include "M07GillContactNode.h"

FM07GillContactNode::FM07GillContactNode()
{
    for (int32 Panel=0; Panel<6; ++Panel)
        for (int32 Joint=0; Joint<3; ++Joint)
            Gill[Panel][Joint].BoneName=FName(*FString::Printf(TEXT("gill_%02d_%02d"),Panel+1,Joint));
    const TCHAR* Names[]={TEXT("upperarm"),TEXT("lowerarm"),TEXT("hand"),TEXT("middle_01")};
    for (int32 Side=0; Side<2; ++Side)
        for (int32 Joint=0; Joint<4; ++Joint)
            Arm[Side][Joint].BoneName=FName(*FString::Printf(TEXT("%s_%s"),Names[Joint],Side==0?TEXT("l"):TEXT("r")));
    Chest.BoneName=TEXT("spine_03");
    Alpha=0.f;
}

void FM07GillContactNode::InitializeBoneReferences(const FBoneContainer& Bones)
{
    Chest.Initialize(Bones);
    for (auto& Panel:Gill) for (auto& Joint:Panel) Joint.Initialize(Bones);
    for (auto& Side:Arm) for (auto& Joint:Side) Joint.Initialize(Bones);
}

bool FM07GillContactNode::IsValidToEvaluate(const USkeleton*, const FBoneContainer& Bones)
{
    if (!Chest.IsValidToEvaluate(Bones)) return false;
    for (const auto& Panel:Gill) for (const auto& Joint:Panel)
        if (!Joint.IsValidToEvaluate(Bones)) return false;
    for (const auto& Side:Arm) for (const auto& Joint:Side)
        if (!Joint.IsValidToEvaluate(Bones)) return false;
    return true;
}

void FM07GillContactNode::EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,
    TArray<FBoneTransform>& Out)
{
    const auto& Bones=Output.Pose.GetPose().GetBoneContainer();
    auto Position=[&](const FBoneReference& Bone)
    { return Output.Pose.GetComponentSpaceTransform(Bone.GetCompactPoseIndex(Bones)).GetLocation(); };
    FVector Arms[2][4];
    for (int32 Side=0; Side<2; ++Side)
        for (int32 Joint=0; Joint<4; ++Joint) Arms[Side][Joint]=Position(Arm[Side][Joint]);
    const FVector Body=Position(Chest);
    const double MaxAngle=FMath::DegreesToRadians(FMath::Clamp(MaxOpeningDegrees,0.f,24.f));
    // Only 6 leaves x 2 longitudinal samples x 6 arm/palm segments. No render
    // vertex skinning, mesh traversal, traces, collision-body allocation or IO.
    const double Radius[]={11.3,8.1,11.5};
    for (int32 Panel=0; Panel<6; ++Panel)
    {
        // Joint 00 is the true shoulder/back attachment and never receives a
        // procedural correction. Open only the free middle/tip chain.
        const auto Index=Gill[Panel][1].GetCompactPoseIndex(Bones);
        FTransform Root=Output.Pose.GetComponentSpaceTransform(Index);
        const FVector Pivot=Root.GetLocation();
        const FVector Tip=Position(Gill[Panel][2]);
        const FVector Samples[]={FMath::Lerp(Pivot,Tip,.25),FMath::Lerp(Pivot,Tip,.70)};
        FVector Push=FVector::ZeroVector, Lever=FVector::ZeroVector;
        double Deepest=0.;
        for (const FVector& Sample:Samples)
            for (int32 Side=0; Side<2; ++Side)
                for (int32 Segment=0; Segment<3; ++Segment)
                {
                    const FVector Near=FMath::ClosestPointOnSegment(Sample,Arms[Side][Segment],Arms[Side][Segment+1]);
                    const FVector Delta=Sample-Near;
                    const double Distance=Delta.Size(), Clearance=Radius[Segment]+5.;
                    const double Depth=Clearance-Distance;
                    if (Depth<=Deepest) continue;
                    FVector Direction=Delta.GetSafeNormal();
                    const FVector Outward=(Sample-Body).GetSafeNormal();
                    if (Direction.IsNearlyZero()) Direction=Outward;
                    // Open the free leaf chain, retaining its attachment and
                    // avoiding any changes to supporting body/arm bones.
                    const double Inward=FVector::DotProduct(Direction,Outward);
                    if (Inward<0.) Direction=(Direction-Outward*Inward+Outward*.35).GetSafeNormal();
                    const double Blend=FMath::SmoothStep(0.,Clearance,Depth);
                    Push=Direction*FMath::Min(22.,Depth)*Blend;
                    Lever=Sample-Pivot;
                    Deepest=Depth;
                }
        if (Deepest<=0. || Lever.IsNearlyZero() || Push.IsNearlyZero()) continue;
        FQuat Open=FQuat::FindBetweenNormals(Lever.GetSafeNormal(),(Lever+Push).GetSafeNormal());
        Open.Normalize();
        FVector Axis; double Angle;
        Open.ToAxisAndAngle(Axis,Angle);
        if (Angle>PI) Angle-=2.*PI;
        Open=FQuat(Axis,FMath::Clamp(Angle,-MaxAngle,MaxAngle));
        Root.SetRotation((Open*Root.GetRotation()).GetNormalized());
        // Rotation only: original root position, scales and all bone lengths
        // survive. Its children carry the same opening into the proxy skin.
        Out.Emplace(Index,Root);
    }
    Out.Sort([](const FBoneTransform& A,const FBoneTransform& B){return A.BoneIndex<B.BoneIndex;});
}
