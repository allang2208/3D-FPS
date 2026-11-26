// Scoped, opt-in review of the actual world pose and fitted gun. No combat,
// saved user profile, render, or network simulation is started by this branch.
const bool KnifeUppercut=FParse::Param(*Params,TEXT("KnifeUppercut"));
for(const FName BodyId:{FName(TEXT("jason")),FName(TEXT("kaitlin"))})
{
    FlushAsyncLoading();
    // Select the published native mesh/clip set directly. This fixture has no
    // character-creation UI and must not invoke profile appearance saving.
    Body->Configuration=Body->BodyConfigurations.FindRef(BodyId);
    Check(BodyId.ToString()+TEXT("/body configuration"),Body->Configuration.IsValid());
    if(!Body->Configuration)continue;
    Body->InitializeBody(false);Body->EquipmentKey.Reset();
    FlushAsyncLoading();
    Check(BodyId.ToString()+TEXT("/body loaded"),Body->GetBodyType()==BodyId);
    SkinProbe=FPistolReloadSkinProbe();SkinProbe.Initialize(Body->GetBodyMesh());
    for(int32 ModelIndex=0;ModelIndex<5;++ModelIndex)
    {
        if(!CaseFilter.IsEmpty()&&CaseFilter!=Variants[ModelIndex].Definition)continue;
        auto Gun=Model->CreateItem(Variants[ModelIndex].Definition),Knife=Model->CreateItem(TEXT("ue_kukri"));
        Gun.Place=Knife.Place=1;Gun.Cell=6;Knife.Cell=8;Gun.Magazine=5;
        Model->Current=Seed;Model->Current.Items={Gun,Knife};Pawn->ApplyColdSteelProfile(Model);
        FlushAsyncLoading();Pawn->WeaponState=EAKMWeaponState::Idle;Pawn->ActiveActionAnimation=nullptr;
        Pawn->DualPistols->InterruptActions();Pawn->bIsAiming=Pawn->bIsSprinting=false;
        Pawn->WeaponADSFactor=Pawn->SprintPoseFactor=0.f;Pawn->UpdateActionPose(0.f);
        auto* Source=Pawn->AKMViewmodel.Get();TickPose(Source);
        Body->DisplayState=Body->SampleLocalState();Body->CaptureEquipment();FlushAsyncLoading();
        const FString Prefix=BodyId.ToString()+TEXT("/")+Variants[ModelIndex].Definition;
        Check(Prefix+TEXT("/pistol and knife bound"),Body->MotionBindings.Num()==2&&Body->BodyAnimation->bOffhandKukriEquipment);
        auto* Clip=Body->BodyAnimation->Clips.FindRef(KnifeUppercut?TEXT("Pistol.KukriUppercut"):TEXT("Pistol.KukriQuickCombat")).Get();
        Check(Prefix+(KnifeUppercut?TEXT("/native uppercut clip"):TEXT("/native thrust clip")),Clip&&Clip->GetSkeleton()==Body->GetBodyMesh()->GetSkeletalMeshAsset()->GetSkeleton());
        if(Body->MotionBindings.Num()!=2||!Clip)continue;
        auto* Weapon=Body->MotionBindings[0].Mesh.Get();
        const auto* Map=Body->MotionMap(Source,TEXT("hand_r"),0);if(!Weapon||!Map)return 2;
        const FTransform NativeHand=Rigid(Source->GetSocketTransform(TEXT("hand_r"),RTS_Component));
        const FTransform NativeRoot=Source->GetSocketTransform(TEXT("WPN_root"),RTS_Component).GetRelativeTransform(NativeHand)*Map->Mount;
        struct FCase {const TCHAR* Name;bool Aim,Crouch;float Pitch,Yaw;};
        const FCase Cases[]={{TEXT("hip"),false,false,0,0},{TEXT("ads"),true,false,0,0},
            {TEXT("up"),true,false,35,20},{TEXT("crouch_down"),true,true,-30,-20}};
        for(const auto& C:Cases)
        {
            auto State=Body->SampleLocalState();State.Action=EFPSBodyAction::None;State.ActionVariant=NAME_None;
            State.bAiming=C.Aim;State.bCrouched=C.Crouch;State.bSprinting=false;State.AimPitch=C.Pitch;State.AimYaw=C.Yaw;
            State.LastShotAt=State.RightHand.LastShotAt=State.LeftHand.LastShotAt=-100.f;
            State.OffhandReloadPhase=0;Body->CaptureMotion(State);
            auto* Anim=Body->BodyAnimation.Get();
            const auto Pose=[&](float Delta)
            {
                Body->DisplayState=State;Body->ApplyMotion(Delta);
                Anim->BodyState=Anim->UpperState=Anim->MotionState=State;Anim->Clock=World->GetTimeSeconds();
                Anim->AimAlpha=State.bAiming?1.f:0.f;Anim->CrouchAlpha=C.Crouch?1.f:0.f;
                Anim->UpperAlpha=Anim->MotionAlpha=Anim->AirAlpha=Anim->SprintAlpha=0.f;Anim->Speed=0.f;
                TickPose(Body->GetBodyMesh(),Delta);Weapon->UpdateComponentToWorld();Weapon->UpdateChildTransforms();
            };
            for(int32 I=0;I<20;++I)Pose(1.f/60.f);
            auto* Blade=Body->MotionBindings[1].Static.Get();if(!Blade)return 2;
            const auto BladePoint=[&](){return Body->GetBodyMesh()->GetComponentTransform().InverseTransformPosition(Blade->GetComponentTransform().TransformPosition(KukriRhythm::BladeTip));};
            const FVector Start=BladePoint();
            double GripError=0.,GripAngle=0.,GunDepth=0.,ArmDepth=0.,MinForward=1.,MaxWrist=0.,Windup=0.;float Reach=0.f;
            int32 WorstArmFrame=0,WorstArmSide=0;FVector WorstArmPoint=FVector::ZeroVector;
            int32 WorstWristFrame=0,WorstWristSide=0;
            double KnifeFingerChange=0.;
            const float Length=KnifeUppercut?OffhandKukriUpper::Length:OffhandKukriStrike::Length;
            const int32 Frames=KnifeUppercut?152:76;
            double Low=Start.Z,High=Start.Z;
            for(int32 Frame=0;Frame<=Frames;++Frame)
            {
                const float T=Length*Frame/Frames;
                State.Action=KnifeUppercut?EFPSBodyAction::HeavyStrike:EFPSBodyAction::Thrust;
                State.ActionVariant=KnifeUppercut?TEXT("OffhandKukriUppercut"):TEXT("OffhandKukriThrust");
                State.bHasActionProgress=true;State.ActionProgress=T/Length;State.ActionProgressRate=0.f;
                State.ActionDuration=Length;State.ContactFraction=(KnifeUppercut?OffhandKukriUpper::ContactStart:OffhandKukriStrike::Contacts[0])/Length;
                State.ReleaseFraction=(KnifeUppercut?OffhandKukriUpper::ContactEnd:.32f)/Length;
                State.bAiming=false;Pose(Length/Frames);
                const FTransform Expected=NativeRoot*Body->GetBodyMesh()->GetSocketTransform(TEXT("hand_r"));
                const FTransform Actual=Weapon->GetSocketTransform(TEXT("WPN_root"));
                GripError=FMath::Max(GripError,FVector::Dist(Expected.GetLocation(),Actual.GetLocation()));
                GripAngle=FMath::Max(GripAngle,FMath::RadiansToDegrees(Expected.GetRotation().AngularDistance(Actual.GetRotation())));
                const FVector Barrel=Body->GetBodyMesh()->GetComponentTransform().InverseTransformVectorNoScale(
                    (Weapon->GetSocketLocation(TEXT("WPN_FrontSight"))-Weapon->GetSocketLocation(TEXT("WPN_RearSight"))).GetSafeNormal());
                const FVector Look=(FQuat(FVector::UpVector,FMath::DegreesToRadians(C.Yaw))*
                    FQuat(FVector::ForwardVector,FMath::DegreesToRadians(C.Pitch))).RotateVector(FVector::RightVector);
                MinForward=FMath::Min(MinForward,FVector::DotProduct(Barrel,Look));
                const FVector Left=BladePoint();
                if(KnifeUppercut)
                {
                    const FName Finger(TEXT("index_01_l"));const auto* NativeBody=Body->GetBodyMesh();
                    const int32 Bone=NativeBody->GetBoneIndex(Finger);
                    if(T>=.2f&&T<=.6f&&Anim->EquipmentFingers.IsValidIndex(Bone))
                    {
                        const FTransform Local=NativeBody->GetSocketTransform(Finger,RTS_Component).GetRelativeTransform(
                            NativeBody->GetSocketTransform(NativeBody->GetParentBone(Finger),RTS_Component));
                        KnifeFingerChange=FMath::Max(KnifeFingerChange,FMath::RadiansToDegrees(Local.GetRotation().AngularDistance(Anim->EquipmentFingers[Bone].GetRotation())));
                    }
                    if(T<.30f)Low=FMath::Min(Low,Left.Z);
                    if(T>=.30f&&T<=.65f)High=FMath::Max(High,Left.Z);
                    if(GeometryReview&&ModelIndex==0&&FCString::Strcmp(C.Name,TEXT("hip"))==0&&
                        (Frame==0||Frame==24||Frame==36||Frame==52||Frame==78||Frame==120||Frame==152))
                        FPSPistolReviewGeometry::Save(FPaths::Combine(GeometryRoot,BodyId.ToString()+FString::Printf(TEXT("-uppercut-%03d.obj"),Frame)),
                            {Body->GetBodyMesh(),Body->HeadMesh.Get(),Weapon},{Blade},Body->GetBodyMesh()->GetComponentTransform());
                }
                const double BladeTravel=FVector::DotProduct(Left-Start,Look);
                if(T<.20f)Windup=FMath::Min(Windup,BladeTravel);
                if(T>.20f&&T<.29f)Reach=FMath::Max(Reach,float(BladeTravel-Windup));
                if(Frame%4==0)
                {
                    SkinProbe.Update(Body->GetBodyMesh());GunDepth=FMath::Max(GunDepth,SkinProbe.Weapon(Weapon,Body->GetBodyMesh()->GetComponentTransform()).Depth);
                    for(int32 Side=0;Side<2;++Side)
                    {
                        const auto Arm=SkinProbe.Arm(Side);
                        if(Arm.Depth>ArmDepth)
                        {
                            ArmDepth=Arm.Depth;WorstArmFrame=Frame;WorstArmSide=Side;WorstArmPoint=Arm.Point;
                            if(GeometryReview&&KnifeUppercut&&ModelIndex==0&&ArmDepth>.2)
                                FPSPistolReviewGeometry::Save(FPaths::Combine(GeometryRoot,BodyId.ToString()+TEXT("-")+C.Name+TEXT("-arm-overlap.obj")),
                                    {Body->GetBodyMesh(),Body->HeadMesh.Get(),Weapon},{Blade},Body->GetBodyMesh()->GetComponentTransform());
                        }
                    }
                    for(const FName Hand:{FName(TEXT("hand_r")),FName(TEXT("hand_l"))})
                    {
                        const auto H=Body->GetBodyMesh()->GetSocketTransform(Hand,RTS_Component);
                        const auto E=Body->GetBodyMesh()->GetSocketTransform(Body->GetBodyMesh()->GetParentBone(Hand),RTS_Component);
                        const auto& Ref=Body->GetBodyMesh()->GetSkeletalMeshAsset()->GetRefSkeleton();
                        const auto& Bind=Ref.GetRefBonePose()[Ref.FindBoneIndex(Hand)];
                        const FVector Axis=(H.GetRotation()*Bind.GetRotation().Inverse()).RotateVector(Bind.GetLocation().GetSafeNormal());
                        const double Bend=FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(Axis,(H.GetLocation()-E.GetLocation()).GetSafeNormal()),-1.,1.)));
                        if(Bend>MaxWrist){MaxWrist=Bend;WorstWristFrame=Frame;WorstWristSide=Hand==TEXT("hand_l")?1:0;}
                    }
                }
            }
            const FString Key=Prefix+TEXT("/")+C.Name;
            Check(Key+TEXT("/gun grip cm"),GripError<.5,GripError);Check(Key+TEXT("/gun grip degrees"),GripAngle<2.,GripAngle);
            Check(Key+TEXT("/gun forward cosine"),MinForward>.85,MinForward);
            Check(Key+TEXT("/gun outside torso cm"),GunDepth<=.2,GunDepth);
            Check(Key+TEXT("/arms outside torso cm"),ArmDepth<=.2,ArmDepth);
            if(KnifeUppercut)Check(Key+TEXT("/knife rising arc cm"),High-Low>25.f,High-Low);
            else Check(Key+TEXT("/knife tip windup to contact cm"),Reach>15.f,Reach);
            if(KnifeUppercut)Check(Key+TEXT("/authored forward-grip fingers survive final layer"),KnifeFingerChange>2.,KnifeFingerChange);
            Check(Key+TEXT("/wrist bend degrees"),MaxWrist<80.,MaxWrist);
            auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Key);Row->SetNumberField(TEXT("max_wrist_bend_deg"),MaxWrist);
            Row->SetNumberField(TEXT("worst_arm_frame"),WorstArmFrame);Row->SetNumberField(TEXT("worst_arm_side"),WorstArmSide);
            Row->SetNumberField(TEXT("worst_wrist_frame"),WorstWristFrame);Row->SetNumberField(TEXT("worst_wrist_side"),WorstWristSide);
            Row->SetStringField(TEXT("worst_arm_point"),WorstArmPoint.ToString());Row->SetNumberField(TEXT("max_arm_depth_cm"),ArmDepth);
            Observations.Add(MakeShared<FJsonValueObject>(Row));
        }
    }
}
