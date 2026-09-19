#pragma once
#include "Kismet/BlueprintFunctionLibrary.h"
#include "AKMAnimationAuditLibrary.generated.h"
class UAnimSequence;

UCLASS()
class FPSGAME_API UAKMAnimationAuditLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    // Editor verification must not silently sample raw data while async compression is pending.
    UFUNCTION(BlueprintCallable, Category="Weapon|Validation")
    static void FinishAnimationCompression(UAnimSequence* Animation);
};
