// Source/FPSGAME/Building/VoxelBuildWorldCasting.cpp — whole method
void AVoxelBuildWorld::RegisterSceneStation(AVoxelBuildPrefabActor* Station)
{
    if(!IsValid(Station)||Station->GetOwner()!=this||!Station->IsSceneStationAvailable()||Station->PrefabId().IsNone())return;
    UnregisterSceneStation(Station);
    const FIntVector Cell=Station->AnchorCell();
    if(Prefabs.ContainsByPredicate([Cell](const auto& P){return P.Cell==Cell;}))
    {UE_LOG(LogTemp,Warning,TEXT("Village station %s overlaps existing construction at %s"),*Station->GetName(),*Cell.ToString());return;}
    SceneStations.Add(Cell,Station);
}

// Source/FPSGAME/Building/VoxelBuildWorldCasting.cpp — whole method
void AVoxelBuildWorld::UnregisterSceneStation(AVoxelBuildPrefabActor* Station)
{
    for(auto It=SceneStations.CreateIterator();It;++It)
        if(!It.Value().IsValid()||It.Value().Get()==Station)It.RemoveCurrent();
}

// Source/FPSGAME/Building/VoxelBuildWorldCasting.cpp — whole method
AVoxelBuildPrefabActor* AVoxelBuildWorld::PrefabActorAt(FIntVector Cell) const
{
    if(auto* Scene=SceneStations.FindRef(Cell).Get())return Scene;
    if(auto* Found=Cast<AVoxelBuildPrefabActor>(PrefabActors.FindRef(Cell).Get()))return Found;
    if(!HasAuthority())for(TActorIterator<AVoxelBuildPrefabActor> It(GetWorld());It;++It)
        if(It->GetOwner()==this&&It->AnchorCell()==Cell&&!It->IsSceneStation()&&!It->PrefabId().IsNone()&&!It->IsFalling())
        {const_cast<AVoxelBuildWorld*>(this)->PrefabActors.Add(Cell,*It);return *It;}
    return nullptr;
}

// Source/FPSGAME/Building/WoodworkingSystem.cpp — whole method
void UWoodworkingSystem::Tick(float)
{
    if(!BoundStation.IsExplicitlyNull()&&!ColdSteelStationNet::IsClient(this))
    {
        const auto* Piece=Cast<AVoxelBuildPrefabActor>(Station());
        const auto* Building=Piece?Cast<AVoxelBuildWorld>(Piece->GetOwner()):nullptr;
        if(!Building||Piece->PrefabId()!=VoxelWoodworkingBenchId||Piece->IsFalling()||Building->PrefabActorAt(Piece->AnchorCell())!=Piece)
        {
            NetworkUnavailable(TEXT("木工工作台已不可用，加工已暂停"));
            return;
        }
    }
    AdvanceClock();
    if(Phase==EWoodworkingPhase::Running&&HasPendingJob()&&!ColdSteelStationNet::IsClient(this)&&FPlatformTime::Seconds()>=NextCheckpointAt)
    {NextCheckpointAt=FPlatformTime::Seconds()+5;SaveCheckpoint();}
}

// Source/FPSGAME/Building/WoodworkingSystem.cpp — whole method
void UWoodworkingSystem::NetworkUnavailable(const FString& Reason)
{
    FrozenElapsed=Elapsed();bMotorOn=false;
    Close();BoundStation.Reset();Notice=Reason;
}

// Source/FPSGAME/Building/AlchemySystem.cpp — whole method
bool UColdSteelAlchemySystem::Reachable() const
{
    const auto* B=Bench.Get();const auto* P=WorkingPawn.Get();
    if(!B||B->PrefabId()!=FName(TEXT("potion_workbench"))||!P||B->GetWorld()!=GetWorld()||B->GetWorld()!=P->GetWorld()||B->IsFalling()||!P->GetController()||P->GetController()->GetPawn()!=P)return false;
    const auto* W=Cast<AVoxelBuildWorld>(B->GetOwner());if(!W||!W->HasPrefabAt(B->AnchorCell())||W->PrefabActorAt(B->AnchorCell())!=B)return false;
    if(const auto* H=P->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead())return false;
    const FVector Near=B->Body()->Bounds.GetBox().GetClosestPointTo(P->GetPawnViewLocation());
    if(FVector::DistSquared(Near,P->GetPawnViewLocation())>FMath::Square(350.f))return false;
    FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(AlchemyReach),false,P);
    return !GetWorld()->LineTraceSingleByChannel(Hit,P->GetPawnViewLocation(),Near,ECC_Visibility,Q)||Hit.GetActor()==B;
}

