// Rune sword special attack: orbiting energy blades (ported from the 2D project's
// rune-sword-system.js). G activates four blades around the player for up to 30 s;
// every further G press launches one at the crosshair. Blades deal magic damage
// (weapon attack + magic attack) x 1.2; kills shorten running ability cooldowns,
// mirroring the 2D contract (the orbit cooldown starts only after the orbit ends).
#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "RuneOrbBladesComponent.generated.h"

class ARuneOrbBlade;
class UColdSteelStatusModel;
class UStaticMesh;
class UFPSFireballComponent;

UCLASS(ClassGroup=(Skills), meta=(BlueprintSpawnableComponent))
class FPSGAME_API URuneOrbBladesComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    URuneOrbBladesComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta, ELevelTick Type, FActorComponentTickFunction* Tick) override;

    // G: while active, launch one blade; otherwise open the orbit (rune sword only).
    UFUNCTION(BlueprintCallable, Category="Rune Sword|Orbit Blades") void Trigger();
    UFUNCTION(BlueprintPure, Category="Rune Sword|Orbit Blades") bool IsOrbitActive() const { return bActive; }
    UFUNCTION(BlueprintPure, Category="Rune Sword|Orbit Blades") float CooldownRemaining() const { return Cooldown; }
    UFUNCTION(BlueprintPure, Category="Rune Sword|Orbit Blades") float CooldownFraction() const
    { return CooldownDuration > 0.f ? FMath::Clamp(Cooldown / CooldownDuration, 0.f, 1.f) : 0.f; }
    // The orbit ends when the sword is stowed or swapped, exactly like the 2D weapon switch.
    void EndOrbit();
    // Blade kills trim all running ability cooldowns through the shared profile path.
    void NotifyBladeResult(bool bKilled);
    void ReduceCooldown(float Seconds) { Cooldown = FMath::Max(0.f, Cooldown - FMath::Max(0.f, Seconds)); }
    // Per-summon affix snapshot consumed by the flying blades (2D craft-affix bridge).
    float BladeRangeCM() const { return ActiveRangeCM; }
    int32 BladeVulnerabilityStacks() const { return VulnerabilityStacks; }

private:
    struct FBladeSlot
    {
        float Lateral = 0.f;   // cm offset along the camera's right axis (ice-spike wings)
        float Roll = 0.f;      // per-blade roll so the row does not read as one clone
        float SwayPhase = 0.f;
        TWeakObjectPtr<ARuneOrbBlade> Orb;
        bool bLaunched = false;
    };
    void OpenOrbit();
    void LaunchOne();
    void FinishOrbit(bool bCancelGesture);
    bool CanUse() const;
    int32 AvailableBladeCount() const;
    bool SwordEquipped() const;
    bool NoAbilityCooldown() const;
    bool ViewBasis(FVector& Eye, FVector& Forward, FVector& Right, FVector& Up, float& TanVertical) const;
    // Shared left-hand spell gesture (the fireball's): raise-and-gather on summon,
    // release push on launch. Requests queue until the hand is free.
    UFPSFireballComponent* Hands() const;
    void ServiceGestureQueue();
    static float BladeDamage(const UColdSteelStatusModel* Profile);

    // Plain runtime bookkeeping: weak refs only, the blades themselves are world actors.
    TArray<FBladeSlot> Slots;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> BladeMesh;
    float Elapsed = 0.f;
    float Cooldown = 0.f;
    bool bActive = false;
    bool bQueuedSummon = false;
    int32 PendingLaunches = 0;
    double LastLaunchTime = -1.0;
    static constexpr float BurstInterval = .10f;
    static constexpr float BurstHoldSeconds = .30f;

    static constexpr int32 BaseBladeCount = 4;
    static constexpr float ActiveSeconds = 30.f;
    static constexpr float CooldownDuration = 15.f;
    static constexpr float BladeDamageMultiplier = 1.2f;
    // Hover placement follows the ice spike's accepted view-space convention:
    // a wing row in front of the camera (even indices left) instead of a world ring
    // around the capsule, which the first-person view could never see.
    static constexpr float ForwardDistance = 72.f;
    static constexpr float WingGap = 8.f;
    static constexpr float WingSpacing = 14.f;

    // 2D craft-affix bridge (craft-config.json keys read through the enhancement
    // system's CraftEffect): runeRestructureCount adds blades, specialRangeDelta
    // extends flight in 2D pixels (x1.6 cm), magicVulnerabilityOnHit stacks the
    // target's magic vulnerability. Zero until an affix carrying the key exists.
    int32 ActiveBladeCount = BaseBladeCount;
    float ActiveRangeCM = 1600.f;
    int32 VulnerabilityStacks = 0;
};
