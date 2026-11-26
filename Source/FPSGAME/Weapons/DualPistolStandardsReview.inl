// Explicit isolated dual-standard review; uses real equipment/source/body graphs.
const bool Quick=FParse::Param(*Params,TEXT("QuickDual"));
const bool Fine=FParse::Param(*Params,TEXT("FineDual"));
const bool EquipOnly=FParse::Param(*Params,TEXT("DualEquipOnly"));
const bool FixesOnly=FParse::Param(*Params,TEXT("DualFixesOnly"));
const bool ArmSupport=FParse::Param(*Params,TEXT("DualArmSupport"));
const bool ReloadReview=FParse::Param(*Params,TEXT("DualReloadReview"));
const bool QuickReload=FParse::Param(*Params,TEXT("QuickReload"));
const bool ReloadStress=FParse::Param(*Params,TEXT("ReloadStress"));
FString ReloadCase;FParse::Value(*Params,TEXT("DualReloadCase="),ReloadCase);
int32 OnlyVariant=INDEX_NONE;FParse::Value(*Params,TEXT("DualVariant="),OnlyVariant);
int32 OnlyLeft=INDEX_NONE;FParse::Value(*Params,TEXT("DualLeftVariant="),OnlyLeft);
int32 MaximumVariant=MAX_int32;FParse::Value(*Params,TEXT("DualMaximumVariant="),MaximumVariant);
for(const TCHAR* Key:{TEXT("DualPistol.Upper.Idle"),TEXT("DualPistol.Upper.Walk"),TEXT("DualPistol.Upper.Sprint")})
    Check(FString(Key)+TEXT(" asset loaded"),Body->BodyAnimation->Clips.FindRef(Key)!=nullptr);
if(ReloadReview)for(const TCHAR* Key:{TEXT("DualPistol.Source.Idle"),TEXT("DualPistol.Source.Walk"),TEXT("DualPistol.Source.Sprint")})
    Check(FString(Key)+TEXT(" actual source loaded"),Body->BodyAnimation->Clips.FindRef(Key)!=nullptr);
