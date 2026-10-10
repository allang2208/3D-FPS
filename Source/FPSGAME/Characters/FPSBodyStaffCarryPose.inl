// The donor owns a complete native shoulder/elbow/forearm chain. Keep fingers
// out of this layer: the accepted equipment grasp is applied separately below.
void FControls::AnchorStaffArm(FPoseContext& Authored,FCSPose<FCompactPose>& Pose,int32 Side)
{
    const auto& Bones=Authored.Pose.GetBoneContainer();
    if(!Hands[Side].IsValidToEvaluate(Bones))return;
    const auto Wrist=Hands[Side].GetCompactPoseIndex(Bones);
    const auto Upper=Bones.GetParentBoneIndex(Bones.GetParentBoneIndex(Wrist));
    const auto Clavicle=Bones.GetParentBoneIndex(Upper),Chest=Bones.GetParentBoneIndex(Clavicle);
    FCSPose<FCompactPose> SourceCS;SourceCS.InitPose(Authored.Pose);
    const FQuat ChestDelta=(Pose.GetComponentSpaceTransform(Chest).GetRotation()*
        SourceCS.GetComponentSpaceTransform(Chest).GetRotation().Inverse()).GetNormalized();
    const FVector Forward=ChestDelta.RotateVector(FVector::RightVector);
    const FQuat Heading(FVector::UpVector,FMath::Atan2(-Forward.X,Forward.Y));
    const FQuat Support=Heading*SourceCS.GetComponentSpaceTransform(Upper).GetRotation();
    const FQuat Parent=(Pose.GetComponentSpaceTransform(Chest).GetRotation()*Authored.Pose[Clavicle].GetRotation()).GetNormalized();
    // Keep the source's complete arm orientation in the character frame. The
    // live clavicle and torso heading still carry the shoulder, but torso lean must
    // not swing the long shaft through the knees. Elbow, wrist, finger and
    // twist-helper locals are unchanged by this whole-arm adjustment.
    Authored.Pose[Upper].SetRotation((Parent.Inverse()*Support).GetNormalized());
}

void FControls::BlendStaffCarry(FPoseContext& Out,FCSPose<FCompactPose>& Pose)
{
    if(!bStaffCarryActive||(ActionWristMask&1)||
        (bStaffAttackLibrary&&!bStaffNativeStrike&&!bStaffQuickCarry&&SwordWeight>ZERO_ANIMWEIGHT_THRESH))return;
    Out.Pose=Pose.GetPose();
    FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Out.Pose);
    FPoseContext Authored(Out);StaffCarry.Evaluate(Authored);
    AnchorStaffArm(Authored,Pose);
    for(int32 I=0;I<StaffMotionBones.Num();++I)
        if(StaffMotionBones[I])Out.Pose[FCompactPoseBoneIndex(I)]=Authored.Pose[FCompactPoseBoneIndex(I)];
    Pose.InitPose(Out.Pose);
    bStaffNativeArmApplied=true;
    const auto& Bones=Out.Pose.GetBoneContainer();
    if(Hands[0].IsValidToEvaluate(Bones))LastHands[0]=Pose.GetComponentSpaceTransform(Hands[0].GetCompactPoseIndex(Bones));
}
