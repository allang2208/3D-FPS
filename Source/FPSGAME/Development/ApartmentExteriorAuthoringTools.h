#pragma once

#include "Kismet/BlueprintFunctionLibrary.h"
#include "ApartmentExteriorAuthoringTools.generated.h"

class UTextureCube;
class UWorld;
class AActor;

/** Offline asset authoring. No actor, capture, or render target is saved in the map. */
UCLASS()
class FPSGAME_API UApartmentExteriorAuthoringTools : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Development|Apartment")
    static UTextureCube* BakeCityReflection(UWorld* World, const TArray<AActor*>& StaticActors,
        const FString& AssetPath, FVector Origin, int32 Resolution = 2048);
};
