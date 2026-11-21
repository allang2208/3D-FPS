#include "VillageDefenseDebris.h"
#include "VillageMasonry.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"

AVillageDefenseDebris::AVillageDefenseDebris()
{
    PrimaryActorTick.bCanEverTick=true;SetReplicates(false);
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}
void AVillageDefenseDebris::Spawn(AActor& Section,const FTransform& Transform,const FVector& Size,const FVector& Direction,int32 Seed,bool Wood)
{
    UWorld* World=Section.GetWorld();
    if(!World||World->GetNetMode()==NM_DedicatedServer)return;
    TArray<AVillageDefenseDebris*> Existing;
    for(TActorIterator<AVillageDefenseDebris> It(World);It;++It)Existing.Add(*It);
    // At most 128 active bodies, including a simultaneous breach in adjacent bays.
    if(Existing.Num()>=8)
    {
        Existing.Sort([](const auto& A,const auto& B){return A.Age>B.Age;});
        Existing[0]->Destroy();
    }
    auto* Debris=World->SpawnActor<AVillageDefenseDebris>();if(!Debris)return;
    Debris->SetOwner(&Section);
    Debris->SetActorTransform(Transform);Debris->SetLifeSpan(12.f);
    FRandomStream R(Seed);
    const int32 Columns=Wood?8:4,Rows=Wood?2:4;
    const FVector Cell(Size.X/Columns,Size.Y,Size.Z/Rows);
    for(int32 Row=0;Row<Rows;++Row)for(int32 Col=0;Col<Columns;++Col)
    {
        const FSoftObjectPath Path=Wood
            ? FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/VillageDefenses/SM_WoodShard.SM_WoodShard"))
            : VillageMasonry::Mesh(R.RandRange(0,1)?TEXT("SM_StoneChunkA"):TEXT("SM_StoneChunkB"));
        auto* Mesh=Cast<UStaticMesh>(Path.ResolveObject());if(!Mesh)continue;
        auto* C=NewObject<UStaticMeshComponent>(Debris);Debris->AddInstanceComponent(C);
        C->SetupAttachment(Debris->RootComponent);C->SetMobility(EComponentMobility::Movable);C->SetStaticMesh(Mesh);
        C->SetRelativeLocation(FVector(-Size.X*.5+(Col+.5)*Cell.X,0,(Row+.5)*Cell.Z));
        const FVector Native=Mesh->GetBoundingBox().GetSize();
        const FVector Scale(Cell.X/FMath::Max(1.,Native.X),Cell.Y/FMath::Max(1.,Native.Y),Cell.Z/FMath::Max(1.,Native.Z));
        C->SetRelativeScale3D(Scale);C->SetCollisionEnabled(ECollisionEnabled::PhysicsOnly);
        C->SetCollisionObjectType(ECC_PhysicsBody);C->SetCollisionResponseToAllChannels(ECR_Ignore);
        C->SetCollisionResponseToChannel(ECC_WorldStatic,ECR_Block);C->SetCanEverAffectNavigation(false);
        C->SetGenerateOverlapEvents(false);C->SetLinearDamping(.6f);C->SetAngularDamping(1.2f);
        C->RegisterComponent();C->SetMassOverrideInKg(NAME_None,Wood?7.f:36.f,true);
        Debris->Chunks.Add(C);Debris->Scales.Add(Scale);
        Debris->ReleaseAt.Add((Rows-1-Row)*.095f+R.FRandRange(0,.09f));
        Debris->Velocities.Add(Direction*R.FRandRange(75.f,155.f)+FVector(R.FRandRange(-35.f,35.f),R.FRandRange(-35.f,35.f),R.FRandRange(20.f,65.f)));
        Debris->Spins.Add(FVector(R.FRandRange(-100.f,100.f),R.FRandRange(-100.f,100.f),R.FRandRange(-70.f,70.f)));
    }
}
void AVillageDefenseDebris::Tick(float Delta)
{
    Super::Tick(Delta);
    if(!IsValid(GetOwner())){Destroy();return;}
    Age+=Delta;
    for(int32 I=0;I<Chunks.Num();++I)
    {
        auto* C=Chunks[I].Get();
        if(ReleaseAt[I]>=0.f&&Age>=ReleaseAt[I])
        {C->SetSimulatePhysics(true);C->SetPhysicsLinearVelocity(Velocities[I]);C->SetPhysicsAngularVelocityInDegrees(Spins[I]);ReleaseAt[I]=-1.f;}
        if(Age>=10.f)
        {
            C->SetSimulatePhysics(false);C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            C->SetWorldScale3D(Scales[I]*(1.f-FMath::SmoothStep(10.f,12.f,Age)));
        }
    }
}
