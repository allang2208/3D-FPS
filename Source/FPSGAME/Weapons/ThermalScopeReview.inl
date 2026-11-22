// Fixed comparison scene for the opt-in scope screenshot run.
namespace ThermalScopeReview
{
static bool Requested()
{
    static const bool Enabled=FParse::Param(FCommandLine::Get(),TEXT("ThermalGlassReview"));
    return Enabled;
}

static TArray<TWeakObjectPtr<AFatZombie>> Monsters;

static void Record(FJsonObject& Row,APlayerController* Controller)
{
    TArray<TSharedPtr<FJsonValue>> Creatures;
    for(const auto& Weak : Monsters)
    {
        const auto* Monster=Weak.Get();
        if(!Monster)continue;
        FVector2D Point=FVector2D::ZeroVector;
        Controller->ProjectWorldLocationToScreen(Monster->GetMesh()->Bounds.Origin,Point);
        auto Data=MakeShared<FJsonObject>();
        Data->SetNumberField(TEXT("x"),Point.X);Data->SetNumberField(TEXT("y"),Point.Y);
        Data->SetStringField(TEXT("bounds_center"),Monster->GetMesh()->Bounds.Origin.ToString());
        TInlineComponentArray<UPrimitiveComponent*> Parts(Monster);
        bool Heat=false;
        for(const auto* P : Parts)
            Heat|=P->bRenderCustomDepth&&P->CustomDepthStencilValue==240&&P->IsRegistered();
        Data->SetBoolField(TEXT("heat_proxy"),Heat);
        Creatures.Add(MakeShared<FJsonValueObject>(Data));
    }
    Row.SetArrayField(TEXT("thermal_review_creatures"),Creatures);
}
static void SetUp(UWorld* World, AFPSGAMECharacter* Player, APlayerController* Controller)
{
    Player->GetCharacterMovement()->DisableMovement();
    Player->SetActorLocation(FVector(0,0,25000),false,nullptr,ETeleportType::TeleportPhysics);
    Player->SetActorRotation(FRotator::ZeroRotator);
    Controller->SetControlRotation(FRotator::ZeroRotator);
    const FVector Eye=Player->FirstPersonCamera->GetComponentLocation();

    // Give the white-hot creature a visible neighbour behind the concrete
    // for comparison. Both use the ordinary monster registration and materials.
    for(double Y : {-68.,110.})
    {
        const FVector Center=Eye+FVector(7400.,Y,0.);
        const FTransform Pose(FRotator(0,180,0),Center);
        auto* Monster=World->SpawnActorDeferred<AFatZombie>(AFatZombie::StaticClass(),Pose,
            nullptr,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if(!Monster)continue;
        Monster->AutoPossessAI=EAutoPossessAI::Disabled;
        Monster->FinishSpawning(Pose);
        Monster->GetCharacterMovement()->DisableMovement();
        auto* Mesh=Monster->GetMesh();
        Mesh->UpdateBounds();
        Monster->AddActorWorldOffset(Center-Mesh->Bounds.Origin,false);
        Mesh->bPauseAnims=true;
        Monsters.Add(Monster);
    }

    UStaticMesh* Block=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
    if(!Block)return;
    auto BlockAt=[&](FVector Offset,FVector Scale,FRotator Rotation)
    {
        auto* A=World->SpawnActor<AStaticMeshActor>();
        if(!A)return;
        auto* Mesh=A->GetStaticMeshComponent();
        Mesh->SetMobility(EComponentMobility::Movable);
        Mesh->SetStaticMesh(Block);
        A->SetActorTransform(FTransform(Rotation,Eye+Offset,Scale));
    };
    BlockAt(FVector(6500,0,-150),FVector(140,70,.6),FRotator::ZeroRotator);
    BlockAt(FVector(8900,0,75),FVector(2,44,6),FRotator(0,16,0));
    BlockAt(FVector(7890,-340,-45),FVector(3,5,1.6),FRotator(0,16,-22));
    BlockAt(FVector(8200,490,-15),FVector(3,5,2.6),FRotator(0,-27,0));
    BlockAt(FVector(6450,132,0),FVector(.35,1.78,3.75),FRotator::ZeroRotator);
    if(auto* Rock=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/UnrealNormandy/StaticMeshes/SM_LS_Rock_00A.SM_LS_Rock_00A")))
    {
        for(double Y : {-190.,245.})
        {
            auto* RockActor=World->SpawnActor<AStaticMeshActor>();
            if(!RockActor)continue;
            auto* Mesh=RockActor->GetStaticMeshComponent();
            Mesh->SetMobility(EComponentMobility::Movable);
            Mesh->SetStaticMesh(Rock);
            const float Scale=155.f/FMath::Max(1.f,float(Rock->GetBounds().SphereRadius));
            RockActor->SetActorTransform(FTransform(FRotator(10,Y,20),Eye,FVector(Scale)));
            Mesh->UpdateBounds();
            RockActor->AddActorWorldOffset(Eye+FVector(8150,Y,-50)-Mesh->Bounds.Origin);
        }
    }
}
}
