#include "../FPSGAMECharacter.h"
#include "AudioMixerBlueprintLibrary.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "TimerManager.h"
#include "Misc/App.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"

// Explicit opt-in: record the old levels and the actual current M4 playback paths.
// Return before profile attachment so this comparison never changes player equipment/save.
void AFPSGAMECharacter::RunWeaponVolumeAudit()
{
    FApp::SetUnfocusedVolumeMultiplier(1.f);
    bUseM4Infima = true; bUseQBZ191 = false; bUseM1911 = false; bUseDanWesson715 = false;
    InitializeWeaponVisuals();
    SetActorTickEnabled(false);
    bInventoryWeaponReady = true;
    const FString Directory = FPaths::ProjectSavedDir() / TEXT("WeaponVolumeAudit");
    IFileManager::Get().MakeDirectory(*Directory, true);
    if (RifleFireVariants.IsEmpty() || !ChargePullSound)
    {
        UE_LOG(LogTemp, Error, TEXT("WEAPON_VOLUME_AUDIT: missing M4 audio"));
        FPlatformMisc::RequestExit(false);
        return;
    }
    RifleFireVariants.SetNum(1);
    UE_LOG(LogTemp, Display, TEXT("WEAPON_VOLUME_AUDIT: fire=%s pull=%s"),
        *RifleFireVariants[0]->GetPathName(), *ChargePullSound->GetPathName());
    for (int32 Index = 0; Index < 4; ++Index)
    {
        FTimerHandle StartHandle;
        GetWorldTimerManager().SetTimer(StartHandle, FTimerDelegate::CreateWeakLambda(this, [this, Index]()
        {
            UAudioMixerBlueprintLibrary::StartRecordingOutput(this, 2.f);
            if (Index == 0) PlaySound2D(RifleFireVariants[0], .562341f);
            if (Index == 1)
            {
                WeaponState = EAKMWeaponState::Idle;
                bIsSprinting = false; SprintFireUnlockTime = 0.; NextAllowedShotTime = 0.;
                MagazineAmmo = 10;
                FireShot();
            }
            if (Index == 2) PlaySound2D(ChargePullSound, .630957f);
            if (Index == 3) PlayMechanicalSound(ChargePullSound, .630957f);
            UE_LOG(LogTemp, Display, TEXT("WEAPON_VOLUME_AUDIT: start=%d shots=%d"), Index, ShotsFired);
        }), 3.f + Index * 3.f, false);
        FTimerHandle StopHandle;
        GetWorldTimerManager().SetTimer(StopHandle, FTimerDelegate::CreateWeakLambda(this, [this, Index, Directory]()
        {
            const TCHAR* Names[] = {TEXT("m4_fire_before"), TEXT("m4_fire_current"), TEXT("m4_pull_before"), TEXT("m4_pull_current")};
            UAudioMixerBlueprintLibrary::StopRecordingOutput(this, EAudioRecordingExportType::WavFile, Names[Index], Directory + TEXT("/"));
        }), 5.f + Index * 3.f, false);
    }
    FTimerHandle ExitHandle;
    GetWorldTimerManager().SetTimer(ExitHandle, []()
    {
        UE_LOG(LogTemp, Display, TEXT("WEAPON_VOLUME_AUDIT: complete"));
        FPlatformMisc::RequestExit(false);
    }, 17.f, false);
}
