TSharedPtr<FStreamableHandle> ATemperateHillsWorld::RequestResidentAppearance(UWorld* World, TArray<FSoftObjectPath> Paths, FSimpleDelegate OnLoaded)
{
    auto& Manager=UAssetManager::GetStreamableManager();
    if(TemperateHillsChapel::IsChapelWorld(World))
    {
        for(TActorIterator<ATemperateHillsWorld> It(World); It; ++It)
        {
            const FString Label=Paths.IsEmpty()?TEXT("Village resident"):Paths[0].GetAssetName();
            auto Handle=Manager.RequestAsyncLoad(MoveTemp(Paths),MoveTemp(OnLoaded),
                FStreamableManager::DefaultAsyncLoadPriority,false,true,Label);
            if(Handle)It->PendingResidentAppearances.Add(Handle);
            return Handle;
        }
    }
    return Manager.RequestAsyncLoad(MoveTemp(Paths),MoveTemp(OnLoaded));
}

void ATemperateHillsWorld::TickResidentAppearanceLoads()
{
    auto& S=*Streaming;
    if(S.Failed || S.LoadingAssets)return;
    const auto* Transit=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>();
    const bool Full=!GUsingNullRHI && Transit && Transit->IsCompletePreloadSelected();
    if(S.StaggerVillageEntry)
    {
        const auto& Sky=S.Batches[HillsStreaming::Atmosphere];
        if(!S.Batches[HillsStreaming::GroundCover].Ready || ((Full || Sky.Requested) && !Sky.Ready))return;
    }
    // Full preload includes repaired workshops even if their residents have not spawned.
    // Normal travel uses the same view-based appearance requests as walking into town.
    if(Full && !bReady && GetNetMode()!=NM_DedicatedServer && bVillageBlacksmithRepaired && !S.SmithAppearance)
        S.SmithAppearance=RequestResidentAppearance(GetWorld(),AVillageBlacksmithResident::AppearancePaths());
    if(Full && !bReady && GetNetMode()!=NM_DedicatedServer && IsVillageCarpenterRepaired() && !S.CarpenterAppearance)
        S.CarpenterAppearance=RequestResidentAppearance(GetWorld(),AVillageCarpenterResident::AppearancePaths());

    if(PendingResidentAppearances.IsEmpty())return;
    const auto Handle=PendingResidentAppearances[0];
    if(!Handle->WasCanceled())
    {
        if(Handle->IsStalled())
        {
            UE_LOG(LogTemp,Display,TEXT("HILLS_PREP resident=%s queued=%d"),*Handle->GetDebugName(),PendingResidentAppearances.Num());
            Handle->StartStalledHandle();
            return;
        }
        if(!Handle->HasLoadCompleted())return;
#if WITH_EDITOR
        bool Compiling=false;
        Handle->ForEachLoadedAsset([&Compiling](UObject* Asset)
        {
            if(const auto* Build=Cast<IInterface_AsyncCompilation>(Asset))Compiling|=Build->IsCompiling();
        });
        if(Compiling)return;
#endif
    }
    PendingResidentAppearances.RemoveAt(0);
}

