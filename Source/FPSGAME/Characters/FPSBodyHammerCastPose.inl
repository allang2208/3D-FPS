// World-body casting follows the turned hammer torso, not the camera rig's
// position. Solve shoulder/elbow/wrist throughout the path, including recovery.
void FControls::BlendHammerCast(FPoseContext& Out,FCSPose<FCompactPose>& Pose)
{
    const bool Active=State.Family==TEXT("Tool")&&State.Weapon==TEXT("warhammer")&&
        State.Action==EFPSBodyAction::Cast&&State.Contacts.Channel!=TEXT("StaffCast")&&!FPSBodyPoses::Traversing(State.Motion);
    const auto& Bones=Out.Pose.GetBoneContainer();
    if(!Active||HammerCastBones.IsEmpty()||!Hands[1].IsValidToEvaluate(Bones))
    {bHadHammerCast=false;HammerCastEntryPose.Reset();return;}
    const auto W=Hands[1].GetCompactPoseIndex(Bones),E=Bones.GetParentBoneIndex(W),U=Bones.GetParentBoneIndex(E);
    if(E==INDEX_NONE||U==INDEX_NONE)return;
    const auto Clavicle=Bones.GetParentBoneIndex(U);
    if(Clavicle==INDEX_NONE)return;
    const auto Chest=Bones.GetParentBoneIndex(Clavicle);if(Chest==INDEX_NONE)return;
    Out.Pose=Pose.GetPose();FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Out.Pose);
    const bool SameWeapon=HammerCastWeaponInstance==State.WeaponInstance;
    if(!bHadHammerCast||!SameWeapon||HammerCastStartedAt!=State.ActionStartedAt||HammerCastPhase!=State.ActionVariant)
    {
        HammerCastEntryPose.SetNum(Bones.GetCompactPoseNumBones());
        for(const auto B:HammerCastBones)HammerCastEntryPose[B.GetInt()]=SameWeapon&&LastHammerCastPose.Num()==HammerCastEntryPose.Num()?LastHammerCastPose[B.GetInt()]:Out.Pose[B];
        HammerCastEntryProgress=State.ActionProgress;HammerCastEntryReleaseFraction=State.ReleaseFraction;
        HammerCastPhase=State.ActionVariant;HammerCastPhaseAge=0.f;
        HammerCastWeaponInstance=State.WeaponInstance;HammerCastStartedAt=State.ActionStartedAt;HammerCastTravel=0.f;
    }
    bHadHammerCast=true;HammerCastPhaseAge+=Delta;
    const bool Recover=State.ActionVariant==TEXT("Recover"),Release=State.ActionVariant==TEXT("Release");
    const float Progress=FMath::Clamp((State.ActionProgress-HammerCastEntryProgress)/FMath::Max(.001f,1.f-HammerCastEntryProgress),0.f,1.f);
    // A detached release starts at palm fraction .48 after Ready, not zero.
    // Remove that entry fraction so the phase boundary cannot jump the arm.
    const float Push=(State.ReleaseFraction-HammerCastEntryReleaseFraction)/FMath::Max(.001f,1.f-HammerCastEntryReleaseFraction);
    const bool ArrivedAtEnd=Release?HammerCastEntryReleaseFraction>=.999f:HammerCastEntryProgress>=.999f;
    const float SampleTravel=State.ActionVariant==TEXT("Hold")||ArrivedAtEnd?Ease(HammerCastPhaseAge/.12f):Ease(Release?Push:Progress);
    // A fresh sparse snapshot can trail this observer's bounded extrapolation.
    // Keep one phase moving forward; only a new phase/cast/equipment resets it.
    const float Travel=HammerCastTravel=FMath::Max(HammerCastTravel,SampleTravel);

    // Rebase the last displayed arm onto the live clavicle. The existing torso,
    // shoulder girdle and right-hand hammer carry keep their native animation.
    FPoseContext Entry(Out);Entry.Pose=Out.Pose;
    for(const auto B:HammerCastBones)if(B!=Clavicle)Entry.Pose[B]=HammerCastEntryPose[B.GetInt()];
    FCSPose<FCompactPose> EntryCS;EntryCS.InitPose(Entry.Pose);
    const FTransform EntryUpper=EntryCS.GetComponentSpaceTransform(U),EntryLower=EntryCS.GetComponentSpaceTransform(E),EntryHand=EntryCS.GetComponentSpaceTransform(W);
    const auto& Ref=Bones.GetReferenceSkeleton().GetRefBonePose();
    const FTransform& LowerRef=Ref[Bones.MakeMeshPoseIndex(E).GetInt()];
    const FTransform& HandRef=Ref[Bones.MakeMeshPoseIndex(W).GetInt()];
    const FTransform CarryUpper=Pose.GetComponentSpaceTransform(U),CarryLower=Pose.GetComponentSpaceTransform(E),CarryHand=Pose.GetComponentSpaceTransform(W);
    auto Upper=CarryUpper,Lower=CarryLower,Hand=CarryHand;
    const FVector Origin=Upper.GetLocation();
    const double L1=FVector::Distance(Origin,Lower.GetLocation()),L2=FVector::Distance(Lower.GetLocation(),Hand.GetLocation());
    if(L1+L2<1.)return;
    const double Size=(L1+L2)/51.3;
    const FQuat ChestFrame=(Pose.GetComponentSpaceTransform(Chest).GetRotation()*HammerCastChestBind.Inverse()).GetNormalized();
    const FVector Left=ChestFrame.GetAxisX(),Front=ChestFrame.GetAxisY(),Up=ChestFrame.GetAxisZ();
    const auto InChest=[&](const FVector& V){return Origin+ChestFrame.RotateVector(V*Size);};
    // Jason's hammer chest is oblique. A mesh-space +Y pole/target can lie
    // BEHIND that chest; clamping arm length cannot make that direction safe.
    const float PitchLift=FMath::Clamp(State.AimPitch,-45.f,45.f)*.16f;
    FVector Goal=InChest(Release?FVector(8,43,12+PitchLift):
        State.ActionVariant==TEXT("Ready")?FVector(13,29,12+PitchLift):FVector(14,32,5+PitchLift));
    FVector GoalPole=InChest(FVector(29,14,-20));
    FQuat GoalHand;
    if(ActionWristMask&2)GoalHand=ActionHands[1].GetRotation();
    else
    {
        const FVector Fingers=Release?Up*.967+Front*.25:Front*.94-Left*.22+Up*.20;
        const FVector Palm=Release?Front*.968-Up*.25:Up*.98-Front*.20;
        GoalHand=(FRotationMatrix::MakeFromXZ(Fingers,Palm).ToQuat()*HammerCastPalmCorrection).GetNormalized();
    }
    if(Recover){Goal=CarryHand.GetLocation();GoalPole=CarryLower.GetLocation();GoalHand=CarryHand.GetRotation();}
    const double Arc=FMath::Sin(PI*double(Travel))*Size;
    // Travel outside/front of the chest. Do not slerp the complete arm's local
    // rotations: their intermediate wrist/elbow can sweep through the torso.
    FVector Target=FMath::Lerp(EntryHand.GetLocation(),Goal,double(Travel))+(Left*4.+Front*5.)*Arc;
    const FVector Pole=FMath::Lerp(EntryLower.GetLocation(),GoalPole,double(Travel))+(Left*6.+Front*3.)*Arc;
    const FVector Axis=(Target-Origin).GetSafeNormal();if(Axis.IsNearlyZero())return;
    const double Distance=FMath::Clamp(FVector::Distance(Origin,Target),FMath::Abs(L1-L2)+.05,(L1+L2)*.955);
    Target=Origin+Axis*Distance;
    const double Along=(L1*L1-L2*L2+Distance*Distance)/(2.*Distance);
    const double Radius=FMath::Sqrt(FMath::Max(0.,L1*L1-Along*Along));
    FVector Bend=FVector::VectorPlaneProject(Pole-Origin,Axis).GetSafeNormal();
    if(Bend.IsNearlyZero())Bend=FVector::VectorPlaneProject(Left-Up,Axis).GetSafeNormal();
    const FVector Elbow=Origin+Axis*Along+Bend*Radius;
    const FVector UpperDirection=(Elbow-Origin).GetSafeNormal(),LowerDirection=(Target-Elbow).GetSafeNormal();
    const FVector UpperAxis=LowerRef.GetLocation().GetSafeNormal(),LowerAxis=HandRef.GetLocation().GetSafeNormal();
    const FVector NativePlane=FVector::CrossProduct(UpperAxis,LowerRef.GetRotation().RotateVector(LowerAxis)).GetSafeNormal();
    const FVector Plane=FVector::CrossProduct(UpperDirection,LowerDirection).GetSafeNormal();
    const auto Align=[](FQuat Q,const FVector& LocalAxis,const FVector& Direction)
    {return (FQuat::FindBetweenNormals(Q.RotateVector(LocalAxis),Direction)*Q).GetNormalized();};
    FQuat UpperQ=(FRotationMatrix::MakeFromXZ(UpperDirection,Plane).ToQuat()*
        FRotationMatrix::MakeFromXZ(UpperAxis,NativePlane).ToQuat().Inverse()).GetNormalized();
    FQuat LowerQ=Align(UpperQ*LowerRef.GetRotation(),LowerAxis,LowerDirection);
    // Use palm width about the forearm, rather than the full wrist quaternion;
    // the latter mixed wrist extension into elbow pronation.
    const FVector From=FVector::VectorPlaneProject((LowerQ*HandRef.GetRotation()).RotateVector(HammerCastPalmAcross),LowerDirection).GetSafeNormal();
    const FVector To=FVector::VectorPlaneProject(GoalHand.RotateVector(HammerCastPalmAcross),LowerDirection).GetSafeNormal();
    const double ForearmRoll=FMath::Clamp(FMath::Atan2(LowerDirection|(From^To),From|To),FMath::DegreesToRadians(-75.),FMath::DegreesToRadians(75.));
    LowerQ=(FQuat(LowerDirection,ForearmRoll)*LowerQ).GetNormalized();
    if(Recover)
    {
        UpperQ=Align(CarryUpper.GetRotation(),UpperAxis,UpperDirection);
        LowerQ=Align(CarryLower.GetRotation(),LowerAxis,LowerDirection);
    }
    else
    {
        const FQuat NeutralHand=(LowerQ*HandRef.GetRotation()).GetNormalized();
        const double Angle=NeutralHand.AngularDistance(GoalHand),Limit=FMath::DegreesToRadians(40.);
        GoalHand=FQuat::Slerp(NeutralHand,GoalHand,Angle>Limit?Limit/Angle:1.).GetNormalized();
    }
    // Both endpoints point down the same solved segment. Blending their axial
    // roll retains the solved elbow/wrist positions throughout the transition.
    UpperQ=FQuat::Slerp(Align(EntryUpper.GetRotation(),UpperAxis,UpperDirection),UpperQ,Travel).GetNormalized();
    LowerQ=FQuat::Slerp(Align(EntryLower.GetRotation(),LowerAxis,LowerDirection),LowerQ,Travel).GetNormalized();
    Upper.SetRotation(UpperQ);Lower.SetLocation(Elbow);Lower.SetRotation(LowerQ);Hand.SetLocation(Target);
    Hand.SetRotation(FQuat::Slerp(EntryHand.GetRotation(),GoalHand,Travel).GetNormalized());
    TArray<FBoneTransform,TInlineAllocator<3>> Main;Main.Emplace(U,Upper);Main.Emplace(E,Lower);Main.Emplace(W,Hand);
    Pose.LocalBlendCSBoneTransforms(Main,1.f);
    TArray<FBoneTransform,TInlineAllocator<32>> Helpers;
    for(const auto B:HammerCastHelpers)
    {
        const auto Parent=Bones.GetParentBoneIndex(B);
        const auto* Written=Helpers.FindByPredicate([&](const FBoneTransform& T){return T.BoneIndex==Parent;});
        const FTransform ParentPose=Written?Written->Transform:Pose.GetComponentSpaceTransform(Parent);
        FTransform Local=Recover?Out.Pose[B]:Ref[Bones.MakeMeshPoseIndex(B).GetInt()];
        if(!Recover&&Parent==E)
        {
            const double Station=FMath::Clamp(FVector::DotProduct(Local.GetLocation(),LowerAxis)/HandRef.GetLocation().Size(),0.,1.);
            Local.SetRotation((FQuat(LowerAxis,-ForearmRoll*(1.-Station))*Local.GetRotation()).GetNormalized());
        }
        FTransform Mixed;Mixed.Blend(HammerCastEntryPose[B.GetInt()],Local,Travel);
        Helpers.Emplace(B,Mixed*ParentPose);
    }
    if(!Helpers.IsEmpty())Pose.LocalBlendCSBoneTransforms(Helpers,1.f);
    LastHands[1]=Pose.GetComponentSpaceTransform(W);
}
