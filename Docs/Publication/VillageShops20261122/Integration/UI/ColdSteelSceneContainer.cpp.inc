bool AColdSteelSceneContainer::IsAvailableForSearch() const
{
    return GetActorEnableCollision() && (Body->IsQueryCollisionEnabled() || Door->IsQueryCollisionEnabled());
}

bool AColdSteelSceneContainer::IsWithinPanelReach(const APlayerController* Controller) const
{
    const APawn* Pawn=Controller?Controller->GetPawn().Get():nullptr;
    return IsAvailableForSearch()&&Pawn&&Pawn->GetWorld()==GetWorld()
        &&FVector::Dist(Pawn->GetActorLocation(),GetActorLocation()+FVector(0,0,70))<=240.f;
}

void AColdSteelSceneContainer::CloseLootVisual()
{
    if(!UsesReusableDoor()||!bVisualInitialized||!HasAuthority()||GetNetMode()==NM_Client)return;
    if(const auto* Search=GetWorld()->GetSubsystem<UColdSteelContainerSearchSubsystem>();Search&&Search->HasViewers(this))return;
    OpeningController.Reset();
    StartReusableDoor(true);
}
