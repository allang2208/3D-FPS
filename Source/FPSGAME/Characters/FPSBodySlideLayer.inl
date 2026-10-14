// Included inside FPSBodyAnimation. Only the pelvis and its lower-body branches
// come from the donor; the existing equipment layer still owns the upper body.
struct FSlideLayer : FAnimNode_Base
{
    FPoseLink Base,Authored;
    FBoneReference Pelvis,Chest;
    TArray<FCompactPoseBoneIndex> LowerBones;
    TArray<FTransform> LastPose,EntryPose;
    float Weight=0.f,Delta=0.f,TransitionAge=1.f;
    bool bChanged=false;
    FQuat Alignment=FQuat::Identity;
    FSlideLayer(){Pelvis.BoneName=TEXT("pelvis");Chest.BoneName=TEXT("spine_01");}
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& C) override
    {Base.Initialize(C);Authored.Initialize(C);}
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& C) override
    {
        Base.CacheBones(C);Authored.CacheBones(C);
        const auto& Bones=C.AnimInstanceProxy->GetRequiredBones();
        Pelvis.Initialize(Bones);Chest.Initialize(Bones);
        LowerBones.Reset();LastPose.Reset();EntryPose.Reset();
        const auto& Ref=Bones.GetReferenceSkeleton();
        const int32 Hip=Ref.FindBoneIndex(Pelvis.BoneName),Upper=Ref.FindBoneIndex(Chest.BoneName);
        for(int32 I=0;I<Bones.GetCompactPoseNumBones();++I)
        {
            const FCompactPoseBoneIndex B(I);
            for(int32 P=Bones.MakeMeshPoseIndex(B).GetInt();P!=INDEX_NONE;P=Ref.GetParentIndex(P))
            {
                if(P==Upper)break;
                if(P==Hip){LowerBones.Add(B);break;}
            }
        }
    }
    virtual void Update_AnyThread(const FAnimationUpdateContext& C) override
    {Base.Update(C);if(Weight>ZERO_ANIMWEIGHT_THRESH)Authored.Update(C);}
    virtual void Evaluate_AnyThread(FPoseContext& Out) override
    {
        Base.Evaluate(Out);
        if(Weight<=ZERO_ANIMWEIGHT_THRESH){LastPose.Reset();EntryPose.Reset();return;}
        const auto& Bones=Out.Pose.GetBoneContainer();
        if(!Pelvis.IsValidToEvaluate(Bones)||!Chest.IsValidToEvaluate(Bones))return;
        FPoseContext Donor(Out);Authored.Evaluate(Donor);
        if(bChanged){EntryPose=LastPose;TransitionAge=0.f;}
        TransitionAge+=Delta;
        const float Transition=Ease(TransitionAge/.12f);
        LastPose.SetNum(LowerBones.Num());
        for(int32 I=0;I<LowerBones.Num();++I)
        {
            const auto B=LowerBones[I];
            if(Transition<1.f&&EntryPose.Num()==LowerBones.Num())
            {
                FTransform Blended;Blended.Blend(EntryPose[I],Donor.Pose[B],Transition);Donor.Pose[B]=Blended;
            }
            LastPose[I]=Donor.Pose[B];
        }
        // Align the authored lower body as one shape. This preserves the knee
        // planes and ankle/toe rotations instead of flattening sliding feet.
        FCSPose<FCompactPose> Slide;Slide.InitPose(Donor.Pose);
        const auto HipIndex=Pelvis.GetCompactPoseIndex(Bones);
        auto Hip=Slide.GetComponentSpaceTransform(HipIndex);
        Hip.SetLocation(Alignment.RotateVector(Hip.GetLocation()));
        Hip.SetRotation((Alignment*Hip.GetRotation()).GetNormalized());
        TArray<FBoneTransform,TInlineAllocator<1>> Change;Change.Emplace(HipIndex,Hip);
        Slide.LocalBlendCSBoneTransforms(Change,1.f);
        Donor.Pose=Slide.GetPose();
        FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Slide,Donor.Pose);
        FCSPose<FCompactPose> Before;Before.InitPose(Out.Pose);
        const auto ChestIndex=Chest.GetCompactPoseIndex(Bones);
        const FQuat UpperRotation=Before.GetComponentSpaceTransform(ChestIndex).GetRotation();
        for(const auto B:LowerBones)
        {
            FTransform Blended;Blended.Blend(Out.Pose[B],Donor.Pose[B],Weight);Out.Pose[B]=Blended;
        }
        // Counter pelvis roll at the first spine joint without changing any
        // bone length or scale. Hands will be fitted to this torso downstream.
        FCSPose<FCompactPose> Mixed;Mixed.InitPose(Out.Pose);
        auto Upper=Mixed.GetComponentSpaceTransform(ChestIndex);Upper.SetRotation(UpperRotation);
        Change.Reset();Change.Emplace(ChestIndex,Upper);Mixed.LocalBlendCSBoneTransforms(Change,1.f);
        Out.Pose=Mixed.GetPose();
        FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Mixed,Out.Pose);
    }
};

