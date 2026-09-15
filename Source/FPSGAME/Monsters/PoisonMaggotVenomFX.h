#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "PoisonMaggotVenomFX.generated.h"

class UStaticMesh;
class UMaterialInterface;
class UInstancedStaticMeshComponent;
class UDecalComponent;

/** Cosmetic liquid fragments shared by all maggots; never applies damage. */
UCLASS()
class FPSGAME_API UPoisonMaggotVenomFX : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    UPoisonMaggotVenomFX();
    void AddTrail(const FVector& Position, const FVector& Velocity, bool bMist);
    void AddImpact(const FHitResult& Hit, const FVector& IncomingVelocity);
    virtual void OnWorldBeginPlay(UWorld& World) override;
    virtual void Deinitialize() override;
    virtual void Tick(float DeltaTime) override;
    virtual bool IsTickable() const override { return bReady && ActiveParticles > 0; }
    virtual TStatId GetStatId() const override;
protected:
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
private:
    static constexpr int32 DropCount = 192;
    static constexpr int32 MistCount = 48;
    static constexpr int32 MarkCount = 40;
    struct FFragment
    {
        FVector Position = FVector::ZeroVector, Velocity = FVector::ZeroVector;
        FVector PlanePoint = FVector::ZeroVector, PlaneNormal = FVector::ZeroVector;
        float Age = 0, Life = 0, Size = 1, Stretch = 1, Gravity = 0, Opacity = 1, Seed = 0;
    };
    void AddFragment(int32 Group, const FVector& Position, const FVector& Velocity,
        float Life, float Size, float Stretch, float Gravity, float Opacity,
        const FVector& PlanePoint = FVector::ZeroVector, const FVector& PlaneNormal = FVector::ZeroVector);

    UPROPERTY() TObjectPtr<UStaticMesh> SphereMesh;
    UPROPERTY() TObjectPtr<UStaticMesh> PlaneMesh;
    UPROPERTY() TObjectPtr<UMaterialInterface> DropMaterial;
    UPROPERTY() TObjectPtr<UMaterialInterface> MistMaterial;
    UPROPERTY() TObjectPtr<UMaterialInterface> WetMaterial;
    UPROPERTY(Transient) TArray<TObjectPtr<UInstancedStaticMeshComponent>> Renderers;
    UPROPERTY(Transient) TArray<TObjectPtr<UDecalComponent>> Marks;
    FFragment Fragments[DropCount + MistCount];
    TArray<FTransform> Transforms[2];
    FRandomStream Random{9152026};
    int32 Cursors[2] = {0,0};
    int32 MarkCursor = 0, ActiveParticles = 0;
    bool bReady = false;
};
