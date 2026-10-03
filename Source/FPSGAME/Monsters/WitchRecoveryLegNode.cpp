#include "WitchRecoveryLegNode.h"
#include "Animation/AnimInstanceProxy.h"
#include "TwoBoneIK.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "Rendering/SkinWeightVertexBuffer.h"

void FWitchRecoveryLegNode::PrepareSupportSamples(USkeletalMeshComponent* CharacterMesh)
{
    const auto* Asset=CharacterMesh?CharacterMesh->GetSkeletalMeshAsset():nullptr;
    if (SupportMesh==Asset) return;
    SupportMesh=Asset; SupportSamples.Reset();
    if (!Asset) return;
    const auto* Info=Asset->GetLODInfo(0);
    const auto* Render=CharacterMesh->GetSkeletalMeshRenderData();
    const auto* Weights=CharacterMesh->GetSkinWeightBuffer(0);
    if (!Info || !Info->bAllowCPUAccess || !Render || Render->LODRenderData.IsEmpty() || !Weights) return;
    const auto& LOD=Render->LODRenderData[0];
    const int32 Count=LOD.GetNumVertices();
    if (!Count || Weights->GetNumVertices()!=static_cast<uint32>(Count)) return;
    const auto& Ref=Asset->GetRefSkeleton();
    TArray<FTransform> Bind=Ref.GetRefBonePose();
    for (int32 I=0;I<Bind.Num();++I) if (Ref.GetParentIndex(I)!=INDEX_NONE) Bind[I]*=Bind[Ref.GetParentIndex(I)];
    const int32 Pelvis=Ref.FindBoneIndex(TEXT("pelvis"));
    const int32 LeftCalf=Ref.FindBoneIndex(TEXT("calf_l")),RightCalf=Ref.FindBoneIndex(TEXT("calf_r"));
    const int32 Head=Ref.FindBoneIndex(TEXT("head"));
    if (Pelvis==INDEX_NONE || LeftCalf==INDEX_NONE || RightCalf==INDEX_NONE) return;
    // Five contact families, 48 visible samples each. Skirt tips, hat and held
    // props cannot become false supports for the rising anatomical body.
    int32 Seen[5]={};
    TArray<int32> Slots[5];
    SupportSamples.Reserve(240);
    for (const auto& Section:LOD.RenderSections)
    {
        if (Section.bDisabled || !Section.NumVertices) continue;
        const uint32 Step=FMath::Max(1u,static_cast<uint32>(Count/2048));
        for (uint32 V=Section.BaseVertexIndex;V<Section.BaseVertexIndex+Section.NumVertices;V+=Step)
        {
            uint32 Offset=0,Influences=0;
            Weights->GetVertexInfluenceOffsetCount(V,Offset,Influences);
            int32 Dominant=INDEX_NONE; uint32 Maximum=0,Total=0;
            for (uint32 I=0;I<Influences;++I)
            {
                const uint32 Weight=Weights->GetBoneWeight(V,I);
                const int32 Local=Weights->GetBoneIndex(V,I);
                if (!Section.BoneMap.IsValidIndex(Local)) continue;
                Total+=Weight;
                if (Weight>Maximum) { Maximum=Weight; Dominant=Section.BoneMap[Local]; }
            }
            if (!Total || Dominant==INDEX_NONE) continue;
            const FVector Position(LOD.StaticVertexBuffers.PositionVertexBuffer.VertexPosition(V));
            const FString Name=Ref.GetBoneName(Dominant).ToString();
            int32 Group=INDEX_NONE;
            if (Name.StartsWith(TEXT("foot_")) || Name.StartsWith(TEXT("ball_"))) Group=0;
            else if (Name.StartsWith(TEXT("calf_")) &&
                FMath::Min(FVector::Distance(Position,Bind[LeftCalf].GetLocation()),
                    FVector::Distance(Position,Bind[RightCalf].GetLocation()))<12.f) Group=1;
            else if ((Name==TEXT("pelvis") || Name.StartsWith(TEXT("spine_"))) &&
                Position.Z>Bind[Pelvis].GetLocation().Z-8.f) Group=2;
            else if (Name.StartsWith(TEXT("hand_"))) Group=3;
            else if (Name==TEXT("head") && Head!=INDEX_NONE &&
                FVector::DistSquared(Position,Bind[Head].GetLocation())<FMath::Square(12.f)) Group=4;
            if (Group==INDEX_NONE) continue;
            const int32 Pick=Seen[Group]<48?Seen[Group]:int32((V*1664525u+uint32(Seen[Group])*1013904223u)%uint32(Seen[Group]+1));
            ++Seen[Group];
            if (Pick>=48) continue;
            if (Pick==Slots[Group].Num()) Slots[Group].Add(SupportSamples.AddDefaulted());
            auto& Sample=SupportSamples[Slots[Group][Pick]];
            Sample.Weights.Reset();
            for (uint32 I=0;I<Influences;++I)
            {
                const uint32 Weight=Weights->GetBoneWeight(V,I);
                const int32 Local=Weights->GetBoneIndex(V,I);
                if (!Weight || !Section.BoneMap.IsValidIndex(Local)) continue;
                const int32 Bone=Section.BoneMap[Local];
                Sample.Weights.Add({Bone,Bind[Bone].InverseTransformPosition(Position),float(Weight)/Total});
            }
        }
    }
}

