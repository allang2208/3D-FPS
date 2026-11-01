#include "FPSGAMECharacter.h"
#include "Weapons/M24WeaponAssets.h"
#include "Weapons/FPSWeaponFXComponent.h"
#include "UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"

float AFPSGAMECharacter::M24CyclePlayRate() const
{
    return M24WeaponAssets::FireDuration/FMath::Max(.01f,float(EffectiveFireInterval()));
}

void AFPSGAMECharacter::PreserveInterruptedM24Cycle()
{
    if(!IsM24Weapon()||!IsLocallyControlled()||!IsRevolverFireActionPlaying())return;
    const float Time=float(GetWorld()->GetTimeSeconds()-LastShotWorldTime)*ActionPlayRate;
    if(Time>=M24WeaponAssets::BoltClosed)return;
    if(WeaponFX&&WeaponFX->PausePumpEjection())M24PendingCasingWeapons.Add(ActiveInventoryWeapon);
    if(auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        Profile->MarkM24CycleInterrupted(ActiveInventoryWeapon);
}

void AFPSGAMECharacter::UpdateM24CycleAudio()
{
    if(!IsM24Weapon()||!IsLocallyControlled())return;
    if(IsReloading()&&bPendingEmptyReload)
    {
        if(ReloadSourceTime(WeaponStateElapsed)>=M24WeaponAssets::ChargeEject
            &&M24PendingCasingWeapons.Remove(ActiveInventoryWeapon)>0&&WeaponFX)
            WeaponFX->EjectPumpCasing();
        return;
    }
    if(!ActiveActionAnimation||(ActiveActionAnimation!=FireAnimation&&ActiveActionAnimation!=AimFireAnimation))return;
    const float Time=float(GetWorld()->GetTimeSeconds()-LastShotWorldTime)*ActionPlayRate;
    if(Time>M24WeaponAssets::FireDuration)return;
    if(!(M24CycleCueMask&1)&&Time>=M24WeaponAssets::BoltPull)
    {M24CycleCueMask|=1;if(Time<M24WeaponAssets::BoltPush)PlayMechanicalSound(ChargePullSound,.8f);}
    if(!(M24CycleCueMask&2)&&Time>=M24WeaponAssets::BoltClosed)
    {M24CycleCueMask|=2;PlayMechanicalSound(ChargeReleaseSound,.8f);}
}
