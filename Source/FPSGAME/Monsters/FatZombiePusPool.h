#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FatZombiePusPool.generated.h"

class APawn;
class UDynamicMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;

USTRUCT(BlueprintType)
struct FFatZombiePusSettings
{
    GENERATED_BODY()
    // game-dev corrosionAura supplies damage/interval; UE death residue lasts 20 s.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="0")) float Damage = 8.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="0.1", Units="s")) float Interval = .5f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="0.5", Units="s")) float Duration = 20.f;
    // UE ground dimensions; the source 200 x 50 ellipse is a 2D ground projection.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="30", Units="cm")) float LongRadius = 145.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="20", Units="cm")) float ShortRadius = 90.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="0", ClampMax="24")) int32 MinDroplets = 7;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="0", ClampMax="24")) int32 MaxDroplets = 12;
    // Death starts a small puddle; the full footprint is reached after this time.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="0", Units="s")) float SpreadSeconds = 1.6f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="0", Units="s")) float FadeSeconds = 1.f;
    // Zero chooses a new seed per death; a nonzero value keeps the same footprint.
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 ShapeSeed = 0;
};

/** One independent death residue; the rendered ground triangles also define damage coverage. */
UCLASS()
class FPSGAME_API AFatZombiePusPool : public AActor
{
    GENERATED_BODY()
public:
    AFatZombiePusPool();
    void InitializeFrom(APawn* Source, const FFatZombiePusSettings& Settings);
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Pus") TObjectPtr<UDynamicMeshComponent> Surface;
    UPROPERTY(EditDefaultsOnly, Category="Pus") TObjectPtr<UMaterialInterface> PusMaterial;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Pus") int32 Seed = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Pus") int32 DamagePulses = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Pus") int32 SuccessfulHits = 0;
private:
    struct FGroundTriangle
    {
        FVector A, B, C; // Local ground positions, excluding cosmetic film thickness.
        FVector Coverage;
        FVector Arrival; // Matches vertex-color B: when the spreading front reaches each corner.
    };
    TArray<FGroundTriangle> GroundTriangles;
    FFatZombiePusSettings Tuning;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Liquid;
    TWeakObjectPtr<AController> DamageInstigator;
    TWeakObjectPtr<APawn> SourcePawn;
    FName SourceFaction;
    uint8 SourceTeam = 255;
    double StartTime = 0;
    float QueryRadius = 200.f;
    FTimerHandle DamageTimer;
    bool BuildFootprint();
    bool TraceGround(FVector LocalXY, FVector& Ground, FVector& Normal) const;
    float GetSpreadProgress(float Age) const;
    bool TouchesGround(const APawn* Target, float Spread) const;
    bool IsHostile(const APawn* Target) const;
    void PulseDamage();
};
