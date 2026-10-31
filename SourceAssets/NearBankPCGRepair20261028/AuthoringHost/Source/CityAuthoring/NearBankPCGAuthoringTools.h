#pragma once

#include "Kismet/BlueprintFunctionLibrary.h"
#include "NearBankPCGAuthoringTools.generated.h"

class APCGVolume;
class UPCGGraphInterface;

/** Offline apartment district authoring. Does not start or tick gameplay. */
UCLASS()
class CITYAUTHORING_API UNearBankPCGAuthoringTools : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Development|NearBankPCG")
    static bool GenerateOffline(APCGVolume* Volume, float TimeoutSeconds = 300.0f);

    UFUNCTION(BlueprintCallable, Category="Development|NearBankPCG")
    static AActor* CreateSplineInput(UObject* WorldContext, const FString& Label,
        const TArray<FVector>& WorldPoints, bool bClosed, FName SemanticTag);

    UFUNCTION(BlueprintCallable, Category="Development|NearBankPCG")
    static FString DescribeParameters(const UPCGGraphInterface* Graph);
};
