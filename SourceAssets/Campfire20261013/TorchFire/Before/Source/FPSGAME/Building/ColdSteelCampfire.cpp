#include "ColdSteelCampfire.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "Net/UnrealNetwork.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "UObject/ConstructorHelpers.h"

AColdSteelCampfire::AColdSteelCampfire()
{
    PrimaryActorTick.bCanEverTick=false;
    bReplicates=true;
    SetReplicateMovement(true);
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("CampfireRoot")));
    Body=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("CampfireBody"));
    Body->SetupAttachment(GetRootComponent());
    Body->SetMobility(EComponentMobility::Movable);
    Body->SetCollisionProfileName(TEXT("BlockAll"));
    Body->SetCanEverAffectNavigation(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Mesh(
        TEXT("/Game/EasyBuildingSystem/Meshes/Props/Stylized/SM_Stylized_Campfire.SM_Stylized_Campfire"));
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> Fire(
        TEXT("/Game/Building/Campfire20261012/Realistic/NS_CampfireRealisticFlame.NS_CampfireRealisticFlame"));
    if(Mesh.Succeeded())
    {
        Body->SetStaticMesh(Mesh.Object);
        const FBoxSphereBounds Bounds=Mesh.Object->GetBounds();
        Body->SetRelativeLocation(FVector(-Bounds.Origin.X,-Bounds.Origin.Y,Bounds.BoxExtent.Z-Bounds.Origin.Z));
    }
    if(Fire.Succeeded())FlameSystem=Fire.Object;
    // Query-only spatial proxy. No overlap events, pawn blocking, per-fire Tick or player list.
    WarmthQuery=CreateDefaultSubobject<USphereComponent>(TEXT("WarmthQuery"));
    WarmthQuery->SetupAttachment(GetRootComponent());
    WarmthQuery->InitSphereRadius(WarmthRadiusCm);
    WarmthQuery->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    WarmthQuery->SetCollisionObjectType(ECC_WorldDynamic);
    WarmthQuery->SetCollisionResponseToAllChannels(ECR_Ignore);
    WarmthQuery->SetGenerateOverlapEvents(false);
    WarmthQuery->SetCanEverAffectNavigation(false);
}

void AColdSteelCampfire::BeginPlay()
{
    Super::BeginPlay();
    if(!HasAuthority())WarmthQuery->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    if(GetNetMode()!=NM_DedicatedServer)
        if(auto* Fluid=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>())Fluid->RegisterCampfire(this);
}

void AColdSteelCampfire::EndPlay(const EEndPlayReason::Type Reason)
{
    WarmthQuery->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    if(auto* Fluid=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>())Fluid->UnregisterCampfire(this);
    SetPresentationActive(false);
    Super::EndPlay(Reason);
}

bool AColdSteelCampfire::IsProvidingWarmth() const
{
    return !bExtinguished&&(HasAuthority()?FuelUntilTicks>FDateTime::UtcNow().GetTicks():bFuelBurning)
        &&!IsActorBeingDestroyed()&&!ActorHasTag(TEXT("VoxelDetached"));
}

void AColdSteelCampfire::SetFuelSeconds(double Seconds)
{
    if(!HasAuthority())return;
    FuelUntilTicks=Seconds>0?FDateTime::UtcNow().GetTicks()
        +FMath::RoundToInt64(Seconds*ETimespan::TicksPerSecond):0;
    // Replicate transitions only; clients never depend on their computer's UTC clock.
    const bool bBurning=Seconds>0;
    if(bFuelBurning!=bBurning){bFuelBurning=bBurning;OnRep_Fuel();ForceNetUpdate();}
}

void AColdSteelCampfire::OnRep_Fuel()
{
    if(!IsProvidingWarmth())SetPresentationActive(false);
}

float AColdSteelCampfire::ConsumptionMultiplierAt(const APawn* Player)
{
    if(!Player||!Player->HasAuthority()||!Player->IsPlayerControlled())return 1.f;
    const UWorld* World=Player->GetWorld();
    if(!World)return 1.f;
    FVector Position=Player->GetActorLocation();
    if(const auto* Character=Cast<ACharacter>(Player))
        Position.Z-=Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    TArray<FOverlapResult> Nearby;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(CampfireWarmth),false,Player);
    // The scene broadphase finds only proxies covering the player's feet. Exact distance below
    // removes the 1 cm query margin. No cached factor survives leaving, death, load or destruction.
    World->OverlapMultiByObjectType(Nearby,Position,FQuat::Identity,
        FCollisionObjectQueryParams(ECC_WorldDynamic),FCollisionShape::MakeSphere(1.f),Query);
    for(const FOverlapResult& Hit:Nearby)
        if(const auto* Fire=Cast<AColdSteelCampfire>(Hit.GetActor());IsValid(Fire)&&Fire->HasAuthority()
            &&Fire->IsProvidingWarmth()&&FVector::DistSquared(Position,Fire->GetActorLocation())<=FMath::Square(WarmthRadiusCm))
            return ConsumptionMultiplier; // Any number of fires contributes exactly one factor.
    return 1.f;
}

void AColdSteelCampfire::SetPresentationActive(bool bActive)
{
    bActive=bActive&&IsProvidingWarmth()&&GetNetMode()!=NM_DedicatedServer&&FlameSystem!=nullptr;
    if(!bActive)
    {
        if(Flame){Flame->DeactivateImmediate();Flame->DestroyComponent();Flame=nullptr;}
        if(FireLight){FireLight->DestroyComponent();FireLight=nullptr;}
        return;
    }
    if(Flame)return;
    Flame=NewObject<UNiagaraComponent>(this,NAME_None,RF_Transient);
    Flame->SetupAttachment(GetRootComponent());
    Flame->SetAutoActivate(false);
    Flame->SetAutoDestroy(false);
    Flame->SetAsset(FlameSystem);
    Flame->SetRelativeLocation(FVector(0,0,20));
    Flame->SetRelativeScale3D(FVector(1.0f));
    Flame->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Flame->SetCanEverAffectNavigation(false);
    Flame->SetCastShadow(false);
    Flame->bAffectDistanceFieldLighting=false;
    Flame->RegisterComponent();
    Flame->Activate(true);
    FireLight=NewObject<UPointLightComponent>(this,NAME_None,RF_Transient);
    FireLight->SetupAttachment(GetRootComponent());
    FireLight->SetMobility(EComponentMobility::Movable);
    FireLight->SetRelativeLocation(FVector(0,0,55));
    FireLight->SetIntensityUnits(ELightUnits::Lumens);
    FireLight->SetIntensity(350.f);
    FireLight->SetLightColor(FLinearColor(1.f,.60f,.26f));
    FireLight->SetAttenuationRadius(500.f);
    FireLight->SetSourceRadius(12.f);
    FireLight->SetCastShadows(false);
    FireLight->SetVolumetricScatteringIntensity(.08f);
    FireLight->RegisterComponent();
}

void AColdSteelCampfire::Extinguish()
{
    if(!HasAuthority()||bExtinguished)return;
    bExtinguished=true;OnRep_Extinguished();ForceNetUpdate();
}

void AColdSteelCampfire::OnRep_Extinguished()
{
    if(!bExtinguished)return;
    WarmthQuery->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    SetPresentationActive(false);
}

void AColdSteelCampfire::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AColdSteelCampfire,bExtinguished);
    DOREPLIFETIME(AColdSteelCampfire,bFuelBurning);
    DOREPLIFETIME(AColdSteelCampfire,Shared);
}
