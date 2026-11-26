// Independent pistol wrists are staged from their own shoulders. The native
// hand-to-gun relation is cached at equipment time; no view-camera transform is
// read by this layer, including equip/reload and the recovery spin.
bool FControls::PistolArmActive(int32 Side) const
{
    if(bSinglePistolReference)return false;
    if(!(IndependentPistolHands&(1<<Side))||!FPSBodyPistolMotion::OwnsHand(State,Side)||
        FPSBodyPoses::Traversing(State.Motion)||State.Action==EFPSBodyAction::Dead)return false;
    // Keep a stable carry underneath the native consume layer. Disabling this
    // baseline would blend from walking arms at entry and snap back on exit.
    if(Side==1&&(State.Action==EFPSBodyAction::DoorPush||
        (State.Action==EFPSBodyAction::Cast&&State.Contacts.Channel!=TEXT("StaffCast"))))return false;
    return true;
}

float FControls::BlendDualPistolHand(FCSPose<FCompactPose>& Pose,int32 Side,FTransform& Target,bool RecoveringCast)
{
    auto& Blend=PistolTransitions[Side];
    const FName Channel=FPSBodyPistolMotion::HandChannel(State,Side);
    const FString& Instance=Side==0?State.WeaponInstance:State.OffhandInstance;
    const auto& Hand=Side==0?State.RightHand:State.LeftHand;
    const bool Bash=Channel==TEXT("PistolBashLeft")||Channel==TEXT("PistolBashRight");
    const float Progress=Bash?State.ActionProgress:Hand.Progress;
    const float Rate=Bash?State.ActionProgressRate:Hand.ProgressRate;
    const bool SameGun=bHasDualHandHistory&&Blend.Instance==Instance;
    if(!SameGun)
    {
        // A new grip must not inherit another pistol's fitted palm frame.
        Blend.Instance=Instance;Blend.Age=1.f;Blend.Duration=0.f;
    }
    else if(Blend.Channel!=Channel)
    {
        const bool NativeBefore=FPSBodyPistolMotion::IsPistolChannel(Blend.Channel);
        const bool NativeNow=FPSBodyPistolMotion::IsPistolChannel(Channel);
        const bool Completed=Blend.Progress+FMath::Max(0.f,Blend.ProgressRate)*Delta>=1.f-UE_KINDA_SMALL_NUMBER;
        // Native clips already own their entry and exit. Preserve that clock.
        // Only an interruption/external handover needs a new return.
        const bool SourceOwnsBlend=NativeBefore&&NativeNow&&(Channel!=TEXT("PistolCarry")||Completed);
        Blend.Duration=SourceOwnsBlend?0.f:.1f;Blend.Age=0.f;
        Blend.EntryInTorso=LastHands[Side].GetRelativeTransform(LastPistolTorso);
    }
    Blend.Channel=Channel;Blend.Progress=Progress;Blend.ProgressRate=Rate;Blend.Age+=Delta;
    const float Weight=Blend.Duration>0.f?Ease(Blend.Age/Blend.Duration):1.f;
    if(SameGun&&Weight<1.f&&!(Side==1&&RecoveringCast))
    {
        auto Torso=Pose.GetComponentSpaceTransform(Spine.GetCompactPoseIndex(Pose.GetPose().GetBoneContainer()));
        Torso.SetScale3D(FVector::OneVector);
        FTransform Mixed;Mixed.Blend(Blend.EntryInTorso*Torso,Target,Weight);Target=Mixed;
    }
    return Weight;
}

