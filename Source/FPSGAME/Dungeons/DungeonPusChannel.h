#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DungeonPusChannel.generated.h"

class UStaticMeshComponent;

/** Permanent dungeon residue. Uses fat-zombie corrosion damage, restricted to wet floor contact. */
UCLASS()
class FPSGAME_API ADungeonPusChannel : public AActor
{
    GENERATED_BODY()
public:
    ADungeonPusChannel();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    /** Starts the normal pulse clock once the owning dungeon has finished assembly. */
    void ActivateDamage();

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Pus") TObjectPtr<UStaticMeshComponent> Surface;
    // Actor origin is the supporting floor; dimensions are the wet footprint in centimetres.
    // PusRadialFootprint tag selects the authored irregular ellipse; otherwise use the trench rectangle.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Pus") FVector2D HalfSize = FVector2D(141,391);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Pus", meta=(ClampMin="0")) float DamagePerPulse;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Pus", meta=(ClampMin="0.1")) float DamageInterval;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Pus", meta=(ClampMin="0",ClampMax="20")) float GroundContactTolerance = 10.f;
private:
    FTimerHandle DamageTimer;
    void PulseDamage();
};
