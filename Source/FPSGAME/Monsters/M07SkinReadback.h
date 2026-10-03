#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "M07SkinReadback.generated.h"

class UAnimSequence;
class USkeletalMesh;

/** Read existing M-07 import and render skin data without changing an asset. */
UCLASS()
class FPSGAME_API UM07SkinReadback : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    /** JSON contains reference bindings, frame-zero poses and bounded vertex samples. */
    UFUNCTION(BlueprintCallable, Category = "Monsters|M07|Authoring")
    static FString ReadSkinData(USkeletalMesh* Mesh, UAnimSequence* Animation);
};