// Source/FPSGAME/Building/FPSForgeWorkComponent.cpp — whole method
bool UFPSForgeWorkComponent::StationValid() const
{
    const auto* S=State.Station.Get();const auto* W=S?Cast<AVoxelBuildWorld>(S->GetOwner()):nullptr;
    return S&&ColdSteelWorldInteraction::IsForgingStation(S)&&W&&W->HasPrefabAt(S->AnchorCell())&&W->PrefabActorAt(S->AnchorCell())==S&&S->Body()->GetComponentTransform().Equals(State.StationFrame,.1f);
}

// Source/FPSGAME/Building/FPSForgeWorkComponent.cpp — whole method
bool UFPSForgeWorkComponent::CanEnter(AVoxelBuildPrefabActor* Station,FString& Reason) const
{
    if(!ReadyForEntry(Reason))return false;
    const auto* Pawn=Character.Get();const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* World=Station?Cast<AVoxelBuildWorld>(Station->GetOwner()):nullptr;
    if(!Pawn||!Station||Station->IsFalling()||!World||!World->HasPrefabAt(Station->AnchorCell())||World->PrefabActorAt(Station->AnchorCell())!=Station||
       !ColdSteelWorldInteraction::IsForgingStation(Station)||!Health||Health->IsDead()||UFPSFurnitureRestComponent::IsResting(Pawn))
    {Reason=TEXT("角色或铸造台当前无法操作");return false;}
    // Match the station interaction reach. No authored feet, travel corridor,
    // quench-bucket stance, full-body clips or tool grips are needed to enter.
    const FVector Eye=Pawn->GetPawnViewLocation();
    const FVector Near=Station->GetComponentsBoundingBox(true).GetClosestPointTo(Eye);
    FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(ForgeStationReach),false,Pawn);
    if(FVector::DistSquared(Eye,Near)>FMath::Square(500.f)||
       (GetWorld()->LineTraceSingleByChannel(Hit,Eye,Near,ECC_Visibility,Query)&&Hit.GetActor()!=Station))
    {Reason=TEXT("请靠近可操作的铸造台");return false;}
    for(TActorIterator<AFPSGAMECharacter> It(GetWorld());It;++It)
        if(*It!=Pawn)if(const auto* Occupant=It->FindComponentByClass<UFPSForgeWorkComponent>();Occupant&&Occupant->IsWorking()&&Occupant->Station()==Station)
        {Reason=TEXT("这张铸造台正有人使用");return false;}
    return true;
}

// Source/FPSGAME/Multiplayer/ColdSteelStationNetwork.cpp — whole method
bool AColdSteelPlayerState::StationReach(FName Kind,AActor* Target) const
{
    const auto* Pawn=GetPawn();const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!Pawn||!Health||Health->IsDead())return false;
    const auto Reachable=[&](const AVoxelBuildPrefabActor* Piece)
    {
        if(!IsValid(Piece)||Piece->GetWorld()!=GetWorld())return false;
        const auto* World=Cast<AVoxelBuildWorld>(Piece->GetOwner());
        if(Piece->IsFalling()||!World||!World->HasPrefabAt(Piece->AnchorCell()))return false;
        const bool Matches=Kind==TEXT("forge")?ColdSteelWorldInteraction::IsForgingStation(Piece):
            Kind==TEXT("wood")?ColdSteelWorldInteraction::IsWoodworkingBench(Piece):
            Kind==TEXT("enhancement")?ColdSteelWorldInteraction::IsEnhancementBench(Piece):
            (Kind==TEXT("assembly")||Kind==TEXT("ammo"))?Piece->PrefabId()==VoxelGunWorkbenchId:
            Kind==TEXT("craft")&&Piece->PrefabId()==VoxelWorkbenchId;
        if(!Matches)return false;
        if((Kind==TEXT("enhancement")||Kind==TEXT("forge")||Kind==TEXT("wood"))&&World->PrefabActorAt(Piece->AnchorCell())!=Piece)return false;
        const FVector Near=Piece->GetComponentsBoundingBox(true).GetClosestPointTo(Pawn->GetPawnViewLocation());
        if(FVector::DistSquared(Near,Pawn->GetPawnViewLocation())>FMath::Square(Kind==TEXT("enhancement")?300.f:500.f))return false;
        FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(WorkstationReach),false,Pawn);
        return !GetWorld()->LineTraceSingleByChannel(Hit,Pawn->GetPawnViewLocation(),Near,ECC_Visibility,Q)||Hit.GetActor()==Piece;
    };
    if(Target)return Reachable(Cast<AVoxelBuildPrefabActor>(Target));
    for(TActorIterator<AVoxelBuildPrefabActor> It(GetWorld());It;++It)
        if(Reachable(*It))return true;
    return false;
}

