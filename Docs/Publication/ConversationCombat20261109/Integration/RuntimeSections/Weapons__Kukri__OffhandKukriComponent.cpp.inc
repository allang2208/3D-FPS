// Integration reference only: preserve shared host declarations and prerequisites.

// Source line 57
void UPistolHatchetArmsMeshComponent::ConfigureCarry()
{
    const auto& Ref=GetSkeletalMeshAsset()->GetRefSkeleton();
    CarryHandInCamera=PistolHatchetCarry::PalmInView(KukriOffhandDraw::Grip().GetRotation());
    Clavicle=Ref.FindBoneIndex(TEXT("clavicle_l"));Upper=Ref.FindBoneIndex(TEXT("upperarm_l"));
    Lower=Ref.FindBoneIndex(TEXT("lowerarm_l"));Hand=Ref.FindBoneIndex(TEXT("hand_l"));
    Twist01=Ref.FindBoneIndex(TEXT("lowerarm_twist_01_l"));Twist02=Ref.FindBoneIndex(TEXT("lowerarm_twist_02_l"));
    CarryBones.Reset();
    if(Hand>=0&&Clavicle>=0&&Upper>=0&&Lower>=0)
        for(int32 I=Clavicle;I<Ref.GetNum();++I)
            if(I==Clavicle||Ref.BoneIsChildOf(I,Clavicle))CarryBones.Add(I);
}

// Source line 70
void UPistolHatchetArmsMeshComponent::FinalizeBoneTransform()
{
    auto& Pose=GetEditableComponentSpaceTransforms();
    const auto* Mesh=GetSkeletalMeshAsset();
    if(bCrossedCarry&&Mesh&&!CarryBones.IsEmpty()&&Pose.Num()==Mesh->GetRefSkeleton().GetNum())
    {
        namespace K=OffhandKukriPose;
        const float A=K::Ease(AimWeight);
        // Keep the accepted crossed-arm shoulder and elbow. A small wrist dip
        // leaves clearance for the newly rotated axe fist beneath the gun hand.
        const FVector Wrist=RightHandInCamera+PistolLeftWristOffset(A)+FVector(0.,0.,-FMath::Lerp(5.f,2.f,A));
        const FVector Shoulder=FMath::Lerp(K::Hip.LeftShoulder,K::Aim.LeftShoulder,A);
        const FVector Pole=FMath::Lerp(K::Hip.LeftPole,K::Aim.LeftPole,A);
        const FQuat ToMesh=GetRelativeRotation().Quaternion().Inverse();
        const auto* Action=CarryWeight<1.f?GetOwner()->FindComponentByClass<UOffhandKukriComponent>():nullptr;
        // The chop already lowers its native wrist. Adding the draw's dip a
        // second time makes the recovery dive and then spring back upward.
        const FVector Arc=Action&&Action->IsHatchetQuickCombat()?FVector::ZeroVector:PistolHatchetDrawMotion::WristArc(CarryWeight);
        const FVector TargetWrist=FMath::Lerp(Pose[Hand].GetLocation(),ToMesh.RotateVector(Wrist),CarryWeight)
            +ToMesh.RotateVector(Arc);
        const FVector TargetShoulder=FMath::Lerp(Pose[Upper].GetLocation(),ToMesh.RotateVector(Shoulder),CarryWeight);
        const FVector TargetPole=FMath::Lerp(Pose[Lower].GetLocation(),ToMesh.RotateVector(Pole),CarryWeight);
        const FQuat TargetHand=FQuat::Slerp(Pose[Hand].GetRotation(),ToMesh*CarryHandInCamera,CarryWeight).GetNormalized();
        const SpellbookPistolArm::FJoints J{Clavicle,Upper,Lower,Hand,Twist01,Twist02};
        // Cross underneath the gun after the catch. Solve the arm along the
        // wrist arc so both native segment lengths survive the whole handoff.
        SpellbookPistolArm::Solve(Mesh->GetRefSkeleton(),Pose,Pose,CarryBones,J,
            TargetShoulder,TargetWrist,TargetPole,TargetHand,0.f,CarryWeight,CarryPose);
        PistolHatchetCarry::FitFingers(Mesh->GetRefSkeleton(),CarryPose,CarryWeight);
        for(const int32 I:CarryBones)Pose[I]=CarryPose[I];
    }
    Super::FinalizeBoneTransform();
}

// Source line 354
void UOffhandKukriComponent::InstallAxeArms()
{
    auto* Skin=Cast<USkeletalMesh>(FSoftObjectPath(KukriRhythm::ArmsMesh).ResolveObject());
    AxeChop=Cast<UAnimSequence>(FSoftObjectPath(HatchetPairRhythm::Attack3KHClip).ResolveObject());
    AxeIdle=Cast<UAnimSequence>(FSoftObjectPath(OffhandAxeQuickMotion::IdlePath).ResolveObject());
    AxeDraw=Cast<UAnimSequence>(FSoftObjectPath(OffhandBladeDraw::Asset(true)).ResolveObject());
    if(!Skin||!AxeIdle||!AxeChop||!AxeDraw)return;
    if(!AxeArms)
    {
        AxeArms=NewObject<UPistolHatchetArmsMeshComponent>(GetOwner(),TEXT("PistolOffhandHatchetArms"));
        GetOwner()->AddInstanceComponent(AxeArms);
        AxeArms->SetupAttachment(Camera.Get());
        AxeArms->SetRelativeRotation(FRotator(0,90,0));
        AxeArms->bLeftHandOnly=true;
        AxeArms->SetOnlyOwnerSee(true);AxeArms->SetCastShadow(false);
        AxeArms->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        AxeArms->SetCanEverAffectNavigation(false);AxeArms->bReceivesDecals=false;
        AxeArms->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        AxeArms->SetVisibility(false);AxeArms->RegisterComponent();
        AxeArms->SetComponentTickEnabled(false);
    }
    AxeArms->SetSkeletalMesh(Skin);
    AxeArms->ConfigureCarry();
    PrepareQuickRift();
    AxeArms->ComponentTags.AddUnique(TEXT("PreloadModularOutfit"));
}

