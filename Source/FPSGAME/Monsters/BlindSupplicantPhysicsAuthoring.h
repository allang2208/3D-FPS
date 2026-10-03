#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "BlindSupplicantPhysicsAuthoring.generated.h"

class USkeletalMesh;

/** Offline production of M-07's anatomical hit volumes and death ragdoll. */
UCLASS()
class FPSGAME_API UBlindSupplicantPhysicsAuthoring : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    /**
     * Create or rebuild /Game/Monsters/BlindSupplicantM07/PA_M07 and assign it
     * to this character's mesh. Gill cloth keeps its own collision assets.
     * Returns a JSON production receipt; the caller saves both asset packages.
     * This entry point does not run physics, open an editor, or save a map.
     */
    UFUNCTION(BlueprintCallable, Category = "Monsters|M07|Authoring")
    static FString BuildBodyPhysics(USkeletalMesh* Mesh);
};
