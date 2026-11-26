// Original full-body dual-gun performance owns the complete carried arm.
// Retargeted local rotations include the source twist stations. Do not replace
// the wrist, infer a new elbow plane, or reset helpers after this layer.
bool FControls::DualSourceOwnsArm(int32 Side) const
{
    const auto& Hand=Side==0?State.RightHand:State.LeftHand;
    return bDualPistolReference&&PistolArmActive(Side)&&
        (!FPSBodyPistolMotion::UsesRelativeAction(State,Side)||Hand.bReloading);
}

void FControls::ApplyDualSourceShot(FPoseContext& Out)
{
    if(!bDualPistolReference)return;
    for(int32 Side=0;Side<2;++Side)
    {
        if(!DualSourceOwnsArm(Side)||FPSBodyPistolMotion::UsesRelativeAction(State,Side)||
            (State.ConsumeHands&(1<<Side))||DualShotWeight[Side]<=ZERO_ANIMWEIGHT_THRESH)continue;
        FPoseContext Shot(Out),Base(Out);
        DualShot[Side].Evaluate(Shot);DualShotBase[Side].Evaluate(Base);
        for(const auto Bone:DualSourceBones[Side])
        {
            // The owning gun adds its actual source recoil to today's gait.
            // Torso/other arm and the per-gun mechanical clock stay independent.
            const FQuat DeltaQ=(Shot.Pose[Bone].GetRotation()*Base.Pose[Bone].GetRotation().Inverse()).GetNormalized();
            Out.Pose[Bone].SetRotation((FQuat::Slerp(FQuat::Identity,DeltaQ,DualShotWeight[Side])*
                Out.Pose[Bone].GetRotation()).GetNormalized());
        }
    }
}

void FControls::AimDualSourceArms(FCSPose<FCompactPose>& Pose)
{
    if(!bDualPistolReference)return;
    const auto& Bones=Pose.GetPose().GetBoneContainer();
    const float Weight=1.f-Sprint;
    const FQuat SourceAim=FQuat(FVector::UpVector,FMath::DegreesToRadians(FMath::Clamp(State.AimYaw,-35.f,35.f)*Weight))*
        FQuat(FVector::ForwardVector,FMath::DegreesToRadians(FMath::Clamp(State.AimPitch,-50.f,55.f)*Weight));
    for(int32 Side=0;Side<2;++Side)
    {
        if(!DualSourceOwnsArm(Side)||(State.ConsumeHands&(1<<Side))||!Hands[Side].IsValidToEvaluate(Bones))continue;
        const auto Wrist=Hands[Side].GetCompactPoseIndex(Bones);
        const auto Shoulder=Bones.GetParentBoneIndex(Bones.GetParentBoneIndex(Wrist));
        auto Arm=Pose.GetComponentSpaceTransform(Shoulder);
        FQuat Transport=FQuat::Identity;
        const auto& Hand=Side==0?State.RightHand:State.LeftHand;
        if((ActionWristMask&(1<<Side))&&Hand.bReloading&&!Hand.bRevolver)
        {
            // FPS reload throws are framed around a camera. Transport the
            // complete library arm through a smaller version of that gesture;
            // never bend the wrist first and chase the resulting gun bounds.
            const auto Palm=Pose.GetComponentSpaceTransform(Wrist);
            const auto& Relative=ActionHands[Side];
            const FVector Reach=Palm.GetLocation()-Arm.GetLocation();
            const FVector Motion=Palm.GetRotation().RotateVector(Relative.GetLocation()*PoseScale*.35f);
            const FQuat Swing=FQuat::FindBetweenNormals(Reach.GetSafeNormal(),(Reach+Motion).GetSafeNormal());
            FQuat RelativeRotation=Relative.GetRotation();
            if(RelativeRotation.W<0.)RelativeRotation=RelativeRotation*-1.;
            const double Angle=RelativeRotation.GetAngle();
            const double Strength=Angle>UE_SMALL_NUMBER?FMath::Min(.20,FMath::DegreesToRadians(15.)/Angle):.20;
            const FQuat Tilt=FQuat::Slerp(FQuat::Identity,RelativeRotation,Strength).GetNormalized();
            Transport=(Swing*Palm.GetRotation()*Tilt*Palm.GetRotation().Inverse()).GetNormalized();
        }
        Arm.SetRotation((SourceAim*Transport*Arm.GetRotation()).GetNormalized());
        TArray<FBoneTransform,TInlineAllocator<1>> Change;Change.Emplace(Shoulder,Arm);
        Pose.LocalBlendCSBoneTransforms(Change,1.f);
    }
}

void FControls::BlendDualSourceTransition(FPoseContext& Out)
{
    if(!bDualPistolReference||FPSBodyPoses::Traversing(State.Motion)||State.Action==EFPSBodyAction::Dead)
    {
        for(int32 Side=0;Side<2;++Side){DualSourceLast[Side].Reset();DualSourceEntry[Side].Reset();}
        return;
    }
    for(int32 Side=0;Side<2;++Side)
    {
        const FName Channel=FPSBodyPistolMotion::HandChannel(State,Side);
        const FString& Instance=Side==0?State.WeaponInstance:State.OffhandInstance;
        const int32 Count=DualSourceBones[Side].Num();
        const bool History=DualSourceInstance[Side]==Instance&&DualSourceLast[Side].Num()==Count;
        if(!History)
        {DualSourceAge[Side]=1.f;DualSourceEntry[Side].Reset();}
        else if(Channel!=DualSourceChannel[Side])
        {
            DualSourceEntry[Side]=DualSourceLast[Side];
            // Cast/food/traversal already own their entrance blend. On returning
            // to a pistol, blend the entire arm instead of only chasing a wrist.
            DualSourceAge[Side]=FPSBodyPistolMotion::IsPistolChannel(Channel)?0.f:1.f;
        }
        DualSourceInstance[Side]=Instance;DualSourceChannel[Side]=Channel;
        DualSourceAge[Side]+=Delta;
        const float Weight=Ease(DualSourceAge[Side]/.12f);
        DualSourceLast[Side].SetNum(Count,EAllowShrinking::No);
        for(int32 I=0;I<Count;++I)
        {
            const auto Bone=DualSourceBones[Side][I];
            if(History&&Weight<1.f&&DualSourceEntry[Side].Num()==Count)
            {
                FTransform Blended;Blended.Blend(DualSourceEntry[Side][I],Out.Pose[Bone],Weight);
                Out.Pose[Bone]=Blended;
            }
            DualSourceLast[Side][I]=Out.Pose[Bone];
        }
    }
    // External-action recovery must capture the final displayed arm, including
    // this whole-chain handover, rather than the pre-blend procedural target.
    FCSPose<FCompactPose> Final;Final.InitPose(Out.Pose);
    const auto& Bones=Out.Pose.GetBoneContainer();
    LastPistolTorso=Final.GetComponentSpaceTransform(Spine.GetCompactPoseIndex(Bones));
    LastPistolTorso.SetScale3D(FVector::OneVector);
    for(int32 Side=0;Side<2;++Side)if(Hands[Side].IsValidToEvaluate(Bones))
        LastHands[Side]=Final.GetComponentSpaceTransform(Hands[Side].GetCompactPoseIndex(Bones));
}
