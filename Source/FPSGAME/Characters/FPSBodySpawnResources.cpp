#include "FPSBodyAssetPreloader.h"
#include "Components/ActorComponent.h"
#include "GameFramework/Actor.h"
#include "UObject/UObjectGlobals.h"

void UFPSBodyAssetPreloader::RetainSpawnAssets(AActor* Character)
{
    if (!Character || CapturedSpawnClasses.Contains(Character->GetClass())) return;
    CapturedSpawnClasses.Add(Character->GetClass());
    TArray<UObject*> References;
    // Only immediate reflected references on the bootstrap pawn and its components:
    // do not walk the World, controller, inventory, or unused equipment variants.
    FReferenceFinder Finder(References, nullptr, false, false, false, false);
    Finder.FindReferences(Character);
    TInlineComponentArray<UActorComponent*> Components(Character);
    for (UActorComponent* Component : Components) Finder.FindReferences(Component);
    for (UObject* Object : References)
        if (Object && Object->IsAsset()) SpawnAssets.AddUnique(Object);

    // The legacy bootstrap probes the native AKM before choosing the default M4.
    // Its first successful probe is not retained by any component after that choice.
    // Retain only the already loaded selection; never load the fallback catalog here.
    if (UObject* Probe = FindObject<UObject>(nullptr,
        TEXT("/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative.SK_AKM_MannyNative")))
        SpawnAssets.AddUnique(Probe);
    UE_LOG(LogTemp, Display, TEXT("PLAYER_SPAWN_RESOURCES retained=%d class=%s"),
        SpawnAssets.Num(), *Character->GetClass()->GetName());
}
