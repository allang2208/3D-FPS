#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "WeaponActionCameraComponent.generated.h"

class UCameraComponent;

enum class EM4CameraAction : uint8
{
    None, Reload, ReloadEmpty, DrumReload, DrumReloadEmpty, EquipCharge,
    Ash12Reload, Ash12ReloadEmpty, PKMReload, PKMReloadEmpty, PKMEquip
};

// Local presentation driven by the weapon's source-animation clock.
// Owns the FPS camera's additive view offset; never changes the component or aim.
UCLASS(ClassGroup=(FPS), Config=Game, meta=(BlueprintSpawnableComponent))
class FPSGAME_API UWeaponActionCameraComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UWeaponActionCameraComponent();

    UPROPERTY(Config, EditAnywhere, Category="Weapon Camera", meta=(ClampMin="0.0", ClampMax="4.0"))
    float Strength = 2.8f;
    UPROPERTY(Config, EditAnywhere, Category="Weapon Camera", meta=(ClampMin="0.0", ClampMax="2.0"))
    float FollowStrength = 2.f;
    // The contact pulses (magazine out, insert, seat, bolt) are what read as
    // punch; they carry more weight than the smooth follow than before.
    UPROPERTY(Config, EditAnywhere, Category="Weapon Camera", meta=(ClampMin="0.0", ClampMax="4.0"))
    float ImpactStrength = 2.6f;

    UPROPERTY(Config, EditAnywhere, Category="Weapon Camera|Sprint", meta=(ClampMin="0.0", ClampMax="3.0"))
    float SprintStrength = 1.f;
    // Pitch, yaw, roll in degrees, before the character's camera motion scale.
    UPROPERTY(Config, EditAnywhere, Category="Weapon Camera|Sprint")
    FVector SprintAnglesDegrees = FVector(2.4f, .9f, 4.f);
    // Forward, right, up in centimetres.
    UPROPERTY(Config, EditAnywhere, Category="Weapon Camera|Sprint")
    FVector SprintTravelCM = FVector(.4f, 2.2f, 2.6f);

    void UpdateSprint(float DeltaSeconds, bool bEnabled, bool bRequested,
        float StridePhase, float MovementWeight);
    void ResetSprint();
    float SprintCameraWeight() const { return SprintBlend * FMath::Clamp(SprintStrength, 0.f, 1.f); }

    void Apply(UCameraComponent& Camera, EM4CameraAction Action, float SourceSeconds,
        float SourceDuration, TConstArrayView<float> ContactSeconds, float CameraMotionWeight) const;

private:
    float SprintBlend = 0.f;
    float SprintPhase = 0.f;
};
