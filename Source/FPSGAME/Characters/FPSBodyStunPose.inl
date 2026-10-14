// Native Jason rotations from the CC0 Dizzy donor. Preserve locomotion and the
// weapon's local arm/hand contact; the held item follows the swaying torso.
void FControls::BlendStun(FPoseContext& Out,FCSPose<FCompactPose>& Pose)
{
    if(!bHasStunLibrary||StunBlend<=ZERO_ANIMWEIGHT_THRESH||State.Action==EFPSBodyAction::Dead)return;
    const float ContactSafety=FPSBodyPoses::Traversing(State.Motion)?.2f:1.f;
    const bool FreeArms=State.Family==TEXT("Unarmed")&&State.Action==EFPSBodyAction::None&&!ActionWristMask;
    const auto& Bones=Out.Pose.GetBoneContainer();
    Out.Pose=Pose.GetPose();
    FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Out.Pose);
    FPoseContext Authored(Out);StunPose.Evaluate(Authored);
    for(int32 I=0;I<StunCoreBones.Num();++I)
    {
        const float Region=StunCoreBones[I]?1.f:(FreeArms&&SwordUpperBones[I]?.65f:0.f);
        if(Region<=0.f)continue;
        const FCompactPoseBoneIndex B(I);
        FTransform Mixed;Mixed.Blend(Out.Pose[B],Authored.Pose[B],StunBlend*ContactSafety*Region);Out.Pose[B]=Mixed;
    }
    Pose.InitPose(Out.Pose);
}
