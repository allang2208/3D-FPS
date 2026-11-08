// Integration reference only: preserve shared host declarations and prerequisites.

// Source line 14
bool UProductionToolComponent::BeginInspect(bool bWalking)
{
    // Cosmetic two-hand inspect: one full turn about the shaft centreline. L
    // plays InspectV1; walking plays only its accelerated turn half (InspectWalkSpeedV3).
    // Walking keeps it; it never occupies IsBusy or the hit clock.
    const FName Clip=bWalking?FName(TEXT("InspectWalk")):FName(TEXT("Inspect"));
    if(!IsWarhammerEquipped()||!CanUse()||!HasReadyPresentation()||!Motions.FindRef(Clip)||ShouldBreakInspect())
        return false;
    InspectAir.Stop();
    InspectClip=Clip;InspectElapsed=0.f;
    ScheduleWalkInspect(true);
    return true;
}

// Source line 53
void UProductionToolComponent::CancelInspect()
{
    InspectElapsed=-1.f;
    InspectAir.Stop();
}

// Source line 59
void UProductionToolComponent::PlayInspectCues(float From,float To,float Rate)
{
    namespace Cues=WarhammerInspectCues;
    if(InspectClip==TEXT("InspectWalk"))
    {
        InspectAir.PlayBeat(this,From,To,Cues::WalkTurnPeak,.53f,Rate);
        return;
    }
    InspectAir.PlayBeat(this,From,To,Cues::RockPeak,.29f,Rate);
    InspectAir.PlayBeat(this,From,To,Cues::TurnPeak,.59f,Rate);
}
