// The library owns complete upper-body FK transforms. Only local-pose blends
// and the source shot delta are applied here; no wrist targets or elbow solve.
struct FSinglePistolSourceLayer : FUpperLayer
{
    FPoseLink Action,Shot,ShotBase;
    float ActionWeight=0.f,ShotWeight=0.f,Delta=0.f,Age=1.f;
    FName Key,LastKey;
    FString Instance,LastInstance;
    TArray<FTransform> Last,Entry;
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& C) override
    {FUpperLayer::Initialize_AnyThread(C);Action.Initialize(C);Shot.Initialize(C);ShotBase.Initialize(C);Last.Reset();Entry.Reset();}
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& C) override
    {FUpperLayer::CacheBones_AnyThread(C);Action.CacheBones(C);Shot.CacheBones(C);ShotBase.CacheBones(C);Last.Reset();Entry.Reset();}
    virtual void Update_AnyThread(const FAnimationUpdateContext& C) override
    {Base.Update(C);if(Weight>ZERO_ANIMWEIGHT_THRESH){Upper.Update(C);if(ActionWeight>0.f)Action.Update(C);if(ShotWeight>0.f){Shot.Update(C);ShotBase.Update(C);}}}
    virtual void Evaluate_AnyThread(FPoseContext& Out) override
    {
        Base.Evaluate(Out);
        if(Weight<=ZERO_ANIMWEIGHT_THRESH){Last.Reset();Entry.Reset();return;}
        FPoseContext Library(Out);Upper.Evaluate(Library);
        if(ActionWeight>0.f)
        {
            FPoseContext ReloadPose(Out);Action.Evaluate(ReloadPose);
            for(const auto Bone:UpperBones)
            {FTransform Mixed;Mixed.Blend(Library.Pose[Bone],ReloadPose.Pose[Bone],ActionWeight);Library.Pose[Bone]=Mixed;}
        }
        if(ShotWeight>0.f)
        {
            FPoseContext FirePose(Out),FireBase(Out);Shot.Evaluate(FirePose);ShotBase.Evaluate(FireBase);
            for(const auto Bone:UpperBones)
            {
                const FQuat Q=(FirePose.Pose[Bone].GetRotation()*FireBase.Pose[Bone].GetRotation().Inverse()).GetNormalized();
                Library.Pose[Bone].SetRotation((FQuat::Slerp(FQuat::Identity,Q,ShotWeight)*Library.Pose[Bone].GetRotation()).GetNormalized());
            }
        }
        if(UpperRoot!=INDEX_NONE)
        {
            FCSPose<FCompactPose> BaseCS,SourceCS;BaseCS.InitPose(Out.Pose);SourceCS.InitPose(Library.Pose);
            const auto Parent=Out.Pose.GetBoneContainer().GetParentBoneIndex(UpperRoot);
            Library.Pose[UpperRoot].SetRotation((BaseCS.GetComponentSpaceTransform(Parent).GetRotation().Inverse()*
                SourceCS.GetComponentSpaceTransform(UpperRoot).GetRotation()).GetNormalized());
        }
        const bool History=Last.Num()==UpperBones.Num()&&LastInstance==Instance;
        if(!History||Key!=LastKey)
        {
            Entry.SetNum(UpperBones.Num(),EAllowShrinking::No);
            for(int32 I=0;I<UpperBones.Num();++I)Entry[I]=History?Last[I]:Out.Pose[UpperBones[I]];
            Age=0.f;
        }
        Age+=Delta;const float Blend=Ease(Age/.10f);
        Last.SetNum(UpperBones.Num(),EAllowShrinking::No);
        for(int32 I=0;I<UpperBones.Num();++I)
        {
            const auto Bone=UpperBones[I];FTransform Value=Library.Pose[Bone];
            if(Blend<1.f&&Entry.Num()==UpperBones.Num())Value.Blend(Entry[I],Library.Pose[Bone],Blend);
            Last[I]=Value;Out.Pose[Bone].Blend(Out.Pose[Bone],Value,Weight);
        }
        LastKey=Key;LastInstance=Instance;
    }
};
