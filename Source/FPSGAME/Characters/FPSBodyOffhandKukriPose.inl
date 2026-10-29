// Body-native shoulders and elbows; the accepted FPS pair supplies palm
// orientation/contact only. The main-hand pistol/book locomotion stays below.
void FControls::BlendOffhandKukriCarry(FPoseContext& Out,FCSPose<FCompactPose>& Pose)
{
    const bool Handoff=State.OffhandReloadPhase==uint8(EOffhandReloadPhase::Lower)||
        State.OffhandReloadPhase==uint8(EOffhandReloadPhase::Raise);
    const bool Busy=FPSBodyPoses::Traversing(State.Motion)||ConsumeWeight>ZERO_ANIMWEIGHT_THRESH||
        State.Action==EFPSBodyAction::Dead||State.Action==EFPSBodyAction::Consume||
        (State.Action!=EFPSBodyAction::None&&!Handoff&&!bKukriQuickActive)||FPSBodyPistolMotion::OffhandItemHidden(State);
    const auto& Bones=Out.Pose.GetBoneContainer();
    if(!bKukriCarryActive||Busy||!Hands[0].IsValidToEvaluate(Bones)||!Hands[1].IsValidToEvaluate(Bones)||!Spine.IsValidToEvaluate(Bones))
    {bHadKukriCarry=false;bHadKukriQuick=false;KukriCarryAge=0.f;return;}
    const FString Pair=State.WeaponInstance+TEXT("|")+State.OffhandInstance;
    if(KukriCarryInstance!=Pair){KukriCarryInstance=Pair;bHadKukriCarry=false;bHadKukriQuick=false;KukriCarryAge=0.f;}
    Out.Pose=Pose.GetPose();FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Out.Pose);
    const int32 Count=Bones.GetCompactPoseNumBones();
    const auto ArmBone=[&](int32 I){return StaffMotionBones[I]||BookMotionBones[I];};
    // A quick action owns the complete native arm from its opening frames.
    // Use the real prior pose for ADS entry; the long equip blend must not
    // wash out the contact. Cancellation into idle gets a short return blend.
    if(!bHadKukriCarry||bHadKukriQuick!=bKukriQuickActive)
    {
        KukriSupportFit.Reset();
        KukriCarryAge=0.f;
        KukriCarryBlendSeconds=bKukriQuickActive?.065f:bHadKukriQuick?.10f:.24f;
        KukriCarryEntryPose.SetNum(Count);
        for(int32 I=0;I<Count;++I)if(ArmBone(I))KukriCarryEntryPose[I]=
            bHadKukriCarry&&KukriCarryLastPose.Num()==Count?KukriCarryLastPose[I]:Out.Pose[FCompactPoseBoneIndex(I)];
    }
    FPoseContext Hip(Out),Aimed(Out);KukriCarryHip.Evaluate(Hip);KukriCarryAim.Evaluate(Aimed);
    FCSPose<FCompactPose> AimSource;AimSource.InitPose(Aimed.Pose);
    const auto Right=Hands[0].GetCompactPoseIndex(Bones);
    const FQuat SourcePistol=AimSource.GetComponentSpaceTransform(Right).GetRotation();
    const FTransform IncomingRight=Pose.GetComponentSpaceTransform(Right);
    const auto Anchor=[&](FPoseContext& Authored,int32 Side)
    {
        const auto W=Hands[Side].GetCompactPoseIndex(Bones),U=Bones.GetParentBoneIndex(Bones.GetParentBoneIndex(W));
        const auto Clavicle=Bones.GetParentBoneIndex(U),Parent=Bones.GetParentBoneIndex(Clavicle);
        FCSPose<FCompactPose> Native;Native.InitPose(Authored.Pose);
        const FQuat ParentRotation=(Pose.GetComponentSpaceTransform(Parent).GetRotation()*Authored.Pose[Clavicle].GetRotation()).GetNormalized();
        // Carry the native complete arm at the live shoulder, in character
        // axes. Crouch/locomotion chest yaw is not another gameplay aim yaw.
        Authored.Pose[U].SetRotation((ParentRotation.Inverse()*Native.GetComponentSpaceTransform(U).GetRotation()).GetNormalized());
    };
    for(int32 Side=0;Side<2;++Side){Anchor(Hip,Side);Anchor(Aimed,Side);}
    const float AimWeight=bKukriQuickActive?0.f:Ease(Aim);
    for(int32 I=0;I<Count;++I)if(ArmBone(I))
    {
        const FCompactPoseBoneIndex Bone(I);FTransform Carry;
        Carry.Blend(Hip.Pose[Bone],Aimed.Pose[Bone],AimWeight);Out.Pose[Bone]=Carry;
    }
    Pose.InitPose(Out.Pose);
    const auto Chest=Pose.GetComponentSpaceTransform(Spine.GetCompactPoseIndex(Bones));
    const FVector Facing=(Chest.GetRotation()*BookChestBind.Inverse()).RotateVector(FVector::RightVector);
    const FQuat Heading(FVector::UpVector,FMath::Atan2(-Facing.X,Facing.Y));
    const float Pitch=FMath::DegreesToRadians(FMath::Clamp(State.AimPitch,-45.f,50.f)*(1.f-Sprint));
    const float Yaw=FMath::DegreesToRadians(FMath::Clamp(State.AimYaw,-30.f,30.f)*(1.f-Sprint));
    const float Age=FMath::Max(0.f,Clock-State.LastShotAt);
    const float Kick=(1.f-FMath::SmoothStep(.025f,.16f,Age))*FMath::SmoothStep(0.f,.012f,Age);
    const FQuat AimFrame=FQuat(FVector::UpVector,Yaw)*
        FQuat(FVector::ForwardVector,Pitch-.28f*Sprint+.07f*Kick);
    // Rotate upper arm, elbow, wrist and helper chain together around each
    // shoulder. Rotating only the wrist target left the elbow in the hip plane.
    TArray<FBoneTransform,TInlineAllocator<2>> LookArms;
    for(int32 Side=0;Side<2;++Side)
    {
        const auto W=Hands[Side].GetCompactPoseIndex(Bones),U=Bones.GetParentBoneIndex(Bones.GetParentBoneIndex(W));
        auto Upper=Pose.GetComponentSpaceTransform(U);Upper.SetRotation((AimFrame*Upper.GetRotation()).GetNormalized());
        LookArms.Emplace(U,Upper);
    }
    LookArms.Sort([](const FBoneTransform& A,const FBoneTransform& B){return A.BoneIndex<B.BoneIndex;});
    Pose.LocalBlendCSBoneTransforms(LookArms,1.f);
    FTransform Targets[2];FVector Shoulders[2];FLegReference Arms[2];
    for(int32 Side=0;Side<2;++Side)
    {
        const auto W=Hands[Side].GetCompactPoseIndex(Bones),E=Bones.GetParentBoneIndex(W),U=Bones.GetParentBoneIndex(E);
        Targets[Side]=Pose.GetComponentSpaceTransform(W);Shoulders[Side]=Pose.GetComponentSpaceTransform(U).GetLocation();
        Arms[Side].Set(Shoulders[Side],Pose.GetComponentSpaceTransform(E).GetLocation(),Targets[Side].GetLocation());
    }
    // The authored aim is a straight pistol. Register the actual equipped
    // pistol's native grip so M1911, G18 and revolvers retain their own grasp.
    Targets[0].SetRotation((Targets[0].GetRotation()*SourcePistol.Inverse()*IndependentPistolRotation[0]).GetNormalized());
    const FVector Travel=Heading.RotateVector(FVector(0,-4.f*Sprint-2.f*Kick,-10.f*Sprint+Kick)*PoseScale);
    for(int32 Side=0;Side<2;++Side)
        Targets[Side].AddToTranslation(Travel);
    if(Handoff)
    {
        const float Lower=FPSBodyPistolMotion::OffhandBodyLowerWeight(State);
        Targets[1].AddToTranslation(Heading.RotateVector(FVector(0,-7,-32)*PoseScale)*Lower);
        Targets[1].SetRotation((FQuat(Heading.RotateVector(FVector::ForwardVector),-.45f*Lower)*Targets[1].GetRotation()).GetNormalized());
        FTransform Gun;Gun.Blend(Targets[0],IncomingRight,Lower);Targets[0]=Gun;
    }
    const FVector Forward=Heading.RotateVector(FVector::RightVector);
    const bool NativeUppercut=bKukriAuthoredStep&&bKukriQuickActive;
    // The rising cut later folds back down under negative aim pitch. Reserve
    // a forward lane for its whole forearm, not just the knife wrist.
    const FVector Plane=Chest.GetLocation()+Forward*(20.f*PoseScale.Y);
    const auto ContactPlane=[&](int32 Side){return Plane+Forward*((NativeUppercut?6.f:0.f)*PoseScale.Y);};
    float Front=FMath::Max(float(FVector::DotProduct(Plane-Targets[0].GetLocation(),Forward)),
        float(FVector::DotProduct(Plane-Targets[1].GetLocation(),Forward)));
    for(const FVector& Point:PistolClearanceInHand[0])
        Front=FMath::Max(Front,float(FVector::DotProduct(Chest.GetLocation()+Forward*(14.f*PoseScale.Y)-Targets[0].TransformPosition(Point),Forward)));
    if(!bKukriQuickActive)FitHandPair(Pose,Targets,Forward,Front,true);
    else for(int32 Side=0;Side<2;++Side)
    {
        // The stab separates the hands; a coupled grip fit would pull the
        // blade back whenever the pistol needs a different reach correction.
        const double Length=(FVector::Dist(Arms[Side].Hip,Arms[Side].Knee)+
            FVector::Dist(Arms[Side].Knee,Arms[Side].Ankle))*.97;
        const FVector Reach=Targets[Side].GetLocation()-Shoulders[Side];
        double Shift=FMath::Max(0.,FVector::DotProduct(ContactPlane(Side)-Targets[Side].GetLocation(),Forward));
        if(Side==0)for(const FVector& Point:PistolClearanceInHand[0])
            Shift=FMath::Max(Shift,FVector::DotProduct(Chest.GetLocation()+Forward*(14.f*PoseScale.Y)-Targets[0].TransformPosition(Point),Forward));
        const double Depth=FMath::Clamp(FVector::DotProduct(Reach,Forward)+Shift,-Length*.98,Length*.98);
        const FVector Across=FVector::VectorPlaneProject(Reach,Forward).GetClampedToMaxSize(FMath::Sqrt(FMath::Max(0.,Length*Length-Depth*Depth)));
        Targets[Side].SetLocation(Shoulders[Side]+Forward*Depth+Across);
    }
    KukriSupportFit.Configure(Chest,BookChestBind,Pose.GetComponentSpaceTransform(Pelvis.GetCompactPoseIndex(Bones)).GetLocation(),Shoulders[0],Shoulders[1]);
    const double BaseRadius=KukriSupportFit.Radius.Y;
    KukriSupportFit.Delta=Delta;
    const auto FitContact=[&](int32 Side,FTransform Goal)
    {
        const bool KnifeCut=NativeUppercut&&Side==1;
        KukriSupportFit.bLongGrip=NativeUppercut;
        KukriSupportFit.Radius.Y=BaseRadius+(NativeUppercut?3.f*PoseScale.Y:0.f);
        KukriSupportFit.Apply(Pose,Hands[Side],Side,Goal,1.f);
        if(!KnifeCut)return;
        const auto W=Hands[Side].GetCompactPoseIndex(Bones),E=Bones.GetParentBoneIndex(W);
        const auto& Ref=Bones.GetRefPoseTransform(W);
        for(int32 Pass=0;Pass<2;++Pass)
        {
            const auto Wrist=Pose.GetComponentSpaceTransform(W);
            const FVector Forearm=(Wrist.GetLocation()-Pose.GetComponentSpaceTransform(E).GetLocation()).GetSafeNormal();
            const FVector Palm=(Wrist.GetRotation()*Ref.GetRotation().Inverse()).RotateVector(Ref.GetLocation().GetSafeNormal());
            const double Angle=FMath::Acos(FMath::Clamp(FVector::DotProduct(Palm,Forearm),-1.,1.));
            if(Angle<=FMath::DegreesToRadians(55.))break;
            // Pitching the whole cut down may make the FPS palm unreachable.
            // Relax that palm and re-solve shoulder/elbow/forearm together;
            // the blade retains its native in-hand grip throughout.
            const FQuat Relax=FQuat::Slerp(FQuat::Identity,FQuat::FindBetweenNormals(Palm,Forearm),
                float((Angle-FMath::DegreesToRadians(53.))/Angle));
            Goal.SetRotation((Relax*Wrist.GetRotation()).GetNormalized());
            KukriSupportFit.Apply(Pose,Hands[Side],Side,Goal,1.f);
        }
    };
    // Reuse the native-chain contact fitter: choose a nearby elbow solution
    // for BOTH torso clearance and wrist bend, preserving helpers/bone lengths.
    // Clearance alone can select the opposite elbow branch and fold the wrist.
    for(int32 Side=0;Side<2;++Side)FitContact(Side,Targets[Side]);
    Out.Pose=Pose.GetPose();FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Out.Pose);
    KukriCarryAge+=Delta;const float Alpha=Ease(KukriCarryAge/KukriCarryBlendSeconds);
    for(int32 I=0;I<Count;++I)if(ArmBone(I))
    {
        const FCompactPoseBoneIndex Bone(I);FTransform Mixed;
        Mixed.Blend(KukriCarryEntryPose[I],Out.Pose[Bone],Alpha);Out.Pose[Bone]=Mixed;
    }
    Pose.InitPose(Out.Pose);
    if(NativeUppercut&&KukriCarryAge<.12f)
    {
        // Local-space entry blending happens after the contact solve. Refit
        // that short blended entry around its achieved palms so a crouched ADS
        // entry cannot take a shortcut through the chest.
        for(int32 Side=0;Side<2;++Side)
        {
            auto Goal=KukriSupportFit.ClearFreeHand(Pose.GetComponentSpaceTransform(Hands[Side].GetCompactPoseIndex(Bones)));
            Goal.AddToTranslation(Forward*FMath::Max(0.,FVector::DotProduct(ContactPlane(Side)-Goal.GetLocation(),Forward)));
            FitContact(Side,Goal);
        }
        Out.Pose=Pose.GetPose();FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Out.Pose);
    }
    KukriCarryLastPose.SetNum(Count);
    for(int32 I=0;I<Count;++I)if(ArmBone(I))KukriCarryLastPose[I]=Out.Pose[FCompactPoseBoneIndex(I)];
    for(int32 Side=0;Side<2;++Side)LastHands[Side]=Pose.GetComponentSpaceTransform(Hands[Side].GetCompactPoseIndex(Bones));
    bHadKukriCarry=true;bHadKukriQuick=bKukriQuickActive;
}
