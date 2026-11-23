// Source/FPSGAME/WorldGeneration/VillageRoadLamp.cpp

void AVillageRoadLamp::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    UpdateWick();
}

void AVillageRoadLamp::UpdateWick()
{
    const float Ignition = GetIgnitionAmount();
    if (Wick && Ignition!=LastIgnition)
    {
        // The depot lantern defaults to 20,000 emissive. The village indoor wick uses 15.
        Wick->SetScalarParameterValue(TEXT("TS00_Emissive_Multiplier"),5.f*Ignition);
        LastIgnition = Ignition;
    }
}
