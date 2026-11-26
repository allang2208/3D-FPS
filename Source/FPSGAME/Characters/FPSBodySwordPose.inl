// Included in FPSBodyAnimation after FControls. Full-body library poses are
// blended before hit reactions and finger fitting, so those layers still apply.
void FControls::BlendSword(FPoseContext& Out,FCSPose<FCompactPose>& Pose)
{
    SwordSupportThumbWeight=0.f;
    static const FName GripRollCurve(TEXT("SwordGripRoll"));
    static const FName GripSlideCurve(TEXT("SwordGripSlide"));
    const bool Warhammer=State.Family==TEXT("Tool")&&State.Weapon==TEXT("warhammer");
    const bool ContinuousHammer=Warhammer&&bHammerContinuousGrip;
    // Native two-handed swords have the same contact constraint as hammers.
    // The Highland supported takes retain their existing two-arm fit below;
    // independent single/dual blades must never be coupled to one handle.
    const bool PairedNative=ContinuousHammer||(State.Family==TEXT("Melee")&&bSwordNativeGrip&&!bHighlandSupportedGrip);
    if(!Warhammer)
    {
        HammerVisiblePose.Reset();HammerPreviousPose.Reset();HammerEntryVelocity.Reset();
        HammerHistoryDelta=0.f;HammerHipLast=FVector::ZeroVector;
    }
    if(!PairedNative)bHasPairedGripHistory=false;
    if(SwordWeight<=ZERO_ANIMWEIGHT_THRESH)
    {
        LastSwordPose.Reset();SwordEntryPose.Reset();LastSwordGripRoll=0.f;SwordEntryGripRoll=0.f;
        LastSwordGripSlide=0.f;SwordEntryGripSlide=0.f;
        // Retain the evaluated live carry for the next lift. The entry must
        // start at the last visible arms, including the sprint's low grip.
        if(Warhammer)
        {
            RememberHammerPose(Out,Pose);HammerHipLast=FVector::ZeroVector;
            FPoseContext Carry(Out);Carry.Pose=Pose.GetPose();
            FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Carry.Pose);
            LastSwordPose.SetNum(Carry.Pose.GetNumBones());
            for(int32 I=0;I<LastSwordPose.Num();++I)LastSwordPose[I]=Carry.Pose[FCompactPoseBoneIndex(I)];
        }
        else if(PairedNative)
        {
            const auto& Bones=Out.Pose.GetBoneContainer();
            if(Hands[0].IsValidToEvaluate(Bones)&&Hands[1].IsValidToEvaluate(Bones))
            {
                PairedGripLast=Pose.GetComponentSpaceTransform(Hands[1].GetCompactPoseIndex(Bones)).GetRelativeTransform(
                    Pose.GetComponentSpaceTransform(Hands[0].GetCompactPoseIndex(Bones)));
                bHasPairedGripHistory=true;
            }
        }
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
    // Mixed hatchet + kukri stage 3: the main take owns the right arm; the complementary take supplies the complete left
    // chain. Both are authored on the same 2.05 s clock, so the left arm simply replaces its side of the evaluated pose.
    if(bMixedPairAlt)
    {
        FPoseContext Alt(Out);SwordAlt.Evaluate(Alt);
        for(int32 I=0;I<LeftArmBones.Num();++I)if(LeftArmBones[I])Authored.Pose[FCompactPoseBoneIndex(I)]=Alt.Pose[FCompactPoseBoneIndex(I)];
    }
    FTransform CarrySupportGrip=FTransform::Identity,SourceSupportGrip=FTransform::Identity;
    if(PairedNative&&Hands[0].IsValidToEvaluate(Bones)&&Hands[1].IsValidToEvaluate(Bones))
    {
        const auto Right=Hands[0].GetCompactPoseIndex(Bones),Left=Hands[1].GetCompactPoseIndex(Bones);
        CarrySupportGrip=Pose.GetComponentSpaceTransform(Left).GetRelativeTransform(Pose.GetComponentSpaceTransform(Right));
        FCSPose<FCompactPose> RawSource;RawSource.InitPose(Authored.Pose);
        SourceSupportGrip=RawSource.GetComponentSpaceTransform(Left).GetRelativeTransform(RawSource.GetComponentSpaceTransform(Right));
    }
    SwordSupportThumbWeight=bSwordNativeGrip?FMath::Clamp(Authored.Curve.Get(TEXT("SwordSupportThumb")),0.f,1.f)*SwordWeight:0.f;
    if(bSwordChanged)
    {
        SwordEntryPose=ContinuousHammer&&!HammerVisiblePose.IsEmpty()?HammerVisiblePose:LastSwordPose;
        if(State.ActionVariant==TEXT("ZhufengWhirlwind")||bHighlandDash)
        {
            // A sprint release starts from the evaluated carry on this frame,
            // not a stale ordinary strike retained from the previous action.
            SwordEntryPose.SetNum(Out.Pose.GetNumBones());
            for(int32 I=0;I<SwordEntryPose.Num();++I)SwordEntryPose[I]=Out.Pose[FCompactPoseBoneIndex(I)];
        }
        SwordEntryGripRoll=LastSwordGripRoll;SwordEntryGripSlide=LastSwordGripSlide;SwordTransitionAge=0.f;
        PairedGripEntry=bHasPairedGripHistory?PairedGripLast:CarrySupportGrip;HammerHipEntry=HammerHipLast;
        HammerEntryVelocity.Init(FVector::ZeroVector,SwordEntryPose.Num());
        if(ContinuousHammer&&HammerPreviousPose.Num()==SwordEntryPose.Num()&&HammerHistoryDelta>SMALL_NUMBER)
            for(int32 I=0;I<HammerEntryVelocity.Num();++I)
            {
                FQuat Motion=(SwordEntryPose[I].GetRotation()*HammerPreviousPose[I].GetRotation().Inverse()).GetNormalized();
                if(Motion.W<0.f)Motion=Motion*-1.f;
                HammerEntryVelocity[I]=Motion.ToRotationVector()/HammerHistoryDelta;
            }
    }
    SwordTransitionAge+=Delta;
    const float Transition=Ease(SwordTransitionAge/SwordTransitionSeconds);
    if(ContinuousHammer)
    {
        const FVector Effort(Authored.Curve.Get(TEXT("HammerHipX")),Authored.Curve.Get(TEXT("HammerHipY")),Authored.Curve.Get(TEXT("HammerHipZ")));
        HammerHipLast=FMath::Lerp(HammerHipEntry,Effort,Transition);
    }
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
            FTransform Entry=SwordEntryPose[I];
            if(ContinuousHammer&&SwordUpperBones[I]&&HammerEntryVelocity.IsValidIndex(I))
            {
                const float U=FMath::Clamp(SwordTransitionAge/SwordTransitionSeconds,0.f,1.f);
                const FVector Continue=(HammerEntryVelocity[I]*(SwordTransitionAge*FMath::Square(1.f-U))).GetClampedToMaxSize(FMath::DegreesToRadians(12.f));
                Entry.SetRotation((FQuat::MakeFromRotationVector(Continue)*Entry.GetRotation()).GetNormalized());
            }
            FTransform Blended;Blended.Blend(Entry,Authored.Pose[B],Transition);
            Authored.Pose[B]=Blended;
        }
        LastSwordPose[I]=Authored.Pose[B];
    }
    FCSPose<FCompactPose> Full;Full.InitPose(Authored.Pose);
    if(UppercutStrideWeight>ZERO_ANIMWEIGHT_THRESH)
    {
        const auto Hip=Pelvis.GetCompactPoseIndex(Bones),Chest=ChestBase.GetCompactPoseIndex(Bones);
        FTransform StrikeChest=Full.GetComponentSpaceTransform(Chest);
        const FVector StrikeHip=Full.GetComponentSpaceTransform(Hip).GetLocation();
        FPoseContext Stride(Out);UppercutStride.Evaluate(Stride);
        for(int32 I=0;I<UppercutStrideBones.Num();++I)if(UppercutStrideBones[I])
        {
            const FCompactPoseBoneIndex B(I);
            FTransform Mixed;Mixed.Blend(Authored.Pose[B],Stride.Pose[B],UppercutStrideWeight);Authored.Pose[B]=Mixed;
        }
        Full.InitPose(Authored.Pose);
        // Retain the complete authored sword/arm frame while the pelvis and
        // legs push forward; the existing ground solver handles both feet below.
        StrikeChest.AddToTranslation(Full.GetComponentSpaceTransform(Hip).GetLocation()-StrikeHip);
        TArray<FBoneTransform,TInlineAllocator<1>> Change;Change.Emplace(Chest,StrikeChest);
        Full.LocalBlendCSBoneTransforms(Change,1.f);
    }
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
    if((State.Family==TEXT("Kukri")||bKukriAuthoredStep)&&Crouch>ZERO_ANIMWEIGHT_THRESH)
    {
        // Crouched attacks still own their step. Adapt the complete donor
        // before mixing instead of discarding every leg track while crouched.
        // Mixed pistol/knife uppercuts use this same native take; their family
        // remains Pistol and must not make the body stand up during the action.
        FTransform Targets[2];FLegReference CrouchLegs[2];
        for(int32 I=0;I<2;++I)if(Feet[I].IsValidToEvaluate(Bones))
        {
            const auto F=Feet[I].GetCompactPoseIndex(Bones),K=Bones.GetParentBoneIndex(F),H=Bones.GetParentBoneIndex(K);
            Targets[I]=Full.GetComponentSpaceTransform(F);
            CrouchLegs[I].Set(Full.GetComponentSpaceTransform(H).GetLocation(),Full.GetComponentSpaceTransform(K).GetLocation(),Targets[I].GetLocation());
        }
        const FVector Drop=FVector(0,-6.f,-40.f)*PoseScale*Crouch;
        auto Hip=Full.GetComponentSpaceTransform(HipIndex);Hip.AddToTranslation(Drop);
        TArray<FBoneTransform,TInlineAllocator<1>> Change;Change.Emplace(HipIndex,Hip);Full.LocalBlendCSBoneTransforms(Change,1.f);
        for(int32 I=0;I<2;++I)if(Feet[I].IsValidToEvaluate(Bones))
        {
            const FVector H=CrouchLegs[I].Hip+Drop;
            Targets[I].SetLocation(CrouchLegs[I].Reachable(H,Targets[I].GetLocation()));
            Solve(Full,Feet[I],Targets[I],CrouchLegs[I].Pole(H,Targets[I].GetLocation()),1.f);
        }
    }
    const FTransform BaseChest=Pose.GetComponentSpaceTransform(ChestIndex);
    const FQuat BaseMiddle=Pose.GetComponentSpaceTransform(Bones.GetParentBoneIndex(Spine.GetCompactPoseIndex(Bones))).GetRotation();
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
        RawFeet[I].bAuthoredAttackStep=bKukriAuthoredStep&&LowerAlpha>.05f;
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
    const FQuat NaturalLower=Out.Pose[ChestIndex].GetRotation();
    Pose.InitPose(Out.Pose);
    // Locomotion supplies the moving pelvis. Copying the donor's local spine
    // onto that unrelated pelvis adds its yaw/roll a second time. Anchor the
    // authored chest in component space at the mixed hip, preserving the cut's
    // actual shoulders/head orientation while the legs keep their gait.
    FTransform Chest=DonorChest;
    Chest.AddToTranslation(Pose.GetComponentSpaceTransform(HipIndex).GetLocation()-DonorHip);
    FTransform MixedChest;MixedChest.Blend(BaseChest,Chest,SwordWeight);
    const bool MixedSpine=(!ContinuousHammer && SwordLegWeight<.999f) || bSingleBladePose;
    if (MixedSpine) MixedChest.SetTranslation(Pose.GetComponentSpaceTransform(ChestIndex).GetTranslation());
    TArray<FBoneTransform,TInlineAllocator<1>> ChestChange;ChestChange.Emplace(ChestIndex,MixedChest);
    Pose.LocalBlendCSBoneTransforms(ChestChange,1.f);
    if (MixedSpine) BladeSpine.Distribute(Pose,NaturalLower);
    if(ContinuousHammer)BlendHammerWaist(Pose,BaseChest.GetRotation(),BaseMiddle);
    if(PairedNative)
    {
        if((Transition<1.f||SwordWeight<.999f)&&Hands[0].IsValidToEvaluate(Bones)&&Hands[1].IsValidToEvaluate(Bones))
        {
            // Interpolating both arm chains alone can separate the palm from
            // the shaft. Correct only the support contact during transitions;
            // the fully blended authored pose needs no second arm solve.
            FTransform AnimatedGrip,SupportGrip;AnimatedGrip.Blend(PairedGripEntry,SourceSupportGrip,Transition);
            SupportGrip.Blend(CarrySupportGrip,AnimatedGrip,SwordWeight);
            const auto W=Hands[1].GetCompactPoseIndex(Bones),E=Bones.GetParentBoneIndex(W),S=Bones.GetParentBoneIndex(E);
            const FVector Shoulder=Pose.GetComponentSpaceTransform(S).GetLocation();
            FLegReference Arm;Arm.Set(Shoulder,Pose.GetComponentSpaceTransform(E).GetLocation(),Pose.GetComponentSpaceTransform(W).GetLocation());
            auto Target=SupportGrip*Pose.GetComponentSpaceTransform(Hands[0].GetCompactPoseIndex(Bones));
            Target.SetLocation(Arm.Reachable(Shoulder,Target.GetLocation()));
            Solve(Pose,Hands[1],Target,Arm.Pole(Shoulder,Target.GetLocation()),1.f);
        }
    }
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
    // Native takes already own both arms, including their anatomical wrist fit.
    // Re-solving a partially blended hammer pose forces the old carry's wrist
    // frame back into it and bypasses the authored joint limits.
    else if(bLeftGrip&&!bSwordNativeGrip&&
        Hands[0].IsValidToEvaluate(Bones)&&Hands[1].IsValidToEvaluate(Bones))
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
        if(bHighlandSupportedGrip&&bLeftGrip&&(Transition<.999f||SwordWeight<.999f))
        {
            // The fitted sources already own complete anatomical arm chains.
            // Only entry/cancel/exit blending can separate the two grip points;
            // restore both contacts using this frame's elbow planes. Moving
            // the hilt as one unit also handles a deep heavy-landing entry;
            // independently clamping the support wrist would leave it behind.
            FTransform Targets[2]={Pose.GetComponentSpaceTransform(Hands[0].GetCompactPoseIndex(Bones)),FTransform::Identity};
            Targets[1]=LeftGrip*Targets[0];
            FLegReference Arms[2];
            for(int32 I=0;I<2;++I)
            {
                const auto W=Hands[I].GetCompactPoseIndex(Bones),E=Bones.GetParentBoneIndex(W),S=Bones.GetParentBoneIndex(E);
                Arms[I].Set(Pose.GetComponentSpaceTransform(S).GetLocation(),
                    Pose.GetComponentSpaceTransform(E).GetLocation(),Pose.GetComponentSpaceTransform(W).GetLocation());
            }
            FitHandPair(Pose,Targets);
            for(int32 I=0;I<2;++I)
                Solve(Pose,Hands[I],Targets[I],Arms[I].Pole(Arms[I].Hip,Targets[I].GetLocation()),1.f);
        }
        // Kwang's complete arm chains and equipment grip were fitted offline.
        // A second live two-hand solve would overwrite their elbow/forearm roll.
        for(int32 I=0;I<2;++I)LastHands[I]=Pose.GetComponentSpaceTransform(Hands[I].GetCompactPoseIndex(Bones));
        LastSwordTorso=Pose.GetComponentSpaceTransform(Spine.GetCompactPoseIndex(Bones));
        LastSwordTorso.SetScale3D(FVector::OneVector);bHadSwordPair=true;bHasHandHistory=true;
    }
    if(Warhammer)RememberHammerPose(Out,Pose);
    else if(PairedNative&&Hands[0].IsValidToEvaluate(Bones)&&Hands[1].IsValidToEvaluate(Bones))
    {
        PairedGripLast=Pose.GetComponentSpaceTransform(Hands[1].GetCompactPoseIndex(Bones)).GetRelativeTransform(
            Pose.GetComponentSpaceTransform(Hands[0].GetCompactPoseIndex(Bones)));
        bHasPairedGripHistory=true;
    }
}
