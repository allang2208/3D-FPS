#include "M07MembraneMotionNode.h"

FM07MembraneMotionNode::FM07MembraneMotionNode()
{
    for (int32 Panel=0; Panel<6; ++Panel)
        for (int32 Joint=0; Joint<3; ++Joint)
            Gill[Panel][Joint].BoneName=FName(*FString::Printf(TEXT("gill_%02d_%02d"),Panel+1,Joint));
    Alpha=0.f;
    LODThreshold=1;
}

void FM07MembraneMotionNode::Prepare(float DeltaSeconds, bool bEnabled,
    const FVector& MeshAcceleration, const FVector& MeshRear)
{
    Alpha=bEnabled ? 1.f : 0.f;
    StepSeconds=FMath::Max(0.,double(DeltaSeconds));
    Acceleration=MeshAcceleration.GetClampedToMaxSize(1800.);
    Rear=MeshRear.GetSafeNormal();
    if (!bEnabled)
    {
        bHasPreviousPose=false;
        for (int32 Panel=0; Panel<6; ++Panel) Bend[Panel]=BendSpeed[Panel]=0.;
    }
}

void FM07MembraneMotionNode::InitializeBoneReferences(const FBoneContainer& Bones)
{
    bHasPreviousPose=false;
    for (int32 Panel=0; Panel<6; ++Panel)
    {
        for (auto& Bone:Gill[Panel]) Bone.Initialize(Bones);
        if (!Gill[Panel][0].IsValidToEvaluate(Bones)) continue;
        const auto Index=Gill[Panel][0].GetCompactPoseIndex(Bones);
        FTransform Ref=Bones.GetRefPoseTransform(Index);
        for (auto Parent=Bones.GetParentBoneIndex(Index); Parent!=INDEX_NONE; Parent=Bones.GetParentBoneIndex(Parent))
            Ref*=Bones.GetRefPoseTransform(Parent);
        ReferenceRoot[Panel]=Ref.GetRotation();
    }
}

bool FM07MembraneMotionNode::IsValidToEvaluate(const USkeleton*, const FBoneContainer& Bones)
{
    for (const auto& Panel:Gill) for (const auto& Bone:Panel)
        if (!Bone.IsValidToEvaluate(Bones)) return false;
    return true;
}

void FM07MembraneMotionNode::EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,
    TArray<FBoneTransform>& Out)
{
    const auto& Bones=Output.Pose.GetPose().GetBoneContainer();
    const double Dt=StepSeconds;
    MotionTime=FMath::Fmod(MotionTime+Dt,120.0*UE_PI);
    for (int32 Panel=0; Panel<6; ++Panel)
    {
        FTransform Chain[3];
        for (int32 Joint=0; Joint<3; ++Joint)
            Chain[Joint]=Output.Pose.GetComponentSpaceTransform(Gill[Panel][Joint].GetCompactPoseIndex(Bones));
        const FQuat RootRotation=Chain[0].GetRotation();
        const FVector PanelRear=(RootRotation*ReferenceRoot[Panel].Inverse()).RotateVector(Rear);
        const FVector Along=(Chain[2].GetLocation()-Chain[0].GetLocation()).GetSafeNormal();
        const FVector BendAxis=FVector::CrossProduct(Along,PanelRear).GetSafeNormal();
        double AngularSpeed=0.;
        if (Dt>UE_SMALL_NUMBER && bHasPreviousPose)
        {
            FQuat Delta=(RootRotation*PreviousRoot[Panel].Inverse()).GetNormalized();
            if (Delta.W<0.) Delta=Delta*-1.;
            FVector Axis; double Angle;
            Delta.ToAxisAndAngle(Axis,Angle);
            AngularSpeed=FMath::RadiansToDegrees(Angle)*FVector::DotProduct(Axis,BendAxis)/Dt;
        }
        if (Dt>UE_SMALL_NUMBER)
        {
            const double Limit=Panel%3==0 ? 1.8 : 1.3;
            const double Breath=.18*FMath::Sin(MotionTime*1.25+(Panel%3)*.16);
            const double Target=FMath::Clamp(Breath-.024*AngularSpeed+
                FVector::DotProduct(Acceleration,PanelRear)/1400.,-Limit,Limit);
            // Analytic critically-damped spring: no Euler timestep instability.
            const double Omega=9.0-(Panel%3)*.8;
            const double Difference=Bend[Panel]-Target;
            const double C=BendSpeed[Panel]+Omega*Difference;
            const double Decay=FMath::Exp(-Omega*Dt);
            Bend[Panel]=FMath::Clamp(Target+(Difference+C*Dt)*Decay,-Limit,Limit);
            BendSpeed[Panel]=(BendSpeed[Panel]-Omega*C*Dt)*Decay;
            PreviousRoot[Panel]=RootRotation;
        }
        const FTransform TipLocal=Chain[2].GetRelativeTransform(Chain[1]);
        const double Angle=FMath::DegreesToRadians(Bend[Panel]);
        // Retain the root and every bone length. Both free joints bend in one
        // plane; there is no longitudinal twist or independently driven seam.
        Chain[1].SetRotation((FQuat(BendAxis,Angle*.25)*Chain[1].GetRotation()).GetNormalized());
        Chain[2]=TipLocal*Chain[1];
        Chain[2].SetRotation((FQuat(BendAxis,Angle*.75)*Chain[2].GetRotation()).GetNormalized());
        Out.Emplace(Gill[Panel][1].GetCompactPoseIndex(Bones),Chain[1]);
        Out.Emplace(Gill[Panel][2].GetCompactPoseIndex(Bones),Chain[2]);
    }
    if (Dt>UE_SMALL_NUMBER) bHasPreviousPose=true;
    Out.Sort(FCompareBoneTransformIndex());
}
