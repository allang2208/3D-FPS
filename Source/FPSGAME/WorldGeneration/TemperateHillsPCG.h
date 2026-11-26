#pragma once
#include "CoreMinimal.h"
#include "PCGSettings.h"
#include "RuntimeGen/GenSources/PCGGenSourceBase.h"
#include "TemperateHillsPCG.generated.h"

// A remote controller has no local viewport on a listen server. Its possessed
// pawn supplies the position for authoritative rock/ore collision instead.
UCLASS(Transient)
class UTemperateHillsGuestSource : public UObject, public IPCGGenSourceBase
{
    GENERATED_BODY()
public:
    TWeakObjectPtr<class APlayerController> Controller;
    virtual TOptional<FVector> GetPosition() const override;
    virtual TOptional<FVector> GetDirection() const override;
    virtual bool IsLocal() const override { return false; }
};

/** Deterministic, cell-owned candidates sampled from the exact runtime terrain function. */
UCLASS(BlueprintType, ClassGroup=(Procedural))
class FPSGAME_API UTemperateHillsPointsSettings : public UPCGSettings
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Hills", meta=(ClampMin="0",ClampMax="4")) int32 Layer = 0;
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
