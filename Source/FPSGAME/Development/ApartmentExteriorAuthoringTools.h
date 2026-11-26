#pragma once

#include "Kismet/BlueprintFunctionLibrary.h"
#include "ApartmentExteriorAuthoringTools.generated.h"

class UTextureCube;
class UWorld;
class AActor;
class USceneCaptureComponent2D;

/** Offline asset authoring. No actor, capture, or render target is saved in the map. */
UCLASS()
class FPSGAME_API UApartmentExteriorAuthoringTools : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Development|Apartment")
    static UTextureCube* BakeCityReflection(UWorld* World, const TArray<AActor*>& StaticActors,
        const FString& AssetPath, FVector Origin, int32 Resolution = 2048);

#if WITH_EDITOR
    /** Render the final editor-world camera across streaming frames before reading its target. */
    UFUNCTION(BlueprintCallable, Category="Development|Scene Capture")
    static bool RenderCommandletCamera(USceneCaptureComponent2D* Camera, int32 WarmupFrames = 48);
#endif
};
