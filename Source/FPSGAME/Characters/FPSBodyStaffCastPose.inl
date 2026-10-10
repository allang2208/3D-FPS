// Native whole-arm casting, evaluated after ordinary carry and before reactions
// and the shared VRE finger layer. The executor supplies every phase clock.
void FControls::BlendStaffCast(FPoseContext& Out,FCSPose<FCompactPose>& Pose)
{
    if(!bStaffCastActive)
    {bHadStaffCast=false;LastStaffCastPose.Reset();StaffCastEntryPose.Reset();return;}
    const auto& Bones=Out.Pose.GetBoneContainer();
    const auto Hip=Pelvis.GetCompactPoseIndex(Bones),Chest=ChestBase.GetCompactPoseIndex(Bones);
    const FVector HipLocation=Pose.GetComponentSpaceTransform(Hip).GetLocation();
    FTransform BaseChest=Pose.GetComponentSpaceTransform(Chest);BaseChest.AddToTranslation(-HipLocation);
    const auto Left=Hands[1].GetCompactPoseIndex(Bones),Elbow=Bones.GetParentBoneIndex(Left),Shoulder=Bones.GetParentBoneIndex(Elbow);
    const FTransform LeftTarget=Pose.GetComponentSpaceTransform(Left);
    FLegReference LeftArm;
    LeftArm.Set(Pose.GetComponentSpaceTransform(Shoulder).GetLocation(),Pose.GetComponentSpaceTransform(Elbow).GetLocation(),LeftTarget.GetLocation());
    Out.Pose=Pose.GetPose();
    FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Out.Pose);
    const int32 Count=Bones.GetCompactPoseNumBones();
    const bool Entry=!bHadStaffCast||LastStaffCastPhase!=StaffCastPhase||StaffCastProgress+.05f<LastStaffCastProgress;
    if(Entry)
    {
        StaffCastEntryPose.SetNum(Count);
        for(int32 I=0;I<Count;++I)
            StaffCastEntryPose[I]=bHadStaffCast&&LastStaffCastPose.Num()==Count?LastStaffCastPose[I]:Out.Pose[FCompactPoseBoneIndex(I)];
        StaffCastEntryChest=bHadStaffCast?LastStaffCastChest:BaseChest;
        StaffCastEntryProgress=StaffCastProgress;
    }
    FPoseContext Authored(Out);StaffCast.Evaluate(Authored);
    if(bStaffNativeCast)AnchorStaffArm(Authored,Pose);
    FCSPose<FCompactPose> Full;Full.InitPose(Authored.Pose);
    const auto Right=Hands[0].GetCompactPoseIndex(Bones);
    TArray<FBoneTransform,TInlineAllocator<1>> Change;
    if(!bStaffNativeCast)
    {
        auto Hand=Full.GetComponentSpaceTransform(Right);
        Hand.SetRotation((Hand.GetRotation()*FPSBodyStaffCastData::ReferenceRotation.Inverse()*StaffHandRotation).GetNormalized());
        Change.Emplace(Right,Hand);Full.LocalBlendCSBoneTransforms(Change,1.f);
    }
    Authored.Pose=Full.GetPose();
    FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Full,Authored.Pose);
    FTransform DesiredChest=Full.GetComponentSpaceTransform(Chest);
    DesiredChest.AddToTranslation(-Full.GetComponentSpaceTransform(Hip).GetLocation());
    // Anchor the take to the live pelvis without inheriting gait yaw twice.
    // The same aim rotation carries shoulder, elbow, wrist and attached shaft.
    if(bStaffNativeCast)DesiredChest=BaseChest;
    else DesiredChest.SetRotation((FQuat(FVector::ForwardVector,FMath::DegreesToRadians(
        FMath::Clamp(State.AimPitch,-70.f,70.f)*.65f))*DesiredChest.GetRotation()).GetNormalized());
    const bool Recover=StaffCastPhase==TEXT("Recover");
    const bool Ready=StaffCastPhase==TEXT("Ready");
    const float Remaining=FMath::Max(.001f,1.f-StaffCastEntryProgress);
    const float Phase=FMath::Clamp((StaffCastProgress-StaffCastEntryProgress)/Remaining,0.f,1.f);
    // Ready and cancellation both start at the last actual native pose. Gather
    // only needs a short entrance blend; its donor owns the rest of the lift.
    const float Alpha=Recover||Ready?Ease(Phase):StaffCastPhase==TEXT("Gather")?Ease(Phase/.18f):1.f;
    FTransform MixedChest;
    MixedChest.Blend(StaffCastEntryChest,Recover?BaseChest:DesiredChest,Alpha);
    for(int32 I=0;I<Count;++I)
    {
        if(bStaffNativeCast?!StaffMotionBones[I]:(!SwordUpperBones[I]||(LibraryArmBones[I]&2)))continue;
        const FCompactPoseBoneIndex B(I);
        FTransform Mixed;Mixed.Blend(StaffCastEntryPose[I],Recover?Out.Pose[B]:Authored.Pose[B],Alpha);
        Out.Pose[B]=Mixed;
    }
    Pose.InitPose(Out.Pose);
    MixedChest.AddToTranslation(HipLocation);
    Change.Reset();Change.Emplace(Chest,MixedChest);Pose.LocalBlendCSBoneTransforms(Change,1.f);
    // Torso effort cannot drag an independent left pistol off its own contact.
    auto SupportedLeft=LeftTarget;
    const FVector NewShoulder=Pose.GetComponentSpaceTransform(Shoulder).GetLocation();
    SupportedLeft.SetLocation(LeftArm.Reachable(NewShoulder,LeftTarget.GetLocation()));
    Solve(Pose,Hands[1],SupportedLeft,LeftArm.Pole(NewShoulder,SupportedLeft.GetLocation()),1.f);
    Out.Pose=Pose.GetPose();
    FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Out.Pose);
    // Recovery history is captured after the final palm-aware arm fit in
    // Evaluate_AnyThread, so cancellation starts at the displayed wrist.
    LastStaffCastPhase=StaffCastPhase;LastStaffCastProgress=StaffCastProgress;bHadStaffCast=true;
    if(bStaffNativeCast)bStaffNativeArmApplied=true;
    for(int32 I=0;I<2;++I)LastHands[I]=Pose.GetComponentSpaceTransform(Hands[I].GetCompactPoseIndex(Bones));
    bHasHandHistory=true;bHadSwordPair=false;
}
