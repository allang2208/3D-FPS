#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "PlayerKnockdownComponent.generated.h"
class APlayerController;
class UCameraComponent;
class USceneComponent;
class UFPSCombatHealthComponent;
class UFPSPlayerBodyComponent;

/**
 * Pawn-owned player knockdown (2026-11-14): fall on the back, lie, get up (PlayerKnockdownMotion, 2.60 s).
 * The server starts it and replicates the start time; every machine replays the same clock. While it runs,
 * move/look/action input is locked like the guard-break stun, the world body plays the full-body
 * "Knockdown" clip for everyone, the owner's first-person camera follows that body's head and the two-handed
 * sword plays A_RuneSword_Knockdown; every other first-person weapon is knocked down out of the frame and brought
 * back up while standing (PlayerKnockdownMotion::ViewmodelDrop). Without the full-body clip (e.g. a body variant
 * that has none) the owner's legs are hidden and the camera uses the keyed fallback curve.
 * A knockdown while airborne waits for the landing; in water, while flying or resting on furniture it is refused.
 * Dying on the ground keeps the body lying (a death while still rising sinks back down) and the death camera low.
 * The server rejects hit reports, spell casts and quick-combat starts while it runs. Entry: the Y test key only.
 */
UCLASS(ClassGroup=(Combat),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UPlayerKnockdownComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UPlayerKnockdownComponent();
    static UPlayerKnockdownComponent* GetOrCreate(AActor* Owner);
    /** Hash lookup (no component scan); every knockdown component registers itself with its owner. */
    static UPlayerKnockdownComponent* Find(const AActor* Owner);
    static bool IsKnockedDown(const AActor* Owner);
    /** The owner's first-person legs are hidden only when no full-body knockdown is available for this body. */
    static bool HidesOwnerLowerBody(const AActor* Owner);
    /** Death camera while the body is held on the ground (see Death* in PlayerKnockdownMotion). */
    static bool GetDeathHoldView(const AActor* Owner,FVector& Eye,FRotator& Rotation);
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    /** Authority only. Ignored while a knockdown runs or waits, while dead, in water, flying or resting. The body
     *  clip falls on the back, away from the current facing; a hit from another side needs its own clip first. */
    bool Apply();
    bool IsRunning() const { return bActive; }
    /** Seconds since the knockdown started, on the shared clock. */
    float Age() const;
    /** World body: clip time and full-body blend weight (0 when neither running nor holding a death). */
    void BodyAnimationSample(float& Seconds,float& Weight) const;
    /** This body has the "Knockdown" clip and its authored eye track. */
    bool HasFullBody() const;
    /** Owner camera: undo last frame's fall before the camera layers run ... */
    void RestoreCamera(UCameraComponent& Camera);
    /** ... and put this frame's fall on top of them (the viewmodel is attached to this camera). */
    void ApplyCamera(UCameraComponent& Camera);
protected:
    virtual void OnRegister() override;
    virtual void OnUnregister() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void Begin(float InitialAge);
    void Release();
    bool IsOwnerDead() const;
    /** Latch the moment of a death that happens during the knockdown (called from every reader). */
    void UpdateDeathLatch() const;
    /** Clip time to hold after a death on the ground; < 0 when the normal death plays. */
    float DeathHoldTime() const;
    bool DeathHoldView(FVector& Eye,FRotator& Rotation) const;
    /** Generic weapon drop: reparent the camera's first-person children (except a weapon with its own clip)
     *  under one root for the knockdown, drive that root, and put them back unchanged at the end. */
    void BeginViewmodelDrop();
    void EndViewmodelDrop();
    UPROPERTY(Transient) TObjectPtr<USceneComponent> ViewmodelDropRoot;
    TArray<TWeakObjectPtr<USceneComponent>> DroppedViewmodels;
    UFUNCTION() void OnRep_StartedAt();
    /** Server world time of the last knockdown start; < 0 before the first one. */
    UPROPERTY(ReplicatedUsing=OnRep_StartedAt) double StartedAt=-1.;
    double LocalStartedAt=0.;
    bool bActive=false;
    /** Server: knocked down in the air; starts on landing (or gives up after PlayerKnockdownMotion::LandingWait). */
    bool bPendingLanding=false;
    double PendingSince=0.;
    mutable bool bDeathLatched=false;
    mutable float DeathAge=0.f;
    mutable double DeathAt=0.;
    bool bCameraApplied=false;
    FVector CameraBaseRelative=FVector::ZeroVector;
    /** Last first-person knockdown view, for the death camera once the character stops ticking. */
    FVector LastEye=FVector::ZeroVector;
    float LastBaseEyeCm=170.f,LastBasePitch=0.f,LastYaw=0.f,LastRoll=0.f;
    bool bHasLastView=false;
    TWeakObjectPtr<APlayerController> LockedController;
    TWeakObjectPtr<UFPSCombatHealthComponent> CachedHealth;
    TWeakObjectPtr<UFPSPlayerBodyComponent> CachedBody;
    FTimerHandle Timer;
};