// Source line 381
bool UOffhandKukriComponent::UsesNativeAxe() const
{
    return bEquipped&&bDrawHatchet&&!bUppercut&&AxeArms&&AxeIdle&&AxeChop&&AxeDraw;
}

// Source line 391
FTransform UOffhandKukriComponent::SampleAxeBlade(float Time,bool Striking)
{
    const bool Drawing=!Striking&&DrawTime>=0.f;
    auto* Clip=Striking?AxeChop.Get():Drawing?AxeDraw.Get():AxeIdle.Get();
    AxeArms->CarryWeight=Striking?OffhandAxeQuickMotion::Carry(Time):Drawing?PistolHatchetDrawMotion::Carry(DrawTime):1.f;
    AxeArms->bCrossedCarry=AxeArms->CarryWeight>0.f;
    if(AxeArms->bCrossedCarry)
    {
        if(auto* Player=AxeArms->GetSingleNodeInstance();!Drawing&&Player&&Player->GetCurrentAsset()==AxeDraw)
            AxeArms->CaptureLeftEntry(.14f);
        // The temporary gun evasion must not drag the receiving left fist along.
        AxeArms->RightHandInCamera=Arms->RightHandInCamera-PistolDrawOffset();
        AxeArms->AimWeight=AimWeight;
    }
    const float ClipTime=Striking?Time*OffhandAxeQuickMotion::ClipRate:Drawing?DrawTime:AxeIdleAge;
    OffhandAxeQuickMotion::Sample(*AxeArms,Clip,ClipTime);
    const FTransform Grip=Drawing?OffhandBladeDraw::InHand(true,DrawTime):KukriOffhandDraw::Grip();
    return Grip*AxeArms->GetSocketTransform(TEXT("hand_l"));
}

// Source line 619
void UOffhandKukriComponent::ApplyPistolRightArm(USkeletalMeshComponent& Gun,TArray<FTransform>& Pose)
{
    ApplyNativeReloadEntry(Gun,Pose);
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    const float Weight=PistolFramingWeight();
    if(!bPair||Weight<=UE_SMALL_NUMBER||!Pawn||Pawn->AKMViewmodel.Get()!=&Gun||!Pawn->FirstPersonCamera||!Gun.GetSkeletalMeshAsset())return;
    if(GunMesh.Get()!=Gun.GetSkeletalMeshAsset())CacheGun(Gun);
    if(RightClavicle<0||RightUpper<0||RightLower<0||RightHand<0||Pose.Num()!=RightReference.Num())return;
    const FTransform ToCamera=Gun.GetComponentTransform().GetRelativeTransform(Pawn->FirstPersonCamera->GetComponentTransform());
    const FTransform ToMesh=Pawn->FirstPersonCamera->GetComponentTransform().GetRelativeTransform(Gun.GetComponentTransform());
    for(int32 I=0;I<Pose.Num();++I)RightSource[I]=Pose[I]*ToCamera;
    namespace K=OffhandKukriPose;
    const float A=K::Ease(AimWeight);
    FVector Shoulder=FMath::Lerp(RightSource[RightUpper].GetLocation(),FMath::Lerp(K::Hip.RightShoulder,K::Aim.RightShoulder,A),Weight);
    FVector Pole=FMath::Lerp(RightSource[RightLower].GetLocation(),FMath::Lerp(K::Hip.RightPole,K::Aim.RightPole,A),Weight);
    if(bQuickCombat&&!bStaffQuickCombat)
    {
        const auto Clearance=OffhandQuickClearance::Sample(QuickElapsed/GetQuickCombatLength(),bHatchetQuickCombat);
        const float Support=FMath::Clamp(float(Clearance.Offset.Y)/22.f,0.f,1.f);
        Shoulder+=Clearance.Offset*.12;
        Pole+=Clearance.Offset*.45+FVector(-1,1,-2)*Support;
    }
    const auto& Ref=Gun.GetSkeletalMeshAsset()->GetRefSkeleton();
    const SpellbookPistolArm::FJoints J{RightClavicle,RightUpper,RightLower,RightHand,RightTwist01,RightTwist02};
    SpellbookPistolArm::Solve(Ref,RightReference,RightSource,RightBones,J,Shoulder,RightSource[RightHand].GetLocation(),Pole,
        RightSource[RightHand].GetRotation(),0.f,Weight,RightTarget);
    for(const int32 I:RightBones)
    {
        // The pistol grip, fingers and gun stay exactly as animated; only the
        // shoulder, elbow and arm helpers follow the crossed stance.
        if(I==RightHand||Ref.BoneIsChildOf(I,RightHand))continue;
        Pose[I]=RightTarget[I]*ToMesh;
    }
}