FWitchRecoveryLegNode::FWitchRecoveryLegNode()
{
    Hip.BoneName=TEXT("pelvis");
    for (int32 I=0;I<2;++I)
    {
        const FString Side=I==0?TEXT("l"):TEXT("r");
        Upper[I].BoneName=FName(*(TEXT("thigh_")+Side));
        Knee[I].BoneName=FName(*(TEXT("calf_")+Side));
        Foot[I].BoneName=FName(*(TEXT("foot_")+Side));
        Toe[I].BoneName=FName(*(TEXT("ball_")+Side));
    }
    Alpha=0.f;
}

void FWitchRecoveryLegNode::InitializeBoneReferences(const FBoneContainer& Bones)
{
    Hip.Initialize(Bones);
    for (int32 I=0;I<2;++I)
    { Upper[I].Initialize(Bones); Knee[I].Initialize(Bones); Foot[I].Initialize(Bones); Toe[I].Initialize(Bones); }
    LegLength=0.f;
    if (!IsValidToEvaluate(nullptr,Bones)) return;
    auto Rest=[&](const FBoneReference& Bone)
    {
        const auto Index=Bone.GetCompactPoseIndex(Bones);
        FTransform Pose=Bones.GetRefPoseTransform(Index);
        for (auto Parent=Bones.GetParentBoneIndex(Index);Parent!=INDEX_NONE;Parent=Bones.GetParentBoneIndex(Parent))
            Pose*=Bones.GetRefPoseTransform(Parent);
        return Pose;
    };
    const FTransform HipRest=Rest(Hip);
    const FVector LeftUpper=Rest(Upper[0]).GetLocation(),RightUpper=Rest(Upper[1]).GetLocation();
    const FVector Feet=(Rest(Foot[0]).GetLocation()+Rest(Foot[1]).GetLocation())*.5;
    const FVector Toes=(Rest(Toe[0]).GetLocation()+Rest(Toe[1]).GetLocation())*.5;
    const FVector Down=(Feet-HipRest.GetLocation()).GetSafeNormal();
    const FVector Across=(RightUpper-LeftUpper).GetSafeNormal();
    FVector Forward=Toes-Feet;
    Forward-=Down*FVector::DotProduct(Forward,Down)+Across*FVector::DotProduct(Forward,Across);
    Forward.Normalize();
    if (Forward.IsNearlyZero()) Forward=FVector::CrossProduct(Across,Down).GetSafeNormal();
    DownLocal=HipRest.InverseTransformVectorNoScale(Down);
    AcrossLocal=HipRest.InverseTransformVectorNoScale(Across);
    ForwardLocal=HipRest.InverseTransformVectorNoScale(Forward);
    LegLength=FVector::Distance((LeftUpper+RightUpper)*.5,Feet);
    HalfWidth=FVector::Distance(LeftUpper,RightUpper)*.5+LegLength*.075f;
}

