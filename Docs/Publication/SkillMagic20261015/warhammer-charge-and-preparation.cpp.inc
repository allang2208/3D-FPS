// Existing host: Source/FPSGAME/Production/ProductionBluntAuthority.cpp
bool UProductionToolComponent::IsHeavyCharging() const
{
    const auto* Pawn=Character.Get();
    return Pawn&&(Pawn->IsLocallyControlled()?bBluntCharging:(Pawn->HasAuthority()&&bBluntServerCharging));
}

// Existing host: Source/FPSGAME/Production/ProductionBluntAuthority.cpp
void UProductionToolComponent::TickAuthorityBluntCharge()
{
    auto* Pawn=Character.Get();
    if(!Pawn||!Pawn->HasAuthority()||Pawn->IsLocallyControlled()||!bBluntServerCharging)return;
    auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    if(!CanCommitBlunt(Pawn,Profile)||!Item||Item->InstanceId!=BluntServerChargeInstance||Profile->Stamina()<=0.f)
    {
        ServerCancelBluntAttack_Implementation(BluntServerAttackId);
        ClientBluntAttackResult(BluntServerAttackId,0,false,false,false);
    }
}

// Existing host: Source/FPSGAME/Production/ProductionBluntHeavy.cpp
float UProductionToolComponent::BluntChargePoseSeconds() const
{
    if(bBluntReturningCharge)
        return BluntChargeReturnFrom*(1.f-FMath::SmoothStep(0.f,BluntChargeReturnDuration,BluntChargeReturnAge));
    return FMath::Clamp(float(GetWorld()->GetTimeSeconds()-BluntChargeStartedAt)/BluntChargeSeconds,0.f,1.f)*WarhammerHeavy::ChargeSeconds;
}

// Existing host: Source/FPSGAME/Production/ProductionBluntHeavy.cpp
void UProductionToolComponent::CancelHeavyCharge()
{
    if(!IsHeavyCharging())return;
    if(Character->HasAuthority()&&!Character->IsLocallyControlled())
    {
        ServerCancelBluntAttack_Implementation(BluntServerAttackId);
        ClientBluntAttackResult(BluntServerAttackId,0,false,false,false);return;
    }
    const float From=BluntChargePoseSeconds();
    CancelUse();
    // Retrace the supported two-hand charge, keeping the camera on that same clock.
    bBluntReturningCharge=true;BluntChargeReturnFrom=From;BluntChargeReturnAge=0.f;
    BluntChargeReturnDuration=FMath::Clamp(From*.25f,.1f,.45f);
}

// Existing host: Source/FPSGAME/Production/ProductionBluntHeavy.cpp
void UProductionToolComponent::AdvanceBluntCharge(float Delta)
{
    if((bBluntCharging||bBluntReturningCharge)&&(!CanUse()||Character->IsCastBlockingLeftHandAction()))
    {CancelUse();return;}
    if(bBluntReturningCharge)
    {
        BluntChargeReturnAge=FMath::Min(BluntChargeReturnDuration,BluntChargeReturnAge+Delta);
        if(BluntChargeReturnAge>=BluntChargeReturnDuration){bBluntReturningCharge=false;VisualTime=0.f;}
    }
}

// Existing host: Source/FPSGAME/Production/WarhammerSlamFXSubsystem.cpp
bool UWarhammerSlamFXSubsystem::PrepareSlot(int32 Index)
{
    if(Dust[Index])return true;
    auto* Plane=Cast<UStaticMesh>(PlanePath.ResolveObject());
    auto* Rock=Cast<UStaticMesh>(RockPath.ResolveObject());
    auto* DustMat=Cast<UMaterialInterface>(DustPath.ResolveObject());
    auto* RockMat=Cast<UMaterialInterface>(RockMaterialPath.ResolveObject());
    auto* CrackMat=Cast<UMaterialInterface>(CrackPath.ResolveObject());
    if(!Plane||!Rock||!DustMat||!RockMat||!CrackMat)return false;
    auto MakeInstances=[&](UStaticMesh* Mesh,UMaterialInterface* Material,int32 DataCount)
    {
        auto* C=NewObject<UInstancedStaticMeshComponent>(GetWorld()->GetWorldSettings());
        C->SetMobility(EComponentMobility::Movable);C->SetStaticMesh(Mesh);C->SetMaterial(0,Material);
        C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetGenerateOverlapEvents(false);
        C->SetCanEverAffectNavigation(false);C->SetCastShadow(false);C->SetReceivesDecals(false);
        C->SetNumCustomDataFloats(DataCount);C->SetVisibility(false);C->RegisterComponent();C->PrecachePSOs();return C;
    };
    Dust[Index]=MakeInstances(Plane,DustMat,3);Debris[Index]=MakeInstances(Rock,RockMat,0);
    auto* Decal=NewObject<UDecalComponent>(GetWorld()->GetWorldSettings());
    Decal->SetDecalMaterial(CrackMat);Decal->SetFadeScreenSize(.001f);Decal->SetVisibility(false);Decal->RegisterComponent();Decal->PrecachePSOs();
    Cracks[Index]=Decal;CrackMaterials[Index]=Decal->CreateDynamicMaterialInstance();
    return true;
}

// Existing host: Source/FPSGAME/Production/WarhammerSlamFXSubsystem.cpp
bool UWarhammerSlamFXSubsystem::PrepareBackground()
{
    if(Impacts.IsEmpty())return true;
    for(int32 I=0;I<Impacts.Num();++I)
    {
        if(!Dust[I]){PrepareSlot(I);return false;} // At most one slot per queue tick.
        if(Dust[I]->IsPSOPrecaching()||Debris[I]->IsPSOPrecaching()||Cracks[I]->GetPSOPrecacheComponentData().IsPSOPrecaching())return false;
    }
    return true;
}
