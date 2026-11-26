#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "WeatherAssetAuthoring.generated.h"

/** Background asset-production helpers; no worlds, actors or playback are started. */
UCLASS()
class FPSGAME_API UWeatherAssetAuthoring : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable,Category="Weather|Authoring")
    static bool SaveWetMaterialIndex(const FString& PackageName,const TMap<FString,FString>& Paths);
    UFUNCTION(BlueprintCallable,Category="Weather|Authoring")
    static FString DescribeWeatherInterface(UObject* Object);
    /** Immediate between-batch collection in the isolated production commandlet. */
    UFUNCTION(BlueprintCallable,Category="Weather|Authoring")
    static void ReleaseAuthoringBatch();
};
