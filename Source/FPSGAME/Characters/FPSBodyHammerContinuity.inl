// Local to the world-body hammer layer. Source poses still own its strikes.
void FControls::RememberHammerPose(FPoseContext& Out,FCSPose<FCompactPose>& Pose)
{
    FPoseContext Visible(Out);Visible.Pose=Pose.GetPose();
    FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Visible.Pose);
    Swap(HammerPreviousPose,HammerVisiblePose);
    HammerVisiblePose.SetNum(Visible.Pose.GetNumBones());
    for(int32 I=0;I<HammerVisiblePose.Num();++I)HammerVisiblePose[I]=Visible.Pose[FCompactPoseBoneIndex(I)];
    HammerHistoryDelta=Delta;
    const auto& Bones=Out.Pose.GetBoneContainer();
    if(Hands[0].IsValidToEvaluate(Bones)&&Hands[1].IsValidToEvaluate(Bones))
    {
        HammerGripLast=Pose.GetComponentSpaceTransform(Hands[1].GetCompactPoseIndex(Bones)).GetRelativeTransform(
            Pose.GetComponentSpaceTransform(Hands[0].GetCompactPoseIndex(Bones)));
        bHasHammerGripHistory=true;
    }
}

void FControls::BlendHammerWaist(FCSPose<FCompactPose>& Pose,const FQuat& BaseLower,const FQuat& BaseMiddle)
{
    const float Weight=HammerMovingWeight*SwordWeight;
    if(!bHammerContinuousGrip||Weight<=ZERO_ANIMWEIGHT_THRESH)return;
    const auto& Bones=Pose.GetPose().GetBoneContainer();
    const auto Hip=Pelvis.GetCompactPoseIndex(Bones),Lower=ChestBase.GetCompactPoseIndex(Bones);
    const auto Upper=Spine.GetCompactPoseIndex(Bones),Middle=Bones.GetParentBoneIndex(Upper);
    const FQuat StrikeMiddle=Pose.GetComponentSpaceTransform(Middle).GetRotation();
    const FQuat StrikeUpper=Pose.GetComponentSpaceTransform(Upper).GetRotation();
    FTransform Ankles[2];FLegReference Legs[2];
    for(int32 I=0;I<2;++I)if(Feet[I].IsValidToEvaluate(Bones))
    {
        const auto F=Feet[I].GetCompactPoseIndex(Bones),K=Bones.GetParentBoneIndex(F),H=Bones.GetParentBoneIndex(K);
        Ankles[I]=Pose.GetComponentSpaceTransform(F);
        Legs[I].Set(Pose.GetComponentSpaceTransform(H).GetLocation(),Pose.GetComponentSpaceTransform(K).GetLocation(),Ankles[I].GetLocation());
    }
    const auto SetRotation=[&](FCompactPoseBoneIndex Bone,const FQuat& Rotation)
    {
        auto Transform=Pose.GetComponentSpaceTransform(Bone);Transform.SetRotation(Rotation.GetNormalized());
        TArray<FBoneTransform,TInlineAllocator<1>> Change;Change.Emplace(Bone,Transform);
        Pose.LocalBlendCSBoneTransforms(Change,1.f);
    };
    const FQuat Effort=FQuat::MakeFromRotationVector(HammerHipLast*Weight);
    SetRotation(Hip,Effort*Pose.GetComponentSpaceTransform(Hip).GetRotation());
    // Taper from the travelling waist to the full source chest rotation.
    // Change rotations only: every spine segment retains its actual length.
    SetRotation(Lower,FQuat::Slerp(Pose.GetComponentSpaceTransform(Lower).GetRotation(),Effort*BaseLower,.45f*Weight));
    SetRotation(Middle,FQuat::Slerp(StrikeMiddle,Effort*BaseMiddle,.20f*Weight));
    SetRotation(Upper,StrikeUpper);
    // Pelvis effort must not drag the gait's feet around with it. Keep both
    // current ankle targets and source knee planes, within native leg reach.
    for(int32 I=0;I<2;++I)if(Feet[I].IsValidToEvaluate(Bones))
    {
        const auto F=Feet[I].GetCompactPoseIndex(Bones),H=Bones.GetParentBoneIndex(Bones.GetParentBoneIndex(F));
        const FVector NewHip=Pose.GetComponentSpaceTransform(H).GetLocation();
        Ankles[I].SetLocation(Legs[I].Reachable(NewHip,Ankles[I].GetLocation()));
        Solve(Pose,Feet[I],Ankles[I],Legs[I].Pole(NewHip,Ankles[I].GetLocation()),1.f);
    }
}
