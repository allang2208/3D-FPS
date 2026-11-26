#pragma once
#include "CoreMinimal.h"
#include "PCGSettings.h"
#include "ForestRootFit.generated.h"

class UStaticMesh;
class UPCGComponent;

namespace ForestRootFit
{
// Coordinates are in centimetres. The offset accounts for the visible root collar above the mesh pivot.
double Seat(FVector2D Center,double Radius,double CollarZ,TFunctionRef<double(double,double)> Height);
#if WITH_EDITOR
FVector2D Measure(UStaticMesh* Mesh);
#endif
}

UCLASS()
class UForestRootFitSettings : public UPCGSettings
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere,Category="Roots") double RootRadius = 45.;
    UPROPERTY(EditAnywhere,Category="Roots") double RootCollarZ = 0.;
    UFUNCTION(BlueprintCallable,Category="Forest|Authoring")
    static FVector2D MeasureRoot(UStaticMesh* Mesh);
    UFUNCTION(BlueprintCallable,Category="Forest|Authoring")
    static bool RegenerateTrees(UPCGComponent* Component);
#if WITH_EDITOR
    virtual FName GetDefaultNodeName() const override { return TEXT("ForestRootFit"); }
    virtual FText GetDefaultNodeTitle() const override { return NSLOCTEXT("ForestVillage","SeatRoots","Seat tree roots on landscape"); }
#endif
protected:
    virtual TArray<FPCGPinProperties> InputPinProperties() const override { return DefaultPointInputPinProperties(); }
    virtual TArray<FPCGPinProperties> OutputPinProperties() const override { return DefaultPointOutputPinProperties(); }
    virtual FPCGElementPtr CreateElement() const override;
};
