// Included in FPSBodyAnimation after FControls. Full-body library poses are
// blended before hit reactions and finger fitting, so those layers still apply.
void FControls::BlendSword(FPoseContext& Out,FCSPose<FCompactPose>& Pose)
{
    SwordSupportThumbWeight=0.f;
    static const FName GripRollCurve(TEXT("SwordGripRoll"));
    static const FName GripSlideCurve(TEXT("SwordGripSlide"));
    if(SwordWeight<=ZERO_ANIMWEIGHT_THRESH)
    {
        LastSwordPose.Reset();SwordEntryPose.Reset();LastSwordGripRoll=0.f;SwordEntryGripRoll=0.f;
        LastSwordGripSlide=0.f;SwordEntryGripSlide=0.f;
        Out.Curve.Set(GripRollCurve,0.f);Out.Curve.Set(GripSlideCurve,0.f);return;
    }
    if(bStaffAttackLibrary&&bStaffNativeStrike&&State.Family==TEXT("Staff"))
    {Out.Curve.Set(GripRollCurve,0.f);Out.Curve.Set(GripSlideCurve,0.f);BlendStaffStrike(Out,Pose);return;}
    const auto& Bones=Out.Pose.GetBoneContainer();
    FTransform PreservedHands[2];FLegReference PreservedArms[2];
    for(int32 I=0;I<2;++I)if((LibraryPreserveHands&(1<<I))&&Hands[I].IsValidToEvaluate(Bones))
    {
        const auto W=Hands[I].GetCompactPoseIndex(Bones),E=Bones.GetParentBoneIndex(W),S=Bones.GetParentBoneIndex(E);
        PreservedHands[I]=Pose.GetComponentSpaceTransform(W);
        PreservedArms[I].Set(Pose.GetComponentSpaceTransform(S).GetLocation(),Pose.GetComponentSpaceTransform(E).GetLocation(),PreservedHands[I].GetLocation());
    }
    Out.Pose=Pose.GetPose();
    FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Out.Pose);
    FPoseContext Authored(Out);Sword.Evaluate(Authored);
    SwordSupportThumbWeight=bSwordNativeGrip?FMath::Clamp(Authored.Curve.Get(TEXT("SwordSupportThumb")),0.f,1.f)*SwordWeight:0.f;
    if(bSwordChanged)
    {SwordEntryPose=LastSwordPose;SwordEntryGripRoll=LastSwordGripRoll;SwordEntryGripSlide=LastSwordGripSlide;SwordTransitionAge=0.f;}
    SwordTransitionAge+=Delta;
    const float Transition=Ease(SwordTransitionAge/.08f);
    const float RollSin=Authored.Curve.Get(TEXT("SwordGripRollSin"));
    const float RollCos=Authored.Curve.Get(TEXT("SwordGripRollCos"));
    // A full physical turn closes at the same grip. Interpolating an unwrapped
    // 365-degree scalar then multiplying by the exit weight spins the blade
    // backwards. Periodic curves interpolate across +/-180 without that branch
    // jump, and return the equivalent 5-degree grip for the carry handoff.
    const float AuthoredRoll=RollSin*RollSin+RollCos*RollCos>.5f
        ?FMath::RadiansToDegrees(FMath::Atan2(RollSin,RollCos)):Authored.Curve.Get(GripRollCurve);
    LastSwordGripRoll=Transition<1.f&&!SwordEntryPose.IsEmpty()
        ?SwordEntryGripRoll+FMath::FindDeltaAngleDegrees(SwordEntryGripRoll,AuthoredRoll)*Transition:AuthoredRoll;
    const float AuthoredSlide=Authored.Curve.Get(GripSlideCurve);
    LastSwordGripSlide=Transition<1.f&&!SwordEntryPose.IsEmpty()
        ?FMath::Lerp(SwordEntryGripSlide,AuthoredSlide,Transition):AuthoredSlide;
    // Carry the same grip phase as the blended arm pose to the finalized-bones
    // callback. Applying it before mesh evaluation would lag the sword a frame.
    Out.Curve.Set(GripRollCurve,LastSwordGripRoll*SwordWeight);
    Out.Curve.Set(GripSlideCurve,LastSwordGripSlide*SwordWeight);
    LastSwordPose.SetNum(Bones.GetCompactPoseNumBones());
    for(int32 I=0;I<LastSwordPose.Num();++I)
    {
        const FCompactPoseBoneIndex B(I);
        if(Transition<1.f&&SwordEntryPose.Num()==LastSwordPose.Num())
        {
            FTransform Blended;Blended.Blend(SwordEntryPose[I],Authored.Pose[B],Transition);
            Authored.Pose[B]=Blended;
        }
        LastSwordPose[I]=Authored.Pose[B];
    }
    FCSPose<FCompactPose> Full;Full.InitPose(Authored.Pose);
    if(bStaffAttackLibrary&&Hands[0].IsValidToEvaluate(Bones))
    {
        const auto W=Hands[0].GetCompactPoseIndex(Bones);
        FTransform Hand=Full.GetComponentSpaceTransform(W);
        // The authored swing uses the bare-shaft grip frame. Preserve the
        // fitted palm frame for leather/silver/steel linings as well.
        Hand.SetRotation((Hand.GetRotation()*FPSBodyHandAttackData::StaffReferenceRotation.Inverse()*StaffHandRotation).GetNormalized());
        TArray<FBoneTransform,TInlineAllocator<1>> Change;Change.Emplace(W,Hand);Full.LocalBlendCSBoneTransforms(Change,1.f);
    }
    const auto HipIndex=Pelvis.GetCompactPoseIndex(Bones);
    const auto ChestIndex=ChestBase.GetCompactPoseIndex(Bones);
    const FTransform BaseChest=Pose.GetComponentSpaceTransform(ChestIndex);
    // Whirlwind assets are authored in actor space. Their donor root rotation
    // is removed offline, preserving the pelvis/chest windup and follow-through.
    // Trace seeds remain pre-correction. Grounding the already corrected output
    // again would accumulate pelvis height and ankle offsets on stairs.
    FTransform FootTargets[2];FLegReference Legs[2];
    const float LowerAlpha=SwordWeight*SwordLegWeight;
    for(int32 I=0;I<2;++I)if(Feet[I].IsValidToEvaluate(Bones))
    {
        const auto F=Feet[I].GetCompactPoseIndex(Bones),K=Bones.GetParentBoneIndex(F),H=Bones.GetParentBoneIndex(K);
        FootTargets[I]=Full.GetComponentSpaceTransform(F);
        Legs[I].Set(Full.GetComponentSpaceTransform(H).GetLocation(),Full.GetComponentSpaceTransform(K).GetLocation(),FootTargets[I].GetLocation());
        FTransform Mixed;Mixed.Blend(RawFeet[I].Ankle,FootTargets[I],LowerAlpha);RawFeet[I].Ankle=Mixed;
        RawFeet[I].Hip=FMath::Lerp(RawFeet[I].Hip,Legs[I].Hip,LowerAlpha);
        RawFeet[I].ReachLimit=FMath::Lerp(RawFeet[I].ReachLimit,Legs[I].Reach,LowerAlpha);
        if(Toes[I].IsValidToEvaluate(Bones))RawFeet[I].Toe=FMath::Lerp(RawFeet[I].Toe,Full.GetComponentSpaceTransform(Toes[I].GetCompactPoseIndex(Bones)).GetLocation(),LowerAlpha);
    }
    if(!bFalling&&State.Motion==EFPSBodyMotion::Ground)
    {
        auto Hip=Full.GetComponentSpaceTransform(HipIndex);Hip.AddToTranslation(FVector(0,0,Ground.PelvisZ));
        TArray<FBoneTransform,TInlineAllocator<1>> Change;Change.Emplace(HipIndex,Hip);Full.LocalBlendCSBoneTransforms(Change,1.f);
        for(int32 I=0;I<2;++I)if(Feet[I].IsValidToEvaluate(Bones))
        {
            const FVector NewHip=Legs[I].Hip+FVector(0,0,Ground.PelvisZ);
            auto Target=FootTargets[I];Target.AddToTranslation(Ground.FootOffset[I]*Ground.Weight[I]);
            Target.SetLocation(Legs[I].Reachable(NewHip,Target.GetLocation()));
            Target.SetRotation((FQuat::Slerp(FQuat::Identity,Ground.FootTilt[I],Ground.Weight[I])*Target.GetRotation()).GetNormalized());
            Solve(Full,Feet[I],Target,Legs[I].Pole(NewHip,Target.GetLocation()),1.f);
        }
    }
    Authored.Pose=Full.GetPose();
    FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Full,Authored.Pose);
    const FTransform DonorChest=Full.GetComponentSpaceTransform(ChestIndex);
    const FVector DonorHip=Full.GetComponentSpaceTransform(HipIndex).GetLocation();
    for(int32 I=0;I<Bones.GetCompactPoseNumBones();++I)
    {
        const FCompactPoseBoneIndex B(I);
        const float Alpha=(LibraryArmBones[I]&LibraryPreserveHands)?0.f:SwordUpperBones[I]?SwordWeight:LowerAlpha;
        FTransform Blended;Blended.Blend(Out.Pose[B],Authored.Pose[B],Alpha);Out.Pose[B]=Blended;
    }
    Pose.InitPose(Out.Pose);
    // Locomotion supplies the moving pelvis. Copying the donor's local spine
    // onto that unrelated pelvis adds its yaw/roll a second time. Anchor the
    // authored chest in component space at the mixed hip, preserving the cut's
    // actual shoulders/head orientation while the legs keep their gait.
    FTransform Chest=DonorChest;
    Chest.AddToTranslation(Pose.GetComponentSpaceTransform(HipIndex).GetLocation()-DonorHip);
    FTransform MixedChest;MixedChest.Blend(BaseChest,Chest,SwordWeight);
    TArray<FBoneTransform,TInlineAllocator<1>> ChestChange;ChestChange.Emplace(ChestIndex,MixedChest);
    Pose.LocalBlendCSBoneTransforms(ChestChange,1.f);
    for(int32 I=0;I<2;++I)if((LibraryPreserveHands&(1<<I))&&Hands[I].IsValidToEvaluate(Bones))
    {
        const auto W=Hands[I].GetCompactPoseIndex(Bones),E=Bones.GetParentBoneIndex(W),S=Bones.GetParentBoneIndex(E);
        const FVector Shoulder=Pose.GetComponentSpaceTransform(S).GetLocation();
        auto Target=PreservedHands[I];Target.SetLocation(PreservedArms[I].Reachable(Shoulder,Target.GetLocation()));
        Solve(Pose,Hands[I],Target,PreservedArms[I].Pole(Shoulder,Target.GetLocation()),1.f);
    }
    if(bHandAttackLibrary)
    {
        for(int32 I=0;I<2;++I)if(Hands[I].IsValidToEvaluate(Bones))LastHands[I]=Pose.GetComponentSpaceTransform(Hands[I].GetCompactPoseIndex(Bones));
        bHasHandHistory=true;bHadSwordPair=false;
    }
    else if(bLeftGrip&&!bSwordNativeGrip&&Hands[0].IsValidToEvaluate(Bones)&&Hands[1].IsValidToEvaluate(Bones))
    {
        FTransform Targets[2]={Pose.GetComponentSpaceTransform(Hands[0].GetCompactPoseIndex(Bones)),FTransform::Identity};
        Targets[1]=LeftGrip*Targets[0];
        FLegReference Arms[2];
        for(int32 I=0;I<2;++I)
        {
            const auto W=Hands[I].GetCompactPoseIndex(Bones),E=Bones.GetParentBoneIndex(W),S=Bones.GetParentBoneIndex(E);
            Arms[I].Set(Pose.GetComponentSpaceTransform(S).GetLocation(),Pose.GetComponentSpaceTransform(E).GetLocation(),Pose.GetComponentSpaceTransform(W).GetLocation());
        }
        FitHandPair(Pose,Targets);
        for(int32 I=0;I<2;++I)
        {
            if(I==1)Targets[1]=LeftGrip*Pose.GetComponentSpaceTransform(Hands[0].GetCompactPoseIndex(Bones));
            // Transfer the donor's actual elbow plane; never substitute the
            // fixed idle elbow pole during a cross-body/overhead attack.
            Solve(Pose,Hands[I],Targets[I],Arms[I].Pole(Arms[I].Hip,Targets[I].GetLocation()),1.f);
            LastHands[I]=Pose.GetComponentSpaceTransform(Hands[I].GetCompactPoseIndex(Bones));
        }
        LastSwordTorso=Pose.GetComponentSpaceTransform(Spine.GetCompactPoseIndex(Bones));
        LastSwordTorso.SetScale3D(FVector::OneVector);bHadSwordPair=true;bHasHandHistory=true;
    }
    else if(bSwordNativeGrip&&Hands[0].IsValidToEvaluate(Bones)&&Hands[1].IsValidToEvaluate(Bones))
    {
        // Kwang's complete arm chains and equipment grip were fitted offline.
        // A second live two-hand solve would overwrite their elbow/forearm roll.
        for(int32 I=0;I<2;++I)LastHands[I]=Pose.GetComponentSpaceTransform(Hands[I].GetCompactPoseIndex(Bones));
        LastSwordTorso=Pose.GetComponentSpaceTransform(Spine.GetCompactPoseIndex(Bones));
        LastSwordTorso.SetScale3D(FVector::OneVector);bHadSwordPair=true;bHasHandHistory=true;
    }
}
