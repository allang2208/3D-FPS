// A closed book has weight: preserve a complete support arm and only a small
// fraction of gait. Active book/left-hand contacts retain their own authority.
void FControls::BlendBookCarry(FPoseContext& Out,FCSPose<FCompactPose>& Pose)
{
    const bool Busy=(ActionWristMask&2)||FPSBodyPoses::Traversing(State.Motion)||
        State.Action==EFPSBodyAction::Consume||State.Action==EFPSBodyAction::DoorPush||
        State.Action==EFPSBodyAction::GunBash||
        (State.Action==EFPSBodyAction::Cast&&State.Contacts.Channel!=TEXT("StaffCast"));
    if(!bBookCarryActive||Busy){bHadBookCarry=false;bHadBookPush=false;BookCarryAge=0.f;return;}
    Out.Pose=Pose.GetPose();
    FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Out.Pose);
    FPoseContext Authored(Out);BookCarry.Evaluate(Authored);
    const int32 Count=Out.Pose.GetBoneContainer().GetCompactPoseNumBones();
    // Cancellation recovers from the displayed complete chain, not from a
    // fresh wrist-only IK result. A completed push already ends at carry.
    if(bHadBookPush&&!bBookPushActive){bHadBookCarry=false;BookCarryAge=0.f;}
    if(!bHadBookCarry)
    {
        BookCarryEntryPose.SetNum(Count);
        for(int32 I=0;I<Count;++I)if(BookMotionBones[I])
            BookCarryEntryPose[I]=LastBookCarryPose.Num()==Count?LastBookCarryPose[I]:Out.Pose[FCompactPoseBoneIndex(I)];
    }
    BookCarryAge+=Delta;
    const float Alpha=Ease(BookCarryAge/.18f);
    const float Gait=FMath::Lerp(.10f,.06f,Sprint);
    FPoseContext Push(Out);
    if(bBookPushActive)
    {
        if(!bHadBookPush||BookPushProgress+.05f<LastBookPushProgress)
        {
            BookPushEntryDelta.SetNum(Count);BookPushEntryProgress=BookPushProgress;
            FPoseContext Start(Out);Start.Pose=Authored.Pose;AnchorStaffArm(Start,Pose,1);
            for(int32 I=0;I<Count;++I)if(BookMotionBones[I])
            {
                const FCompactPoseBoneIndex Bone(I);
                const auto& Entry=LastBookCarryPose.Num()==Count?LastBookCarryPose[I]:Authored.Pose[Bone];
                BookPushEntryDelta[I]=FTransform((Entry.GetRotation()*Start.Pose[Bone].GetRotation().Inverse()).GetNormalized(),
                    Entry.GetLocation()-Start.Pose[Bone].GetLocation());
            }
        }
        BookPush.Evaluate(Push);AnchorStaffArm(Push,Pose,1);
    }
    for(int32 I=0;I<Count;++I)if(BookMotionBones[I])
    {
        const FCompactPoseBoneIndex Bone(I);
        FTransform Supported,Mixed;
        Supported.Blend(Authored.Pose[Bone],Out.Pose[Bone],Gait);
        Mixed.Blend(BookCarryEntryPose[I],Supported,Alpha);
        if(bBookPushActive)
        {
            // Remove the live carry offset during the brief cock, then let
            // the authored shoulder/elbow chain drive the contact. Hand local
            // rotation and all weighted helpers belong to that same chain.
            const float Entry=1.f-Ease((BookPushProgress-BookPushEntryProgress)/.12f);
            Mixed=Push.Pose[Bone];
            Mixed.SetRotation((FQuat::Slerp(FQuat::Identity,BookPushEntryDelta[I].GetRotation(),Entry)*Mixed.GetRotation()).GetNormalized());
            Mixed.AddToTranslation(BookPushEntryDelta[I].GetLocation()*Entry);
            // The final recovery rejoins the current gait within this action,
            // so ending the gameplay state cannot cause a second wrist snap.
            const float Return=Ease((BookPushProgress-.78f)/.22f);
            FTransform Recovered;Recovered.Blend(Mixed,Supported,Return);Mixed=Recovered;
        }
        Out.Pose[Bone]=Mixed;
    }
    Pose.InitPose(Out.Pose);
    const auto& Bones=Out.Pose.GetBoneContainer();
    if(Hands[1].IsValidToEvaluate(Bones))LastHands[1]=Pose.GetComponentSpaceTransform(Hands[1].GetCompactPoseIndex(Bones));
    bHadBookCarry=true;
    bHadBookPush=bBookPushActive;LastBookPushProgress=BookPushProgress;
}