// Use the primary arm's complete ready support as the anatomical reference.
// Only the arm is reflected: the left pistol keeps its own wrist, fingers,
// mechanical animation and positive-scale mount.
void FControls::FitLeftPistolCarryFromRight(FCSPose<FCompactPose>& Pose,const FQuat& NativeWrist)
{
    if(!State.bDual||State.Motion!=EFPSBodyMotion::Ground||bFalling||!PistolArmActive(1)||
        ConsumeWeight>ZERO_ANIMWEIGHT_THRESH||PistolArmMirror.IsEmpty())
    {LeftPistolCarryBlend=0.f;return;}
    const auto& Bones=Pose.GetPose().GetBoneContainer();
    const auto W=Hands[1].GetCompactPoseIndex(Bones),E=Bones.GetParentBoneIndex(W),U=Bones.GetParentBoneIndex(E);
    const auto Index=[&](FCompactPoseBoneIndex B)
    {return PistolArmMirror.IndexOfByPredicate([&](const FPistolArmMirrorBone& P){return P.Left==B;});};
    const int32 UpperIndex=Index(U),ElbowIndex=Index(E);
    if(UpperIndex==INDEX_NONE||ElbowIndex==INDEX_NONE)return;
    auto Torso=Pose.GetComponentSpaceTransform(Spine.GetCompactPoseIndex(Bones));Torso.SetScale3D(FVector::OneVector);
    if(RightPistolCarryInstance!=State.WeaponInstance)
    {
        RightPistolCarryInTorso.Reset();RightPistolCarryInstance=State.WeaponInstance;LeftPistolCarryBlend=0.f;
    }
    // Never copy the other gun's reload, equip, recoil or melee into the left.
    // A previously captured ready reference remains anchored to today's torso.
    if(FPSBodyPistolMotion::HandChannel(State,0)==TEXT("PistolCarry")&&PistolArmActive(0)&&Clock-State.RightHand.LastShotAt>.18f)
    {
        RightPistolCarryInTorso.SetNum(PistolArmMirror.Num());
        for(int32 I=0;I<PistolArmMirror.Num();++I)
            RightPistolCarryInTorso[I]=Pose.GetComponentSpaceTransform(PistolArmMirror[I].Right).GetRelativeTransform(Torso);
    }
    if(RightPistolCarryInTorso.Num()!=PistolArmMirror.Num())return;
    const bool Carry=FPSBodyPistolMotion::HandChannel(State,1)==TEXT("PistolCarry");
    LeftPistolCarryBlend=FMath::FInterpConstantTo(LeftPistolCarryBlend,Carry?1.f:0.f,Delta,1.f/.12f);
    const float Weight=Ease(LeftPistolCarryBlend);if(Weight<=ZERO_ANIMWEIGHT_THRESH)return;
    const auto ReflectVector=[](FVector V){return FVector(-V.X,V.Y,V.Z);};
    const auto ReflectRotation=[](FQuat Q){return FQuat(Q.X,-Q.Y,-Q.Z,Q.W).GetNormalized();};
    TArray<FQuat,TInlineAllocator<64>> Mirrored;
    TArray<FTransform,TInlineAllocator<64>> ExistingLocal;
    Mirrored.SetNum(PistolArmMirror.Num());ExistingLocal.SetNum(PistolArmMirror.Num());
    for(int32 I=0;I<PistolArmMirror.Num();++I)
    {
        const auto& Pair=PistolArmMirror[I];
        const auto Right=RightPistolCarryInTorso[I]*Torso;
        // Reflect the pose delta in body space, then reapply the LEFT bind.
        // Mirroring Euler angles or copying right bone axes twists the left arm.
        Mirrored[I]=(ReflectRotation(Right.GetRotation()*Pair.RightBind.Inverse())*Pair.LeftBind).GetNormalized();
        const auto Parent=Bones.GetParentBoneIndex(Pair.Left);
        ExistingLocal[I]=Pose.GetComponentSpaceTransform(Pair.Left).GetRelativeTransform(Pose.GetComponentSpaceTransform(Parent));
    }
    auto Upper=Pose.GetComponentSpaceTransform(U),Lower=Pose.GetComponentSpaceTransform(E),Hand=Pose.GetComponentSpaceTransform(W);
    FTransform FixedHand=Hand;
    // Preserve this pistol's native palm orientation instead of retaining a
    // wrist correction produced by the old independent left-arm roll solve.
    FixedHand.SetRotation(FQuat::Slerp(Hand.GetRotation(),NativeWrist,Weight).GetNormalized());
    const double L1=FVector::Distance(Upper.GetLocation(),Lower.GetLocation()),L2=FVector::Distance(Lower.GetLocation(),Hand.GetLocation());
    const FVector SourceUpper=(RightPistolCarryInTorso[UpperIndex]*Torso).GetLocation();
    const FVector SourceElbow=(RightPistolCarryInTorso[ElbowIndex]*Torso).GetLocation();
    const FVector MirrorPole=Upper.GetLocation()+ReflectVector(SourceElbow-SourceUpper);
    const FVector Pole=FMath::Lerp(Lower.GetLocation(),MirrorPole,Weight);
    Upper.SetRotation(FQuat::Slerp(Upper.GetRotation(),Mirrored[UpperIndex],Weight).GetNormalized());
    Lower.SetRotation(FQuat::Slerp(Lower.GetRotation(),Mirrored[ElbowIndex],Weight).GetNormalized());
    // Seed segment directions from their own native local binds before IK.
    // The solver then changes swing only, preserving the mirrored axial roll.
    const auto& Ref=Bones.GetReferenceSkeleton().GetRefBonePose();
    const FVector UpperAxis=Ref[Bones.MakeMeshPoseIndex(E).GetInt()].GetLocation().GetSafeNormal();
    const FVector LowerAxis=Ref[Bones.MakeMeshPoseIndex(W).GetInt()].GetLocation().GetSafeNormal();
    Lower.SetLocation(Upper.GetLocation()+Upper.GetRotation().RotateVector(UpperAxis)*L1);
    Hand.SetLocation(Lower.GetLocation()+Lower.GetRotation().RotateVector(LowerAxis)*L2);
    AnimationCore::SolveTwoBoneIK(Upper,Lower,Hand,Pole,FixedHand.GetLocation(),L1,L2,false,1.,1.);
    Hand.SetRotation(FixedHand.GetRotation());
    TArray<FBoneTransform,TInlineAllocator<3>> Main;
    Main.Emplace(U,Upper);Main.Emplace(E,Lower);Main.Emplace(W,Hand);Pose.LocalBlendCSBoneTransforms(Main,1.f);
    TArray<FBoneTransform,TInlineAllocator<64>> Helpers;
    for(int32 I=0;I<PistolArmMirror.Num();++I)
    {
        const auto& Pair=PistolArmMirror[I];
        if(Pair.Parent==INDEX_NONE||Pair.Left==U||Pair.Left==E||Pair.Left==W)continue;
        const int32 MeshBone=Bones.MakeMeshPoseIndex(Pair.Left).GetInt();
        if(!Bones.GetReferenceSkeleton().BoneIsChildOf(MeshBone,Bones.MakeMeshPoseIndex(U).GetInt()))continue;
        auto Local=ExistingLocal[I];
        const FQuat MirrorLocal=(Mirrored[Pair.Parent].Inverse()*Mirrored[I]).GetNormalized();
        Local.SetRotation(FQuat::Slerp(Local.GetRotation(),MirrorLocal,Weight).GetNormalized());
        const auto Parent=Bones.GetParentBoneIndex(Pair.Left);
        const auto* Changed=Helpers.FindByPredicate([&](const FBoneTransform& T){return T.BoneIndex==Parent;});
        Helpers.Emplace(Pair.Left,Local*(Changed?Changed->Transform:Pose.GetComponentSpaceTransform(Parent)));
    }
    if(!Helpers.IsEmpty())Pose.LocalBlendCSBoneTransforms(Helpers,1.f);
    LastHands[1]=Pose.GetComponentSpaceTransform(W);
}

