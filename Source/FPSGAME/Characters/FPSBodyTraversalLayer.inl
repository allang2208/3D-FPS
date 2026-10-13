// Included inside FPSBodyAnimation after FControls. Full-body traversal owns
// the final pose; ordinary weapon/aim layers cannot overwrite its support arms.
struct FTraversalLayer : FAnimNode_Base
{
    FPoseLink Base,Authored;
    FBoneReference Pelvis,Hands[2];
    TArray<FTransform> LastAuthoredPose;
    float Weight=0.f,ContactWeight=0.f;
    bool bActive=false;
    FQuat Alignment=FQuat::Identity;
    FVector Handholds[2];
    FTraversalLayer()
    {Pelvis.BoneName=TEXT("pelvis");Hands[0].BoneName=TEXT("hand_r");Hands[1].BoneName=TEXT("hand_l");}
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& C) override
    {Base.Initialize(C);Authored.Initialize(C);}
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& C) override
    {
        Base.CacheBones(C);Authored.CacheBones(C);LastAuthoredPose.Reset();
        const auto& Bones=C.AnimInstanceProxy->GetRequiredBones();
        Pelvis.Initialize(Bones);for(auto& Hand:Hands)Hand.Initialize(Bones);
    }
    virtual void Update_AnyThread(const FAnimationUpdateContext& C) override
    {Base.Update(C);if(bActive)Authored.Update(C);}
    virtual void Evaluate_AnyThread(FPoseContext& Out) override
    {
        Base.Evaluate(Out);
        if(Weight<=ZERO_ANIMWEIGHT_THRESH){LastAuthoredPose.Reset();return;}
        const auto& Bones=Out.Pose.GetBoneContainer();
        if(bActive)
        {
            if(!Pelvis.IsValidToEvaluate(Bones)||!Hands[0].IsValidToEvaluate(Bones)||!Hands[1].IsValidToEvaluate(Bones))return;
            FPoseContext Donor(Out);Authored.Evaluate(Donor);
            FCSPose<FCompactPose> Pose;Pose.InitPose(Donor.Pose);
            const auto HipIndex=Pelvis.GetCompactPoseIndex(Bones);
            auto Hip=Pose.GetComponentSpaceTransform(HipIndex);
            const FVector HandCenter=(Pose.GetComponentSpaceTransform(Hands[0].GetCompactPoseIndex(Bones)).GetLocation()
                +Pose.GetComponentSpaceTransform(Hands[1].GetCompactPoseIndex(Bones)).GetLocation())*.5;
            // Root translation is locked in the asset: only the swept capsule
            // moves the actor. Fit the donor's whole support pose to the actual
            // ledge, retaining its hip/leg effort and both native arm lengths.
            const FVector SupportShift=((Handholds[0]+Handholds[1])*.5-Alignment.RotateVector(HandCenter))*ContactWeight;
            Hip.SetLocation(Alignment.RotateVector(Hip.GetLocation())+SupportShift);
            Hip.SetRotation((Alignment*Hip.GetRotation()).GetNormalized());
            TArray<FBoneTransform,TInlineAllocator<1>> Change;Change.Emplace(HipIndex,Hip);
            Pose.LocalBlendCSBoneTransforms(Change,1.f);
            if(ContactWeight>ZERO_ANIMWEIGHT_THRESH)for(int32 I=0;I<2;++I)
            {
                const auto Wrist=Hands[I].GetCompactPoseIndex(Bones),Elbow=Bones.GetParentBoneIndex(Wrist),Shoulder=Bones.GetParentBoneIndex(Elbow);
                const auto Hand=Pose.GetComponentSpaceTransform(Wrist);
                FLegReference Arm;Arm.Set(Pose.GetComponentSpaceTransform(Shoulder).GetLocation(),
                    Pose.GetComponentSpaceTransform(Elbow).GetLocation(),Hand.GetLocation());
                FTransform Target=Hand;Target.SetLocation(FMath::Lerp(Hand.GetLocation(),Handholds[I],ContactWeight));
                FControls::Solve(Pose,Hands[I],Target,Arm.Pole(Arm.Hip,Target.GetLocation()),1.f);
            }
            Donor.Pose=Pose.GetPose();
            FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Donor.Pose);
            LastAuthoredPose.SetNum(Bones.GetCompactPoseNumBones());
            for(int32 I=0;I<LastAuthoredPose.Num();++I)LastAuthoredPose[I]=Donor.Pose[FCompactPoseBoneIndex(I)];
        }
        // On completion or interruption, stop chasing world handholds at once.
        // Blend the last visible local pose into the current fall/ground/action.
        if(LastAuthoredPose.Num()!=Bones.GetCompactPoseNumBones())return;
        for(int32 I=0;I<LastAuthoredPose.Num();++I)
        {
            const FCompactPoseBoneIndex Bone(I);
            FTransform Mixed;Mixed.Blend(Out.Pose[Bone],LastAuthoredPose[I],Weight);Out.Pose[Bone]=Mixed;
        }
    }
};

struct FTraversalPlayback
{
    UAnimSequence* Asset=nullptr;
    float Contact=0.f,Release=0.f,End=0.f,Time=0.f,Weight=0.f,LastProgress=0.f;
    bool bActive=false;
    template<typename FLookup>
    void Update(const UFPSPlayerBodyAnimInstance& D,float Dt,FLookup&& Lookup)
    {
        const auto& S=D.BodyState;
        const bool WasActive=bActive;
        bActive=FPSBodyPoses::Traversing(S.Motion)&&S.Action!=EFPSBodyAction::Dead;
        if(bActive)
        {
            const FName Key=S.Motion==EFPSBodyMotion::Vault?TEXT("Traversal.Vault"):
                S.ActionVariant==TEXT("Climb")?TEXT("Traversal.Climb"):TEXT("Traversal.Mantle");
            auto* Next=Lookup(Key);
            if(Next!=Asset)
            {
                Asset=Next;Contact=Release=End=0.f;
                if(Asset)for(const auto& Marker:Asset->AuthoredSyncMarkers)
                {
                    if(Marker.MarkerName==TEXT("TraversalContact"))Contact=Marker.Time;
                    if(Marker.MarkerName==TEXT("TraversalRelease"))Release=Marker.Time;
                    if(Marker.MarkerName==TEXT("TraversalExit"))End=Marker.Time;
                }
            }
            bActive=Asset&&Contact>0.f&&Release>Contact&&End>Release;
        }
        if(bActive)
        {
            if(!WasActive||S.MotionProgress+.08f<LastProgress)Weight=0.f;
            const float P=FMath::Clamp(S.MotionProgress,0.f,1.f);
            Time=FPSTraversalTiming::Sample(P,S.MotionContact,S.MotionRelease,Contact,Release,End);
            LastProgress=P;
        }
        // These are pose handoffs only; playback/contact never gain a second clock.
        Weight=FMath::FInterpConstantTo(Weight,bActive?1.f:0.f,Dt,bActive?20.f:1.f/.12f);
    }
};
