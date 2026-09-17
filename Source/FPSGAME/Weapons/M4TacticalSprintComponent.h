#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "M4TacticalSprintComponent.generated.h"

class UAnimSequence;
class UFPSGunplayAnimInstance;

enum class EM4SprintGrip : uint8 { Base, Drum, Angled, Vertical, Canted, Prism };
enum class ERifleSprintWeapon : uint8 { None, M4, AKM, QBZ191 };

// Presentation only: the character retains ownership of speed and fire timing.
UCLASS()
class FPSGAME_API UM4TacticalSprintComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UM4TacticalSprintComponent();
    void Configure(ERifleSprintWeapon Weapon);
    void Reset();
    void Advance(float DeltaSeconds, bool bWeaponReady, bool bSprintRequested,
        EM4SprintGrip Grip, float StridePhase, float GroundWeight, bool bWeaponActionExit = false);
    void Apply(UFPSGunplayAnimInstance& Animation) const;
    bool OwnsPose() const;
    float PoseProgress() const { return Progress; }

private:
    UPROPERTY(Transient) TArray<TObjectPtr<UAnimSequence>> Clips;
    UAnimSequence* Clip(int32 Kind) const;
    EM4SprintGrip CurrentGrip = EM4SprintGrip::Base;
    ERifleSprintWeapon CurrentWeapon = ERifleSprintWeapon::None;
    bool bEnabled = false;
    bool bEntering = false;
    float Progress = 0.f;
    float Phase = 0.f;
    float StrideWeight = 0.f;
};