void FControls::FitSinglePistolReload(FCSPose<FCompactPose>& Pose,FTransform (&Targets)[2],int32 Primary)
{
    const auto Torso=Pose.GetComponentSpaceTransform(Spine.GetCompactPoseIndex(Pose.GetPose().GetBoneContainer()));
    const FQuat Frame=(Torso.GetRotation()*PistolTorsoBind.Inverse()).GetNormalized();
    const FVector Forward=Frame.RotateVector(FVector::RightVector);
    const int32 Support=1-Primary;
    const FTransform Relation=Primary==1?RightGrip:LeftGrip;
    const FVector Span=Targets[Support].GetLocation()-Targets[Primary].GetLocation();
    const double Depth=FVector::DotProduct(Span,Forward);
    const double Radius=Span.Size();
    // The FPS pocket reach sweeps back through the torso when transplanted.
    // Swing the complete contact group until its backward span fits in front
    // of the body; wrist spacing, magazine contacts and source time stay intact.
    const double FittedDepth=FMath::Clamp(Depth,-8.*PoseScale.Y,18.*PoseScale.Y);
    if(!FMath::IsNearlyEqual(Depth,FittedDepth)&&Radius>UE_SMALL_NUMBER)
    {
        FVector Across=Span-Forward*Depth;
        if(!Across.Normalize())Across=Frame.RotateVector(FVector(Support==0?-1:1,0,-1).GetSafeNormal());
        const FVector Desired=Across*FMath::Sqrt(FMath::Max(0.,Radius*Radius-FittedDepth*FittedDepth))+Forward*FittedDepth;
        const FQuat Swing=FQuat::FindBetweenNormals(Span/Radius,Desired.GetSafeNormal());
        const double Angle=Swing.GetAngle(),Limit=FMath::DegreesToRadians(55.);
        const FQuat Rotation=FQuat::Slerp(FQuat::Identity,Swing,Angle>Limit?Limit/Angle:1.).GetNormalized();
        Targets[Primary].SetRotation((Rotation*Targets[Primary].GetRotation()).GetNormalized());
        Targets[Support]=Relation*Targets[Primary];
    }
    // Jason's torso is in front of spine_03. Reserve the palm/forearm thickness,
    // then fit BOTH arm reaches with this half-space constraint still active.
    const FVector Plane=Torso.GetLocation()+Forward*(26.f*PoseScale.Y);
    float Shift=FMath::Max(float(FVector::DotProduct(Plane-Targets[0].GetLocation(),Forward)),
        float(FVector::DotProduct(Plane-Targets[1].GetLocation(),Forward)));
    // A long revolver/foregrip can cross the chest even with both wrists clear.
    // Include its actual muzzle and attachment corners in the same rigid fit.
    const FVector GunPlane=Torso.GetLocation()+Forward*(16.f*PoseScale.Y);
    for(const FVector& Point:PistolClearanceInHand[Primary])
        Shift=FMath::Max(Shift,float(FVector::DotProduct(GunPlane-Targets[Primary].TransformPosition(Point),Forward)));
    FitHandPair(Pose,Targets,Forward,Shift,true);
    const auto& Bones=Pose.GetPose().GetBoneContainer();
    const auto& Ref=Bones.GetReferenceSkeleton().GetRefBonePose();
    const FQuat Original=Targets[Primary].GetRotation();
    const float Progress=Primary==1?State.LeftHand.Progress:State.ActionProgress;
    const float Envelope=Ease(Progress/.08f)*Ease((1.f-Progress)/.12f)*Ease(float((50.*PoseScale.Y-Radius)/(20.*PoseScale.Y)));
    for(int32 Pass=0;Pass<8&&Envelope>ZERO_ANIMWEIGHT_THRESH;++Pass)
    {
        FQuat Corrections[2];
        for(int32 Side=0;Side<2;++Side)
        {
            const auto W=Hands[Side].GetCompactPoseIndex(Bones);
            const auto& HandRef=Ref[Bones.MakeMeshPoseIndex(W).GetInt()];
            const FVector Expected=(Targets[Side].GetRotation()*HandRef.GetRotation().Inverse()).RotateVector(HandRef.GetLocation().GetSafeNormal());
            const FVector Actual=(Targets[Side].GetLocation()-SinglePistolElbow(Pose,Targets[Side],Side,true)).GetSafeNormal();
            Corrections[Side]=FQuat::FindBetweenNormals(Expected,Actual);
        }
        const FQuat Step=FQuat::Slerp(FQuat::Identity,FQuat::Slerp(Corrections[Primary],Corrections[Support],.6),.6*Envelope).GetNormalized();
        FQuat Rotation=(Step*Targets[Primary].GetRotation()).GetNormalized();
        const double Angle=Original.AngularDistance(Rotation),Limit=FMath::DegreesToRadians(80.)*Envelope;
        if(Angle>Limit)Rotation=FQuat::Slerp(Original,Rotation,Limit/Angle).GetNormalized();
        const FVector Center=(Targets[0].GetLocation()+Targets[1].GetLocation())*.5;
        const FQuat GroupDelta=Rotation*Targets[Primary].GetRotation().Inverse();
        Targets[Primary].SetLocation(Center+GroupDelta.RotateVector(Targets[Primary].GetLocation()-Center));
        Targets[Primary].SetRotation(Rotation);Targets[Support]=Relation*Targets[Primary];
        const FVector WorkingSpan=Targets[Support].GetLocation()-Targets[Primary].GetLocation();
        const double WorkingDepth=FVector::DotProduct(WorkingSpan,Forward),WorkingRadius=WorkingSpan.Size();
        const double BoundedDepth=FMath::Clamp(WorkingDepth,-8.*PoseScale.Y,18.*PoseScale.Y);
        if(WorkingRadius>UE_SMALL_NUMBER&&!FMath::IsNearlyEqual(WorkingDepth,BoundedDepth))
        {
            const FVector Across=FVector::VectorPlaneProject(WorkingSpan,Forward).GetSafeNormal();
            const FVector Fitted=Across*FMath::Sqrt(FMath::Max(0.,WorkingRadius*WorkingRadius-BoundedDepth*BoundedDepth))+Forward*BoundedDepth;
            const FQuat Swing=FQuat::FindBetweenNormals(WorkingSpan/WorkingRadius,Fitted.GetSafeNormal());
            Targets[Primary].SetRotation((Swing*Targets[Primary].GetRotation()).GetNormalized());
            Targets[Support]=Relation*Targets[Primary];
        }
        FitSinglePistolCarry(Pose,Targets,Primary);
    }
}

