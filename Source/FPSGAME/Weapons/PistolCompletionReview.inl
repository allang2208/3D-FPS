// User-requested current-revision checks: dual cosmetic props and presentation
// ingress/expiry, plus the active-set bug. No persistent profile is written.
Check(TEXT("fixture enables local third-person drops"),
    UDevelopmentTuningSubsystem::Find(Pawn)->SetEnabled(EDevelopmentTuningOption::ThirdPersonView,true,PC)&&Body->IsThirdPersonViewEnabled());
Body->GetBodyMesh()->SetComponentTickEnabled(false);
Pawn->GetCharacterMovement()->SetComponentTickEnabled(false);
// InitializeStandalone creates a trace-only world by default.
World->bShouldSimulatePhysics=true;
auto* DropFloorActor=World->SpawnActor<AActor>();
auto* DropFloor=NewObject<UBoxComponent>(DropFloorActor);DropFloorActor->SetRootComponent(DropFloor);
DropFloor->SetBoxExtent(FVector(2000,2000,5));DropFloor->SetCollisionObjectType(ECC_WorldStatic);
DropFloor->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);DropFloor->SetCollisionResponseToAllChannels(ECR_Block);
DropFloor->RegisterComponent();DropFloor->SetWorldLocation(FVector(0,0,395));
uint32 Sequence=100;
for(int32 ModelIndex=0;ModelIndex<5;++ModelIndex)
{
    const auto& V=Variants[ModelIndex];const bool Revolver=ModelIndex>=3;const int32 Capacity=ModelIndex==4?5:6;
    auto R=Model->CreateItem(V.Definition),L=Model->CreateItem(V.Definition);
    R.Place=L.Place=1;R.Cell=6;L.Cell=8;R.Magazine=L.Magazine=Revolver?Capacity:8;
    Model->Current=Seed;Model->Current.Items={R,L};Pawn->ApplyColdSteelProfile(Model);
    Pawn->DualPistols->InterruptActions();Pawn->WeaponState=EAKMWeaponState::Idle;Pawn->ActiveActionAnimation=nullptr;
    for(int32 Side=0;Side<2;++Side){Pawn->DualPistols->Hands[Side].Mesh->SetComponentTickEnabled(false);Pawn->DualPistols->Pose(Side,0.f);TickPose(Pawn->DualPistols->Hands[Side].Mesh);}
    Body->DisplayState=Body->SampleLocalState();Body->CaptureEquipment();
    Check(FString(V.Definition)+TEXT("/dual equipment"),Body->MotionBindings.Num()==2);if(Body->MotionBindings.Num()!=2)continue;
    const TArray<FString> Roles=Revolver?TArray<FString>{TEXT("speed_0"),TEXT("single_0_1"),TEXT("single_1_1")}:
        TArray<FString>{TEXT("reload"),TEXT("reload_empty")};
    for(const FString& Role:Roles)
    {
        const FString Prefix=FString(V.Definition)+TEXT("/")+Role;
        const bool Speed=Role.StartsWith(TEXT("speed_"));const bool Partial=Role==TEXT("single_1_1");
        const float Length=Revolver?(Speed?3.85f:DanWesson715WeaponAssets::SingleDuration(1,!Partial)):Role==TEXT("reload_empty")?2.25f:1.75f;
        const float Eject=Revolver?(Speed?DanWesson715WeaponAssets::Eject/3.6f*3.85f:
            Partial?DanWesson715WeaponAssets::Open+.06f:ModelIndex==4?DanWesson715WeaponAssets::Eject:DanWesson715WeaponAssets::EmptyCaseClear):.3167f;
        for(int32 Side=0;Side<2;++Side)
        {
            auto& H=Pawn->DualPistols->Hands[Side];Pawn->DualPistols->StartAction(Side,Role,1.f);
            H.Reloading=true;H.ReloadSpeedloader=Speed;H.SourceLength=Length;
            H.ReloadStart=Partial?1:0;H.ReloadCount=Revolver?(Speed?Capacity:1):8;
            H.Rounds=H.ReloadStart;H.Cases=Capacity;H.ActionStarted=World->GetTimeSeconds();
            Body->MotionBindings[Side].Revolver.StartedAt=-100.f;Body->MotionBindings[Side].MagazineReloadStartedAt=-100.f;
        }
        TSet<TWeakObjectPtr<AActor>> OldDrops;
        if(Revolver)for(const auto& Drop:Body->DroppedRevolverCases)OldDrops.Add(Drop);
        else for(const auto& Drop:Body->DroppedPistolMagazines)OldDrops.Add(Drop);
        bool Props=true,ReleaseClock=true,Finite=true;double Depth=0.,SeatError=0.,Mechanical=0.;
        const int32 Steps=FMath::CeilToInt(Length*30.f);
        for(int32 Step=0;Step<=Steps;++Step)
        {
            const float Time=FMath::Min(Length-.001f,float(Step)/Steps*Length);
            for(int32 Side=0;Side<2;++Side)
            {
                auto& H=Pawn->DualPistols->Hands[Side];H.ActionTime=Time/Length*H.Action->GetPlayLength();
                H.ActionBlendStarted=World->GetTimeSeconds()-1.f;H.ActionRate=0.f;
                const float Seat=Revolver?(Speed?DanWesson715WeaponAssets::Seat/3.6f*3.85f:DanWesson715WeaponAssets::SingleSeatTime(0,!Partial)):1.05f;
                H.Rounds=(Partial?1:0)+(Time>=Seat?H.ReloadCount:0);H.Cases=Time<Eject?Capacity:H.Rounds;
                Pawn->DualPistols->Pose(Side,0.f);TickPose(H.Mesh);
            }
            auto State=Body->SampleLocalState();State.LastShotAt=State.LeftHand.LastShotAt=State.RightHand.LastShotAt=-100.f;
            Body->CaptureMotion(State);Body->DisplayState=State;Body->ApplyMotion(1.f/30.f);
            auto* Anim=Body->BodyAnimation.Get();Anim->BodyState=Anim->UpperState=Anim->MotionState=State;
            Anim->Clock=100.f+Time;Anim->UpperAlpha=Anim->MotionAlpha=Anim->CrouchAlpha=Anim->AimAlpha=Anim->SprintAlpha=0.f;
            TickPose(Body->GetBodyMesh(),1.f/30.f);
            if(Step%3==0)SkinProbe.Update(Body->GetBodyMesh());
            auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Prefix);Row->SetNumberField(TEXT("source_time"),Time);
            for(int32 Side=0;Side<2;++Side)
            {
                auto& B=Body->MotionBindings[Side];auto* Weapon=B.Mesh.Get();Weapon->UpdateComponentToWorld();Weapon->UpdateChildTransforms();
                const auto Root=Weapon->GetSocketTransform(TEXT("WPN_root"),RTS_Component);
                Finite&=!Root.ContainsNaN()&&Root.GetScale3D().GetMin()>0.;
                if(Step%3==0)
                {
                    Depth=FMath::Max(Depth,SkinProbe.Arm(Side).Depth);Depth=FMath::Max(Depth,SkinProbe.Weapon(Weapon,Body->GetBodyMesh()->GetComponentTransform()).Depth);
                    FPistolReloadSkinProbe::FResult Loose;
                    for(const auto& Part:B.Revolver.IncomingRounds)SkinProbe.Part(Loose,Part.Get(),Body->GetBodyMesh()->GetComponentTransform());
                    SkinProbe.Part(Loose,B.Revolver.Loader.Get(),Body->GetBodyMesh()->GetComponentTransform());Depth=FMath::Max(Depth,Loose.Depth);
                }
                if(Revolver)
                {
                    const auto& RR=B.Revolver;Props&=RR.bPrepared;
                    ReleaseClock&=RR.bDropped==(Time>=Eject);
                    int32 VisibleRounds=0;for(const auto& Part:RR.IncomingRounds)if(Part.IsValid()&&Part->IsVisible()&&!Part->bHiddenInGame)++VisibleRounds;
                    const float Seat=Speed?DanWesson715WeaponAssets::Seat/3.6f*3.85f:DanWesson715WeaponAssets::SingleSeatTime(0,!Partial);
                    const float Appear=Speed?DanWesson715WeaponAssets::RoundsVisible/3.6f*3.85f:Seat-.48f;
                    Props&=VisibleRounds==((Time>=Appear&&Time<Seat)?(Speed?Capacity:1):0);
                    Row->SetNumberField(Side?TEXT("left_rounds"):TEXT("right_rounds"),VisibleRounds);
                    Row->SetBoolField(Side?TEXT("left_dropped"):TEXT("right_dropped"),RR.bDropped);
                    const auto* Native=Pawn->DualPistols->Hands[Side].Mesh.Get();
                    const auto NativeCylinder=Native->GetSocketTransform(TEXT("WPN_Cylinder"),RTS_Component).GetRelativeTransform(Rigid(Native->GetSocketTransform(TEXT("WPN_root"),RTS_Component)));
                    const auto ActualCylinder=Weapon->GetSocketTransform(TEXT("WPN_Cylinder"),RTS_Component).GetRelativeTransform(Rigid(Root));
                    Mechanical=FMath::Max(Mechanical,FVector::Distance(NativeCylinder.GetLocation(),ActualCylinder.GetLocation()));
                }
                else
                {
                    Props&=B.bMagazineOverride&&B.bMagazineHidden==(Time>=.3167f&&Time<.78f);
                    ReleaseClock&=B.bMagazineDropped==(Time>=.3167f);
                    if(Time>=1.05f)
                    {
                        const auto Seat=B.FrozenPose[B.MagazineBone].GetRelativeTransform(Rigid(B.FrozenPose[B.NativeWeaponRoot]))*Rigid(Root);
                        const auto Displayed=Weapon->GetSocketTransform(TEXT("WPN_SOCKET_Magazine"),RTS_Component);
                        SeatError=FMath::Max(SeatError,FVector::Distance(Seat.GetLocation(),Displayed.GetLocation()));
                    }
                }
            }
            Observations.Add(MakeShared<FJsonValueObject>(Row));
            FString GeometryDir;
            if(Step==Steps/2&&FParse::Value(*Params,TEXT("Geometry="),GeometryDir))
            {
                TArray<USkeletalMeshComponent*> Meshes={Body->GetBodyMesh()};TArray<UStaticMeshComponent*> Parts;
                for(const auto& B:Body->MotionBindings)
                {
                    Meshes.Add(B.Mesh.Get());for(const auto& Part:B.Parts)if(Part.IsValid())Parts.Add(Part.Get());
                    for(const auto& Part:B.Revolver.IncomingRounds)if(Part.IsValid())Parts.Add(Part.Get());if(B.Revolver.Loader.IsValid())Parts.Add(B.Revolver.Loader.Get());
                }
                FPSPistolReviewGeometry::Save(GeometryDir/(Prefix.Replace(TEXT("/"),TEXT("_"))+TEXT("_dual.obj")),Meshes,Parts,Body->GetBodyMesh()->GetComponentTransform());
            }
            ++GFrameCounter;World->Tick(LEVELTICK_All,1.f/30.f);
        }
        Check(Prefix+TEXT("/prop phase visibility"),Props);Check(Prefix+TEXT("/ejection matches native commit clock"),ReleaseClock);
        Check(Prefix+TEXT("/finite gun transform"),Finite);Check(Prefix+TEXT("/skin torso depth cm"),Depth<=.2,Depth);
        Check(Prefix+TEXT("/seated magazine cm"),SeatError<.1,SeatError);Check(Prefix+TEXT("/cylinder relative to gun cm"),Mechanical<.1,Mechanical);
        const int32 ExpectedDrops=Revolver?2*(Capacity-(Partial?1:0)):2;
        int32 ActualDrops=0;
        if(Revolver)for(const auto& Drop:Body->DroppedRevolverCases)ActualDrops+=!OldDrops.Contains(Drop);
        else for(const auto& Drop:Body->DroppedPistolMagazines)ActualDrops+=!OldDrops.Contains(Drop);
        Check(Prefix+TEXT("/one release per hand"),ActualDrops==ExpectedDrops,ActualDrops);
        for(int32 Settle=0;Settle<30;++Settle){++GFrameCounter;World->Tick(LEVELTICK_All,1.f/60.f);}
        bool OnGround=ActualDrops==ExpectedDrops;
        const auto CheckDrop=[&](const TWeakObjectPtr<AActor>& Drop)
        {
            if(OldDrops.Contains(Drop)||!Drop.IsValid())return;
            const auto* Physics=Cast<UBoxComponent>(Drop->GetRootComponent());FVector Center,Extent;Drop->GetActorBounds(true,Center,Extent);
            OnGround&=Physics&&Physics->IsSimulatingPhysics()&&FMath::Abs(Center.Z-Extent.Z-400.)<2.;
            auto Ground=MakeShared<FJsonObject>();Ground->SetStringField(TEXT("case"),Prefix+TEXT("/ground"));
            Ground->SetStringField(TEXT("actor"),Drop->GetName());Ground->SetStringField(TEXT("center"),Center.ToString());
            Ground->SetNumberField(TEXT("bottom_cm"),Center.Z-Extent.Z);Ground->SetBoolField(TEXT("simulating"),Physics&&Physics->IsSimulatingPhysics());
            Observations.Add(MakeShared<FJsonValueObject>(Ground));
        };
        if(Revolver)for(const auto& Drop:Body->DroppedRevolverCases)CheckDrop(Drop);
        else for(const auto& Drop:Body->DroppedPistolMagazines)CheckDrop(Drop);
        Check(Prefix+TEXT("/dropped props land on static floor"),OnGround);

        auto Packet=Body->DisplayState;Packet.PresentationSampledAt=Body->ServerClock();
        Body->AcceptBodyPresentation(Packet,++Sequence);
        Check(Prefix+TEXT("/authority relays both hand clocks"),Body->ReplicatedState.LeftHand.bReloading&&Body->ReplicatedState.RightHand.bReloading&&
            FMath::IsNearlyEqual(Body->ReplicatedState.LeftHand.ReloadSourceLength,Length));
        const auto Accepted=Body->ReplicatedState;auto Old=Packet;Old.LeftHand.Progress=0.f;
        Body->AcceptBodyPresentation(Old,Sequence-1);
        Check(Prefix+TEXT("/older sequence rejected"),FMath::IsNearlyEqual(Body->ReplicatedState.LeftHand.Progress,Accepted.LeftHand.Progress));
        auto Wrong=Packet;Wrong.OffhandInstance=TEXT("old-loadout");Body->AcceptBodyPresentation(Wrong,++Sequence);
        Check(Prefix+TEXT("/wrong loadout rejected"),Body->ReplicatedState.Contacts.Rigs.IsEmpty()&&!Body->ReplicatedState.LeftHand.bReloading);
        Body->AcceptBodyPresentation(Packet,++Sequence);Body->LastPresentationReceivedAt=Body->ServerClock()-1.f;
        const auto Expired=Body->SampleRemoteAuthorityState();
        Check(Prefix+TEXT("/lease ends reload"),!Expired.LeftHand.bReloading&&!Expired.RightHand.bReloading&&Expired.Contacts.Rigs.IsEmpty());
        for(int32 Side=0;Side<2;++Side){Pawn->DualPistols->StopAction(Side);Pawn->DualPistols->Pose(Side,0.f);TickPose(Pawn->DualPistols->Hands[Side].Mesh);}
        auto Idle=Body->SampleLocalState();Body->CaptureMotion(Idle);Body->DisplayState=Idle;Body->ApplyMotion(1.f);
        bool Hidden=true;for(const auto& B:Body->MotionBindings)
        {for(const auto& Part:B.Revolver.IncomingRounds)Hidden&=!Part.IsValid()||!Part->IsVisible()||Part->bHiddenInGame;
         Hidden&=!B.Revolver.Loader.IsValid()||!B.Revolver.Loader->IsVisible()||B.Revolver.Loader->bHiddenInGame;}
        Check(Prefix+TEXT("/reload props cleared on return"),Hidden);
        Body->UpdateWorldWeaponPresentation();Hidden=true;
        for(const auto& B:Body->MotionBindings)
        {for(const auto& Part:B.Revolver.IncomingRounds)Hidden&=!Part.IsValid()||!Part->IsVisible()||Part->bHiddenInGame;
         Hidden&=!B.Revolver.Loader.IsValid()||!B.Revolver.Loader->IsVisible()||B.Revolver.Loader->bHiddenInGame;}
        Check(Prefix+TEXT("/equipment visibility cannot revive reload props"),Hidden);
    }
    for(int32 Active:{6,9})
    {
        auto Lone=Model->CreateItem(V.Definition);Lone.Place=1;Lone.Cell=Active==6?8:11;Lone.Magazine=Revolver?1:0;
        if(Revolver)
        {
            TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Lone.Data),Data);
            Data->SetNumberField(TEXT("revolver_case_count"),Capacity);Lone.Data.Reset();
            FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Lone.Data));
        }
        Model->Current=Seed;Model->Current.ActiveWeaponSlot=Active;Model->Current.Items={Lone};Pawn->ApplyColdSteelProfile(Model);
        Check(FString(V.Definition)+FString::Printf(TEXT("/set_%d own offhand active"),Active),Pawn->IsLoneOffhandPistol());
        if(Revolver)
        {
            Pawn->DualPistols->InterruptActions();Pawn->bInventoryWeaponReady=true;
            Model->Current.AmmoPouch.Add(Model->AmmoDefinitionFor(Lone),Capacity);
            Pawn->DualPistols->BeginReload(1);auto& H=Pawn->DualPistols->Hands[1];
            const FString Label=FString(V.Definition)+FString::Printf(TEXT("/set_%d real partial reload/"),Active);
            Check(Label+TEXT("does not skip spent cases"),H.Reloading&&!H.CasesCleared);
            if(H.Action&&H.Reloading)
            {
                H.ActionTime=(DanWesson715WeaponAssets::Open+.061f)/H.SourceLength*H.Action->GetPlayLength();
                Pawn->DualPistols->AdvanceReload(1,0.f);
                const auto* Item=Model->FindItem(Lone.InstanceId);
                Check(Label+TEXT("eject preserves one live round"),Item&&Item->Magazine==1&&
                    int32(ColdSteelInventory::Number(*Item,TEXT("revolver_case_count"),0))==1&&H.CasesCleared);
                const int32 Count=H.ReloadCount;
                for(int32 Round=0;Round<Count&&H.Action;++Round)
                {
                    const float Before=H.ActionTime/H.Action->GetPlayLength()*H.SourceLength;
                    H.ActionTime=(DanWesson715WeaponAssets::SingleSeatTime(Round,false)+.001f)/H.SourceLength*H.Action->GetPlayLength();
                    Pawn->DualPistols->AdvanceReload(1,Before);
                }
                if(H.Action)
                {
                    const float Before=H.ActionTime/H.Action->GetPlayLength()*H.SourceLength;
                    H.ActionTime=H.Action->GetPlayLength();Pawn->DualPistols->AdvanceReload(1,Before);Pawn->DualPistols->Advance(.016f);
                }
                Check(Label+TEXT("completes without loop"),!H.Reloading&&H.Rounds==Capacity);
            }
        }
        Model->Current.ActiveWeaponSlot=Active==6?9:6;Pawn->ApplyColdSteelProfile(Model);
        Body->DisplayState=Body->SampleLocalState();Body->CaptureEquipment();
        Check(FString(V.Definition)+FString::Printf(TEXT("/set_%d empty group no pistol or reload"),Active),!Pawn->IsLoneOffhandPistol()&&!Pawn->DualPistols->IsActive()&&
            !Pawn->DualPistols->IsReloading()&&Body->MotionBindings.IsEmpty());
        auto Staff=Model->CreateItem(TEXT("ue_apprentice_staff"));Staff.Place=1;Staff.Cell=Active;
        Model->Current.Items.Add(Staff);Model->Current.ActiveWeaponSlot=Active;Pawn->ApplyColdSteelProfile(Model);
        Body->DisplayState=Body->SampleLocalState();Body->CaptureEquipment();
        int32 PistolBindings=0;for(const auto& B:Body->MotionBindings)PistolBindings+=B.Definition.GunInstance==Lone.InstanceId;
        Check(FString(V.Definition)+FString::Printf(TEXT("/set_%d staff has exactly its paired pistol"),Active),
            !Pawn->IsLoneOffhandPistol()&&PistolBindings==1&&Body->DisplayState.OffhandInstance==Lone.InstanceId);
        Model->Current.ActiveWeaponSlot=Active==6?9:6;Pawn->ApplyColdSteelProfile(Model);
        Body->DisplayState=Body->SampleLocalState();Body->CaptureEquipment();
        Check(FString(V.Definition)+FString::Printf(TEXT("/set_%d staff offhand does not leak into empty group"),Active),
            !Pawn->IsLoneOffhandPistol()&&!Pawn->DualPistols->IsActive()&&Body->MotionBindings.IsEmpty());
    }
}