for(int32 Right=0;Right<UE_ARRAY_COUNT(Variants);++Right)for(int32 Left=0;Left<5;++Left)
{
    if(Quick&&(Right>=5||(Right!=Left&&OnlyLeft==INDEX_NONE)))continue;
    if(OnlyVariant!=INDEX_NONE&&Right!=OnlyVariant)continue;
    if(Right>MaximumVariant)continue;
    if(OnlyLeft!=INDEX_NONE&&Left!=OnlyLeft)continue;
    if(Right>=5&&Left!=(Right==5?1:4))continue;
    if(EquipOnly&&Right<5&&Right!=Left)continue;
    if(FixesOnly&&Right<5&&Right!=Left)continue;
    if(ArmSupport&&Right<5&&Right!=Left&&!(Right==0&&Left==2))continue;
    if(ReloadReview&&Right<5&&Right!=Left&&!(Right>=3&&Left>=3&&(!QuickReload||OnlyLeft!=INDEX_NONE)))continue;
    const auto& RV=Variants[Right];const auto& LV=Variants[Left];
    auto RItem=Model->CreateItem(RV.Definition),LItem=Model->CreateItem(LV.Definition);
    RItem.Place=LItem.Place=1;RItem.Cell=6;LItem.Cell=8;RItem.Magazine=LItem.Magazine=5;
    if(*RV.Slot)
    {
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(RItem.Data),Data);
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(RV.Slot,RV.Part);
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Data->SetNumberField(TEXT("gunsmith_version"),1);
        RItem.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&RItem.Data));
        LItem.Data=RItem.Data;
    }
    Model->Current=Seed;Model->Current.Items={RItem,LItem};Pawn->ApplyColdSteelProfile(Model);
    Pawn->DualPistols->InterruptActions();Pawn->WeaponState=EAKMWeaponState::Idle;
    Pawn->ActiveActionAnimation=nullptr;Pawn->bIsAiming=false;Pawn->WeaponADSFactor=0;
    for(int32 Side=0;Side<2;++Side){Pawn->DualPistols->Pose(Side,0);TickPose(Pawn->DualPistols->Hands[Side].Mesh);}
    FlushAsyncLoading();Body->DisplayState=Body->SampleLocalState();Body->CaptureEquipment();
    const FString Prefix=FString::Printf(TEXT("%s+%s/%s/"),RV.Definition,LV.Definition,*RV.Part?RV.Part:TEXT("base"));
    Check(Prefix+TEXT(" two native independent guns"),Pawn->IsDualWieldingPistols()&&Body->MotionBindings.Num()==2&&
        !Body->BodyAnimation->bHasLeftGrip&&!Body->BodyAnimation->bHasRightGrip);
    if(Body->MotionBindings.Num()!=2)continue;
    for(int32 Side=0;Side<2;++Side)Check(Prefix+FString::Printf(TEXT("hand %d socket"),Side),
        Body->MotionBindings[Side].Mesh->GetAttachSocketName()==FName(Side?TEXT("hand_l"):TEXT("hand_r")));
    struct FCase {FString Name,Role;uint8 Hands=0;float Speed=0,Direction=0,Pitch=0,Yaw=0;bool Crouch=false,Run=false;
        FString LeftRole;float LeftDelay=0.f,StopFraction=1.f;bool Return=false;};
    TArray<FCase> Cases={
        {TEXT("idle"),TEXT("idle")},
        {TEXT("walk_forward"),TEXT("idle"),0,300},
        {TEXT("walk_left"),TEXT("idle"),0,300,-90},
        {TEXT("walk_back"),TEXT("idle"),0,300,180},
        {TEXT("crouch"),TEXT("idle"),0,0,0,0,0,true},
        {TEXT("crouch_walk"),TEXT("idle"),0,180,90,0,0,true},
        {TEXT("sprint"),TEXT("idle"),0,600,0,0,0,false,true},
        {TEXT("aim_up"),TEXT("idle"),0,0,0,35,20},
        {TEXT("aim_down"),TEXT("idle"),0,0,0,-30,-20},
        {TEXT("fire_right"),TEXT("fire"),1},
        {TEXT("fire_left"),TEXT("fire"),2},
        {TEXT("fire_both"),TEXT("fire"),3}
    };
    // All ordered loadouts get locomotion/aim and independent fire. Complete
    // action trajectories use each same-gun pair and every explicit variant.
    if(Right==Left||Right>=5)
    {
        for(uint8 Mask:{uint8(1),uint8(2),uint8(3)})
        {
            Cases.Add({FString::Printf(TEXT("equip_%d"),Mask),TEXT("equip"),Mask});
            Cases.Add({FString::Printf(TEXT("reload_%d"),Mask),TEXT("reload"),Mask});
            Cases.Add({FString::Printf(TEXT("empty_%d"),Mask),TEXT("reload_empty"),Mask,0,0,0,0,true});
        }
        if(!Quick||Fine)
        {
            FCase Mixed;Mixed.Name=TEXT("reload_right_fire_left");Mixed.Role=TEXT("reload");Mixed.LeftRole=TEXT("fire");Mixed.Hands=3;Cases.Add(Mixed);
            Mixed.Name=TEXT("fire_right_reload_left");Mixed.Role=TEXT("fire");Mixed.LeftRole=TEXT("reload");Cases.Add(Mixed);
            Mixed.Name=TEXT("staggered_reload");Mixed.Role=TEXT("reload");Mixed.LeftDelay=.35f;Cases.Add(Mixed);
            FCase Tail;Tail.Name=TEXT("reload_return");Tail.Role=TEXT("reload");Tail.Hands=3;Tail.Return=true;Cases.Add(Tail);
            Tail.Name=TEXT("reload_interrupt_return");Tail.StopFraction=.45f;Cases.Add(Tail);
        }
    }
    if(ArmSupport)
    {
        Cases.Reset();
        for(float Pitch:{-50.f,-30.f,0.f,35.f,55.f})for(float Yaw:{-35.f,0.f,35.f})
            Cases.Add({FString::Printf(TEXT("look_%.0f_%.0f"),Pitch,Yaw),TEXT("idle"),0,0,0,Pitch,Yaw});
        if(Right==0&&Left==2)Cases.Add({TEXT("look_sweep"),TEXT("idle"),0,0,0,55});
    }
    if(ReloadReview)
    {
        Cases.Reset();
        const auto& H=Pawn->DualPistols->Hands[0];
        const auto AddRole=[&](const FString& Role)
        {for(uint8 Mask:{uint8(1),uint8(2),uint8(3)})Cases.Add({Role+FString::Printf(TEXT("_%d"),Mask),Role,Mask});};
        if(H.Revolver&&Right==Left)
        {
            for(int32 Start=0;Start<H.Stats.Capacity;++Start)for(int32 Count=1;Count<=H.Stats.Capacity-Start;++Count)
            {
                if(QuickReload&&(Start!=0&&Start!=H.Stats.Capacity-1))continue;
                if(QuickReload&&Count!=1&&Count!=H.Stats.Capacity-Start)continue;
                AddRole(FString::Printf(TEXT("single_%d_%d"),Start,Count));
            }
            AddRole(TEXT("speed_0"));
            AddRole(TEXT("speed_partial"));
        }
        else {AddRole(TEXT("reload"));AddRole(TEXT("reload_empty"));}
        const FString Main=H.Revolver?TEXT("single_full"):TEXT("reload_empty");
        for(uint8 Mask:{uint8(1),uint8(2),uint8(3)})
        {
            FCase Tail;Tail.Role=Main;Tail.Hands=Mask;Tail.Return=true;
            Tail.Name=FString::Printf(TEXT("complete_return_%d"),Mask);Cases.Add(Tail);
            Tail.StopFraction=.45f;Tail.Name=FString::Printf(TEXT("interrupt_return_%d"),Mask);Cases.Add(Tail);
        }
        if(!QuickReload||ReloadStress)
        {
            Cases.Add({TEXT("crouch_reload"),Main,3,0,0,0,0,true});
            Cases.Add({TEXT("moving_reload"),Main,3,300,90});
            Cases.Add({TEXT("low_look_reload"),Main,3,0,0,-30,-20});
            Cases.Add({TEXT("high_look_reload"),Main,3,0,0,35,20});
            FCase Mixed;Mixed.Name=TEXT("reload_right_fire_left");Mixed.Role=Main;Mixed.LeftRole=TEXT("fire");Mixed.Hands=3;Cases.Add(Mixed);
            Mixed.Name=TEXT("fire_right_reload_left");Mixed.Role=TEXT("fire");Mixed.LeftRole=Main;Cases.Add(Mixed);
        }
    }
    for(const auto& C:Cases)
    {
        if(!ReloadCase.IsEmpty()&&C.Name!=ReloadCase)continue;
        if(EquipOnly&&C.Role!=TEXT("equip"))continue;
        if(FixesOnly&&Right!=5&&C.Role!=TEXT("equip"))continue;
        UAnimSequence* Clips[2]={};FString Roles[2];double Worst[4]={},Contact=0.,ContactAngle=0.,AimDot=1.,MaxStep=0.;
        double MaxReach=0.,MaxWrist=0.,QuietStep=0.,Mechanical=0.,MechanicalAngle=0.,BoneLengthError=0.;bool Finite=true;FVector Previous[2];bool HadPrevious=false;
        double MagazineAxialError=0.,MagazineSeatError=0.,MagazineRigidError=0.;
        int32 MagazineSeatSamples=0;
        double MinElbowSide=DBL_MAX,MaxUpperFlare=0.,MinUpperDrop=DBL_MAX;
        double MaxElbowStep=0.;FVector PreviousElbows[2];
        float Duration=C.Hands?0.f:1.f;
        for(int32 Side=0;Side<2;++Side)
        {
            const auto& H=Pawn->DualPistols->Hands[Side];FString Role=(C.Hands&(1<<Side))?(Side&&!C.LeftRole.IsEmpty()?C.LeftRole:C.Role):TEXT("idle");
            if(H.Revolver&&Role.StartsWith(TEXT("reload")))Role=Role==TEXT("reload_empty")?
                FString::Printf(TEXT("single_0_%d"),H.Item.Definition==TEXT("ue_rsh12")?5:6):TEXT("speed_0");
            if(Role==TEXT("single_full"))Role=FString::Printf(TEXT("single_0_%d"),H.Stats.Capacity);
            if(Role==TEXT("speed_partial"))Role=TEXT("speed_0");
            Roles[Side]=Role;Clips[Side]=H.Clips.FindRef(Role);
            Check(Prefix+C.Name+FString::Printf(TEXT("/%d source"),Side),Clips[Side]!=nullptr);
            if(C.Hands&(1<<Side))Duration=FMath::Max(Duration,Clips[Side]?Clips[Side]->GetPlayLength():0.f);
        }
        if(!Clips[0]||!Clips[1])continue;
        if(ReloadReview)
        {
            for(int32 Side=0;Side<2;++Side)
            {
                auto& H=Pawn->DualPistols->Hands[Side];H.Action=nullptr;H.Reloading=false;H.Rounds=H.Stats.Capacity;
                Pawn->DualPistols->Pose(Side,0.f);TickPose(H.Mesh);
            }
            // Enter every case from a real settled source carry. A single .2 s
            // first tick skips the entire .12 s handover being reviewed.
            for(int32 Warm=0;Warm<16;++Warm)
            {
                auto State=Body->SampleLocalState();State.bCrouched=C.Crouch;State.bSprinting=false;
                State.AimPitch=C.Pitch;State.AimYaw=C.Yaw;State.LastShotAt=-100;
                State.RightHand.LastShotAt=State.LeftHand.LastShotAt=-100;
                Body->CaptureMotion(State);Body->DisplayState=State;Body->ApplyMotion(1.f/60.f);
                auto* Anim=Body->BodyAnimation.Get();Anim->BodyState=Anim->UpperState=Anim->MotionState=State;
                Anim->Clock=100.f-(16-Warm)/60.f;Anim->CrouchAlpha=C.Crouch?1.f:0.f;
                Anim->SprintAlpha=0;Anim->Speed=C.Speed;Anim->Direction=C.Direction;Anim->AimAlpha=0;
                Anim->UpperAlpha=Anim->MotionAlpha=Anim->AirAlpha=0;Anim->bFalling=false;
                TickPose(Body->GetBodyMesh(),1.f/60.f);
            }
        }
        // Use the real action dispatcher to select private grip/profile layers.
        // The old fixture cleared ActionPoseProfile and missed fitted/revolver paths.
        if(ReloadReview)for(int32 Side=0;Side<2;++Side)
        {
            auto& H=Pawn->DualPistols->Hands[Side];
            Pawn->DualPistols->StartAction(Side,Roles[Side],1.f);
            H.ReloadSpeedloader=Roles[Side].StartsWith(TEXT("speed_"));
            H.ReloadStart=0;H.ReloadCount=H.Stats.Capacity;
            if(!H.Revolver&&Roles[Side]==TEXT("reload")){H.ReloadStart=H.Stats.Capacity-1;H.ReloadCount=1;}
            if(H.ReloadSpeedloader&&C.Role==TEXT("speed_partial"))H.ReloadStart=H.Stats.Capacity-1;
            if(Roles[Side].StartsWith(TEXT("single_")))
            {
                TArray<FString> Fields;Roles[Side].ParseIntoArray(Fields,TEXT("_"));
                H.ReloadStart=FCString::Atoi(*Fields[1]);H.ReloadCount=FCString::Atoi(*Fields[2]);
            }
            H.SourceLength=H.Revolver?(H.ReloadSpeedloader?3.85f:DanWesson715WeaponAssets::SingleDuration(H.ReloadCount,H.ReloadStart==0)):
                Roles[Side]==TEXT("reload_empty")?2.25f:1.75f;
            H.Rounds=H.ReloadStart;H.Cases=H.Stats.Capacity;H.Seated=0;
            if(!(C.Hands&(1<<Side))||Roles[Side]==TEXT("fire"))H.Rounds=H.Stats.Capacity;
        }
        const float SourceDuration=Duration;
        const float LeftStart=C.LeftDelay*SourceDuration;
        if(C.LeftDelay>0.f)Duration=FMath::Max(Duration,LeftStart+Clips[1]->GetPlayLength());
        if(C.Return)Duration=SourceDuration*C.StopFraction+.3f;
        const bool LookSweep=ArmSupport&&C.Name==TEXT("look_sweep");
        const int32 Steps=Fine||LookSweep?FMath::CeilToInt(Duration*60.f):C.Hands?(Quick?20:40):(Quick||ArmSupport?4:8);
        for(int32 Sample=0;Sample<=Steps;++Sample)
        {
            const float Fraction=float(Sample)/Steps;
            for(int32 Side=0;Side<2;++Side)
            {
                auto& H=Pawn->DualPistols->Hands[Side];const float Elapsed=Fraction*Duration-(Side?LeftStart:0.f);
                const bool Active=(C.Hands&(1<<Side))!=0&&Elapsed>=0.f&&Elapsed<Clips[Side]->GetPlayLength()&&
                    (!C.Return||Fraction*Duration<SourceDuration*C.StopFraction);
                H.Action=Active?Clips[Side]:nullptr;H.ActionTime=FMath::Clamp(Elapsed,0.f,Clips[Side]->GetPlayLength());H.ActionRate=1.f;
                H.Reloading=Active&&(Roles[Side].StartsWith(TEXT("reload"))||Roles[Side].StartsWith(TEXT("speed_"))||Roles[Side].StartsWith(TEXT("single_")));
                H.ActionBlendStarted=World->GetTimeSeconds()-H.ActionTime;
                if(!ReloadReview)H.ActionPoseProfile=NAME_None;
                else
                {
                    H.ActionStarted=World->GetTimeSeconds()-H.ActionTime;
                    if(H.Reloading)
                    {
                        H.ActionTime=0.f; // Sample the warped production clock, not max(linear, warped).
                        H.ActionTime=Pawn->DualPistols->SampleActionTime(Side);
                        const float SourceTime=H.ActionTime/Clips[Side]->GetPlayLength()*H.SourceLength;
                        const float EjectAt=H.ReloadSpeedloader?DanWesson715WeaponAssets::Eject/3.6f*3.85f:
                            H.Item.Definition==TEXT("ue_rsh12")?(H.ReloadStart==0?DanWesson715WeaponAssets::Eject:DanWesson715WeaponAssets::Open+.06f):DanWesson715WeaponAssets::EmptyCaseClear;
                        H.ReloadCasesReleased=SourceTime>=EjectAt;
                        H.Seated=0;
                        if(!H.Revolver)H.Seated=SourceTime>=1.05f?H.ReloadCount:0;
                        else if(H.ReloadSpeedloader)H.Seated=SourceTime>=DanWesson715WeaponAssets::Seat/3.6f*3.85f?H.ReloadCount:0;
                        else for(int32 Round=0;Round<H.ReloadCount;++Round)
                            H.Seated+=SourceTime>=DanWesson715WeaponAssets::SingleSeatTime(Round,H.ReloadStart==0);
                        H.Rounds=H.ReloadSpeedloader?(H.ReloadCasesReleased?H.Seated:H.ReloadStart):H.ReloadStart+H.Seated;
                        H.Cases=H.ReloadCasesReleased?H.Rounds:H.Stats.Capacity;
                    }
                }
                Pawn->DualPistols->Pose(Side,0);TickPose(H.Mesh);
            }
            auto State=Body->SampleLocalState();State.bCrouched=C.Crouch;State.bSprinting=C.Run;
            State.bAiming=false;State.AimPitch=LookSweep?FMath::Lerp(-50.f,55.f,Fraction):C.Pitch;State.AimYaw=C.Yaw;State.LastShotAt=-100;
            State.RightHand.LastShotAt=State.LeftHand.LastShotAt=-100;
            const float Clock=100.f+Fraction*Duration;
            for(int32 Side=0;Side<2;++Side)if((C.Hands&(1<<Side))&&Roles[Side]==TEXT("fire"))
                (Side==0?State.RightHand:State.LeftHand).LastShotAt=100.f+(Side?LeftStart:0.f);
            Body->CaptureMotion(State);Body->DisplayState=State;Body->ApplyMotion(1.f/60.f);
            auto* Anim=Body->BodyAnimation.Get();Anim->BodyState=Anim->UpperState=Anim->MotionState=State;
            Anim->Clock=Clock;Anim->CrouchAlpha=C.Crouch?1.f:0.f;Anim->SprintAlpha=C.Run?1.f:0.f;
            Anim->Speed=C.Speed;Anim->Direction=C.Direction;Anim->AimAlpha=0;
            Anim->UpperAlpha=Anim->MotionAlpha=Anim->AirAlpha=0;Anim->bFalling=false;
            TickPose(Body->GetBodyMesh(),Sample==0&&!ReloadReview?.2f:Duration/Steps);
            SkinProbe.Update(Body->GetBodyMesh());
            auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Prefix+C.Name);Row->SetNumberField(TEXT("fraction"),Fraction);
            Row->SetNumberField(TEXT("time"),Fraction*Duration);
            for(int32 Side=0;Side<2;++Side)
            {
                auto& Binding=Body->MotionBindings[Side];auto* Weapon=Binding.Mesh.Get();
                auto* Source=Pawn->DualPistols->Hands[Side].Mesh.Get();
                Weapon->UpdateComponentToWorld();Weapon->UpdateChildTransforms();
                const FName Wrist=Side?TEXT("hand_l"):TEXT("hand_r");
                const auto* Map=Body->MotionMap(Source,Wrist,Side);
                const FTransform SourceHand=Rigid(Source->GetSocketTransform(Wrist,RTS_Component));
                const FTransform Expected=Source->GetSocketTransform(TEXT("WPN_root"),RTS_Component).GetRelativeTransform(SourceHand)*
                    Map->Mount*Body->GetBodyMesh()->GetSocketTransform(Wrist);
                const auto Actual=Weapon->GetSocketTransform(TEXT("WPN_root"));
                if(ReloadReview)
                {
                    const auto& NativeRef=Source->GetSkeletalMeshAsset()->GetRefSkeleton();
                    const int32 Magazine=NativeRef.FindBoneIndex(TEXT("WPN_SOCKET_Magazine"));
                    const bool AdaptedMagazine=Magazine!=INDEX_NONE&&!Pawn->DualPistols->Hands[Side].Revolver&&
                        Pawn->DualPistols->Hands[Side].Reloading;
                    for(int32 Bone=0;Bone<NativeRef.GetNum();++Bone)
                    {
                        const FName Name=NativeRef.GetBoneName(Bone);
                        if(!Name.ToString().StartsWith(TEXT("WPN_"))||Weapon->GetBoneIndex(Name)==INDEX_NONE)continue;
                        const auto Wanted=Source->GetSocketTransform(Name,RTS_Component).GetRelativeTransform(SourceHand)*Map->Mount*
                            Body->GetBodyMesh()->GetSocketTransform(Wrist);
                        const auto Displayed=Weapon->GetSocketTransform(Name);
                        if(AdaptedMagazine&&(Bone==Magazine||NativeRef.BoneIsChildOf(Bone,Magazine)))
                        {
                            const FName MagazineName=NativeRef.GetBoneName(Magazine);
                            const auto OriginalMag=Rigid(Source->GetSocketTransform(MagazineName,RTS_Component));
                            const auto DisplayedMag=Rigid(Weapon->GetSocketTransform(MagazineName));
                            const auto OriginalLocal=Source->GetSocketTransform(Name,RTS_Component).GetRelativeTransform(OriginalMag);
                            const auto DisplayedLocal=Displayed.GetRelativeTransform(DisplayedMag);
                            MagazineRigidError=FMath::Max(MagazineRigidError,FVector::Distance(OriginalLocal.GetLocation(),DisplayedLocal.GetLocation()));
                            if(Bone==Magazine)
                            {
                                const auto FrozenGun=Rigid(Binding.FrozenPose[Binding.NativeWeaponRoot]);
                                const auto CurrentGun=Rigid(Actual);
                                const auto Seat=Binding.FrozenPose[Magazine].GetRelativeTransform(FrozenGun)*CurrentGun;
                                const FVector Up=CurrentGun.GetRotation().RotateVector(FrozenGun.GetRotation().UnrotateVector(FVector::UpVector));
                                MagazineAxialError=FMath::Max(MagazineAxialError,FMath::Abs(FVector::DotProduct(Displayed.GetLocation()-Wanted.GetLocation(),Up)));
                                if(FVector::Distance(Wanted.GetLocation(),Seat.GetLocation())<.1)
                                {++MagazineSeatSamples;MagazineSeatError=FMath::Max(MagazineSeatError,FVector::Distance(Wanted.GetLocation(),Displayed.GetLocation()));}
                            }
                        }
                        else Mechanical=FMath::Max(Mechanical,FVector::Distance(Wanted.GetLocation(),Displayed.GetLocation()));
                        MechanicalAngle=FMath::Max(MechanicalAngle,FMath::RadiansToDegrees(Wanted.GetRotation().AngularDistance(Displayed.GetRotation())));
                        Finite&=!Displayed.ContainsNaN();
                    }
                    Row->SetStringField(Side?TEXT("left_role"):TEXT("right_role"),Roles[Side]);
                    Row->SetNumberField(Side?TEXT("left_source_time"):TEXT("right_source_time"),Pawn->DualPistols->Hands[Side].ActionTime);
                    Row->SetStringField(Side?TEXT("left_action_delta"):TEXT("right_action_delta"),Anim->ActionHands[Side].ToString());
                    Row->SetStringField(Side?TEXT("left_display_wrist"):TEXT("right_display_wrist"),Body->GetBodyMesh()->GetSocketTransform(Wrist,RTS_Component).ToString());
                }
                Contact=FMath::Max(Contact,FVector::Distance(Expected.GetLocation(),Actual.GetLocation()));
                ContactAngle=FMath::Max(ContactAngle,FMath::RadiansToDegrees(Expected.GetRotation().AngularDistance(Actual.GetRotation())));
                Finite&=!Actual.ContainsNaN()&&Actual.GetScale3D().GetMin()>0;
                const auto Arm=SkinProbe.Arm(Side),Gun=SkinProbe.Weapon(Weapon,Body->GetBodyMesh()->GetComponentTransform());
                FPistolReloadSkinProbe::FResult Parts;
                for(const auto& P:Binding.Parts)SkinProbe.Part(Parts,P.Get(),Body->GetBodyMesh()->GetComponentTransform());
                Worst[Side]=FMath::Max(Worst[Side],Arm.Depth);Worst[2]=FMath::Max(Worst[2],Gun.Depth);Worst[3]=FMath::Max(Worst[3],Parts.Depth);
                Row->SetNumberField(Side?TEXT("left_arm_depth"):TEXT("right_arm_depth"),Arm.Depth);
                Row->SetNumberField(Side?TEXT("left_gun_depth"):TEXT("right_gun_depth"),Gun.Depth);
                if(ReloadReview&&Gun.Depth>.2)
                {
                    Row->SetStringField(Side?TEXT("left_inside_bone"):TEXT("right_inside_bone"),Gun.Bone.ToString());
                    Row->SetStringField(Side?TEXT("left_inside_point"):TEXT("right_inside_point"),Gun.Point.ToString());
                    Row->SetNumberField(Side?TEXT("left_inside_vertex"):TEXT("right_inside_vertex"),Gun.Vertex);
                    Row->SetStringField(Side?TEXT("left_inside_bone_transform"):TEXT("right_inside_bone_transform"),Weapon->GetSocketTransform(Gun.Bone,RTS_Component).ToString());
                }
                Row->SetNumberField(Side?TEXT("left_part_depth"):TEXT("right_part_depth"),Parts.Depth);
                if(Right==5)
                {
                    Row->SetStringField(Side?TEXT("left_part_inside_point"):TEXT("right_part_inside_point"),Parts.Point.ToString());
                    Row->SetStringField(Side?TEXT("left_wrist_transform"):TEXT("right_wrist_transform"),Body->GetBodyMesh()->GetSocketTransform(Wrist,RTS_Component).ToString());
                    TArray<TSharedPtr<FJsonValue>> Points;
                    for(const FVector& P:Anim->PistolClearanceInHand[Side])Points.Add(MakeShared<FJsonValueString>(P.ToString()));
                    Row->SetArrayField(Side?TEXT("left_clearance_points"):TEXT("right_clearance_points"),Points);
                }
                auto B=MakeShared<FJsonObject>();
                FVector P[3];int32 I=0;
                for(const TCHAR* Stem:{TEXT("upperarm"),TEXT("lowerarm"),TEXT("hand")})
                {
                    const FString Bone=FString::Printf(TEXT("%s_%s"),Stem,Side?TEXT("l"):TEXT("r"));
                    P[I++]=Body->GetBodyMesh()->GetSocketTransform(*Bone,RTS_Component).GetLocation();
                    B->SetStringField(Bone,P[I-1].ToString());
                }
                const double Reach=FVector::Dist(P[0],P[2])/(FVector::Dist(P[0],P[1])+FVector::Dist(P[1],P[2]));
                if(ArmSupport)
                {
                    const FVector OtherShoulder=Body->GetBodyMesh()->GetSocketTransform(Side?TEXT("upperarm_r"):TEXT("upperarm_l"),RTS_Component).GetLocation();
                    const double Sign=Side?1.:-1.;
                    const double ElbowSide=Sign*(P[1].X-(P[0].X+OtherShoulder.X)*.5);
                    const double Flare=Sign*(P[1].X-P[0].X),Drop=P[0].Z-P[1].Z;
                    MinElbowSide=FMath::Min(MinElbowSide,ElbowSide);
                    MaxUpperFlare=FMath::Max(MaxUpperFlare,Flare);MinUpperDrop=FMath::Min(MinUpperDrop,Drop);
                    if(HadPrevious)MaxElbowStep=FMath::Max(MaxElbowStep,FVector::Distance(P[1],PreviousElbows[Side]));
                    PreviousElbows[Side]=P[1];
                    Row->SetNumberField(Side?TEXT("left_elbow_side_cm"):TEXT("right_elbow_side_cm"),ElbowSide);
                    Row->SetNumberField(Side?TEXT("left_upper_flare_cm"):TEXT("right_upper_flare_cm"),Flare);
                    Row->SetNumberField(Side?TEXT("left_upper_drop_cm"):TEXT("right_upper_drop_cm"),Drop);
                    Row->SetStringField(Side?TEXT("left_upper_transform"):TEXT("right_upper_transform"),Body->GetBodyMesh()->GetSocketTransform(Side?TEXT("upperarm_l"):TEXT("upperarm_r"),RTS_Component).ToString());
                }
                MaxReach=FMath::Max(MaxReach,Reach);
                const auto WristPose=Body->GetBodyMesh()->GetSocketTransform(Wrist,RTS_Component);
                const auto ElbowPose=Body->GetBodyMesh()->GetSocketTransform(Side?TEXT("lowerarm_l"):TEXT("lowerarm_r"),RTS_Component);
                const auto& Skeleton=Body->GetBodyMesh()->GetSkeletalMeshAsset()->GetRefSkeleton();
                if(ReloadReview)
                {
                    const int32 ElbowBone=Skeleton.FindBoneIndex(Side?TEXT("lowerarm_l"):TEXT("lowerarm_r"));
                    const int32 WristBone=Skeleton.FindBoneIndex(Wrist);
                    BoneLengthError=FMath::Max(BoneLengthError,FMath::Abs(FVector::Distance(P[0],P[1])-Skeleton.GetRefBonePose()[ElbowBone].GetTranslation().Size()));
                    BoneLengthError=FMath::Max(BoneLengthError,FMath::Abs(FVector::Distance(P[1],P[2])-Skeleton.GetRefBonePose()[WristBone].GetTranslation().Size()));
                }
                const auto NativeWrist=Skeleton.GetRefBonePose()[Skeleton.FindBoneIndex(Wrist)].GetRotation();
                const double WristAngle=FMath::RadiansToDegrees((ElbowPose.GetRotation()*NativeWrist).AngularDistance(WristPose.GetRotation()));
                MaxWrist=FMath::Max(MaxWrist,WristAngle);
                Row->SetNumberField(Side?TEXT("left_wrist_angle"):TEXT("right_wrist_angle"),WristAngle);
                if(HadPrevious)MaxStep=FMath::Max(MaxStep,FVector::Distance(P[2],Previous[Side]));
                if(HadPrevious&&C.Hands&&!(C.Hands&(1<<Side)))QuietStep=FMath::Max(QuietStep,FVector::Distance(P[2],Previous[Side]));
                Previous[Side]=P[2];Row->SetObjectField(Side?TEXT("left_bones"):TEXT("right_bones"),B);
                if(!C.Hands&&!C.Run)
                {
                    const auto Bore=(Weapon->GetSocketLocation(TEXT("WPN_FrontSight"))-Weapon->GetSocketLocation(TEXT("WPN_RearSight"))).GetSafeNormal();
                    const auto ExpectedAim=FRotator(State.AimPitch,Pawn->GetActorRotation().Yaw+C.Yaw,0).Vector();
                    AimDot=FMath::Min(AimDot,FVector::DotProduct(Bore,ExpectedAim));
                }
            }
            HadPrevious=true;Observations.Add(MakeShared<FJsonValueObject>(Row));
        }
        const FString Label=Prefix+C.Name;
        for(int32 I=0;I<4;++I)Check(Label+FString::Printf(TEXT("/depth %d"),I),Worst[I]<=.2,Worst[I]);
        Check(Label+TEXT("/gun attachment cm"),Contact<.5,Contact);
        Check(Label+TEXT("/gun attachment degrees"),ContactAngle<2.,ContactAngle);
        Check(Label+TEXT("/positive finite"),Finite);
        if(ReloadReview)
        {
            Check(Label+TEXT("/unadapted mechanical bones cm"),Mechanical<.1,Mechanical);
            Check(Label+TEXT("/all mechanical bones degrees"),MechanicalAngle<.1,MechanicalAngle);
            if(!Pawn->DualPistols->Hands[0].Revolver||!Pawn->DualPistols->Hands[1].Revolver)
            {
                Check(Label+TEXT("/magazine axial stroke cm"),MagazineAxialError<.1,MagazineAxialError);
                Check(Label+TEXT("/magazine rigid part cm"),MagazineRigidError<.1,MagazineRigidError);
                Check(Label+TEXT("/magazine seated contact cm"),MagazineSeatSamples>0&&MagazineSeatError<.1,MagazineSeatError);
            }
        }
        if(ReloadReview)Check(Label+TEXT("/native bone lengths cm"),BoneLengthError<.1,BoneLengthError);
        else Check(Label+TEXT("/native bent arms"),MaxReach<.97,MaxReach);
        Check(Label+TEXT("/wrist bend degrees"),MaxWrist<(C.Hands?90.:60.),MaxWrist);
        if(ArmSupport)
        {
            Check(Label+TEXT("/elbows on own side cm"),MinElbowSide>8.,MinElbowSide);
            if(LookSweep)Check(Label+TEXT("/60Hz elbow step cm"),MaxElbowStep<5.,MaxElbowStep);
            if(C.Pitch<=0.f&&C.Yaw==0.f)
            {
                Check(Label+TEXT("/lowered upper arms cm"),MinUpperDrop>8.,MinUpperDrop);
                Check(Label+TEXT("/upper arm flare cm"),MaxUpperFlare<12.,MaxUpperFlare);
            }
        }
        if(!C.Hands&&!C.Run)Check(Label+TEXT("/aim forward"),AimDot>.9,AimDot);
        if(C.Hands==1||C.Hands==2)Check(Label+TEXT("/quiet hand step cm"),QuietStep<1.,QuietStep);
        // Coarse sample distances are recorded, not called per-frame jitter.
        auto Motion=MakeShared<FJsonObject>();Motion->SetStringField(TEXT("case"),Label);
        Motion->SetNumberField(TEXT("max_sample_wrist_step_cm"),MaxStep);Observations.Add(MakeShared<FJsonValueObject>(Motion));
        if(Fine||LookSweep)Check(Label+TEXT("/60Hz wrist step cm"),MaxStep<5.,MaxStep);
    }
}
