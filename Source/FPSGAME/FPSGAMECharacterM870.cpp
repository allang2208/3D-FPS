#include "FPSGAMECharacter.h"
#include "Weapons/M870WeaponAssets.h"
#include "Weapons/FPSWeaponFXComponent.h"
#include "UI/ColdSteelStatusModel.h"
#include "Multiplayer/ColdSteelPlayerState.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"

float AFPSGAMECharacter::M870PumpPlayRate() const
{
    return FMath::Max(1.f,M870WeaponAssets::FireDuration/float(FMath::Max(.01,EffectiveFireInterval())));
}

void AFPSGAMECharacter::PreserveInterruptedM870Pump()
{
    if(!IsM870Weapon()||!IsLocallyControlled()||!IsRevolverFireActionPlaying())return;
    const float SourceTime=float(GetWorld()->GetTimeSeconds()-LastShotWorldTime)*ActionPlayRate;
    if(SourceTime+1.e-6f>=M870WeaponAssets::PumpClosed)return;
    if(WeaponFX&&WeaponFX->PausePumpEjection())M870PendingCasingWeapons.Add(ActiveInventoryWeapon);
    // A weapon-slot transaction may already have selected the next gun. Save
    // the outgoing instance explicitly, without syncing its magazine into it.
    if(auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        Profile->MarkM870PumpInterrupted(ActiveInventoryWeapon);
    if(GetNetMode()==NM_Client)
        if(auto* PS=GetPlayerState<AColdSteelPlayerState>())
            PS->RequestM870PumpInterrupt(ActiveInventoryWeapon,M870ShotSequence);
}

void AFPSGAMECharacter::UpdateM870PumpAudio()
{
    if(!IsM870Weapon()||!IsLocallyControlled()||!ActiveActionAnimation
        ||(ActiveActionAnimation!=FireAnimation&&ActiveActionAnimation!=AimFireAnimation))return;
    const float Time=float(GetWorld()->GetTimeSeconds()-LastShotWorldTime)*ActionPlayRate;
    if(Time> M870WeaponAssets::FireDuration)return;
    if(!(M870PumpCueMask&1)&&Time>=M870WeaponAssets::PumpPull)
    {
        M870PumpCueMask|=1;
        if(Time<M870WeaponAssets::PumpPush)PlayMechanicalSound(ChargePullSound,.8f);
    }
    if(!(M870PumpCueMask&2)&&Time>=M870WeaponAssets::PumpPush)
    {
        M870PumpCueMask|=2;
        PlayMechanicalSound(ChargeReleaseSound,.8f);
    }
}
