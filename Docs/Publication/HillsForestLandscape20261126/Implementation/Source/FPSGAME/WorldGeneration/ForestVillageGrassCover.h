#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "PCGSettings.h"
#include "ForestVillageGrassCover.generated.h"

class UPCGComponent;

// One temporary PCG owner per visible patch. All cells use the same cooked graph.
UCLASS(NotBlueprintable, Transient)
class AForestGrassCell : public AActor
{
    GENERATED_BODY()
public:
    AForestGrassCell();
    FIntPoint Cell = FIntPoint::ZeroValue;
    UPROPERTY() TObjectPtr<UPCGComponent> PCG;
};

UCLASS()
class UForestGrassSitesSettings : public UPCGSettings
{
    GENERATED_BODY()
public:
#if WITH_EDITOR
    virtual FName GetDefaultNodeName() const override { return TEXT("ForestGrassSites"); }
    virtual FText GetDefaultNodeTitle() const override { return NSLOCTEXT("ForestVillage","GrassSites","Nearby forest grass sites"); }
#endif
protected:
    virtual TArray<FPCGPinProperties> InputPinProperties() const override { return {}; }
    virtual TArray<FPCGPinProperties> OutputPinProperties() const override;
    virtual FPCGElementPtr CreateElement() const override;
};
