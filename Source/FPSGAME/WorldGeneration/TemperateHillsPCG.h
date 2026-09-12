#pragma once
#include "CoreMinimal.h"
#include "PCGSettings.h"
#include "TemperateHillsPCG.generated.h"

/** Deterministic, cell-owned candidates sampled from the exact runtime terrain function. */
UCLASS(BlueprintType, ClassGroup=(Procedural))
class FPSGAME_API UTemperateHillsPointsSettings : public UPCGSettings
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Hills", meta=(ClampMin="0",ClampMax="3")) int32 Layer = 0;
#if WITH_EDITOR
    virtual FName GetDefaultNodeName() const override { return TEXT("TemperateHillsPoints"); }
    virtual FText GetDefaultNodeTitle() const override { return NSLOCTEXT("Hills","Points","Temperate Hills Candidates"); }
    virtual EPCGSettingsType GetType() const override { return EPCGSettingsType::Spatial; }
#endif
protected:
    virtual TArray<FPCGPinProperties> InputPinProperties() const override { return {}; }
    virtual TArray<FPCGPinProperties> OutputPinProperties() const override { return DefaultPointOutputPinProperties(); }
    virtual FPCGElementPtr CreateElement() const override;
};
