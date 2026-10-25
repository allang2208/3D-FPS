// Opposite bed-side motion in native bind frames. Mirror the full pose before
// its locomotion blend so bone lengths, clothing followers and timing agree.
struct FFurnitureMirrorLayer : FAnimNode_Base
{
    FPoseLink Source;
    bool bEnabled=false;
    TArray<FCompactPoseBoneIndex> MirrorBones;
    TCustomBoneIndexArray<FQuat,FCompactPoseBoneIndex> ReferenceRotations;
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& C) override {Source.Initialize(C);}
    virtual void Update_AnyThread(const FAnimationUpdateContext& C) override {Source.Update(C);}
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& C) override
    {
        Source.CacheBones(C);const auto& Bones=C.AnimInstanceProxy->GetRequiredBones();
        const auto& Skeleton=Bones.GetReferenceSkeleton();const int32 Count=Bones.GetCompactPoseNumBones();
        MirrorBones.SetNum(Count);ReferenceRotations.SetNumUninitialized(Count);
        TMap<FName,FCompactPoseBoneIndex> ByName;
        for(int32 I=0;I<Count;++I)
        {
            const FCompactPoseBoneIndex Bone(I);ByName.Add(Skeleton.GetBoneName(Bones.MakeMeshPoseIndex(Bone).GetInt()),Bone);
            const auto Parent=Bones.GetParentBoneIndex(Bone);
            ReferenceRotations[Bone]=Parent==INDEX_NONE?Bones.GetRefPoseTransform(Bone).GetRotation():
                (ReferenceRotations[Parent]*Bones.GetRefPoseTransform(Bone).GetRotation()).GetNormalized();
        }
        for(int32 I=0;I<Count;++I)
        {
            const FCompactPoseBoneIndex Bone(I);const FString Name=Skeleton.GetBoneName(Bones.MakeMeshPoseIndex(Bone).GetInt()).ToString();
            const FString Opposite=Name.EndsWith(TEXT("_l"))?Name.LeftChop(2)+TEXT("_r"):
                Name.EndsWith(TEXT("_r"))?Name.LeftChop(2)+TEXT("_l"):Name;
            const auto* Other=ByName.Find(FName(*Opposite));MirrorBones[I]=Other?*Other:Bone;
        }
    }
    virtual void Evaluate_AnyThread(FPoseContext& Out) override
    {
        Source.Evaluate(Out);
        if(bEnabled&&!MirrorBones.IsEmpty())FAnimationRuntime::MirrorPose(Out.Pose,EAxis::X,MirrorBones,ReferenceRotations);
    }
};

// Final authored pose plus the measured seat-to-floor difference. Shared by
// the owner body, clothing followers and observers; no furniture world scan.
struct FFurnitureFloorLayer : FAnimNode_Base
{
    FPoseLink Source;
    FBoneReference Feet[2];
    float Drop=0.f,Weight=0.f;
    FFurnitureFloorLayer(){Feet[0].BoneName=TEXT("foot_l");Feet[1].BoneName=TEXT("foot_r");}
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& C) override {Source.Initialize(C);}
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& C) override
    {Source.CacheBones(C);for(auto& Foot:Feet)Foot.Initialize(C.AnimInstanceProxy->GetRequiredBones());}
    virtual void Update_AnyThread(const FAnimationUpdateContext& C) override {Source.Update(C);}
    virtual void Evaluate_AnyThread(FPoseContext& Out) override
    {
        Source.Evaluate(Out);if(Weight<=ZERO_ANIMWEIGHT_THRESH||FMath::IsNearlyZero(Drop))return;
        const auto& Bones=Out.Pose.GetBoneContainer();FCSPose<FCompactPose> Pose;Pose.InitPose(Out.Pose);
        for(const auto& Foot:Feet)
        {
            if(!Foot.IsValidToEvaluate(Bones))continue;
            const auto F=Foot.GetCompactPoseIndex(Bones),K=Bones.GetParentBoneIndex(F),H=Bones.GetParentBoneIndex(K);
            FTransform Target=Pose.GetComponentSpaceTransform(F);Target.AddToTranslation(FVector(0,0,-Drop));
            const FVector Pole=Pose.GetComponentSpaceTransform(H).GetLocation()+FVector(0,100,-25);
            FControls::Solve(Pose,Foot,Target,Pole,Weight);
        }
        Out.Pose=Pose.GetPose();FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Out.Pose);
    }
};
