#pragma once

#include "Kismet/BlueprintFunctionLibrary.h"
#include "TemperateForestAuthoringLibrary.generated.h"

/** Small editor-only bridge for the native material-attribute pin API. */
UCLASS()
class FPSGAME_API UTemperateForestAuthoringLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Development|Temperate Forest")
    static int32 AddWindOffsetPin(UObject* Expression);

    UFUNCTION(BlueprintCallable, Category="Development|Temperate Forest")
    static int32 AddVisibilityMaskPin(UObject* Expression);

    UFUNCTION(BlueprintCallable, Category="Development|Temperate Forest")
    static int32 AddSurfaceBlendPin(UObject* Expression,int32 Channel);

    /** X=fade start, Y=visible end, Z=runtime generation radius, all in cm. */
    UFUNCTION(BlueprintPure, Category="Development|Temperate Forest")
    static FVector GetVisibilityDistances(int32 Layer);
};
