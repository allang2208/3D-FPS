#include "FPSGAMECharacter.h"
#include "UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HAL/PlatformMisc.h"

void AFPSGAMECharacter::RunInfiniteAmmoAudit()
{
    FString ProfileName;
    if (!FParse::Value(FCommandLine::Get(), TEXT("ColdSteelProfile="), ProfileName) || !ProfileName.StartsWith(TEXT("InfiniteAmmoAudit_")))
    {
        UE_LOG(LogTemp, Error, TEXT("InfiniteAmmoAudit: FAIL requires isolated profile"));
        FGenericPlatformMisc::RequestExit(false);
        return;
    }
    auto* Profile = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if (!Profile || IsWeaponBusy() || GetWorld()->GetTimeSeconds() < 5.0) return;
    auto Check = [](bool OK, const TCHAR* Case)
    {
        UE_LOG(LogTemp, Display, TEXT("InfiniteAmmoAudit: %s %s"), OK ? TEXT("PASS") : TEXT("FAIL"), Case);
    };
    if (InfiniteAmmoAuditStage == 0)
    {
        Check(HasInfiniteReserveAmmo() && bInventoryWeaponReady, TEXT("scene enabled and weapon equipped"));
        InfiniteAmmoAuditReserve = Profile->AmmoCount();
        MagazineAmmo = 0;
        ReserveAmmo = 0;
        // The next regular Tick must initiate an empty reload without input.
        InfiniteAmmoAuditStage = 1;
    }
    else if (InfiniteAmmoAuditStage == 1)
    {
        Check(MagazineAmmo == MagazineCapacity, TEXT("automatic empty reload completed with zero reserve"));
        Check(Profile->AmmoCount() == InfiniteAmmoAuditReserve, TEXT("backpack ammo preserved"));
        MagazineAmmo = MagazineCapacity - 3;
        ReserveAmmo = 0;
        ReloadPressed();
        Check(IsReloading(), TEXT("manual partial reload accepted with zero reserve"));
        InfiniteAmmoAuditStage = 2;
    }
    else if (InfiniteAmmoAuditStage == 2)
    {
        Check(MagazineAmmo == MagazineCapacity && Profile->AmmoCount() == InfiniteAmmoAuditReserve, TEXT("partial refill and inventory preserved"));
        Check(Profile->Equipped() && Profile->Equipped()->Magazine == MagazineCapacity, TEXT("filled magazine synchronized to profile"));
        UE_LOG(LogTemp, Display, TEXT("InfiniteAmmoAudit: COMPLETE"));
        InfiniteAmmoAuditStage = 3;
        FGenericPlatformMisc::RequestExit(false);
    }
}
