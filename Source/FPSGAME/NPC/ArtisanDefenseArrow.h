#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ArtisanDefenseArrow.generated.h"

class UStaticMeshComponent;

/** Ordinary village hunting arrow. Its first blocking contact ends the flight. */
UCLASS(NotBlueprintable)
class FPSGAME_API AArtisanDefenseArrow : public AActor
{
    GENERATED_BODY()
public:
    AArtisanDefenseArrow();
    void Launch(const FVector& Direction, float Damage);
    virtual void Tick(float Dt) override;
    static void FitWoodArrow(UStaticMeshComponent& Mesh, const FVector& Tail, const FVector& Tip);
protected:
    virtual void BeginPlay() override;
private:
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Shaft;
    FVector Velocity = FVector::ZeroVector;
    float HitDamage = 0.f;
};