void FControls::FitSinglePistolCarry(FCSPose<FCompactPose>& Pose,FTransform (&Targets)[2],int32 Primary)
{
    const auto Torso=Pose.GetComponentSpaceTransform(Spine.GetCompactPoseIndex(Pose.GetPose().GetBoneContainer()));
    const FVector Forward=(Torso.GetRotation()*PistolTorsoBind.Inverse()).RotateVector(FVector::RightVector);
    float Shift=0.f;
    for(const auto& Hand:Targets)
        Shift=FMath::Max(Shift,float((FPSBodyPistolMotion::IsSingleReload(State)?26.:24.)*PoseScale.Y-FVector::DotProduct(Hand.GetLocation()-Torso.GetLocation(),Forward)));
    for(const FVector& Point:PistolClearanceInHand[Primary])
        Shift=FMath::Max(Shift,float(16.*PoseScale.Y-FVector::DotProduct(Targets[Primary].TransformPosition(Point)-Torso.GetLocation(),Forward)));
    FitHandPair(Pose,Targets,Forward,Shift,true);
}

void FControls::FitLeftSinglePistol(FCSPose<FCompactPose>& Pose,FTransform (&Targets)[2])
{
    const auto& Bones=Pose.GetPose().GetBoneContainer();
    const auto& Reference=Bones.GetReferenceSkeleton().GetRefBonePose();
    const bool Reload=FPSBodyPistolMotion::IsSingleReload(State);
    Targets[0]=RightGrip*Targets[1];
    if(Reload)FitSinglePistolReload(Pose,Targets,1);
    else FitSinglePistolCarry(Pose,Targets,1);

    for(const int32 Side:{1,0})
    {
        FitSinglePistolArm(Pose,Targets[Side],Side,Reload);
        if(Side==1)Targets[0]=RightGrip*Pose.GetComponentSpaceTransform(Hands[Side].GetCompactPoseIndex(Bones));
    }
}

// Preserve the source chain's roll and corrective locals. The elbow is selected
// on the native two-bone circle; a far-forward fixed pole used to lift the
// loading elbow and leave the wrist bent against an otherwise correct contact.
FVector FControls::SinglePistolElbow(FCSPose<FCompactPose>& Pose,const FTransform& Target,int32 Side,bool Reload) const
{
    const auto& Bones=Pose.GetPose().GetBoneContainer();
    const auto& Reference=Bones.GetReferenceSkeleton().GetRefBonePose();
    const auto Wrist=Hands[Side].GetCompactPoseIndex(Bones);
    const auto Elbow=Bones.GetParentBoneIndex(Wrist),Shoulder=Bones.GetParentBoneIndex(Elbow);
    const auto SourceLower=Pose.GetComponentSpaceTransform(Elbow);
    const auto SourceWrist=Pose.GetComponentSpaceTransform(Wrist);
    const auto Torso=Pose.GetComponentSpaceTransform(Spine.GetCompactPoseIndex(Bones));
    const FQuat Frame=(Torso.GetRotation()*PistolTorsoBind.Inverse()).GetNormalized();
    const FVector Forward=Frame.RotateVector(FVector::RightVector);
    const FVector Origin=Pose.GetComponentSpaceTransform(Shoulder).GetLocation();
    const double L1=FVector::Distance(Origin,SourceLower.GetLocation());
    const double L2=FVector::Distance(SourceLower.GetLocation(),SourceWrist.GetLocation());
    const FVector Axis=(Target.GetLocation()-Origin).GetSafeNormal();
    const double D=FMath::Clamp(FVector::Distance(Origin,Target.GetLocation()),FMath::Abs(L1-L2)+.01,L1+L2-.01);
    const double Along=(L1*L1-L2*L2+D*D)/(2.*D);
    const double Radius=FMath::Sqrt(FMath::Max(0.,L1*L1-Along*Along));
    const FVector Center=Origin+Axis*Along;
    const auto& HandRef=Reference[Bones.MakeMeshPoseIndex(Wrist).GetInt()];
    FVector Bend=FVector::VectorPlaneProject(SourceLower.GetLocation()-Center,Axis).GetSafeNormal();
    if(Reload)Bend=FVector::VectorPlaneProject(Frame.RotateVector(FVector(Side==0?-30.:30.,20.,-35.)*PoseScale),Axis).GetSafeNormal();
    const FVector Normals[2]={Frame.RotateVector(FVector(Side==0?-1.:1.,0,0)),Forward};
    const double Clearance[2]={12.*PoseScale.X,18.*PoseScale.Y};
    TArray<FVector,TInlineAllocator<5>> Candidates;Candidates.Add(Bend);
    for(int32 I=0;I<2&&Radius>UE_SMALL_NUMBER;++I)
    {
        FVector N=FVector::VectorPlaneProject(Normals[I],Axis);const double Size=N.Size();
        if(Size<=UE_SMALL_NUMBER)continue;N/=Size;
        const double Min=FMath::Clamp((Clearance[I]-FVector::DotProduct(Center-Torso.GetLocation(),Normals[I]))/(Radius*Size),-1.,1.);
        const FVector Across=FVector::CrossProduct(Axis,N)*FMath::Sqrt(FMath::Max(0.,1.-Min*Min));
        Candidates.Add(N*Min+Across);Candidates.Add(N*Min-Across);
    }
    FVector Best=Bend;double BestLoss=DBL_MAX,BestScore=-DBL_MAX;
    for(const FVector& Candidate:Candidates)
    {
        const FVector Point=Center+Candidate*Radius-Torso.GetLocation();double Loss=0.;
        for(int32 I=0;I<2;++I)Loss+=(Reload&&I==1?1000.:1.)*FMath::Square(FMath::Max(0.,Clearance[I]-FVector::DotProduct(Point,Normals[I])));
        const double Score=FVector::DotProduct(Candidate,Bend);
        if(Loss<BestLoss-1.e-5||(FMath::Abs(Loss-BestLoss)<1.e-5&&Score>BestScore))
        {Best=Candidate;BestLoss=Loss;BestScore=Score;}
    }
    return Center+Best*Radius;
}

