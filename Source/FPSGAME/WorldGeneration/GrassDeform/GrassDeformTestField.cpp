#include "GrassDeformTestField.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/SceneComponent.h"

AGrassDeformTestField::AGrassDeformTestField()
{
    PrimaryActorTick.bCanEverTick = false;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
    RootComponent->SetMobility(EComponentMobility::Static);
    TallGrassA = CreateDefaultSubobject<UHierarchicalInstancedStaticMeshComponent>(TEXT("TallGrassA"));
    TallGrassB = CreateDefaultSubobject<UHierarchicalInstancedStaticMeshComponent>(TEXT("TallGrassB"));
    for (auto* Grass : { TallGrassA.Get(), TallGrassB.Get() })
    {
        Grass->SetupAttachment(RootComponent);
        Grass->SetMobility(EComponentMobility::Static);
        Grass->SetCollisionProfileName(TEXT("NoCollision"));
        Grass->SetGenerateOverlapEvents(false);
        Grass->SetCanEverAffectNavigation(false);
        Grass->SetCastShadow(false);
        Grass->SetEvaluateWorldPositionOffset(true);
        Grass->SetCullDistances(6000, 10000);
        Grass->bEnableDensityScaling = false;
    }
}