void ATemperateHillsWorld::LoadNextEnvironmentStage()
{
    using namespace HillsStreaming;
    auto& S=*Streaming;
    if(S.LoadingAssets||S.Failed||S.CompletedStages==BatchCount)return;
    auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>();
    const bool Full=!GUsingNullRHI&&Loading&&Loading->IsCompletePreloadSelected();

    for(int32 Stage=0;Stage<BatchCount;++Stage)
    {
        auto& Batch=S.Batches[Stage];
        if(Batch.Ready)continue;
        if(S.StaggerVillageEntry && Stage>0 && !S.Batches[Stage-1].Ready)break;
        if(!Batch.Requested)
        {
            // Quick entry can defer atmosphere until existing resident loads finish.
            if(Stage==Atmosphere&&!Full&&(!bReady||(Loading&&Loading->IsHoldingGameplayInput())||
                (S.StaggerVillageEntry&&!PendingResidentAppearances.IsEmpty())))continue;
            Batch.Requested=true;
            TArray<FSoftObjectPath> Paths;
            switch(Stage)
            {
            case Solids:
                Paths.Add(Assets->Graphs[0].ToSoftObjectPath());
                Paths.Add(Assets->Graphs[1].ToSoftObjectPath());
                Paths.Add(Assets->TrunkCollisionMesh.ToSoftObjectPath());
                AddPaths(Paths,Assets->Trees);
                AddPaths(Paths,Assets->Rocks);AddPaths(Paths,Assets->RiverRocks);
                AddPaths(Paths,Assets->FallenLogs);AddPaths(Paths,Assets->ForestRoots);AddPaths(Paths,Assets->Cliffs);
                Paths.Add(Assets->RainforestBankBoulder.ToSoftObjectPath());
                Paths.Append(ProductionOreRocks::AllMeshes());
                break;
            case Understory:
                Paths.Add(Assets->Graphs[2].ToSoftObjectPath());
                AddPaths(Paths,Assets->Shrubs);AddPaths(Paths,Assets->ForestSaplings);
                AddPaths(Paths,Assets->WetBankSaplings);
                AddPaths(Paths,Assets->ForestShrubs);AddPaths(Paths,Assets->ForestFerns);
                break;
            case GroundCover:
                Paths.Add(Assets->Graphs[3].ToSoftObjectPath());
                AddPaths(Paths,Assets->Grass);AddPaths(Paths,Assets->GrassAccents);
                AddPaths(Paths,Assets->RainforestGrass);AddPaths(Paths,Assets->RainforestCarpetGrass);
                AddPaths(Paths,Assets->RainforestTwigs);AddPaths(Paths,Assets->RainforestHerbs);
                AddPaths(Paths,Assets->ForestFungi);AddPaths(Paths,Assets->ForestMoss);
                AddPaths(Paths,Assets->RiverGroundCover);AddPaths(Paths,Assets->RiverPebbles);
                AddPaths(Paths,Assets->RiverReeds);AddPaths(Paths,Assets->RiverBankGrasses);AddPaths(Paths,Assets->RiverUnderstory);
                AddPaths(Paths,Assets->MeadowFlowers);
                for(const auto& Family:Assets->ClearingFlowers)AddPaths(Paths,Family.Variants);
                break;
            case Atmosphere:
                Paths.Add(Assets->ValleyFogClass.ToSoftObjectPath());
                Paths.Add(Assets->ValleyFogMaterial.ToSoftObjectPath());
                AddPaths(Paths,Assets->BackdropTrees);
                break;
            }
            Paths.RemoveAll([](const FSoftObjectPath& Path){return Path.IsNull();});
            Batch.Paths=MoveTemp(Paths);
        }
        const double Now=FPlatformTime::Seconds();
        if(Batch.Finished==Batch.Submitted && Batch.Submitted<Batch.Paths.Num())
        {
            // Each root can bring its own dependencies and editor compilation jobs.
            constexpr int32 VillagePathsPerRequest=12;
            const int32 Remaining=Batch.Paths.Num()-Batch.Submitted;
            const int32 Count=S.StaggerVillageEntry?FMath::Min(VillagePathsPerRequest,Remaining):Remaining;
            TArray<FSoftObjectPath> Slice(Batch.Paths.GetData()+Batch.Submitted,Count);
            Batch.Submitted+=Count;
            Batch.Handle=UAssetManager::GetStreamableManager().RequestAsyncLoad(MoveTemp(Slice),FStreamableDelegate(),
                Stage==Solids?FStreamableManager::AsyncLoadHighPriority:FStreamableManager::DefaultAsyncLoadPriority);
            if(Batch.Handle)S.Handles.Add(Batch.Handle);
            UE_LOG(LogTemp,Display,TEXT("HILLS_PREP requested_batch=%d range=%d-%d/%d elapsed=%.2fs"),
                Stage,Batch.Finished+1,Batch.Submitted,Batch.Paths.Num(),Now-StartSeconds);
        }
        if(Batch.Handle&&!Batch.Handle->HasLoadCompleted())continue;
        if(!Batch.Loaded && Batch.Submitted==Batch.Paths.Num())
        {
            Batch.Loaded=true;
            bool Valid=true;
            for(const auto& Path:Batch.Paths)if(!Path.ResolveObject())
            {
                UE_LOG(LogTemp,Error,TEXT("HILLS_PREP missing batch=%d asset=%s"),Stage,*Path.ToString());
                Valid=false;
            }
            if(Stage==Solids)
                Valid&=Loaded(Assets->Trees)&&Loaded(Assets->Rocks)&&(Assets->TrunkCollisionMesh.IsNull()||Assets->TrunkCollisionMesh.IsValid());
            else if(Stage==Understory)Valid&=Loaded(Assets->Shrubs);
            else if(Stage==GroundCover)Valid&=Loaded(Assets->Grass)&&Loaded(Assets->GrassAccents);
            else S.FogReady=Assets->ValleyFogClass.IsValid()&&Assets->ValleyFogMaterial.IsValid();
            const int32 FirstLayer=Stage==Solids?0:Stage+1;
            const int32 EndLayer=Stage==Solids?2:FMath::Min(FirstLayer+1,4);
            for(int32 Layer=FirstLayer;Layer<EndLayer;++Layer)
            {
                const auto* Graph=Assets->Graphs[Layer].Get();
                if(!Graph||!Graph->Use2DGrid()||Graph->GetDefaultGridSize()==0||Graph->GetDefaultGridSize()==PCGHiGenGrid::UnboundedGridSize())
                {
                    UE_LOG(LogTemp,Error,TEXT("HILLS_PREP layer=%d requires a loaded bounded 2D graph"),Layer);
                    Valid=false;
                }
            }
            UE_LOG(LogTemp,Display,TEXT("HILLS_PREP loaded_batch=%d valid=%d elapsed=%.2fs"),
                Stage,Valid,FPlatformTime::Seconds()-StartSeconds);
            if(!Valid&&(Stage!=Atmosphere||Full))
            {
                S.Failed=true;
                if(Loading)
                    Loading->FailPreparation(FText::FromString(TEXT("环境资源未能载入，请返回主场景后重试。")));
            }
            if(S.Failed)return;
        }
        // Package completion can precede mesh compilation in the editor. Placement
        // uses mesh bounds, but does not need unused material shader permutations.
        bool Compiling=false;
#if WITH_EDITOR
        const auto Platform=GetFeatureLevelShaderPlatform_Checked(GetWorld()->GetFeatureLevel());
        // A retained package that has finished compiling need not be polled again
        // while the next tree mesh or shared foliage material is still pending.
        for(;Batch.NextCompilationPath<Batch.Submitted;++Batch.NextCompilationPath)
        {
            const FSoftObjectPath& Path=Batch.Paths[Batch.NextCompilationPath];
            UObject* Asset=Path.ResolveObject();
            if(auto* Mesh=Cast<UStaticMesh>(Asset))
            {
                Compiling|=Mesh->IsCompiling();
                if(!Compiling&&Full)for(const auto& MaterialSlot:Mesh->GetStaticMaterials())Compiling|=MaterialPending(MaterialSlot.MaterialInterface,Platform);
            }
            else if(auto* Skin=Cast<USkeletalMesh>(Asset))
            {
                Compiling|=Skin->IsCompiling();
                if(!Compiling&&Full)for(const auto& MaterialSlot:Skin->GetMaterials())Compiling|=MaterialPending(MaterialSlot.MaterialInterface,Platform);
            }
            else if(Full)Compiling|=MaterialPending(Cast<UMaterialInterface>(Asset),Platform);
            if(Compiling)
            {
                if(Now>=Batch.NextWaitLog)
                {
                    Batch.NextWaitLog=Now+5.;
                    UE_LOG(LogTemp,Display,TEXT("HILLS_PREP waiting_batch=%d phase=compilation asset=%s elapsed=%.2fs"),
                        Stage,*Path.ToString(),Now-StartSeconds);
                }
                break;
            }
        }
#endif
        if(Compiling)continue;
        Batch.Finished=Batch.Submitted;
        if(Batch.Finished<Batch.Paths.Num())continue;
        Batch.Paths.Reset();Batch.Ready=true;++S.CompletedStages;
        UE_LOG(LogTemp,Display,TEXT("HILLS_PREP ready_batch=%d completed=%d/%d elapsed=%.2fs"),Stage,S.CompletedStages,int32(BatchCount),FPlatformTime::Seconds()-StartSeconds);
        if(Loading)
        {
            Loading->RetainBiomeResources(S.Handles,S.CompletedStages==BatchCount);
            S.RetainedHandleCount=S.Handles.Num();
        }
        if(S.StaggerVillageEntry)break;
    }
}