void FControls::FitSinglePistolArm(FCSPose<FCompactPose>& Pose,const FTransform& Target,int32 Side,bool Reload,const FVector* AuthoredPole)
{
    const auto& Bones=Pose.GetPose().GetBoneContainer();
    const auto& Reference=Bones.GetReferenceSkeleton().GetRefBonePose();
    const auto Wrist=Hands[Side].GetCompactPoseIndex(Bones);
    const auto Elbow=Bones.GetParentBoneIndex(Wrist);
    const auto SourceLower=Pose.GetComponentSpaceTransform(Elbow);
    const auto SourceWrist=Pose.GetComponentSpaceTransform(Wrist);
    const FQuat WristInLower=(SourceLower.GetRotation().Inverse()*SourceWrist.GetRotation()).GetNormalized();
    Solve(Pose,Hands[Side],Target,AuthoredPole?*AuthoredPole:SinglePistolElbow(Pose,Target,Side,Reload),1.f);
    if(Reload){FitStaffArm(Pose,Side,false,true);return;}
    // Transfer only the palm's extra pronation along the forearm. Keep
    // the donor's wrist bend and upper-arm twist instead of replacing
    // every helper with its reference pose after moving the hand.
    auto Lower=Pose.GetComponentSpaceTransform(Elbow);
    const auto Hand=Pose.GetComponentSpaceTransform(Wrist);
    const FVector ForearmAxis=(Hand.GetLocation()-Lower.GetLocation()).GetSafeNormal();
    const FQuat DesiredLower=(Hand.GetRotation()*WristInLower.Inverse()).GetNormalized();
    FQuat Difference=(DesiredLower*Lower.GetRotation().Inverse()).GetNormalized();
    if(Difference.W<0.)Difference=Difference*-1.;
    const double Roll=FMath::Clamp(2.*FMath::Atan2(FVector::DotProduct(FVector(Difference.X,Difference.Y,Difference.Z),ForearmAxis),Difference.W),
        FMath::DegreesToRadians(-85.),FMath::DegreesToRadians(85.));
    const auto& HandReference=Reference[Bones.MakeMeshPoseIndex(Wrist).GetInt()];
    const FVector LocalAxis=Lower.GetRotation().UnrotateVector(ForearmAxis);
    TArray<FBoneTransform,TInlineAllocator<16>> HelperLocals;
    for(int32 I=0;I<LibraryArmBones.Num();++I)
    {
        const FCompactPoseBoneIndex Bone(I);
        if(Bone==Wrist||!(LibraryArmBones[I]&(1<<Side))||Bones.GetParentBoneIndex(Bone)!=Elbow)continue;
        auto Local=Pose.GetComponentSpaceTransform(Bone).GetRelativeTransform(Lower);
        const auto& HelperReference=Reference[Bones.MakeMeshPoseIndex(Bone).GetInt()];
        const double Station=FMath::Clamp(FVector::DotProduct(HelperReference.GetLocation(),HandReference.GetLocation().GetSafeNormal())/
        FMath::Max(HandReference.GetLocation().Size(),UE_SMALL_NUMBER),0.,1.);
        const FQuat Unroll(LocalAxis,-Roll*(1.-Station));
        Local.SetRotation((Unroll*Local.GetRotation()).GetNormalized());
        Local.SetLocation(Unroll.RotateVector(Local.GetLocation()));
        HelperLocals.Emplace(Bone,Local);
    }
    Lower.SetRotation((FQuat(ForearmAxis,Roll)*Lower.GetRotation()).GetNormalized());
    TArray<FBoneTransform,TInlineAllocator<16>> Changes;
    Changes.Emplace(Elbow,Lower);Changes.Emplace(Wrist,Hand);
    for(const auto& Helper:HelperLocals)Changes.Emplace(Helper.BoneIndex,Helper.Transform*Lower);
    Changes.Sort([](const FBoneTransform& A,const FBoneTransform& B){return A.BoneIndex<B.BoneIndex;});
    Pose.LocalBlendCSBoneTransforms(Changes,1.f);

}

