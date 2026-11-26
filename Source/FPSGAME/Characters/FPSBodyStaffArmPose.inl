// Jason's staff palm owns a complete arm, rather than a rotation pasted over
// positional IK. Use the native elbow plane and hand bind, then pronate the
// forearm. The held staff follows any bounded wrist correction as one group.
void FControls::FitStaffArm(FCSPose<FCompactPose>& Pose,int32 Side,bool bBeforeConsume,bool bPistolSupport)
{
    if(!bBeforeConsume&&FPSBodyPistolMotion::OwnsHand(State,Side)&&
        ConsumeWeight>ZERO_ANIMWEIGHT_THRESH&&(Side==1||bConsumeTwoHands))return;
    if(Side==0&&!bPistolSupport&&!PistolArmActive(0)&&(bStaffNativeArmApplied||State.Family!=TEXT("Staff")||!(EquipmentGripHands&1)))return;
    if(FPSBodyPoses::Traversing(State.Motion)||State.Action==EFPSBodyAction::Dead)return;
    const auto& Bones=Pose.GetPose().GetBoneContainer();
    if(!Hands[Side].IsValidToEvaluate(Bones))return;
    const auto W=Hands[Side].GetCompactPoseIndex(Bones),E=Bones.GetParentBoneIndex(W),S=Bones.GetParentBoneIndex(E);
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
    // The complete pistol stance already supplies its anatomical elbow plane.
    // Palm pronation belongs to the forearm roll below; using it to choose the
    // elbow plane flares both upper arms when the guns point down.
    if(bPistolSupport&&!IncomingBend.IsNearlyZero())Bend=IncomingBend;
    else if(Bend.IsNearlyZero())Bend=IncomingBend;
    else Bend=(Bend+IncomingBend*.15).GetSafeNormal();
    if(Bend.IsNearlyZero())return;
    if(bPistolSupport&&State.bDual)
    {
        // Both elbows need their own side of the chest and room around it.
        // A palm-driven bend can cross the midline while the wrist remains on
        // its correct side, especially when aiming down. Solve both planes on
        // the native elbow circle; moving only the wrist cannot separate arms.
        const auto Torso=Pose.GetComponentSpaceTransform(Spine.GetCompactPoseIndex(Bones));
        const FQuat Frame=(Torso.GetRotation()*PistolTorsoBind.Inverse()).GetNormalized();
        const FVector Normals[2]={Frame.RotateVector(FVector(Side==0?-1.:1.,0,0)),Frame.RotateVector(FVector::RightVector)};
        // Jason's measured torso front is 10.54 cm from this spine frame.
        // Keep about 4 cm of forearm room. The old 18 cm plane excluded the
        // lowered authored elbow and forced a high, sideways bend instead.
        const double Clearances[2]={10.*PoseScale.X,14.5*PoseScale.Y};
        const FVector Center=Origin+Axis*Along;
        TArray<FVector,TInlineAllocator<5>> Candidates;Candidates.Add(Bend);
        for(int32 Plane=0;Plane<2&&Radius>UE_SMALL_NUMBER;++Plane)
        {
            FVector Direction=FVector::VectorPlaneProject(Normals[Plane],Axis);
            const double Projected=Direction.Size();if(Projected<=UE_SMALL_NUMBER)continue;
            Direction/=Projected;
            const double Minimum=FMath::Clamp((Clearances[Plane]-FVector::DotProduct(Center-Torso.GetLocation(),Normals[Plane]))/(Radius*Projected),-1.,1.);
            const FVector Around=FVector::CrossProduct(Axis,Direction)*FMath::Sqrt(FMath::Max(0.,1.-Minimum*Minimum));
            Candidates.Add(Direction*Minimum+Around);Candidates.Add(Direction*Minimum-Around);
        }
        // The closest feasible point is the requested bend or a plane boundary.
        // Low-look wrists are staged forwards by DualPistolHandTarget so the
        // authored lower elbow branch remains reachable outside the torso.
        FVector Best=Bend;double BestSideLoss=DBL_MAX,BestFrontLoss=DBL_MAX,BestScore=-DBL_MAX;
        for(const FVector& Candidate:Candidates)
        {
            const FVector Point=Center+Candidate*Radius-Torso.GetLocation();
            const double SideLoss=FMath::Max(0.,Clearances[0]-FVector::DotProduct(Point,Normals[0]));
            const double FrontLoss=FMath::Max(0.,Clearances[1]-FVector::DotProduct(Point,Normals[1]));
            const double Score=FVector::DotProduct(Candidate,Bend);
            const bool SideTie=FMath::Abs(SideLoss-BestSideLoss)<1.e-4;
            const bool FrontTie=FMath::Abs(FrontLoss-BestFrontLoss)<1.e-4;
            if(SideLoss<BestSideLoss-1.e-4||(SideTie&&(FrontLoss<BestFrontLoss-1.e-4||(FrontTie&&Score>BestScore))))
            {Best=Candidate;BestSideLoss=SideLoss;BestFrontLoss=FrontLoss;BestScore=Score;}
        }
        Bend=Best;
    }
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
    const double WristLimit=FMath::DegreesToRadians(bPistolSupport&&State.bDual?55.:25.);
    // The reload contact and its body-clear elbow were solved as one group.
    // Rebuild native roll/helpers without moving that contact or elbow plane.
    if(!bPistolSupport||State.bDual)Hand.SetRotation(FQuat::Slerp(NeutralHand,Hand.GetRotation(),WristAngle>WristLimit?WristLimit/WristAngle:1.).GetNormalized());
    Upper.SetRotation(UpperQ);Lower.SetLocation(Elbow);Lower.SetRotation(LowerQ);Hand.SetLocation(Target);
    TArray<FBoneTransform,TInlineAllocator<3>> Change;Change.Emplace(S,Upper);Change.Emplace(E,Lower);Change.Emplace(W,Hand);
    Pose.LocalBlendCSBoneTransforms(Change,1.f);
    // IK replaces the library arm, so its twist/corrective locals must be
    // replaced too. Keeping gait's bicep/tricep offsets under the new upper
    // arm folds and bulges the sleeve despite correct main-bone lengths.
    // Rebuild only the arm helpers, in parent order, on native segment binds.
    // The wrist and its complete first-person-derived grip are untouched.
    TArray<FBoneTransform,TInlineAllocator<24>> Helpers;
    const auto AddHelper=[&](FCompactPoseBoneIndex Bone)
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
    };
    if(Side==0)for(const auto Bone:StaffArmHelpers)AddHelper(Bone);
    else
    {
        const auto& Skeleton=Bones.GetReferenceSkeleton();
        const int32 UpperBone=Bones.MakeMeshPoseIndex(S).GetInt(),WristBone=Bones.MakeMeshPoseIndex(W).GetInt();
        for(int32 I=0;I<BookMotionBones.Num();++I)if(BookMotionBones[I])
        {
            const FCompactPoseBoneIndex Bone(I);const int32 MeshBone=Bones.MakeMeshPoseIndex(Bone).GetInt();
            if(Bone!=E&&Bone!=W&&Skeleton.BoneIsChildOf(MeshBone,UpperBone)&&!Skeleton.BoneIsChildOf(MeshBone,WristBone))AddHelper(Bone);
        }
    }
    if(!Helpers.IsEmpty())Pose.LocalBlendCSBoneTransforms(Helpers,1.f);
    LastHands[Side]=Pose.GetComponentSpaceTransform(W);
}
