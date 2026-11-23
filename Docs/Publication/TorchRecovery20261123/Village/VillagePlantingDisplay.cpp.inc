// Source/FPSGAME/WorldGeneration/VillagePlantingDisplay.cpp

void AVillagePlantingDisplay::Tick(float Delta)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(VillagePlanting_Submit);
    Super::Tick(Delta);if(!Hills.IsValid()){Destroy();return;}
    if(!Hills->bReady)return;
    auto* Assets=Hills->Assets.Get();if(!Assets)return;
    if(!Area.IsValid)
    {
        // The hills streaming handles retain the palette throughout placement.
        for(const auto& Ref:Assets->ForestSaplings)if(!Ref.Get())return;
        for(const auto& Ref:Assets->ForestShrubs)if(!Ref.Get())return;
        for(const auto& Ref:Assets->Shrubs)if(!Ref.Get())return;
        for(const auto& Ref:Assets->Grass)if(!Ref.Get())return;
        for(const auto& Ref:Assets->GrassAccents)if(!Ref.Get())return;
        for(const auto& Ref:Assets->Rocks)if(!Ref.IsNull()&&!Ref.Get())return;
        for(const auto& Ref:Assets->MeadowFlowers)if(!Ref.IsNull()&&!Ref.Get())return;
        const auto& V=Hills->GetVillageSite();const auto E=V.Extent();
        Area=FBox(V.Ground-FVector(E,5000),V.Ground+FVector(E,5000));
        Cell=Area;Cell.Max.X=FMath::Min(Cell.Min.X+2000.,Area.Max.X);
        Cell.Max.Y=FMath::Min(Cell.Min.Y+2000.,Area.Max.Y);NextY=Cell.Min.Y;
    }
    if(!Neighborhood)
    {
        // Retain the same finite competition halo and world-space candidate IDs.
        // Preparing the whole village at once was an unbudgeted 55 ms work unit.
        Neighborhood=Hills->BeginVegetationCell(Cell);return;
    }
    if(!RelationshipsReady)
    {
        RelationshipsReady=Hills->AdvanceVegetationCell(Neighborhood,true);return;
    }
    const double Until=FPlatformTime::Seconds()+.0007;
    // Submit a bounded slice at a time. Keep candidate order within each mesh
    // so instance indices, placement and wind animation stay deterministic.
    TMap<UPrimitiveComponent*, TArray<FTransform>> Batches;
    TArray<int32> AnimationIndices;
    TSet<UPrimitiveComponent*> ChangedTreeGroups;
    while ((PendingIndex < Pending.Num() || NextY < Cell.Max.Y) && FPlatformTime::Seconds() < Until)
    {
        if(PendingIndex>=Pending.Num())
        {
            Pending.Reset();PendingIndex=0;
            FBox Strip=Cell;Strip.Min.Y=NextY;Strip.Max.Y=FMath::Min(NextY+200.,Cell.Max.Y);
            Hills->GetVegetationStrip(2,Strip,*Neighborhood,Pending);Hills->GetVegetationStrip(4,Strip,*Neighborhood,Pending);Hills->GetVegetationStrip(3,Strip,*Neighborhood,Pending);
            NextY=Strip.Max.Y;
        }
        constexpr int32 MaxCandidatesPerBatch = 32;
        const int32 EndIndex = FMath::Min(PendingIndex + MaxCandidatesPerBatch, Pending.Num());
        while (PendingIndex < EndIndex)
        {
            const auto& P=Pending[PendingIndex++];
            if(!P.bVillagePlanting)continue;
            const int32 Pass = int32((P.CandidateId >> 16) & 255);
            const FVector Offset = P.Transform.GetLocation() - Area.Min;
            const FIntPoint Sector = Pass == 0 ? FIntPoint(FMath::FloorToInt(Offset.X / 6400.),
                FMath::FloorToInt(Offset.Y / 6400.)) : FIntPoint(-1, -1);
            auto& Entry = Groups.FindOrAdd(TPair<FIntPoint,FSoftObjectPath>(Sector, P.Mesh));
            if(!Entry)
            {
                if(auto* Skin=Cast<USkeletalMesh>(P.Mesh.ResolveObject()))
                {
                    auto* C=NewObject<UInstancedSkinnedMeshComponent>(this);C->SetSkinnedAsset(Skin);
                    if(Assets->ForestWindProvider)C->SetTransformProvider(Assets->ForestWindProvider);
                    C->SetCullDistances(Pass==0?18000:12500,Pass==0?21000:15000);Entry=C;
                }
                else if(auto* Mesh=Cast<UStaticMesh>(P.Mesh.ResolveObject()))
                {
                    auto* C=NewObject<UInstancedStaticMeshComponent>(this);C->SetStaticMesh(Mesh);
                    C->SetCullDistances(Pass<2?15000:9500,Pass<2?18000:13000);Entry=C;
                }
                if(!Entry)continue;
                // Thousands of ankle-high plants and embedded chips share these
                // groups. Keep them lit by the wall and trees without adding
                // the whole verge to every virtual shadow map marking pass.
                if(Pass==2){Entry->SetCastShadow(false);Entry->bAffectDistanceFieldLighting=false;}
                AddInstanceComponent(Entry);Entry->SetupAttachment(RootComponent);Entry->SetMobility(EComponentMobility::Movable);
                Entry->SetCollisionEnabled(ECollisionEnabled::NoCollision);Entry->SetCanEverAffectNavigation(false);
                Entry->SetGenerateOverlapEvents(false);Entry->SetReceivesDecals(false);Entry->ComponentTags.Add(TEXT("VillagePlanting"));Entry->RegisterComponent();
            }
            Batches.FindOrAdd(Entry.Get()).Add(P.Transform);
            if (Pass == 0) ChangedTreeGroups.Add(Entry.Get());
            if (FPlatformTime::Seconds() >= Until) break;
        }
        for (auto& Batch : Batches)
        {
            if (Batch.Value.IsEmpty()) continue;
            if (auto* SkinGroup = Cast<UInstancedSkinnedMeshComponent>(Batch.Key))
            {
                AnimationIndices.SetNumZeroed(Batch.Value.Num(), EAllowShrinking::No);
                SkinGroup->AddInstances(Batch.Value, AnimationIndices, false, true);
            }
            else if (auto* StaticGroup = Cast<UInstancedStaticMeshComponent>(Batch.Key))
            {
                StaticGroup->AddInstances(Batch.Value, false, true, false);
            }
            PlantCount += Batch.Value.Num();
            Batch.Value.Reset();
        }
    }
    if (!ChangedTreeGroups.IsEmpty())
    {
        auto* Canopy = UVillageCanopyDetail::For(*Hills.Get());
        for (auto* Tree : ChangedTreeGroups) Canopy->AddTree(Tree);
    }
    if(NextY>=Cell.Max.Y&&PendingIndex>=Pending.Num())
    {
        Pending.Reset();PendingIndex=0;Neighborhood.Reset();RelationshipsReady=false;
        Cell.Min.X=Cell.Max.X;
        if(Cell.Min.X>=Area.Max.X){Cell.Min.X=Area.Min.X;Cell.Min.Y=Cell.Max.Y;}
        if(Cell.Min.Y>=Area.Max.Y)
        {SetActorTickEnabled(false);UE_LOG(LogTemp,Display,TEXT("VILLAGE_PLANTING_DISPLAY count=%d groups=%d"),PlantCount,Groups.Num());return;}
        Cell.Max.X=FMath::Min(Cell.Min.X+2000.,Area.Max.X);Cell.Max.Y=FMath::Min(Cell.Min.Y+2000.,Area.Max.Y);NextY=Cell.Min.Y;
    }
}