// Source/FPSGAME/Multiplayer/ColdSteelStationNetwork.cpp — method prefix before GuestAlchemy state update
void AColdSteelPlayerState::TickStations(float Delta)
{
    if(!HasAuthority()||(!GuestForge&&!GuestAssembly))return;
    auto* PC=Cast<APlayerController>(GetOwner());if(!PC||PC->IsLocalController())return;
    const double Now=GetWorld()->GetRealTimeSeconds();if(Now<StationPublishAt)return;StationPublishAt=Now+.25;
    if(GuestForge&&GuestForge->Active())
    {
        const auto* Work=GetPawn()?GetPawn()->FindComponentByClass<UFPSForgeWorkComponent>():nullptr;
        if(!Work||!Work->Station()||!StationReach(TEXT("forge"),Work->Station()))
        {FString Reason;GuestForge->Finish(Reason);bStationDirty=true;bServerDirty=true;}
    }

// Source/FPSGAME/Multiplayer/ColdSteelWoodworkingNetwork.cpp — whole method
void AColdSteelPlayerState::TickWoodNetwork()
{
    const auto* PC=Cast<APlayerController>(GetOwner());
    if(!HasAuthority()||!PC||PC->IsLocalController()||!GuestWood)return;
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(Now>=WoodPublishAt)
    {
        WoodPublishAt=Now+.5;
        if(GuestWood->NetworkOpen()&&(!GuestWood->Station()||!StationReach(TEXT("wood"),GuestWood->Station())))
        {
            GuestWood->NetworkUnavailable(TEXT("已离开木工工作台或角色无法操作，本次加工已停止"));
            bWoodDirty=true;
        }
        if(WoodOutgoing.IsEmpty()&&(bWoodDirty||GuestWood->IsTickable())&&
            ColdSteelProfileTransfer::SaveToBlob(GuestWood->NetworkState(),WoodOutgoing))
        {WoodChunk=0;++WoodTransfer;WoodOutgoingAck=WoodAuthoritySequence;WoodOutgoingPawn=GetPawn();bWoodDirty=GuestWood->IsTickable();}
    }
    if(WoodOutgoing.IsEmpty()||!InventoryReplyOutgoing.IsEmpty())return;
    auto* Connection=PC->GetNetConnection();if(!Connection||!Connection->IsNetReady())return;
    const double Rate=FMath::Min(8192.,double(Connection->CurrentNetSpeed)*.1);
    if(Rate<=0||Now<WoodSendAt)return;
    const int32 Total=FMath::DivideAndRoundUp(WoodOutgoing.Num(),1024),Offset=WoodChunk*1024;
    TArray<uint8> Bytes;Bytes.Append(WoodOutgoing.GetData()+Offset,FMath::Min(1024,WoodOutgoing.Num()-Offset));
    ClientWoodChunk(WoodTransfer,WoodOutgoingAck,WoodChunk,Total,Bytes,WoodOutgoingPawn.Get());WoodSendAt=Now+1280./Rate;
    if(++WoodChunk==Total)WoodOutgoing.Reset();
}
