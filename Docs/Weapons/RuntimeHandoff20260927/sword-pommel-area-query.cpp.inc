TArray<FHitResult> MeleeSmallTargets::QueryQuickAreaContacts(UWorld* World,ACharacter* Owner,
    const FTransform& Aim,const FVector& Start,float Reach,float Radius)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(Melee_QuickAreaContact);
    TArray<FHitResult> Result;
    if(!World||!Owner||Reach<=0.f)return Result;
    const FVector End=Start+Aim.GetUnitAxis(EAxis::X)*Reach;
    const auto Shape=FCollisionShape::MakeSphere(Radius);
    FCollisionQueryParams Params(SCENE_QUERY_STAT(QuickMeleeAreaContact),false,Owner);
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_Pawn);
    TArray<FHitResult> Contacts;
    World->SweepMultiByObjectType(Contacts,Start,End,FQuat::Identity,Objects,Shape,Params);
    Contacts.Sort([](const FHitResult& A,const FHitResult& B){return A.Time<B.Time;});

    // Ignore bodies, not scenery: the original sphere still stops at the first world blocker.
    FCollisionQueryParams Cover=Params;
    for(const auto& Hit:Contacts)
        if(Cast<APawn>(Hit.GetActor()))Cover.AddIgnoredActor(Hit.GetActor());
    FHitResult Blocker;
    const bool bBlocked=World->SweepSingleByChannel(Blocker,Start,End,FQuat::Identity,ECC_Pawn,Shape,Cover);
    TSet<TWeakObjectPtr<AActor>> Seen;
    for(const auto& Hit:Contacts)
    {
        if(bBlocked&&Hit.Time>Blocker.Time)break;
        auto* Target=Hit.GetActor();
        auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
        if(!Combat||Combat->IsDead()||!Target->CanBeDamaged()||Seen.Contains(Target))continue;
        if(const auto* Hand=LivingSmallHand(Target);Hand&&Hit.GetComponent()!=Hand->GetCapsuleComponent())continue;
        Seen.Add(Target);
        FCollisionQueryParams TargetCover=Cover;TargetCover.AddIgnoredActor(Target);
        if(Covered(World,Start,Hit.ImpactPoint,TargetCover)||Covered(World,Aim.GetLocation(),Hit.ImpactPoint,TargetCover))continue;
        Result.Add(Hit);
    }
    // Preserve the existing fallback condition and its range/arc; no new explosion radius.
    if(Result.IsEmpty())Result=QueryLowSector(World,Owner,Aim,Reach,{},true);
    return Result;
}
