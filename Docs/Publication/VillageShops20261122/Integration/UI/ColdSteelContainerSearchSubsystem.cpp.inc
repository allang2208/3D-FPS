bool UColdSteelContainerSearchSubsystem::CanAccess(const APawn* Pawn,const AActor* Target)
{
    if(!IsValid(Pawn)||!IsValid(Target)||Pawn->GetWorld()!=Target->GetWorld()||!Pawn->GetController()
        ||FVector::DistSquared(Pawn->GetActorLocation(),Target->GetActorLocation()+FVector(0,0,70))>FMath::Square(250.f))return false;
    if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return false;
    if(const auto* Scene=Cast<AColdSteelSceneContainer>(Target);Scene&&!Scene->IsAvailableForSearch())return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ContainerSearchReach),false,Pawn);Query.AddIgnoredActor(Target);
    FHitResult Wall;
    return !Pawn->GetWorld()->LineTraceSingleByChannel(Wall,Pawn->GetPawnViewLocation(),Target->GetActorLocation()+FVector(0,0,70),ECC_Visibility,Query);
}

bool UColdSteelContainerSearchSubsystem::HasViewers(const AActor* Target) const
{
    for(const auto& Pair:Viewers)if(Pair.Key.IsValid()&&Pair.Value.Anchor.Get()==Target)return true;
    return false;
}

void UColdSteelContainerSearchSubsystem::Close(APlayerController* Player,AActor* Target)
{
    auto* Viewer=Viewers.Find(Player);
    if(Viewer&&Viewer->Anchor==Target)
    {
        Viewer->Anchor.Reset();Viewer->Key.Empty();
        if(GetWorld()->GetNetMode()!=NM_Client)if(auto* Scene=Cast<AColdSteelSceneContainer>(Target))Scene->CloseLootVisual();
    }
}
