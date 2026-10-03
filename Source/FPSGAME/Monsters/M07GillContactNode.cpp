#include "M07GillContactNode.h"
#include "M07GillClearanceSamples.h"

FM07GillContactNode::FM07GillContactNode()
{
    for (int32 Panel=0; Panel<6; ++Panel)
        for (int32 Joint=0; Joint<3; ++Joint)
            Gill[Panel][Joint].BoneName=FName(*FString::Printf(TEXT("gill_%02d_%02d"),Panel+1,Joint));
    const TCHAR* Names[]={TEXT("upperarm"),TEXT("lowerarm"),TEXT("hand"),TEXT("middle_01"),
        TEXT("middle_03"),TEXT("thumb_01"),TEXT("thumb_03")};
    for (int32 Side=0; Side<2; ++Side)
        for (int32 Joint=0; Joint<7; ++Joint)
            Arm[Side][Joint].BoneName=FName(*FString::Printf(TEXT("%s_%s"),Names[Joint],Side==0?TEXT("l"):TEXT("r")));
    Chest.BoneName=TEXT("spine_03");
    Alpha=0.f;
    LODThreshold=1;
}

void FM07GillContactNode::InitializeBoneReferences(const FBoneContainer& Bones)
{
    Chest.Initialize(Bones);
    for (auto& Panel:Gill) for (auto& Joint:Panel) Joint.Initialize(Bones);
    for (auto& Side:Arm) for (auto& Joint:Side) Joint.Initialize(Bones);
    for (int32 Panel=0; Panel<6; ++Panel)
        for (int32 Joint=0; Joint<3; ++Joint)
        {
            if (!Gill[Panel][Joint].IsValidToEvaluate(Bones)) continue;
            auto Index=Gill[Panel][Joint].GetCompactPoseIndex(Bones);
            FTransform Reference=Bones.GetRefPoseTransform(Index);
            for (auto Parent=Bones.GetParentBoneIndex(Index); Parent.GetInt()!=INDEX_NONE; Parent=Bones.GetParentBoneIndex(Parent))
                Reference*=Bones.GetRefPoseTransform(Parent);
            for (int32 Sample=0; Sample<9; ++Sample)
                SampleLocal[Panel][Sample][Joint]=Reference.InverseTransformPosition(
                    FVector(M07GillClearanceSamples::Samples[Panel][Sample].ReferencePoint));
        }
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
    FVector Arms[2][7];
    FBox ArmBounds[2]={FBox(ForceInit),FBox(ForceInit)};
    for (int32 Side=0; Side<2; ++Side)
    {
        for (int32 Joint=0; Joint<7; ++Joint)
        {
            Arms[Side][Joint]=Position(Arm[Side][Joint]);
            ArmBounds[Side]+=Arms[Side][Joint];
        }
        ArmBounds[Side]=ArmBounds[Side].ExpandBy(16.+M07GillClearanceSamples::PatchRadius+4.);
    }
    const FVector Body=Position(Chest);
    const double MaxAngle=FMath::DegreesToRadians(FMath::Clamp(MaxOpeningDegrees,0.f,24.f));
    const FVector Rear=RearDirection.GetSafeNormal();
    const int32 Stride=FMath::Clamp(SampleStride,1,3);
    const int32 FirstSample=Stride==3?1:0;
    const int32 Passes=FMath::Clamp(SolverPasses,1,2);
    // Five conservative capsules cover arm, forearm, palm, long claws and
    // thumb. Two near passes are bounded at 1080 point/segment distances;
    // LOD1 uses 180, LOD2+ uses only the authored clearance baked into clips.
    // Per-arm AABBs reject unrelated leaves before narrow-phase work.
    const int32 Start[]={0,1,2,3,5}, End[]={1,2,3,4,6};
    const double Radius[]={11.3,8.1,14.,16.,8.4};
    for (int32 Panel=0; Panel<6; ++Panel)
    {
        FTransform Chain[3];
        for (int32 Joint=0; Joint<3; ++Joint)
            Chain[Joint]=Output.Pose.GetComponentSpaceTransform(Gill[Panel][Joint].GetCompactPoseIndex(Bones));
        const FQuat OriginalRotation=Chain[1].GetRotation();
        const FTransform TipLocal=Chain[2].GetRelativeTransform(Chain[1]);
        bool bChanged=false;
        for (int32 Pass=0; Pass<Passes; ++Pass)
        {
            FVector Samples[9];
            FBox LeafBounds(ForceInit);
            for (int32 Sample=FirstSample; Sample<9; Sample+=Stride)
            {
                Samples[Sample]=FVector::ZeroVector;
                const FVector3f Weights=M07GillClearanceSamples::Samples[Panel][Sample].Weights;
                for (int32 Joint=0; Joint<3; ++Joint)
                    Samples[Sample]+=Chain[Joint].TransformPosition(SampleLocal[Panel][Sample][Joint])*Weights[Joint];
                LeafBounds+=Samples[Sample];
            }
            const bool NearSide[]={LeafBounds.Intersect(ArmBounds[0]),LeafBounds.Intersect(ArmBounds[1])};
            double Deepest=0.;
            FVector Lever=FVector::ZeroVector, Push=FVector::ZeroVector;
            for (int32 Sample=FirstSample; Sample<9; Sample+=Stride)
                for (int32 Side=0; Side<2; ++Side)
                {
                    if (!NearSide[Side]) continue;
                    for (int32 Segment=0; Segment<5; ++Segment)
                    {
                        const FVector Near=FMath::ClosestPointOnSegment(Samples[Sample],Arms[Side][Start[Segment]],Arms[Side][End[Segment]]);
                        const double Depth=Radius[Segment]+M07GillClearanceSamples::PatchRadius+4.-FVector::Distance(Samples[Sample],Near);
                        if (Depth<=Deepest) continue;
                        FVector Lateral=Samples[Sample]-Body;
                        Lateral-=Rear*FVector::DotProduct(Lateral,Rear);
                        Lateral.Z=0.;
                        // Keep the leaf on its back/outside branch even if the
                        // claw crosses the sheet, avoiding shortest-away flips.
                        Push=(Rear+Lateral.GetSafeNormal()*.3).GetSafeNormal()*FMath::Min(24.,Depth);
                        Lever=Samples[Sample]-Chain[1].GetLocation();
                        Deepest=Depth;
                    }
                }
            if (Deepest<=0. || Lever.SizeSquared()<1.) break;
            FQuat Open=FQuat::FindBetweenNormals(Lever.GetSafeNormal(),(Lever+Push).GetSafeNormal());
            FQuat Relative=(Open*Chain[1].GetRotation()*OriginalRotation.Inverse()).GetNormalized();
            if (Relative.W<0.) Relative=Relative*-1.;
            FVector Axis; double Angle;
            Relative.ToAxisAndAngle(Axis,Angle);
            Relative=FQuat(Axis,FMath::Min(Angle,MaxAngle));
            Chain[1].SetRotation((Relative*OriginalRotation).GetNormalized());
            Chain[2]=TipLocal*Chain[1];
            bChanged=true;
        }
        if (bChanged)
        {
            // Keep the real attachment (00), all arm transforms, positions and
            // bone lengths; explicitly carry the distal joint with the middle.
            Out.Emplace(Gill[Panel][1].GetCompactPoseIndex(Bones),Chain[1]);
            Out.Emplace(Gill[Panel][2].GetCompactPoseIndex(Bones),Chain[2]);
        }
    }
    Out.Sort([](const FBoneTransform& A,const FBoneTransform& B){return A.BoneIndex<B.BoneIndex;});
}
