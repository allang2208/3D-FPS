// Reuse the right-primary pistol library for a lone left-primary pistol.
// Mirror complete local chains in their native bind frames, including weighted
// twist/corrective bones. The movement layer keeps its feet and root motion.
struct FSinglePistolMirrorLayer : FAnimNode_Base
{
    FPoseLink Source;
    bool bEnabled=false;
    FCompactPoseBoneIndex ChestRoot{INDEX_NONE};
    TArray<FCompactPoseBoneIndex> MirrorBones;
    TCustomBoneIndexArray<FQuat,FCompactPoseBoneIndex> ReferenceRotations;

    virtual void Initialize_AnyThread(const FAnimationInitializeContext& C) override {Source.Initialize(C);}
    virtual void Update_AnyThread(const FAnimationUpdateContext& C) override {Source.Update(C);}
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& C) override
    {
        Source.CacheBones(C);
        const auto& Bones=C.AnimInstanceProxy->GetRequiredBones();
        const auto& Skeleton=Bones.GetReferenceSkeleton();
        const int32 SpineRoot=Skeleton.FindBoneIndex(TEXT("spine_01"));
        ChestRoot=FCompactPoseBoneIndex(INDEX_NONE);
        MirrorBones.Init(FCompactPoseBoneIndex(INDEX_NONE),Bones.GetCompactPoseNumBones());
        ReferenceRotations.SetNumUninitialized(Bones.GetCompactPoseNumBones());
        TMap<FName,FCompactPoseBoneIndex> ByName;
        for(int32 I=0;I<MirrorBones.Num();++I)
        {
            const FCompactPoseBoneIndex Bone(I);
            const int32 MeshBone=Bones.MakeMeshPoseIndex(Bone).GetInt();
            ByName.Add(Skeleton.GetBoneName(MeshBone),Bone);
            const auto Parent=Bones.GetParentBoneIndex(Bone);
            ReferenceRotations[Bone]=Parent==INDEX_NONE?Bones.GetRefPoseTransform(Bone).GetRotation():
                (ReferenceRotations[Parent]*Bones.GetRefPoseTransform(Bone).GetRotation()).GetNormalized();
            if(MeshBone==SpineRoot)ChestRoot=Bone;
        }
        for(int32 I=0;I<MirrorBones.Num();++I)
        {
            const FCompactPoseBoneIndex Bone(I);
            const int32 MeshBone=Bones.MakeMeshPoseIndex(Bone).GetInt();
            if(SpineRoot==INDEX_NONE||(MeshBone!=SpineRoot&&!Skeleton.BoneIsChildOf(MeshBone,SpineRoot)))continue;
            const FString Name=Skeleton.GetBoneName(MeshBone).ToString();
            const FString Counterpart=Name.EndsWith(TEXT("_r"))?Name.LeftChop(2)+TEXT("_l"):
                Name.EndsWith(TEXT("_l"))?Name.LeftChop(2)+TEXT("_r"):Name;
            if(const auto* Other=ByName.Find(FName(Counterpart)))MirrorBones[I]=*Other;
        }
    }
    virtual void Evaluate_AnyThread(FPoseContext& Out) override
    {
        Source.Evaluate(Out);
        if(!bEnabled||ChestRoot==INDEX_NONE)return;
        const auto Parent=Out.Pose.GetBoneContainer().GetParentBoneIndex(ChestRoot);
        FCSPose<FCompactPose> Before;Before.InitPose(Out.Pose);
        const FQuat PelvisRotation=Before.GetComponentSpaceTransform(Parent).GetRotation();
        const FQuat MirroredPelvis=(FAnimationRuntime::MirrorQuat(PelvisRotation,EAxis::X)*
            FAnimationRuntime::MirrorQuat(ReferenceRotations[Parent],EAxis::X).Inverse()*ReferenceRotations[Parent]).GetNormalized();
        FAnimationRuntime::MirrorPose(Out.Pose,EAxis::X,MirrorBones,ReferenceRotations);
        // Keep the donor's mirrored chest orientation even though the pelvis
        // still belongs to the unmirrored directional gait. Retain its native
        // attachment/translation so the waist cannot separate from the legs.
        Out.Pose[ChestRoot].SetRotation((PelvisRotation.Inverse()*MirroredPelvis*Out.Pose[ChestRoot].GetRotation()).GetNormalized());
    }
};