void FControls::FitDualPistolFinalClearance(FCSPose<FCompactPose>& Pose,int32 Side)
{
    if(ConsumeWeight>ZERO_ANIMWEIGHT_THRESH&&(Side==1||bConsumeTwoHands))return;
    const auto& Bones=Pose.GetPose().GetBoneContainer();
    const auto W=Hands[Side].GetCompactPoseIndex(Bones),E=Bones.GetParentBoneIndex(W),S=Bones.GetParentBoneIndex(E);
    const auto Torso=Pose.GetComponentSpaceTransform(Spine.GetCompactPoseIndex(Bones));
    const FVector Forward=(Torso.GetRotation()*PistolTorsoBind.Inverse()).RotateVector(FVector::RightVector);
    // Natural wrist fitting rotates the held gun as a group. Evaluate its
    // current attachment envelope AFTER that fit (not the earlier target).
    // Small bounded refinements only run when the final gun needs more room.
    for(int32 Pass=0;Pass<3;++Pass)
    {
        auto Target=Pose.GetComponentSpaceTransform(W);double Shift=0.;
        for(const FVector& Point:PistolClearanceInHand[Side])
            Shift=FMath::Max(Shift,17.*PoseScale.Y-FVector::DotProduct(Target.TransformPosition(Point)-Torso.GetLocation(),Forward));
        if(Shift<=.05)break;
        const FVector Shoulder=Pose.GetComponentSpaceTransform(S).GetLocation();
        const FVector Elbow=Pose.GetComponentSpaceTransform(E).GetLocation();
        const double Length=(FVector::Dist(Shoulder,Elbow)+FVector::Dist(Elbow,Target.GetLocation()))*.94;
        const FVector Reach=Target.GetLocation()-Shoulder;
        const double Depth=FMath::Min(FVector::DotProduct(Reach,Forward)+Shift,Length*.98);
        const FVector Across=FVector::VectorPlaneProject(Reach,Forward).GetClampedToMaxSize(FMath::Sqrt(FMath::Max(0.,Length*Length-Depth*Depth)));
        Target.SetLocation(Shoulder+Forward*Depth+Across);
        Solve(Pose,Hands[Side],Target,Elbow,1.f);
        FitStaffArm(Pose,Side,false,true);
    }
}

