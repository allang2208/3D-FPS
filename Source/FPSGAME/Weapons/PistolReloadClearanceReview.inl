// Runs inside the isolated per-equipment fixture. No ammo or inventory events.
const bool Revolver=FString(Variant.Definition)==TEXT("ue_dan_wesson715")||FString(Variant.Definition)==TEXT("ue_rsh12");
const int32 Capacity=FString(Variant.Definition)==TEXT("ue_rsh12")?5:6;
const TArray<FString> Roles=Revolver?TArray<FString>{TEXT("speed_0"),FString::Printf(TEXT("single_0_%d"),Capacity),TEXT("single_1_1")}:
    TArray<FString>{TEXT("reload"),TEXT("reload_empty")};
for(const FString& Role:Roles)
{
    UAnimSequence* Clip=Side?Pawn->DualPistols->Hands[1].Clips.FindRef(Role).Get():
        Revolver?LoadObject<UAnimSequence>(nullptr,*(Role==TEXT("speed_0")?DanWesson715WeaponAssets::SpeedAnimationPath():
            DanWesson715WeaponAssets::SingleAnimationPath(Role==TEXT("single_1_1")?1:0,Role==TEXT("single_1_1")?1:Capacity))):
        ClipFor(Role);
    Check(Prefix+Role+TEXT(" source loaded"),Clip!=nullptr);if(!Clip)continue;
    for(int32 Crouch=0;Crouch<(QuickClearance?1:2);++Crouch)
    {
        // Start each independent scenario from its own ready pose, including
        // the crouch pelvis. Carrying the preceding scenario's crouched end
        // into a standing reload creates an artificial full-body jump.
        Pawn->WeaponState=EAKMWeaponState::Idle;Pawn->ActiveActionAnimation=nullptr;
        Pawn->DualPistols->StopAction(1);Pawn->bRevolverSingleReload=false;
        if(Side)Pawn->DualPistols->Pose(1,0.f);
        else {Pawn->UpdateActionPose(0.f);Pawn->GunplayAnimation->ActionAlpha=0.f;}
        TickPose(Source);
        auto ReadyState=Body->SampleLocalState();ReadyState.bCrouched=Crouch!=0;
        ReadyState.LastShotAt=ReadyState.RightHand.LastShotAt=ReadyState.LeftHand.LastShotAt=-100.f;
        Body->CaptureMotion(ReadyState);Body->DisplayState=ReadyState;
        for(int32 Settle=0;Settle<20;++Settle)
        {
            Body->ApplyMotion(1.f/60.f);auto* ReadyAnim=Body->BodyAnimation.Get();
            ReadyAnim->BodyState=ReadyAnim->UpperState=ReadyAnim->MotionState=ReadyState;
            ReadyAnim->CrouchAlpha=Crouch?1.f:0.f;ReadyAnim->AimAlpha=ReadyAnim->UpperAlpha=ReadyAnim->MotionAlpha=ReadyAnim->AirAlpha=ReadyAnim->SprintAlpha=0.f;
            ReadyAnim->Clock=World->GetTimeSeconds();TickPose(Body->GetBodyMesh(),1.f/60.f);
        }
        double Worst[4]={0.,0.,0.,0.},WorstContact=0.,WorstWrist=0.,WorstHoldingWrist=0.,WorstBoneLength=0.,WorstStep=0.;
        FVector PreviousHands[2];bool HavePrevious=false;
        const float Epoch=World->GetTimeSeconds();
        if(Side)
        {
            Pawn->DualPistols->StartAction(1,Role,1.f);
            auto& H=Pawn->DualPistols->Hands[1];H.ReloadSpeedloader=Revolver&&Role==TEXT("speed_0");
            H.ReloadStart=Role==TEXT("single_1_1")?1:0;H.ReloadCount=Role==TEXT("single_1_1")?1:Capacity;
            H.SourceLength=Clip->GetPlayLength();H.ActionStarted=Epoch;
        }
        Pawn->RevolverReloadStartLive=Role==TEXT("single_1_1")?1:0;
        Pawn->RevolverReloadCount=Role==TEXT("single_1_1")?1:Capacity;
        const int32 Steps=QuickClearance?20:FMath::CeilToInt(Clip->GetPlayLength()*30.f);
        for(int32 Frame=0;Frame<=Steps;++Frame)
        {
            const float Fraction=float(Frame)/Steps,Time=Clip->GetPlayLength()*Fraction;
            Pawn->WeaponState=Role==TEXT("reload_empty")?EAKMWeaponState::ReloadingEmpty:EAKMWeaponState::Reloading;
            Pawn->WeaponStateElapsed=Time;Pawn->WeaponStateDuration=Clip->GetPlayLength();
            if(Side)
            {
                auto& H=Pawn->DualPistols->Hands[1];H.Action=Clip;H.ActionTime=Time;H.ActionRate=1.f;
                H.Reloading=true;H.ActionBlendStarted=World->GetTimeSeconds()-1.;H.ActionPoseProfile=NAME_None;
                Pawn->DualPistols->Pose(1,0.f);
            }
            else
            {
                Pawn->ActiveActionAnimation=Clip;Pawn->ActionElapsed=Time;Pawn->ActionDuration=Clip->GetPlayLength();
                Pawn->ActionStartPosition=0;Pawn->ActionPlayRate=1;Pawn->bRevolverSingleReload=Revolver&&Role.StartsWith(TEXT("single_"));
                Pawn->UpdateActionPose(0.f);Pawn->GunplayAnimation->ActionClip=Clip;
                Pawn->GunplayAnimation->ActionTime=Time;Pawn->GunplayAnimation->ActionAlpha=1.f;
            }
            TickPose(Source);
            auto State=Body->SampleLocalState();State.bCrouched=Crouch!=0;State.AimPitch=State.AimYaw=0.f;
            State.ActionStartedAt=Epoch;State.LeftHand.ReloadStartedAt=State.RightHand.ReloadStartedAt=Epoch;
            State.LastShotAt=State.RightHand.LastShotAt=State.LeftHand.LastShotAt=-100.f;
            Body->CaptureMotion(State);Body->DisplayState=State;Body->ApplyMotion(1.f/60.f);
            auto* Anim=Body->BodyAnimation.Get();Anim->BodyState=Anim->UpperState=Anim->MotionState=State;
            Anim->Clock=Epoch+Time;Anim->CrouchAlpha=Crouch?1.f:0.f;Anim->AimAlpha=0.f;
            Anim->UpperAlpha=1.f;Anim->MotionAlpha=Anim->AirAlpha=Anim->SprintAlpha=0.f;
            TickPose(Body->GetBodyMesh(),QuickClearance?.2f:Clip->GetPlayLength()/Steps);Weapon->UpdateComponentToWorld();Weapon->UpdateChildTransforms();
            SkinProbe.Update(Body->GetBodyMesh());
            auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Prefix+Role);
            Row->SetStringField(TEXT("clip"),Clip->GetPathName());Row->SetNumberField(TEXT("fraction"),Fraction);
            Row->SetBoolField(TEXT("crouched"),Crouch!=0);
            Row->SetNumberField(TEXT("source_seconds"),Time);
            Row->SetNumberField(TEXT("operation_weight"),Anim->SinglePistolContact.OperationWeight);
            const auto ReloadSample=FPSBodySinglePistolSource::Reload(State);
            Row->SetStringField(TEXT("body_phase"),ReloadSample.Phase);
            Row->SetNumberField(TEXT("body_fraction"),ReloadSample.Fraction);
            const auto StoreProbe=[&](const TCHAR* Name,const FPistolReloadSkinProbe::FResult& R)
            {
                auto Result=MakeShared<FJsonObject>();Result->SetNumberField(TEXT("inside_vertices"),R.Inside);
                Result->SetNumberField(TEXT("max_depth_cm"),R.Depth);Result->SetStringField(TEXT("deepest_point"),R.Point.ToString());
                Row->SetObjectField(Name,Result);
            };
            FPistolReloadSkinProbe::FResult Measures[4]={SkinProbe.Arm(0),SkinProbe.Arm(1),
                SkinProbe.Weapon(Weapon,Body->GetBodyMesh()->GetComponentTransform()),{}};
            for(const auto& Part:Binding.Parts)SkinProbe.Part(Measures[3],Part.Get(),Body->GetBodyMesh()->GetComponentTransform());
            const TCHAR* Names[]={TEXT("right_arm"),TEXT("left_arm"),TEXT("gun"),TEXT("parts")};
            for(int32 I=0;I<4;++I){StoreProbe(Names[I],Measures[I]);Worst[I]=FMath::Max(Worst[I],Measures[I].Depth);}
            auto Bones=MakeShared<FJsonObject>();
            for(const TCHAR* N:{TEXT("pelvis"),TEXT("spine_03"),TEXT("upperarm_r"),TEXT("lowerarm_r"),TEXT("hand_r"),TEXT("upperarm_l"),TEXT("lowerarm_l"),TEXT("hand_l")})
                Bones->SetStringField(N,Body->GetBodyMesh()->GetSocketTransform(N,RTS_Component).GetLocation().ToString());
            Row->SetObjectField(TEXT("bones"),Bones);
            const bool Native=Anim->UsesNativeSinglePistolSource();
            const bool ContactRequired=!Native||Anim->SinglePistolContact.OperationWeight>.99f||Fraction>=1.f;
            const FTransform Relation=Native?(Fraction>=1.f?Anim->SinglePistolContact.Ready:Anim->SinglePistolContact.Operation):
                (Side?Anim->RightGripFromLeft:Anim->LeftGripFromRight);
            const double Contact=FVector::Dist((Relation*Body->GetBodyMesh()->GetSocketTransform(Dominant)).GetLocation(),Body->GetBodyMesh()->GetSocketLocation(Support));
            Row->SetNumberField(TEXT("support_contact_cm"),Contact);
            Row->SetBoolField(TEXT("support_contact_required"),ContactRequired);
            if(ContactRequired)WorstContact=FMath::Max(WorstContact,Contact);
            const auto* Mesh=Body->GetBodyMesh();const auto& Ref=Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
            for(int32 Arm=0;Arm<2;++Arm)
            {
                const FName HandName=Arm?TEXT("hand_l"):TEXT("hand_r");
                const int32 W=Ref.FindBoneIndex(HandName),E=Ref.GetParentIndex(W),U=Ref.GetParentIndex(E);
                const auto H=Mesh->GetSocketTransform(HandName,RTS_Component),J=Mesh->GetSocketTransform(Ref.GetBoneName(E),RTS_Component);
                const auto S=Mesh->GetSocketTransform(Ref.GetBoneName(U),RTS_Component);
                const auto& Bind=Ref.GetRefBonePose()[W];
                const FVector Axis=(H.GetRotation()*Bind.GetRotation().Inverse()).RotateVector(Bind.GetLocation().GetSafeNormal());
                const double Bend=FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(Axis,(H.GetLocation()-J.GetLocation()).GetSafeNormal()),-1.,1.)));
                Row->SetNumberField(Arm?TEXT("left_wrist_bend_deg"):TEXT("right_wrist_bend_deg"),Bend);
                if(ContactRequired&&Arm!=Side)WorstWrist=FMath::Max(WorstWrist,Bend);
                if(Arm==Side)WorstHoldingWrist=FMath::Max(WorstHoldingWrist,Bend);
                WorstBoneLength=FMath::Max(WorstBoneLength,FMath::Abs(FVector::Distance(H.GetLocation(),J.GetLocation())-Bind.GetLocation().Size()));
                WorstBoneLength=FMath::Max(WorstBoneLength,FMath::Abs(FVector::Distance(J.GetLocation(),S.GetLocation())-Ref.GetRefBonePose()[E].GetLocation().Size()));
                if(HavePrevious)WorstStep=FMath::Max(WorstStep,FVector::Distance(H.GetLocation(),PreviousHands[Arm]));
                PreviousHands[Arm]=H.GetLocation();
            }
            HavePrevious=true;
            float GeometryAt=-1.f;
            if(GeometryReview&&FParse::Value(*Params,TEXT("ReloadAt="),GeometryAt)&&FMath::Abs(Time-GeometryAt)<Clip->GetPlayLength()/Steps*.5f)
            {
                TArray<USkeletalMeshComponent*> Meshes={Body->GetBodyMesh(),Weapon};TArray<UStaticMeshComponent*> Parts;
                for(const auto& Part:Binding.Parts)Parts.Add(Part.Get());
                FPSPistolReviewGeometry::Save(GeometryRoot/((Prefix+Role+(Crouch?TEXT("_crouch"):TEXT("_standing"))).Replace(TEXT("/"),TEXT("_"))+TEXT(".obj")),Meshes,Parts,Body->GetBodyMesh()->GetComponentTransform());
            }
            Observations.Add(MakeShared<FJsonValueObject>(Row));
        }
        const FString Label=Prefix+Role+(Crouch?TEXT("/crouch/"):TEXT("/standing/"));
        const TCHAR* Names[]={TEXT("right arm skin depth cm"),TEXT("left arm skin depth cm"),TEXT("gun skin depth cm"),TEXT("attachment depth cm")};
        for(int32 I=0;I<4;++I)Check(Label+Names[I],Worst[I]<=.2,Worst[I]);
        Check(Label+TEXT("support contact cm"),WorstContact<.5,WorstContact);
        Check(Label+TEXT("contact wrist axis bend deg"),WorstWrist<80.,WorstWrist);
        Check(Label+TEXT("holding wrist axis bend deg"),WorstHoldingWrist<80.,WorstHoldingWrist);
        Check(Label+TEXT("bone length error cm"),WorstBoneLength<.05,WorstBoneLength);
        if(!QuickClearance)Check(Label+TEXT("wrist step cm at 30hz"),WorstStep<10.,WorstStep);
    }
}
