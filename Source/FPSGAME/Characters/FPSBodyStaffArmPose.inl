// Jason's staff palm owns a complete arm, rather than a rotation pasted over
// positional IK. Use the native elbow plane and hand bind, then pronate the
// forearm. The held staff follows any bounded wrist correction as one group.
void FControls::FitStaffArm(FCSPose<FCompactPose>& Pose)
{
    if(bStaffNativeArmApplied||State.Family!=TEXT("Staff")||!(EquipmentGripHands&1)||
        FPSBodyPoses::Traversing(State.Motion)||State.Action==EFPSBodyAction::Dead)return;
    const auto& Bones=Pose.GetPose().GetBoneContainer();
    if(!Hands[0].IsValidToEvaluate(Bones))return;
    const auto W=Hands[0].GetCompactPoseIndex(Bones),E=Bones.GetParentBoneIndex(W),S=Bones.GetParentBoneIndex(E);
    if(E==INDEX_NONE||S==INDEX_NONE)return;
    const auto& Ref=Bones.GetReferenceSkeleton().GetRefBonePose();
    const FTransform& LowerRef=Ref[Bones.MakeMeshPoseIndex(E).GetInt()];
    const FTransform& HandRef=Ref[Bones.MakeMeshPoseIndex(W).GetInt()];
    auto Upper=Pose.GetComponentSpaceTransform(S),Lower=Pose.GetComponentSpaceTransform(E),Hand=Pose.GetComponentSpaceTransform(W);
    const FVector Origin=Upper.GetLocation();
    const double L1=FVector::Distance(Origin,Lower.GetLocation()),L2=FVector::Distance(Lower.GetLocation(),Hand.GetLocation());
    const FVector Axis=(Hand.GetLocation()-Origin).GetSafeNormal();
    const double Distance=FMath::Clamp(FVector::Distance(Origin,Hand.GetLocation()),FMath::Abs(L1-L2)+.01,(L1+L2)*.965);
    const FVector Target=Origin+Axis*Distance;
    const double Along=(L1*L1-L2*L2+Distance*Distance)/(2.*Distance);
    const double Radius=FMath::Sqrt(FMath::Max(0.,L1*L1-Along*Along));
    const FVector UpperAxis=LowerRef.GetLocation().GetSafeNormal(),LowerAxis=HandRef.GetLocation().GetSafeNormal();
    const FQuat ExpectedLower=Hand.GetRotation()*HandRef.GetRotation().Inverse();
    const FVector PreferredElbow=Target-ExpectedLower.RotateVector(LowerAxis)*L2;
    FVector Bend=FVector::VectorPlaneProject(PreferredElbow-Origin,Axis).GetSafeNormal();
    const FVector IncomingBend=FVector::VectorPlaneProject(Lower.GetLocation()-Origin,Axis).GetSafeNormal();
    if(Bend.IsNearlyZero())Bend=IncomingBend;
    else Bend=(Bend+IncomingBend*.15).GetSafeNormal();
    if(Bend.IsNearlyZero())return;
    const FVector Elbow=Origin+Axis*Along+Bend*Radius;
    const FVector UpperDirection=(Elbow-Origin).GetSafeNormal(),LowerDirection=(Target-Elbow).GetSafeNormal();
    const FVector NativeNormal=FVector::CrossProduct(UpperAxis,LowerRef.GetRotation().RotateVector(LowerAxis)).GetSafeNormal();
    const FVector Normal=FVector::CrossProduct(UpperDirection,LowerDirection).GetSafeNormal();
    const FQuat UpperQ=(FRotationMatrix::MakeFromXY(UpperDirection,Normal).ToQuat()*
        FRotationMatrix::MakeFromXY(UpperAxis,NativeNormal).ToQuat().Inverse()).GetNormalized();
    FQuat LowerQ=(UpperQ*LowerRef.GetRotation()).GetNormalized();
    LowerQ=(FQuat::FindBetweenNormals(LowerQ.RotateVector(LowerAxis),LowerDirection)*LowerQ).GetNormalized();
    FQuat Difference=(ExpectedLower*LowerQ.Inverse()).GetNormalized();
    if(Difference.W<0.)Difference=Difference*-1.;
    const double Roll=2.*FMath::Atan2(FVector::DotProduct(FVector(Difference.X,Difference.Y,Difference.Z),LowerDirection),Difference.W);
    const double ForearmRoll=FMath::Clamp(Roll,FMath::DegreesToRadians(-85.),FMath::DegreesToRadians(85.));
    LowerQ=(FQuat(LowerDirection,ForearmRoll)*LowerQ).GetNormalized();
    const FQuat NeutralHand=(LowerQ*HandRef.GetRotation()).GetNormalized();
    const double WristAngle=NeutralHand.AngularDistance(Hand.GetRotation());
    const double WristLimit=FMath::DegreesToRadians(25.);
    Hand.SetRotation(FQuat::Slerp(NeutralHand,Hand.GetRotation(),WristAngle>WristLimit?WristLimit/WristAngle:1.).GetNormalized());
    Upper.SetRotation(UpperQ);Lower.SetLocation(Elbow);Lower.SetRotation(LowerQ);Hand.SetLocation(Target);
    TArray<FBoneTransform,TInlineAllocator<3>> Change;Change.Emplace(S,Upper);Change.Emplace(E,Lower);Change.Emplace(W,Hand);
    Pose.LocalBlendCSBoneTransforms(Change,1.f);
    // IK replaces the library arm, so its twist/corrective locals must be
    // replaced too. Keeping gait's bicep/tricep offsets under the new upper
    // arm folds and bulges the sleeve despite correct main-bone lengths.
    // Rebuild only the arm helpers, in parent order, on native segment binds.
    // The wrist and its complete first-person-derived grip are untouched.
    TArray<FBoneTransform,TInlineAllocator<24>> Helpers;
    for(const auto Bone:StaffArmHelpers)
    {
        const auto Parent=Bones.GetParentBoneIndex(Bone);
        const auto* ParentChange=Helpers.FindByPredicate([&](const FBoneTransform& T){return T.BoneIndex==Parent;});
        const FTransform ParentPose=ParentChange?ParentChange->Transform:Pose.GetComponentSpaceTransform(Parent);
        FTransform Local=Ref[Bones.MakeMeshPoseIndex(Bone).GetInt()];
        if(Parent==E)
        {
            // Jason's elbow-side twist and corrective root must not inherit
            // the full wrist pronation. Distribute it by native station along
            // the forearm; descendants keep their complete local bind.
            const double Station=FMath::Clamp(FVector::DotProduct(Local.GetLocation(),LowerAxis)/HandRef.GetLocation().Size(),0.,1.);
            Local.SetRotation((FQuat(LowerAxis,-ForearmRoll*(1.-Station))*Local.GetRotation()).GetNormalized());
        }
        Helpers.Emplace(Bone,Local*ParentPose);
    }
    if(!Helpers.IsEmpty())Pose.LocalBlendCSBoneTransforms(Helpers,1.f);
    LastHands[0]=Pose.GetComponentSpaceTransform(W);
}
