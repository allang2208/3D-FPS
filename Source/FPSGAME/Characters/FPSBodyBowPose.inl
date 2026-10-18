// Sparrow owns the complete native upper body. The live gait keeps the pelvis
// and legs; the saved contact curves are consumed after the final body pose.
void FControls::BlendNativeBow(FPoseContext& Out,FCSPose<FCompactPose>& Pose)
{
    Out.Curve.Set(FPSBodyBowMotion::WeightCurve,NativeBowWeight);
    Out.Curve.Set(FPSBodyBowMotion::RightHoldCurve,0.f);
    if(NativeBowWeight<=ZERO_ANIMWEIGHT_THRESH)
    {bHadNativeBow=false;bHadNativeBowCast=false;LastNativeBowPose.Reset();NativeBowEntryPose.Reset();NativeBowReferencePose.Reset();return;}
    const auto& Bones=Out.Pose.GetBoneContainer();const int32 Count=Bones.GetCompactPoseNumBones();
    Out.Pose=Pose.GetPose();FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Out.Pose);
    FPoseContext Authored(Out);BowNative.Evaluate(Authored);
    const bool Changed=!bHadNativeBow||NativeBowPhase!=LastNativeBowPhase;
    if(Changed)
    {
        NativeBowEntryAge=0.f;NativeBowEntryPose.SetNum(Count);NativeBowReferencePose.SetNum(Count);
        for(int32 I=0;I<Count;++I)
        {
            const auto B=FCompactPoseBoneIndex(I);NativeBowReferencePose[I]=Authored.Pose[B];
            NativeBowEntryPose[I]=bHadNativeBow&&LastNativeBowPose.Num()==Count?LastNativeBowPose[I]:Authored.Pose[B];
        }
    }
    NativeBowEntryAge+=Delta;LastNativeBowPose.SetNum(Count);
    const bool Release=NativeBowPhase==TEXT("Bow.Sparrow.Release");
    const float Entry=Ease(NativeBowEntryAge/.10f);
    const float Remaining=1.f-Ease((NativeBowProgress-.24f)/.76f);
    for(int32 I=0;I<Count;++I)
    {
        const auto B=FCompactPoseBoneIndex(I);
        if(!SwordUpperBones[I])continue;
        FTransform Target=Authored.Pose[B];
        if(Release)
        {
            // A partial draw releases from the displayed pose, not the full
            // draw at the beginning of the donor's release take.
            const FTransform& Reference=NativeBowReferencePose[I];
            const FQuat Offset=NativeBowEntryPose[I].GetRotation()*Reference.GetRotation().Inverse();
            Target.SetRotation((FQuat::Slerp(FQuat::Identity,Offset,Remaining)*Target.GetRotation()).GetNormalized());
            Target.AddToTranslation((NativeBowEntryPose[I].GetLocation()-Reference.GetLocation())*Remaining);
        }
        else if(Entry<1.f){FTransform Mixed;Mixed.Blend(NativeBowEntryPose[I],Target,Entry);Target=Mixed;}
        Authored.Pose[B]=Target;LastNativeBowPose[I]=Target;
    }
    FCSPose<FCompactPose> Desired;Desired.InitPose(Authored.Pose);
    const auto Hip=Pelvis.GetCompactPoseIndex(Bones),Chest=ChestBase.GetCompactPoseIndex(Bones);
    FTransform AuthoredChest=Desired.GetComponentSpaceTransform(Chest);
    const FVector AuthoredHip=Desired.GetComponentSpaceTransform(Hip).GetLocation();
    for(int32 I=0;I<Count;++I)if(!SwordUpperBones[I])
    {const FCompactPoseBoneIndex B(I);Authored.Pose[B]=Out.Pose[B];}
    Desired.InitPose(Authored.Pose);
    // The donor's local spine compensates its own pelvis, not the walking
    // pelvis. Preserve the authored chest orientation at the live hip before
    // aiming both arms; otherwise gait yaw/roll shakes the whole bow hold.
    AuthoredChest.AddToTranslation(Desired.GetComponentSpaceTransform(Hip).GetLocation()-AuthoredHip);
    TArray<FBoneTransform,TInlineAllocator<1>> Anchor;Anchor.Emplace(Chest,AuthoredChest);
    Desired.LocalBlendCSBoneTransforms(Anchor,1.f);
    FTransform BowAimFrame=FTransform::Identity;
    const float Pitch=FMath::Clamp(State.AimPitch,-65.f,65.f),Yaw=FMath::Clamp(State.AimYaw,-60.f,60.f);
    if(FMath::Abs(Pitch)+FMath::Abs(Yaw)>.01f)
    {
        const FQuat AimRotation=FQuat(FVector::UpVector,FMath::DegreesToRadians(Yaw))
            *FQuat(FVector::ForwardVector,FMath::DegreesToRadians(Pitch));
        auto ChestPose=Desired.GetComponentSpaceTransform(Chest);
        const FVector Pivot=ChestPose.GetLocation();FTransform Targets[2];FVector Poles[2];
        BowAimFrame=FTransform(AimRotation,Pivot-AimRotation.RotateVector(Pivot));
        for(int32 Side=0;Side<2;++Side)
        {
            const auto Hand=Hands[Side].GetCompactPoseIndex(Bones),Elbow=Bones.GetParentBoneIndex(Hand);
            Targets[Side]=Desired.GetComponentSpaceTransform(Hand);
            Targets[Side].SetLocation(Pivot+AimRotation.RotateVector(Targets[Side].GetLocation()-Pivot));
            Targets[Side].SetRotation((AimRotation*Targets[Side].GetRotation()).GetNormalized());
            Poles[Side]=Pivot+AimRotation.RotateVector(Desired.GetComponentSpaceTransform(Elbow).GetLocation()-Pivot);
        }
        const FQuat Torso=FQuat::Slerp(FQuat::Identity,AimRotation,.35f);
        ChestPose.SetRotation((Torso*ChestPose.GetRotation()).GetNormalized());
        TArray<FBoneTransform,TInlineAllocator<1>> Change;Change.Emplace(Chest,ChestPose);
        Desired.LocalBlendCSBoneTransforms(Change,1.f);
        FitHandPair(Desired,Targets);
        for(int32 Side=0;Side<2;++Side)Solve(Desired,Hands[Side],Targets[Side],Poles[Side],1.f);
    }
    if(State.BowCastTransfer>0.f)
    {
        // Work in native mesh indices, independent of compact-pose LOD indices.
        NativeBowFullPose=NativeBowTransfer.Reference;
        for(int32 I=0;I<Count;++I)NativeBowFullPose[NativeBowMeshIndices[I]]=Desired.GetComponentSpaceTransform(FCompactPoseBoneIndex(I));
        const FQuat GripRotation(Authored.Curve.Get(FPSBodyBowMotion::GripCurves[3]),Authored.Curve.Get(FPSBodyBowMotion::GripCurves[4]),
            Authored.Curve.Get(FPSBodyBowMotion::GripCurves[5]),Authored.Curve.Get(FPSBodyBowMotion::GripCurves[6]));
        const FTransform GripLocal(GripRotation.GetNormalized(),FVector(Authored.Curve.Get(FPSBodyBowMotion::GripCurves[0]),
            Authored.Curve.Get(FPSBodyBowMotion::GripCurves[1]),Authored.Curve.Get(FPSBodyBowMotion::GripCurves[2])));
        const FTransform MovedBowGrip=NativeBowTransfer.Apply(NativeBowFullPose,GripLocal*NativeBowFullPose[NativeBowTransfer.Wrist[1]],State.BowCastTransfer,BowAimFrame);
        for(int32 I=0;I<Count;++I)
        {
            const int32 B=NativeBowMeshIndices[I],P=NativeBowTransfer.Parents[B];
            Authored.Pose[FCompactPoseBoneIndex(I)]=P<0?NativeBowFullPose[B]:NativeBowFullPose[B].GetRelativeTransform(NativeBowFullPose[P]);
        }
        Desired.InitPose(Authored.Pose);
        const auto InRight=MovedBowGrip.GetRelativeTransform(NativeBowFullPose[NativeBowTransfer.Wrist[0]]);
        const FVector P=InRight.GetLocation();const FQuat Q=InRight.GetRotation();
        const double Values[]={P.X,P.Y,P.Z,Q.X,Q.Y,Q.Z,Q.W};
        for(int32 I=0;I<7;++I)Out.Curve.Set(FPSBodyBowMotion::RightGripCurves[I],float(Values[I]));
        Out.Curve.Set(FPSBodyBowMotion::RightHoldCurve,State.BowCastTransfer>=.45f?1.f:0.f);
    }
    if(State.bBowTwoHandConsume&&State.BowStowWeight>0.f)
    {
        // Large food needs both hands. Lower the native carry before hiding
        // it, and raise the same grip after the food's own recovery finishes.
        for(int32 Side=0;Side<2;++Side)
        {
            const auto W=Hands[Side].GetCompactPoseIndex(Bones),E=Bones.GetParentBoneIndex(W),U=Bones.GetParentBoneIndex(E);
            auto Target=Desired.GetComponentSpaceTransform(W);
            FLegReference Arm;Arm.Set(Desired.GetComponentSpaceTransform(U).GetLocation(),Desired.GetComponentSpaceTransform(E).GetLocation(),Target.GetLocation());
            Target.AddToTranslation(FVector(0,-12,-34)*PoseScale*State.BowStowWeight);
            Solve(Desired,Hands[Side],Target,Arm.Pole(Arm.Hip,Target.GetLocation()),1.f);
        }
    }
    const bool Casting=State.Action==EFPSBodyAction::Cast&&State.BowCastTransfer>=1.f-UE_KINDA_SMALL_NUMBER;
    if(Casting)
    {
        const auto W=Hands[1].GetCompactPoseIndex(Bones),E=Bones.GetParentBoneIndex(W),U=Bones.GetParentBoneIndex(E);
        const FTransform Rest=Desired.GetComponentSpaceTransform(W);
        if(!bHadNativeBowCast||NativeBowCastPhase!=State.ActionVariant)
            NativeBowCastEntry=bHadNativeBowCast?NativeBowCastLast:Rest;
        FTransform Target;
        if(State.ActionVariant==TEXT("Recover"))Target.Blend(NativeBowCastEntry,Rest,Ease(State.ActionProgress));
        else
        {
            Target=FPSBodyPoses::CastHand(State,Crouch,NativeBowCastEntry,PoseScale);
            if(ActionWristMask&2)Target.SetRotation(FQuat::Slerp(NativeBowCastEntry.GetRotation(),ActionHands[1].GetRotation(),
                State.ActionVariant==TEXT("Release")?1.f:Ease(State.ActionProgress)).GetNormalized());
        }
        FLegReference Arm;Arm.Set(Desired.GetComponentSpaceTransform(U).GetLocation(),Desired.GetComponentSpaceTransform(E).GetLocation(),Rest.GetLocation());
        Solve(Desired,Hands[1],Target,Arm.Pole(Arm.Hip,Target.GetLocation()),1.f);
        NativeBowCastLast=Desired.GetComponentSpaceTransform(W);NativeBowCastPhase=State.ActionVariant;
    }
    bHadNativeBowCast=Casting;
    Authored.Pose=Desired.GetPose();FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Desired,Authored.Pose);
    for(int32 I=0;I<Count;++I)if(SwordUpperBones[I])
    {const auto B=FCompactPoseBoneIndex(I);FTransform Mixed;Mixed.Blend(Out.Pose[B],Authored.Pose[B],NativeBowWeight);Out.Pose[B]=Mixed;}
    for(FName Curve:FPSBodyBowMotion::GripCurves)Out.Curve.Set(Curve,Authored.Curve.Get(Curve));
    for(FName Curve:FPSBodyBowMotion::NockCurves)Out.Curve.Set(Curve,Authored.Curve.Get(Curve));
    Pose.InitPose(Out.Pose);LastNativeBowPhase=NativeBowPhase;bHadNativeBow=true;
}
