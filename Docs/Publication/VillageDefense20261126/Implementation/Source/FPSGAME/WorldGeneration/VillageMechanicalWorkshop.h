#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "VillageMechanicalWorkshop.generated.h"

class UStaticMeshComponent;

/** Roadside workshop opposite the east-gate stable; progression belongs to the current hills world. */
UCLASS()
class FPSGAME_API AVillageMechanicalWorkshop : public AActor
{
    GENERATED_BODY()
public:
    AVillageMechanicalWorkshop();
    UFUNCTION(BlueprintPure, Category="Village|Mechanical Workshop")
    FTransform GetUpgradeWorkbenchTransform() const;
    UFUNCTION(BlueprintPure, Category="Village|Mechanical Workshop")
    FTransform GetUpgradeApproachTransform() const;
protected:
    virtual void BeginPlay() override;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Shell;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> AssemblyBay;
};
