#include "FPSGAMECharacter.h"
#include "Weapons/M24WeaponAssets.h"
#include "Weapons/M24ReloadTiming.h"
#include "Weapons/WeaponReloadStages.h"
#include "Weapons/FPSWeaponFXComponent.h"
#include "UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"

float AFPSGAMECharacter::M24CyclePlayRate() const
{
    return M24WeaponAssets::FireDuration/FMath::Max(.01f,float(EffectiveFireInterval()));
}

void AFPSGAMECharacter::PreserveInterruptedM24Cycle()
{
    AdvanceM24EquipBolt();
    if(!IsM24Weapon()||!IsLocallyControlled()||!IsRevolverFireActionPlaying())return;
    const float Time=float(GetWorld()->GetTimeSeconds()-LastShotWorldTime)*ActionPlayRate;
    // Fire reaches its locked handle pose on frame 39. Its release sound
    // follows on frame 40; a switch in between must not request another cycle.
    if(Time>=39.f/30.f)return;
    const bool Queued=WeaponFX&&WeaponFX->PausePumpEjection();
    bM24PendingCasing=Queued||Time<M24WeaponAssets::BoltEject;
    if(auto* Profile=NetShadowProfile?NetShadowProfile.Get():GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        Profile->MarkM24CycleInterrupted(ActiveInventoryWeapon,true,bM24PendingCasing);
}

void AFPSGAMECharacter::EjectInterruptedM24Casing()
{
    if(!bM24PendingCasing||!IsLocallyControlled())return;
    bM24PendingCasing=false;
    if(auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        if(const auto* Gun=Profile->FindItem(ActiveInventoryWeapon);Gun&&WeaponReloadStages::NeedsM24ShotCycle(*Gun))
            Profile->MarkM24CycleInterrupted(ActiveInventoryWeapon,true,false);
    if(WeaponFX)WeaponFX->EjectPumpCasing();
}

void AFPSGAMECharacter::AdvanceM24EquipBolt()
{
    if(!bM24EquipBoltPending||!IsM24Weapon()||WeaponState!=EAKMWeaponState::Equipping)return;
    // The shadow can receive a coalesced equip update several frames later.
    // Its independent draw clock is cosmetic, not a second owner of this flag.
    if(!IsLocallyControlled())return;
    const float SourceTime=M24EquipSourceTime(float(GetWorld()->GetTimeSeconds()-WeaponActionStartedAt));
    if(SourceTime>=M24WeaponAssets::EquipBoltEject)EjectInterruptedM24Casing();
    if(SourceTime<M24WeaponAssets::EquipBoltClosed)return;
    bM24EquipBoltPending=false;
    if(auto* Profile=NetShadowProfile?NetShadowProfile.Get():GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        Profile->MarkM24CycleInterrupted(ActiveInventoryWeapon,false);
}

float AFPSGAMECharacter::M24EquipSourceTime(float RuntimeSeconds) const
{
    if(!EquipAnimation||WeaponStateDuration<=0.f)return 0.f;
    const float Phase=FMath::Clamp(RuntimeSeconds/WeaponStateDuration,0.f,1.f);
    const float Time=Phase*M24ReloadTiming::EquipPacedTime(EquipAnimation->GetPlayLength(),M24ActionBoltDurationScale);
    return M24ReloadTiming::UnpaceBoltTime(Time,M24WeaponAssets::BoltLift+3.f/30.f,M24WeaponAssets::EquipBoltClosed,M24ActionBoltDurationScale);
}

void AFPSGAMECharacter::UpdateM24CycleAudio()
{
    if(!IsM24Weapon()||!IsLocallyControlled())return;
    if(IsReloading()&&bPendingEmptyReload)
    {
        if(ReloadSourceTime(WeaponStateElapsed)>=M24WeaponAssets::ChargeEject)EjectInterruptedM24Casing();
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