FTransform FControls::DualPistolHandTarget(FCSPose<FCompactPose>& Pose,int32 Side) const
{
    const auto& Bones=Pose.GetPose().GetBoneContainer();
    const auto W=Hands[Side].GetCompactPoseIndex(Bones),E=Bones.GetParentBoneIndex(W),S=Bones.GetParentBoneIndex(E);
    const auto Torso=Pose.GetComponentSpaceTransform(Spine.GetCompactPoseIndex(Bones));
    const FVector Shoulder=Pose.GetComponentSpaceTransform(S).GetLocation();
    const FQuat BodyFrame=(Torso.GetRotation()*PistolTorsoBind.Inverse()).GetNormalized();
    const FQuat ReadyFrame=(Torso.GetRotation()*DualReadyTorso.GetRotation().Inverse()).GetNormalized();
    const auto& Hand=Side==0?State.RightHand:State.LeftHand;
    const bool Gesture=(ActionWristMask&(1<<Side))&&FPSBodyPistolMotion::UsesRelativeAction(State,Side);
    const float ActionWeight=Gesture?Ease(Hand.Progress/.08f)*Ease((1.f-Hand.Progress)/.12f):0.f;
    const float Run=Sprint*(1.f-ActionWeight);
    const float LookPitch=FMath::Clamp(State.AimPitch,-50.f,55.f)*(1.f-Run);
    const FQuat LookYaw(FVector::UpVector,FMath::DegreesToRadians(FMath::Clamp(State.AimYaw,-35.f,35.f)*(1.f-Run)));
    const FQuat AimFrame=LookYaw*FQuat(FVector::ForwardVector,FMath::DegreesToRadians(LookPitch));
    // Actual complete stance supplies the wrist path. The constant native palm
    // calibration adapts it to this gun without borrowing the other hand.
    // Counter the torso's walking/crouch lean in the held group. Otherwise a
    // source torso dip lowers the wrists a second time, even at level aim,
    // forcing the elbows onto the high branch and turning the gun at the wrist.
    // Keep the authored shoulder-relative arm motion and current shoulder point.
    const FQuat StanceDelta=(ReadyFrame.Inverse()*DualStanceHands[Side].GetRotation()*DualReadyHands[Side].GetRotation().Inverse()).GetNormalized();
    const FVector StanceLocation=Shoulder+ReadyFrame.UnrotateVector(DualStanceHands[Side].GetLocation()-Shoulder);
    FTransform Target((StanceDelta*IndependentPistolRotation[Side]).GetNormalized(),StanceLocation);
    if(Gesture)
    {
        const FTransform Ready((ReadyFrame*IndependentPistolRotation[Side]).GetNormalized(),
            Shoulder+ReadyFrame.RotateVector(DualReadyHands[Side].GetLocation()-DualReadyShoulders[Side].GetLocation()));
        FTransform Anchor;Anchor.Blend(Target,Ready,ActionWeight);
        FTransform Relative=ActionHands[Side];Relative.SetLocation(Relative.GetLocation()*PoseScale);
        if(Hand.bReloading||Hand.bEquipping)
        {
            // FPS throws leave the frame and reach below the full-body elbow.
            // Retarget their trajectory to a chest-height one-hand workspace;
            // the independent gun mechanisms still consume the exact source time.
            Relative.SetLocation(Relative.GetLocation()*.35f);
            FQuat GestureRotation=Relative.GetRotation();if(GestureRotation.W<0.)GestureRotation=GestureRotation*-1.;
            const double Angle=GestureRotation.GetAngle(),Limit=FMath::DegreesToRadians(45.);
            Relative.SetRotation(FQuat::Slerp(FQuat::Identity,GestureRotation,Angle>Limit?Limit/Angle:1.).GetNormalized());
            if(Hand.bEquipping)
            {
                // A 25 ms FPS entrance can move the full-body wrist several
                // centimetres in one frame. Raise/settle this arm inside the
                // equip clip, while its mechanisms retain their source clock.
                const float EquipWeight=Ease(Hand.Progress/.18f)*Ease((1.f-Hand.Progress)/.18f);
                Relative.SetLocation(Relative.GetLocation()*EquipWeight);
                Relative.SetRotation(FQuat::Slerp(FQuat::Identity,Relative.GetRotation(),EquipWeight).GetNormalized());
            }
        }
        Target=Relative*Anchor;
    }
    // Pitching the whole arm around its shoulder put low-look wrists against
    // the abdomen. No elbow pole could then keep the arm both lowered and clear.
    // Stage the carry wrist forward while lowering it more gently; the gun and
    // palm still follow the full aim rotation. Reload/equip keep their own path.
    const FQuat ArmAim=Gesture?AimFrame:LookYaw*FQuat(FVector::ForwardVector,FMath::DegreesToRadians(LookPitch<0.f?LookPitch*.5f:LookPitch));
    Target.SetLocation(Shoulder+ArmAim.RotateVector(Target.GetLocation()-Shoulder));
    if(!Gesture)
    {
        Target.AddToTranslation(LookYaw.RotateVector(FVector(0,8.f*Ease(-LookPitch/50.f),0)*PoseScale));
        // Turning inwards must not undo the low-look working space. Keep the
        // authored carry depth as the lower-look floor, smoothly introduced.
        const FVector CarryForward=BodyFrame.RotateVector(FVector::RightVector);
        const double MissingDepth=FMath::Max(0.,FVector::DotProduct(StanceLocation-Target.GetLocation(),CarryForward));
        Target.AddToTranslation(CarryForward*MissingDepth*Ease(-LookPitch/20.f));
    }
    Target.SetRotation((AimFrame*Target.GetRotation()).GetNormalized());
    if(!Gesture)
    {
        const float Age=FMath::Max(0.f,Clock-Hand.LastShotAt);
        const float Kick=(1.f-FMath::SmoothStep(.025f,.16f,Age))*FMath::SmoothStep(0.f,.012f,Age);
        Target.AddToTranslation(AimFrame.RotateVector(FVector(0,-3.f,1.5f)*PoseScale)*Kick);
        Target.SetRotation((AimFrame*FQuat(FVector::ForwardVector,.09f*Kick)*AimFrame.Inverse()*Target.GetRotation()).GetNormalized());
    }
    // Source FPS equip/reload throws must stay on this side of the body.
    // Use a single native reach sphere with torso-space front/side boundaries,
    // including the owning gun's current muzzle and attachment bounds.
    const float Sign=Side==0?-1.f:1.f;
    FVector Reach=BodyFrame.UnrotateVector(Target.GetLocation()-Shoulder);
    if(Hand.bReloading||Hand.bEquipping)Reach.Z=FMath::Clamp(Reach.Z,-22.*PoseScale.Z,16.*PoseScale.Z);
    const FVector Chest=BodyFrame.UnrotateVector(Torso.GetLocation()-Shoulder);
    double Front=Chest.Y+22.*PoseScale.Y;
    double Outside=Sign*Chest.X+13.*PoseScale.X;
    const FVector Forward=BodyFrame.RotateVector(FVector::RightVector);
    const FVector Lateral=BodyFrame.RotateVector(FVector(Sign,0,0));
    for(const FVector& Point:PistolClearanceInHand[Side])
    {
        const FVector Offset=Target.GetRotation().RotateVector(Point*Target.GetScale3D());
        Front=FMath::Max(Front,Chest.Y+15.*PoseScale.Y-FVector::DotProduct(Offset,Forward));
        Outside=FMath::Max(Outside,Sign*Chest.X+6.*PoseScale.X-FVector::DotProduct(Offset,Lateral));
    }
    const double Length=(FVector::Dist(Shoulder,Pose.GetComponentSpaceTransform(E).GetLocation())+
        FVector::Dist(Pose.GetComponentSpaceTransform(E).GetLocation(),Pose.GetComponentSpaceTransform(W).GetLocation()))*.94;
    // A bound may extend outside the feasible sphere. Keep the front half-space
    // and use the nearest feasible side/height rather than an inward fallback.
    Front=FMath::Clamp(Front,0.,Length*.84);
    Outside=FMath::Clamp(Outside,0.,FMath::Sqrt(FMath::Max(0.,Length*Length-Front*Front))*.85);
    Reach.X=Sign*FMath::Max(Sign*Reach.X,Outside);
    Reach.Y=FMath::Max(Reach.Y,Front);
    const FVector Wanted=Reach;
    Reach=Reach.GetClampedToMaxSize(Length);
    // Continuous projection onto the native reach sphere and the two body
    // half-spaces. Resetting X to Outside at the sphere boundary made a moving
    // drum attachment snap the wrist sideways by more than ten centimetres.
    if(Sign*Reach.X<Outside)
    {
        Reach.X=Sign*Outside;
        const FVector YZ=FVector(0,Wanted.Y,Wanted.Z).GetClampedToMaxSize(FMath::Sqrt(FMath::Max(0.,Length*Length-Outside*Outside)));
        Reach.Y=FMath::Max(YZ.Y,Front);Reach.Z=YZ.Z;
    }
    else if(Reach.Y<Front)
    {
        Reach.Y=Front;
        const FVector XZ=FVector(Wanted.X,0,Wanted.Z).GetClampedToMaxSize(FMath::Sqrt(FMath::Max(0.,Length*Length-Front*Front)));
        Reach.X=Sign*FMath::Max(Sign*XZ.X,Outside);Reach.Z=XZ.Z;
    }
    const double Vertical=FMath::Sqrt(FMath::Max(0.,Length*Length-Reach.X*Reach.X-Reach.Y*Reach.Y));
    Reach.Z=FMath::Clamp(Reach.Z,-Vertical,Vertical);
    Target.SetLocation(Shoulder+BodyFrame.RotateVector(Reach));
    if(State.ConsumeHands&(1<<Side))
    {
        const FTransform Lowered((FQuat(FVector::ForwardVector,-.65f)*IndependentPistolRotation[Side]).GetNormalized(),
            Shoulder+FVector(Sign*10.f,14.f,-52.f)*PoseScale);
        FTransform Mixed;Mixed.Blend(Target,Lowered,FMath::Clamp(State.ConsumeStowWeight,0.f,1.f));Target=Mixed;
    }
    return Target;
}

