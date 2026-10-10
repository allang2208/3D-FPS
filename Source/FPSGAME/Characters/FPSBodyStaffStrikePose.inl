// Native strike starts/ends at the accepted carry and retains its wrist, fingers
// and helper-bone relationships. The executor still owns timing and damage.
void FControls::BlendStaffStrike(FPoseContext& Out,FCSPose<FCompactPose>& Pose)
{
    Out.Pose=Pose.GetPose();
    FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Out.Pose);
    FPoseContext Authored(Out);Sword.Evaluate(Authored);
    AnchorStaffArm(Authored,Pose);
    const auto& Bones=Out.Pose.GetBoneContainer();
    LastSwordPose.SetNum(Bones.GetCompactPoseNumBones());
    for(int32 I=0;I<LastSwordPose.Num();++I)
    {
        const FCompactPoseBoneIndex Bone(I);
        if(StaffMotionBones[I])
        {
            FTransform Mixed;Mixed.Blend(Out.Pose[Bone],Authored.Pose[Bone],SwordWeight);
            Out.Pose[Bone]=Mixed;
        }
        LastSwordPose[I]=Out.Pose[Bone];
    }
    Pose.InitPose(Out.Pose);
    LastSwordGripRoll=0.f;SwordEntryGripRoll=0.f;
    bStaffNativeArmApplied=true;bHasHandHistory=true;bHadSwordPair=false;
    if(Hands[0].IsValidToEvaluate(Bones))LastHands[0]=Pose.GetComponentSpaceTransform(Hands[0].GetCompactPoseIndex(Bones));
}
