// Source/FPSGAME/WorldGeneration/TemperateHillsChapel.cpp

    // Daylight comes through the real apertures. Nearby artificial rectangle
    // lights used to bleach the deep stone reveals when viewed from outside.
    // Reuse the village's view-local adaptation, bounded by the nave interior.
    if(GetNetMode()!=NM_DedicatedServer)
    {
        auto* VisionRoom=NewObject<UChildActorComponent>(this,TEXT("OldChapel_InteriorVision"));
        VisionRoom->SetupAttachment(RootComponent);
        const FTransform RoomTransform(Orientation,Floor,FVector(Size));
        VisionRoom->SetRelativeTransform(RoomTransform.GetRelativeTransform(RootComponent->GetComponentTransform()));
        VisionRoom->SetChildActorClass(ABuildingDaylight::StaticClass());
        AddInstanceComponent(VisionRoom);
        VisionRoom->RegisterComponent();
        if(auto* Room=Cast<ABuildingDaylight>(VisionRoom->GetChildActor()))
        {
            Room->RoomMinimum=FVector(-722.,-348.,0.);
            Room->RoomMaximum=FVector(746.,348.,450.);
            // The deep stone nave uses the same daylight adaptation as the tavern hall.
            Room->ExposureCompensation=2.f;
            Room->AdditionalDarkAdaptationStops=4.f;
            Room->EntranceTransitionCm=60.f;
            Room->ShadowContrast=.5f;
            // Child actor registration may have already run construction with
            // default house bounds; apply the authored chapel bounds as well.
            Room->OnConstruction(Room->GetActorTransform());
        }
    }
