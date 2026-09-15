#include "FPSGAMECharacter.h"
#include "UI/ColdSteelStatusModel.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "HighResScreenshot.h"
#include "InputKeyEventArgs.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"

// Opt-in, isolated single-player test. Locomotion and weapon state changes use
// real controller inputs; the magazine is the only gameplay fixture.
void AFPSGAMECharacter::RunSlideCombatAcceptance(float DeltaSeconds)
{
    GunplayAuditElapsed += DeltaSeconds;
    if (GunplayAuditDirectory.IsEmpty())
    {
        FString Label = TEXT("slide-combat");
        FParse::Value(FCommandLine::Get(), TEXT("GunplayLabel="), Label);
        GunplayAuditDirectory = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("GunplayUpgrade") / FPaths::MakeValidFileName(Label));
        IFileManager::Get().MakeDirectory(*GunplayAuditDirectory, true);
    }
    const auto Record = [&](const FString& Line)
    {
        UE_LOG(LogTemp, Display, TEXT("%s"), *Line);
        FFileHelper::SaveStringToFile(Line + TEXT("\n"), *(GunplayAuditDirectory / TEXT("assertions.log")),
            FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append);
    };
    const auto Check = [&](const TCHAR* Name, bool Pass)
    {
        if (!Pass) ++GunplayAuditFailures;
        Record(FString::Printf(TEXT("GUNPLAY_ASSERT %s %s t=%.3f slide=%d aim=%d ads=%.3f reload=%d shots=%d ammo=%d speed=%.1f"),
            Pass ? TEXT("PASS") : TEXT("FAIL"), Name, GunplayAuditElapsed, bIsSliding, bIsAiming, WeaponADSFactor, IsReloading(), ShotsFired, MagazineAmmo, HorizontalSpeed()));
    };
    auto* PC = Cast<APlayerController>(Controller);
    auto* Profile = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if (!PC || !Profile || !Profile->IsAudit())
    {
        if (GunplayAuditElapsed < 3.f) return;
        Check(TEXT("isolated_controller_fixture"), false);
        FPlatformMisc::RequestExitWithStatus(false, 1);
        return;
    }
    const auto Key = [&](FKey Input, EInputEvent Event)
    {
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(Input, Event, Event == IE_Released ? 0.f : 1.f));
    };
    const auto Capture = [&](const TCHAR* Name)
    {
        if (FParse::Param(FCommandLine::Get(), TEXT("GunplayCaptureFrames")))
            FScreenshotRequest::RequestScreenshot(GunplayAuditDirectory / Name, false, false);
    };
    const auto Advance = [&]() { AuditSavedActionTime = GunplayAuditElapsed; ++GunplayAuditStage; };
    const float Age = GunplayAuditElapsed - AuditSavedActionTime;
    switch (GunplayAuditStage)
    {
    case 0:
        if (GunplayAuditElapsed < 1.5f) break;
        Check(TEXT("weapon_ready"), bInventoryWeaponReady && !IsWeaponBusy());
        Key(EKeys::W, IE_Pressed); Key(EKeys::LeftShift, IE_Pressed); Advance(); break;
    case 1:
        if (Age < .8f) break;
        Check(TEXT("sprint_reaches_slide_speed"), bIsSprinting && HorizontalSpeed() >= SlideMinimumSpeed);
        Key(EKeys::LeftControl, IE_Pressed); Advance(); break;
    case 2:
        if (Age < .12f) break;
        Check(TEXT("slide_entered"), bIsSliding && !bIsSprinting);
        Key(EKeys::LeftControl, IE_Released); Key(EKeys::LeftShift, IE_Released);
        AuditSavedShots = ShotsFired;
        Key(EKeys::LeftMouseButton, IE_Pressed); Advance(); break;
    case 3:
        if (Age < .2f) break;
        Check(TEXT("slide_hip_fire"), bIsSliding && !bIsAiming && ShotsFired > AuditSavedShots);
        Capture(TEXT("01_Slide_HipFire.png"));
        AuditSavedShots = ShotsFired;
        Key(EKeys::RightMouseButton, IE_Pressed); Advance(); break;
    case 4:
        if (Age < .3f) break;
        Check(TEXT("slide_ads_fire"), bIsSliding && bIsAiming && WeaponADSFactor > .95f && ShotsFired > AuditSavedShots);
        Capture(TEXT("02_Slide_ADSFire.png"));
        Key(EKeys::LeftMouseButton, IE_Released); Key(EKeys::R, IE_Pressed); Advance(); break;
    case 5:
        if (Age < .1f) break;
        Check(TEXT("reload_started_during_slide"), bIsSliding && IsReloading() && !bIsAiming);
        AuditSavedShots = ShotsFired; AuditSavedAmmo = MagazineAmmo;
        Capture(TEXT("03_Slide_Reload.png"));
        Key(EKeys::R, IE_Released); Key(EKeys::LeftMouseButton, IE_Pressed); Advance(); break;
    case 6:
        if (Age < .2f) break;
        Check(TEXT("reload_blocks_held_fire_and_ads"), IsReloading() && !bIsAiming && ShotsFired == AuditSavedShots && MagazineAmmo == AuditSavedAmmo);
        Key(EKeys::LeftMouseButton, IE_Released); Key(EKeys::W, IE_Released); Advance(); break;
    case 7:
        if (Age < ReloadDuration + .25f) break;
        Check(TEXT("reload_settles_once_and_held_ads_recovers"), !IsReloading() && bIsAiming && WeaponADSFactor > .95f && MagazineAmmo == MagazineCapacity && ShotsFired == AuditSavedShots);
        Key(EKeys::RightMouseButton, IE_Released); Key(EKeys::LeftShift, IE_Pressed); Key(EKeys::W, IE_Pressed); Advance(); break;
    case 8:
        if (Age < .9f) break;
        // Start a reload first, then enter slide while the same clip is running.
        {
            auto State = Profile->Snapshot();
            for (auto& Item : State.Items) if (Item.Place == 1 && Item.Cell == State.ActiveWeaponSlot) Item.Magazine = 12;
            Check(TEXT("partial_magazine_fixture"), Profile->CommitState(State));
        }
        Key(EKeys::R, IE_Pressed); Advance(); break;
    case 9:
        if (Age < .1f) break;
        Check(TEXT("reload_before_slide"), IsReloading() && bIsSprinting);
        Key(EKeys::R, IE_Released); Key(EKeys::LeftControl, IE_Pressed); Advance(); break;
    case 10:
        if (Age < .2f) break;
        Check(TEXT("slide_preserves_active_reload_clock"), bIsSliding && IsReloading() && WeaponStateElapsed >= .25f);
        Key(EKeys::LeftControl, IE_Released); Key(EKeys::LeftShift, IE_Released); Key(EKeys::W, IE_Released);
        Key(EKeys::RightMouseButton, IE_Pressed); Advance(); break;
    case 11:
        if (Age < .3f) break;
        Key(EKeys::SpaceBar, IE_Pressed); Advance(); break;
    case 12:
        if (Age < .12f) break;
        Check(TEXT("slide_jump_preserves_reload"), !bIsSliding && !GetCharacterMovement()->IsMovingOnGround() && IsReloading());
        Key(EKeys::SpaceBar, IE_Released); Advance(); break;
    case 13:
        if (Age < ReloadDuration + .2f) break;
        Check(TEXT("slide_jump_reload_recovers_ads"), !IsReloading() && bIsAiming && MagazineAmmo == MagazineCapacity);
        Check(TEXT("camera_and_mesh_finite"), !FirstPersonCamera->GetComponentTransform().ContainsNaN() && !AKMViewmodel->GetComponentTransform().ContainsNaN());
        Key(EKeys::RightMouseButton, IE_Released);
        Capture(TEXT("04_Recovered.png")); Advance(); break;
    case 14:
        if (Age < .3f) break;
        Record(FString::Printf(TEXT("GUNPLAY_ACCEPTANCE_COMPLETE failures=%d"), GunplayAuditFailures));
        bRunSlideCombatAudit = false; bRunGunplayAcceptance = false;
        FPlatformMisc::RequestExitWithStatus(false, GunplayAuditFailures ? 1 : 0); break;
    }
}