FTransform FControls::PistolHandTarget(FCSPose<FCompactPose>& Pose,int32 Side) const
{
    if(State.bDual&&bDualPistolStandards)return DualPistolHandTarget(Pose,Side);
    const auto& Bones=Pose.GetPose().GetBoneContainer();
    const auto Wrist=Hands[Side].GetCompactPoseIndex(Bones),Elbow=Bones.GetParentBoneIndex(Wrist),Upper=Bones.GetParentBoneIndex(Elbow);
    const FVector Shoulder=Pose.GetComponentSpaceTransform(Upper).GetLocation();
    const auto& Hand=Side==0?State.RightHand:State.LeftHand;
    const float Sign=Side==0?-1.f:1.f;
    const bool Gesture=(ActionWristMask&(1<<Side))&&FPSBodyPistolMotion::UsesRelativeAction(State,Side);
    const float Run=Gesture?0.f:Sprint;
    // Aim rotates a bounded shoulder-relative group. It cannot pin either
    // wrist to the eye or inherit the single-pistol support-hand orientation.
    const FQuat AimFrame=FQuat(FVector::UpVector,FMath::DegreesToRadians(FMath::Clamp(State.AimYaw,-35.f,35.f)*(1.f-Run)))*
        FQuat(FVector::ForwardVector,FMath::DegreesToRadians(FMath::Clamp(State.AimPitch,-50.f,55.f)*(1.f-Run)));
    FVector Offset=FMath::Lerp(FVector(Sign*6.f,34.f,-12.f),FVector(Sign*10.f,23.f,-25.f),Run);
    if(!Gesture)
    {
        const float Phase=GaitPhase*2.f*PI+(Side==1?PI:0.f);
        const float Walk=GaitWeight*(bFalling?0.f:1.f);
        Offset.Y+=FMath::Sin(Phase)*FMath::Lerp(1.2f,4.f,Run)*Walk;
        Offset.Z+=FMath::Cos(Phase)*FMath::Lerp(.7f,2.f,Run)*Walk;
    }
    FQuat Rotation=(AimFrame*FQuat(FVector::ForwardVector,-.24f*Run)*IndependentPistolRotation[Side]).GetNormalized();
    FTransform Target(Rotation,Shoulder+AimFrame.RotateVector(Offset*PoseScale));
    if(Gesture)
    {
        FTransform Relative=ActionHands[Side];Relative.SetLocation(Relative.GetLocation()*PoseScale);
        Target=Relative*Target;
    }
    else
    {
        const float ShotAt=FPSBodyPistolMotion::IsRightSingle(State)?State.LastShotAt:Hand.LastShotAt;
        const float Age=FMath::Max(0.f,Clock-ShotAt);
        const float Kick=(1.f-FMath::SmoothStep(.025f,.16f,Age))*FMath::SmoothStep(0.f,.012f,Age);
        Target.AddToTranslation(AimFrame.RotateVector(FVector(0,-4.f,2.f)*PoseScale)*Kick);
        Target.SetRotation((AimFrame*FQuat(FVector::ForwardVector,.10f*Kick)*AimFrame.Inverse()*Target.GetRotation()).GetNormalized());
    }
    // Retain each gun on its own side of the chest, including long FPS reload
    // throws. Native joint fitting below reserves elbow bend and wrist volume.
    FVector Reach=Target.GetLocation()-Shoulder;
    Reach.X=Sign*FMath::Clamp(Sign*Reach.X,-2.*PoseScale.X,32.*PoseScale.X);
    Reach.Y=FMath::Clamp(Reach.Y,8.*PoseScale.Y,57.*PoseScale.Y);
    Reach.Z=FMath::Clamp(Reach.Z,-58.*PoseScale.Z,45.*PoseScale.Z);
    Target.SetLocation(Shoulder+Reach);
    if(State.ConsumeHands&(1<<Side))
    {
        // Lower and return on the consumable's real stow envelope. This pose
        // stays shoulder-relative even while the player turns the camera.
        const FTransform Lowered((FQuat(FVector::ForwardVector,-.65f)*IndependentPistolRotation[Side]).GetNormalized(),
            Shoulder+FVector(Sign*10.f,14.f,-52.f)*PoseScale);
        FTransform Blended;Blended.Blend(Target,Lowered,FMath::Clamp(State.ConsumeStowWeight,0.f,1.f));Target=Blended;
    }
    return Target;
}