bool FWitchRecoveryLegNode::IsValidToEvaluate(const USkeleton*,const FBoneContainer& Bones)
{
    if (!Hip.IsValidToEvaluate(Bones)) return false;
    for (int32 I=0;I<2;++I)
        if (!Upper[I].IsValidToEvaluate(Bones) || !Knee[I].IsValidToEvaluate(Bones)
            || !Foot[I].IsValidToEvaluate(Bones) || !Toe[I].IsValidToEvaluate(Bones)) return false;
    return true;
}

void FWitchRecoveryLegNode::EvaluateSkeletalControl_AnyThread(
    FComponentSpacePoseContext& Output,TArray<FBoneTransform>& Out)
{
    if (LegLength<=SMALL_NUMBER) return;
    const auto& Bones=Output.Pose.GetPose().GetBoneContainer();
    const FTransform Pelvis=Output.Pose.GetComponentSpaceTransform(Hip.GetCompactPoseIndex(Bones));
    const FVector Down=Pelvis.TransformVectorNoScale(DownLocal).GetSafeNormal();
    const FVector Across=Pelvis.TransformVectorNoScale(AcrossLocal).GetSafeNormal();
    const FVector Forward=Pelvis.TransformVectorNoScale(ForwardLocal).GetSafeNormal();
    // All limits use this rig's original leg length. There are no traces, cloth
    // scans or UObject reads on the animation worker thread.
    auto InsideLegRegion=[&](FVector Point,float Side,bool bAnkle)
    {
        const FVector Relative=Point-Pelvis.GetLocation();
        const float Lateral=FVector::DotProduct(Relative,Across);
        const float Along=FVector::DotProduct(Relative,Down);
        const float Front=FVector::DotProduct(Relative,Forward);
        const float MinSide=LegLength*.025f;
        const float DesiredSide=Side*FMath::Clamp(Side*Lateral,MinSide,HalfWidth);
        // Walking keeps the original lift/contact height. Recovery separately
        // prevents a curled leg from folding into the torso.
        const float DesiredAlong=bWalkingPose?Along:FMath::Max(Along,LegLength*(bAnkle?.18f:.09f));
        Point+=Across*(DesiredSide-Lateral)+Down*(DesiredAlong-Along);
        if (!bAnkle && !bWalkingPose) Point+=Forward*(FMath::Max(Front,LegLength*.035f)-Front);
        return Point;
    };
    for (int32 I=0;I<2;++I)
    {
        const auto UpperIndex=Upper[I].GetCompactPoseIndex(Bones);
        const auto KneeIndex=Knee[I].GetCompactPoseIndex(Bones);
        const auto FootIndex=Foot[I].GetCompactPoseIndex(Bones);
        FTransform U=Output.Pose.GetComponentSpaceTransform(UpperIndex);
        FTransform K=Output.Pose.GetComponentSpaceTransform(KneeIndex);
        FTransform F=Output.Pose.GetComponentSpaceTransform(FootIndex);
        const float Side=I==0?-1.f:1.f;
        FVector Target=InsideLegRegion(F.GetLocation(),Side,true);
        const FVector ToeOffset=Output.Pose.GetComponentSpaceTransform(Toe[I].GetCompactPoseIndex(Bones)).GetLocation()-F.GetLocation();
        const float ToeAlong=FVector::DotProduct(Target+ToeOffset-Pelvis.GetLocation(),Down);
        // A curled ankle can leave its toes pointing back into the torso.
        // Move the whole foot target, retaining the authored ankle rotation.
        if (!bWalkingPose) Target+=Down*FMath::Max(0.f,LegLength*.18f-ToeAlong);
        if (bWalkingPose)
        {
            // Measured original Master/Walk: leg 87.38 cm, hem 89.13 cm
            // below pelvis, robe front/back +17.18/-29.02 cm. Constrain the
            // lifted foot inside that silhouette after stride/ground IK;
            // planted toes remain free to emerge below the original hem.
            const float Covered=FMath::Clamp((LegLength*1.045f-ToeAlong)/(LegLength*.06f),0.f,1.f);
            const float Front=FVector::DotProduct(Target-Pelvis.GetLocation(),Forward);
            const float ToeFront=FVector::DotProduct(ToeOffset,Forward);
            const float Rear=-LegLength*.332f+LegLength*.07f;
            const float Ahead=LegLength*.197f-FMath::Max(0.f,ToeFront)-LegLength*.045f;
            const float Fitted=FMath::Clamp(Front,Rear,FMath::Max(Rear,Ahead));
            Target+=Forward*((Fitted-Front)*Covered);
        }
        const FVector Pole=bWalkingPose?K.GetLocation():InsideLegRegion(K.GetLocation(),Side,false);
        if (Target.Equals(F.GetLocation(),.01f) && Pole.Equals(K.GetLocation(),.01f)) continue;
        const FQuat FootRotation=F.GetRotation();
        AnimationCore::SolveTwoBoneIK(U,K,F,Pole,Target,false,1.f,1.f);
        F.SetRotation(FootRotation);
        Out.Emplace(UpperIndex,U); Out.Emplace(KneeIndex,K); Out.Emplace(FootIndex,F);
    }
    if (bGroundRecovery && !SupportSamples.IsEmpty())
    {
        // Evaluate the selected contact skin against the admitted floor plane.
        // This includes the robe-aware leg solve, without reinstating walking
        // foot locks or planting both feet during an authored kneel/roll.
        TArray<FTransform,TInlineAllocator<128>> ContactFrames;
        ContactFrames.SetNum(Bones.GetCompactPoseNumBones());
        for (int32 I=0;I<ContactFrames.Num();++I)
        {
            const FCompactPoseBoneIndex Index(I);
            const auto Parent=Bones.GetParentBoneIndex(Index);
            const FTransform Original=Output.Pose.GetComponentSpaceTransform(Index);
            ContactFrames[I]=Parent==INDEX_NONE?Original:
                Original.GetRelativeTransform(Output.Pose.GetComponentSpaceTransform(Parent))*ContactFrames[Parent.GetInt()];
            for (const auto& Change:Out) if (Change.BoneIndex==Index)
            { ContactFrames[I]=Change.Transform; break; }
        }
        double Gap=TNumericLimits<double>::Max();
        for (const auto& Sample:SupportSamples)
        {
            FVector Point=FVector::ZeroVector; bool bComplete=true;
            for (const auto& Weight:Sample.Weights)
            {
                const auto Index=Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(Weight.MeshBone));
                if (Index==INDEX_NONE)
                { bComplete=false; break; }
                Point+=ContactFrames[Index.GetInt()].TransformPosition(Weight.BonePoint)*Weight.Weight;
            }
            if (bComplete) Gap=FMath::Min(Gap,FVector::DotProduct(Point-FloorPoint,FloorNormal)-ContactClearance);
        }
        if (Gap!=TNumericLimits<double>::Max())
        {
            const double Vertical=FMath::Max(.2,FVector::DotProduct(WorldUp,FloorNormal));
            const FVector Offset=WorldUp*FMath::Clamp(-Gap/Vertical,-double(LegLength),double(LegLength*.3f));
            for (auto& Change:Out) Change.Transform.AddToTranslation(Offset);
            FTransform Root=Output.Pose.GetComponentSpaceTransform(FCompactPoseBoneIndex(0));
            Root.AddToTranslation(Offset);
            Out.Emplace(FCompactPoseBoneIndex(0),Root);
        }
    }
    Out.Sort(FCompareBoneTransformIndex());
}
