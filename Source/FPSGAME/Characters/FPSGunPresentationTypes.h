#pragma once
#include "CoreMinimal.h"
#include "FPSGunPresentationTypes.generated.h"

UENUM()
enum class EFPSGunEvent : uint8 { Shot, Mechanical, StopMechanical, Cartridge };

/** Transient cosmetics only. Assets are checked against the server's equipped gun. */
USTRUCT()
struct FFPSGunEvent
{
    GENERATED_BODY()
    UPROPERTY() EFPSGunEvent Kind=EFPSGunEvent::Shot;
    UPROPERTY() uint8 Hand=0;
    UPROPERTY() FString Instance;
    UPROPERTY() uint32 Sequence=0;
    UPROPERTY() float SentAt=0.f;
    UPROPERTY() TSoftObjectPtr<class USoundBase> Sound;
    UPROPERTY() float Volume=1.f;
    UPROPERTY() float Pitch=1.f;
    UPROPERTY() float StartTime=0.f;
    UPROPERTY() bool bAiming=false;
    UPROPERTY() bool bSuppressed=false;
    // The accepted tube-shot RPC supplies this; observer pawns do not own the
    // shooter's evaluated gunsmith stats. Start time accounts for queue latency.
    UPROPERTY() float PumpRate=1.f;
    UPROPERTY() TSoftObjectPtr<class UStaticMesh> Cartridge;
    // Release frame and velocity relative to WPN_root, never the owner's camera.
    UPROPERTY() FTransform Release=FTransform::Identity;
    UPROPERTY() FVector ReleaseVelocity=FVector::ZeroVector;
};

USTRUCT()
struct FFPSRemoteGunHand
{
    GENERATED_BODY()
    UPROPERTY(Transient) TObjectPtr<class UFPSWeaponFXComponent> FX;
    UPROPERTY(Transient) TArray<TObjectPtr<class UAudioComponent>> MechanicalVoices;
    UPROPERTY(Transient) TObjectPtr<class USoundConcurrency> FireConcurrency;
    FString Instance;
};
