#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "ExplosiveWarningSubsystem.generated.h"

class ABellowSacProjectile;
class APlayerController;

struct FExplosiveWarning
{
    TWeakObjectPtr<ABellowSacProjectile> Projectile;
    float Distance = 0.f;
    bool bExposed = false;
};

/** Local presentation registry. Damage remains entirely on the projectile. */
UCLASS()
class FPSGAME_API UExplosiveWarningSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    void Register(ABellowSacProjectile* Projectile);
    void Unregister(ABellowSacProjectile* Projectile);
    const TArray<FExplosiveWarning>& ForPlayer(const APlayerController* Player) const;
    virtual void Tick(float DeltaTime) override;
    virtual bool IsTickable() const override { return Projectiles.Num() > 0; }
    virtual TStatId GetStatId() const override;
    virtual void Deinitialize() override;
protected:
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
private:
    TArray<TWeakObjectPtr<ABellowSacProjectile>> Projectiles;
    TMap<TWeakObjectPtr<const APlayerController>, TArray<FExplosiveWarning>> Views;
    float UntilRefresh = 0.f;
};
