#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "BlindSupplicantAuthoring.generated.h"

class USkeletalMesh;

/** Offline authoring entry points for M-07's six separate gill membranes. */
UCLASS()
class FPSGAME_API UBlindSupplicantAuthoring : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    /**
     * Extract the six simulation sections, or rebind their saved cloth assets
     * after reimporting the display mesh. The manifest uses mesh-reference cm
     * for vertices and bone-local cm for collision capsule endpoints.
     * Returns a JSON authoring receipt. The caller saves the mesh package.
     */
    UFUNCTION(BlueprintCallable, Category = "Monsters|M07|Authoring")
    static FString BuildGillCloth(USkeletalMesh* Mesh, const FString& WeightManifestFile, bool bExtractSimulation = true);

    /** Keep the six display panels, combine their saved simulation islands so
     * Chaos self-collision also acts between panels. Caller saves the mesh. */
    UFUNCTION(BlueprintCallable, Category = "Monsters|M07|Authoring")
    static FString BuildInteractingGillCloth(USkeletalMesh* Mesh, const FString& WeightManifestFile);

    /** Restore this task's original six simulation captures from its preserved
     * source package, then build the interacting runtime cloth on the display. */
    UFUNCTION(BlueprintCallable, Category = "Monsters|M07|Authoring")
    static FString BuildInteractingGillClothFromSavedSource(USkeletalMesh* Mesh, USkeletalMesh* SimulationSource, const FString& WeightManifestFile);

    /** Detach this task's failed cloth before replacing its display geometry.
     * The caller keeps the package in memory and saves after replacement. */
    UFUNCTION(BlueprintCallable, Category = "Monsters|M07|Authoring")
    static FString RemoveGillClothForReimport(USkeletalMesh* Mesh);

    /** Configure distant reductions on the V13 candidate; caller generates and saves LODs. */
    UFUNCTION(BlueprintCallable, Category = "Monsters|M07|Authoring", meta=(ScriptName="configure_distance_lods"))
    static bool ConfigureDistanceLODs(USkeletalMesh* Mesh);
};