// Value-only playback state. Sequence ranges are authored sync markers, avoiding
// the long approach/recovery padding in motion-matching source recordings.
struct FSlidePlayback
{
    FName Key,EntryKey;
    UAnimSequence* Asset=nullptr;
    float Begin=0.f,End=0.f,Time=0.f,Age=0.f,ExitAge=0.f,ExitDuration=.5f;
    float LastProgress=0.f,Weight=0.f,Yaw=0.f;
    bool bWasSliding=false,bExiting=false,bChanged=false;
    FQuat Tilt=FQuat::Identity;
    template<typename FLookup>
    void Select(FName Next,FLookup&& Lookup)
    {
        auto* NextAsset=Lookup(Next);
        if(Next==Key&&NextAsset==Asset)return;
        Key=Next;Asset=NextAsset;bChanged=true;Begin=0.f;End=Asset?Asset->GetPlayLength():0.f;
        if(Asset)for(const auto& Marker:Asset->AuthoredSyncMarkers)
        {
            if(Marker.MarkerName==TEXT("SlideBegin"))Begin=Marker.Time;
            if(Marker.MarkerName==TEXT("SlideEnd"))End=Marker.Time;
        }
    }
    template<typename FLookup>
    void Update(const UFPSPlayerBodyAnimInstance& D,float Dt,float Gait,FLookup&& Lookup)
    {
        bChanged=false;
        const bool Sliding=D.BodyState.Motion==EFPSBodyMotion::Slide&&!D.bFalling&&D.BodyState.Action!=EFPSBodyAction::Dead;
        const bool Available=Lookup(FName(TEXT("Slide.Loop")))!=nullptr;
        const bool NewSlide=Sliding&&(!bWasSliding||D.BodyState.MotionProgress+.1f<LastProgress);
        // Progress saturates at one on sustained downhill slides; its measured
        // rate then becomes zero. Keep advancing the loop instead of dividing
        // by that zero rate and jumping through the recording.
        const bool HasClock=D.BodyState.MotionProgressRate>.001f&&D.BodyState.MotionProgress<.999f;
        const float RecordedAge=HasClock?D.BodyState.MotionProgress/D.BodyState.MotionProgressRate:0.f;
        if(NewSlide)
        {
            Age=HasClock?RecordedAge:(D.BodyState.MotionProgress>=.999f?.42f:0.f);bExiting=false;
            // Slide entry clears sprint intent in gameplay; use actual speed.
            const bool Fast=D.Speed>500.f,Left=FMath::Frac(Gait)<.5f;
            EntryKey=FName(Fast?(Left?TEXT("Slide.Enter.Sprint.L"):TEXT("Slide.Enter.Sprint.R")):
                (Left?TEXT("Slide.Enter.L"):TEXT("Slide.Enter.R")));
        }
        float Target=0.f;
        if(Sliding&&Available)
        {
            if(!NewSlide)Age=FMath::Max(Age+Dt,RecordedAge);
            constexpr float EntrySeconds=.42f;
            Select(Age<EntrySeconds?EntryKey:FName(TEXT("Slide.Loop")),Lookup);
            const float Length=FMath::Max(.01f,End-Begin);
            Time=Begin+(Age<EntrySeconds?FMath::Clamp(Age/EntrySeconds,0.f,1.f)*Length:
                FMath::Fmod(FMath::Max(0.f,Age-EntrySeconds),Length));
            Target=1.f;
            const FVector Direction=D.BodyState.MotionDirection;
            const float Desired=FMath::Clamp(FMath::RadiansToDegrees(FMath::Atan2(-Direction.X,Direction.Y)),-65.f,65.f);
            Yaw=FMath::FInterpTo(Yaw,Desired,Dt,12.f);
        }
        else if(bWasSliding&&Available&&D.BodyState.Motion==EFPSBodyMotion::Ground&&!D.bFalling&&D.BodyState.Action!=EFPSBodyAction::Dead)
        {
            const bool Moving=D.Speed>25.f;
            const TCHAR* Exit=D.BodyState.bCrouched?(Moving?TEXT("Slide.Exit.CrouchMove"):TEXT("Slide.Exit.Crouch")):
                !Moving?TEXT("Slide.Exit.Stand"):D.BodyState.bSprinting?TEXT("Slide.Exit.Sprint"):
                D.Speed>300.f?TEXT("Slide.Exit.Run"):TEXT("Slide.Exit.Walk");
            Select(FName(Exit),Lookup);ExitAge=0.f;bExiting=Asset!=nullptr;
            ExitDuration=FMath::Clamp(End-Begin,.3f,.65f);
        }
        if(!Sliding&&bExiting)
        {
            if(D.bFalling||D.BodyState.Motion!=EFPSBodyMotion::Ground||D.BodyState.Action==EFPSBodyAction::Dead)bExiting=false;
            else
            {
                ExitAge+=Dt;
                Time=FMath::Lerp(Begin,End,FMath::Clamp(ExitAge/ExitDuration,0.f,1.f));
                Target=1.f-Ease((ExitAge-(ExitDuration-.16f))/.16f);
                if(ExitAge>=ExitDuration)bExiting=false;
            }
        }
        Weight=FMath::FInterpConstantTo(Weight,Asset?Target:0.f,Dt,Target>Weight?10.f:12.5f);
        if(Weight<=ZERO_ANIMWEIGHT_THRESH){Key=NAME_None;Asset=nullptr;Yaw=0.f;Tilt=FQuat::Identity;}
        bWasSliding=Sliding;LastProgress=D.BodyState.MotionProgress;
    }
};
