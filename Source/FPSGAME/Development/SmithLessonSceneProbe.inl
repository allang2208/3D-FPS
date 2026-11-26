// Included inside the opt-in village network fixture to reuse its peer and evidence helpers.
    void CaptureSmithLighting(UWorld* W,APlayerController* PC,ASmithYardShelter* Yard)
    {
        const auto Pose=Yard->GetActorTransform();
        const FVector Aim=Pose.TransformPosition(FVector(0,0,110));
        const FVector Eye=Pose.TransformPosition(FVector(590,380,210));
        auto* Camera=W->SpawnActor<ACameraActor>(Eye,(Aim-Eye).Rotation());
        if(!Camera)return;
        Camera->GetCameraComponent()->SetFieldOfView(76);
        PC->bAutoManageActiveCameraTarget=false;PC->SetViewTarget(Camera);
        TArray<TWeakObjectPtr<UPointLightComponent>> Lights;
        for(TActorIterator<AVillageShopChainLamp> It(W);It;++It)
            if(auto* Light=It->FindComponentByClass<UPointLightComponent>())Lights.Add(Light);
        const FString File=Folder/TEXT("yard-frame-times.csv");
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda(
            [Lights,File,Phase=0,Frame=0,Rows=FString(TEXT("phase,original,frame,game_ms,render_ms,gpu_ms\n"))](float) mutable
            {
                const bool Original=Phase==0||Phase==3;
                if(Frame==0)for(const auto& Weak:Lights)if(auto* Light=Weak.Get())Light->SetHiddenInGame(!Original);
                if(++Frame>90)Rows+=FString::Printf(TEXT("%d,%d,%d,%.3f,%.3f,%.3f\n"),Phase,int(Original),Frame-90,
                    FPlatformTime::ToMilliseconds(GGameThreadTime),FPlatformTime::ToMilliseconds(GRenderThreadTime),
                    FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles(0)));
                if(Frame<180)return true;
                Frame=0;
                if(++Phase<4)return true;
                FFileHelper::SaveStringToFile(Rows,*File,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
                return false;
            }));
    }
    bool SmithLessonScene(UWorld* W,ATemperateHillsWorld& H,const FSite& Site)
    {
        namespace Smith = BlacksmithApprenticeship;
        auto* Local=W->GetFirstPlayerController();
        auto* M=W->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        if(!Local||!Local->GetPawn()||!M||!M->ProfileView().NetworkProfileId.IsValid())return true;
        int32 Lamps=0,Bays=0,Canopies=0;
        for(TActorIterator<AVillageShopChainLamp> It(W);It;++It)++Lamps;
        for(TActorIterator<ASmithYardFurnace> It(W);It;++It)if(It->IsSceneStationAvailable())++Bays;
        for(TActorIterator<ASmithYardShelter> It(W);It;++It)++Canopies;
        const auto Stage=Smith::Stage(M->ProfileView());
        const int64 Picks=CountItem(*M,TEXT("tool_pickaxe")),OreCount=CountItem(*M,TEXT("iron_ore"));
        const FString Holdings=FString::Printf(TEXT("pickaxes=%lld ore=%lld"),Picks,OreCount);
        Last=FString::Printf(TEXT("stage=%d lamps=%d bays=%d shelters=%d %s"),int32(Stage),Lamps,Bays,Canopies,*Holdings);
        const bool Yard=H.IsVillageBlacksmithRepaired()&&Bays==2&&Canopies==1&&Lamps==18;
        if(Role==TEXT("owner")&&Step>=3)
        {
            for(TActorIterator<AFPSGAMECharacter> It(W);It;++It)
            {
                if(It->IsLocallyControlled())continue;
                const auto* Guard=It->FindComponentByClass<UEagleTalonGuardComponent>();
                const auto* Field=FindFProperty<FStructProperty>(UEagleTalonGuardComponent::StaticClass(),TEXT("Charge"));
                const auto* Value=Guard&&Field?Field->ContainerPtrToValuePtr<FEagleGuardCharge>(Guard):nullptr;
                if(!Value||Value->Weapon.IsEmpty())continue;
                if(Value->Blocks==6&&!Has(TEXT("owner.eagle-ready")))Record(TEXT("eagle-ready"),true,TEXT("replicated six blocks"));
                if(Value->Blocks==0&&Has(TEXT("server.eagle-spent"))&&!Has(TEXT("owner.eagle-spent")))Record(TEXT("eagle-spent"),true,TEXT("replicated consumption"));
            }
        }
        if(Role==TEXT("rejoin"))
        {
            if(!Yard||Stage!=Smith::EStage::Smelting)return true;
            FString Saved;
            TSharedPtr<FJsonObject> Previous;
            const bool Loaded=FFileHelper::LoadFileToString(Saved,*(Folder/TEXT("owner.delivered.json")))
                && FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Saved),Previous) && Previous.IsValid();
            Record(TEXT("restored"),Loaded&&Previous->GetStringField(TEXT("detail"))==Holdings,Last);
            return false;
        }
        if(Role==TEXT("owner"))
        {
            auto* PS=Local->GetPlayerState<AColdSteelPlayerState>();
            auto* D=Local->FindComponentByClass<UChapelDialogueComponent>();
            if(!D||!PS)return true;
            if(Step==0&&Site.bSmithStation&&!H.IsVillageBlacksmithRepaired()&&Lamps==2)
            {Record(TEXT("ruins"),Bays==0&&Canopies==0,Last);Advance();}
            else if(Step==1&&Yard&&Site.Smith&&Has(TEXT("server.at-smith"))&&Site.Smith->CanTradeWith(Local->GetPawn()))
            {Pickaxes=Picks;SmithStartingOre=OreCount;Record(TEXT("repaired-yard"),true,Last);D->OpenArtisan(Site.Smith);Advance();}
            else if(Step==2&&D->IsBlacksmith()&&D->IsOpen()&&!D->IsPending())
            {D->RequestSmithTraining();Advance();}
            else if(Step==3&&Stage==Smith::EStage::Mining&&Picks==Pickaxes+1)
            {Record(TEXT("accepted"),true,Last);Advance();}
            else if(Step==4&&Has(TEXT("server.ore-drop")))
            {
                if(Stage==Smith::EStage::ReturnOre&&OreCount==SmithStartingOre+10&&!D->IsPending())
                {Record(TEXT("ten-ore"),true,Last);D->RequestSmithTraining();Advance();}
                else if(FPlatformTime::Seconds()>HoldAt)
                {PS->RequestInventoryAction(EColdSteelInventoryAction::PickupNearby);HoldAt=FPlatformTime::Seconds()+3.;}
            }
            else if(Step==5&&Has(TEXT("owner.eagle-spent"))&&Stage==Smith::EStage::Smelting&&OreCount==SmithStartingOre+3)
            {Record(TEXT("delivered"),Picks==Pickaxes+1&&CountItem(*M,TEXT("search_forging_alloy_blank"))>=1,Holdings);return false;}
            return true;
        }
        APlayerController* Guest=nullptr;
        for(auto It=W->GetPlayerControllerIterator();It;++It)
            if(It->Get()&&!It->Get()->IsLocalController()){Guest=It->Get();break;}
        if(Step==3&&Has(TEXT("owner.eagle-ready"))&&!Has(TEXT("server.eagle-spent")))
        {
            const auto* Item=M->Equipped();
            const bool Spent=Item&&UEagleTalonGuardComponent::Commit(Local->GetPawn(),Item->InstanceId,EEagleStrike::Whirlwind,17);
            Record(TEXT("eagle-spent"),Spent&&!UEagleTalonGuardComponent::Ready(M)&&UEagleTalonGuardComponent::WasEmpowered(Local->GetPawn(),Item->InstanceId,EEagleStrike::Whirlwind,17),TEXT("one authorized skill receipt"));
        }
        if(Step==3&&Has(TEXT("owner.delivered"))&&!Guest)
        {Record(TEXT("disconnected"),Stage==Smith::EStage::NotStarted,Last);Advance();}
        if(Step==4&&Has(TEXT("rejoin.restored"))&&(!FParse::Param(FCommandLine::Get(),TEXT("RenderOffScreen"))||IFileManager::Get().FileExists(*(Folder/TEXT("yard-frame-times.csv")))))
        {Record(TEXT("done"),Yard&&Stage==Smith::EStage::NotStarted,Last);return false;}
        if(!Guest||!Guest->GetPawn())return true;
        if(Step==0&&Has(TEXT("owner.ruins"))&&Site.bSmithStation&&Site.bCarpenterStation)
        {
#if DO_ENABLE_NET_TEST
            const auto Sim=W->GetNetDriver()->PacketSimulationSettings;
            Record(TEXT("transport"),Sim.PktLag==60&&Sim.PktLoss==2,FString::Printf(TEXT("lag=%d loss=%d"),Sim.PktLag,Sim.PktLoss));
#endif
            FText Reason;
            for(FName Plan:{FName(TEXT("blacksmith")),FName(TEXT("carpenter")),FName(TEXT("herbalist")),FName(TEXT("tavern")),FName(TEXT("windmill")),FName(TEXT("bakery")),FName(TEXT("gunshop"))})
            {
                const bool Repaired=H.UnlockVillagePlan(Plan,Reason);
                Record(TEXT("repair-")+Plan.ToString(),Repaired,Reason.ToString());
            }
            Advance();
        }
        else if(Step==1&&Yard&&H.bReady&&Position(Guest,Site.Smith))
        {
            if(FParse::Param(FCommandLine::Get(),TEXT("RenderOffScreen")))
                for(TActorIterator<ASmithYardShelter> It(W);It;++It){CaptureSmithLighting(W,Local,*It);break;}
            Record(TEXT("at-smith"),true,Last);Advance();
        }
        else if(Step==2&&Has(TEXT("owner.accepted")))
        {
            auto P=M->Snapshot();
            P.ActiveWeaponSlot=6;P.ActiveProductionTool.Reset();
            P.Items.RemoveAll([](const FColdSteelItem& I){return I.Place==1&&I.Cell==6;});
            auto Sword=M->CreateItem(TEXT("ue_forged_steel_greatsword"));
            TSharedPtr<FJsonObject> Data;
            if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Sword.Data),Data)||!Data)return Finish();
            auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("guard"),TEXT("eagle_talon_guard"));
            Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Sword.Data.Reset();
            FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Sword.Data));
            Sword.Place=1;Sword.Cell=6;P.Items.Add(Sword);
            auto* Guard=Local->GetPawn()->FindComponentByClass<UEagleTalonGuardComponent>();
            if(!Guard||!M->CommitState(P)){Record(TEXT("equip"),false,M->ResultMessage());return Finish();}
            Guard->Equip(M);
            auto* Enemy=W->SpawnActor<AActor>();Enemy->Tags.Add(TEXT("Enemy"));
            Guard->Defended(Sword.InstanceId,Enemy,false);
            Guard->Defended(Sword.InstanceId,Enemy,true);Guard->Defended(Sword.InstanceId,Enemy,true);
            const bool Five=!UEagleTalonGuardComponent::Ready(M);
            Guard->Defended(Sword.InstanceId,Enemy,false);Enemy->Destroy();
            Record(TEXT("eagle-six"),Five&&UEagleTalonGuardComponent::Ready(M)&&ColdSteelMelee::AttackStamina(M->Equipped(),M)==0.&&M->DashAttackStats(1).StaminaCost==0.,
                TEXT("two parries plus two blocks; ready basic and dash stamina costs"));
            // Stage a genuine shared drop. From here the guest uses the normal pickup and dialogue RPCs.
            auto* Shared=W->GetSubsystem<UColdSteelSharedInventorySubsystem>();
            auto Ore=M->CreateItem(TEXT("iron_ore"),10);
            Ore.Place=2;Ore.Cell=-1;Ore.bFreshMinedIron=true;Ore.Map=UGameplayStatics::GetCurrentLevelName(W,true);
            Ore.Position=Guest->GetPawn()->GetActorLocation()+FVector(0,0,-42);
            Record(TEXT("ore-drop"),Stage==Smith::EStage::NotStarted&&Shared&&Shared->AddWorldDrops({Ore}),Last);
            Advance();
        }
        return true;
    }
