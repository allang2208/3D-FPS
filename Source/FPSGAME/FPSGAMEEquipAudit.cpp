#include "FPSGAMECharacter.h"
#include "UI/ColdSteelStatusModel.h"
#include "Weapons/FPSGunplayAnimInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Sound/SoundBase.h"
#include "AudioMixerBlueprintLibrary.h"
#include "GameFramework/PlayerController.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "HighResScreenshot.h"
#include "InputKeyEventArgs.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"

// Opt-in isolated profile. Switching goes through the real G input / inventory
// publication route; only the two equipped weapons and ammunition are fixtures.
void AFPSGAMECharacter::RunEquipFramingAcceptance(float DeltaSeconds)
{
    // This mode replaces the ordinary gunplay audit, so reuse its per-pawn
    // measurement storage without adding fields to the shared character layout.
    float& MaxEquipFraming = AuditMaxMechanicalLateness;
    float& MaxEquipHipOffsetCM = AuditMaxRigidBoneDriftCM;
    int32& EquipPoseSamples = AuditRigidPoseSamples;
    GunplayAuditElapsed += DeltaSeconds;
    if (GunplayAuditDirectory.IsEmpty())
    {
        MaxEquipFraming = MaxEquipHipOffsetCM = 0.0f;
        EquipPoseSamples = 0;
        FString Label;
        FParse::Value(FCommandLine::Get(), TEXT("GunplayLabel="), Label);
        GunplayAuditDirectory = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("GunplayUpgrade") / Label);
        IFileManager::Get().MakeDirectory(*(GunplayAuditDirectory / TEXT("Frames")), true);
        if (FParse::Param(FCommandLine::Get(), TEXT("GunplayCaptureAudio")))
            UAudioMixerBlueprintLibrary::StartRecordingOutput(this, 10.0f);
    }
    const auto Record = [&](const FString& Line)
    {
        UE_LOG(LogTemp, Display, TEXT("%s"), *Line);
        FFileHelper::SaveStringToFile(Line + TEXT("\n"), *(GunplayAuditDirectory / TEXT("assertions.log")),
            FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append);
    };
    const auto Verify = [&](const TCHAR* Name, bool Pass)
    {
        if (!Pass) ++GunplayAuditFailures;
        Record(FString::Printf(TEXT("GUNPLAY_ASSERT %s %s t=%.4f state=%d frame=%.6f ads=%.6f hip=%s actual=%s"),
            Pass ? TEXT("PASS") : TEXT("FAIL"), Name, GunplayAuditElapsed, int32(WeaponState), M4ActionFramingAlpha,
            WeaponADSFactor, *HipViewmodelLocation.ToCompactString(), *AKMViewmodel->GetRelativeLocation().ToCompactString()));
    };
    auto* PC = Cast<APlayerController>(Controller);
    auto* Profile = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if (!PC || !Profile) return;
    const auto Key = [&](const FKey& K, EInputEvent Event)
    {
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(K, Event, Event == IE_Released ? 0.0f : 1.0f));
    };
    const auto Switch = [&]()
    {
        const FString Previous = ActiveInventoryWeapon;
        Key(EKeys::G, IE_Pressed); Key(EKeys::G, IE_Released);
        Verify(TEXT("switch_uses_inventory_instance"), ActiveInventoryWeapon != Previous && WeaponState == EAKMWeaponState::Equipping);
        Verify(TEXT("switch_starts_at_own_hip"), M4ActionFramingAlpha == 0.0f && WeaponADSFactor == 0.0f
            && SprintPoseFactor == 0.0f && AKMViewmodel->GetRelativeLocation().Equals(HipViewmodelLocation, 0.001f));
        bool Stopped = MechanicalCueTimes.IsEmpty() && MechanicalCueSounds.IsEmpty() && NextMechanicalCue == 0;
        for (const auto& Pair : MechanicalVoices)
            if (Pair.Key != EquipSound->GetFName() && Pair.Value && Pair.Value->IsPlaying()) Stopped = false;
        Verify(TEXT("switch_stops_previous_action_audio_and_queue"), Stopped);
    };
    if (WeaponState == EAKMWeaponState::Equipping)
    {
        ++EquipPoseSamples;
        MaxEquipFraming = FMath::Max(MaxEquipFraming, FMath::Abs(M4ActionFramingAlpha));
        const FVector Offset = AKMViewmodel->GetRelativeLocation() - HipViewmodelLocation;
        MaxEquipHipOffsetCM = FMath::Max(MaxEquipHipOffsetCM, FVector2D(Offset.X, Offset.Y).Size());
    }
    const FString Sample = FString::Printf(TEXT("%.6f,%d,%d,%.6f,%.6f,%.6f,%.6f,%.6f\n"),
        GunplayAuditElapsed, GunplayAuditStage, int32(WeaponState), M4ActionFramingAlpha, WeaponADSFactor,
        AKMViewmodel->GetRelativeLocation().X, AKMViewmodel->GetRelativeLocation().Y, AKMViewmodel->GetRelativeLocation().Z);
    FFileHelper::SaveStringToFile(Sample, *(GunplayAuditDirectory / TEXT("equip_samples.csv")),
        FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append);
    switch (GunplayAuditStage)
    {
    case 0:
        if (GunplayAuditElapsed < 1.6f) break;
        Verify(TEXT("initial_equip_returns_directly_to_idle"), WeaponState == EAKMWeaponState::Idle && !ActiveActionAnimation);
        {
            auto State = Profile->Snapshot(); State.Items.Reset(); State.ActiveWeaponSlot = 6;
            State.Hotbar.Init(TEXT(""),4); State.HotbarDefinitions.Init(TEXT(""),4);
            for (int32 Slot : {6,9}) { auto Gun=Profile->CreateItem(TEXT("ue_m4a1")); Gun.Place=1; Gun.Cell=Slot; Gun.Magazine=15; State.Items.Add(Gun); }
            auto Ammo=Profile->CreateItem(TEXT("ammo_556"),90); Ammo.Place=0; Ammo.Cell=0; State.Items.Add(Ammo);
            Verify(TEXT("inventory_equip_fixture"), Profile->CommitState(State) && WeaponState == EAKMWeaponState::Equipping);
            Verify(TEXT("m4_equip_uses_slower_duration"), FMath::IsNearlyEqual(WeaponStateDuration, 0.72f, 0.001f));
        }
        ++GunplayAuditStage; break;
    case 1:
        if (GunplayAuditElapsed < 3.0f) break;
        Verify(TEXT("inventory_equip_returns_to_idle"), WeaponState == EAKMWeaponState::Idle && !ActiveActionAnimation);
        Key(EKeys::RightMouseButton, IE_Pressed);
        ++GunplayAuditStage; break;
    case 2:
        if (GunplayAuditElapsed < 3.5f) break;
        Verify(TEXT("ads_before_switch"), WeaponADSFactor > 0.98f);
        Switch(); ++GunplayAuditStage; break;
    case 3:
        if (GunplayAuditElapsed < 5.0f) break;
        Verify(TEXT("ads_switch_finishes_in_hip_idle"), WeaponState == EAKMWeaponState::Idle && WeaponADSFactor == 0.0f && !ActiveActionAnimation);
        Key(EKeys::R, IE_Pressed); Key(EKeys::R, IE_Released);
        ++GunplayAuditStage; break;
    case 4:
        if (GunplayAuditElapsed < 5.6f) break;
        Verify(TEXT("reload_contact_voice_created_before_interrupt"), MagOutSound && MechanicalVoices.Contains(MagOutSound->GetFName()));
        Verify(TEXT("reload_still_uses_action_framing"), IsReloading() && M4ActionFramingAlpha > 0.9f);
        Switch(); ++GunplayAuditStage; break;
    case 5:
        if (GunplayAuditElapsed < 5.85f) break;
        Verify(TEXT("rapid_switch_interrupts_equip"), WeaponState == EAKMWeaponState::Equipping);
        Switch(); ++GunplayAuditStage; break;
    case 6:
        if (GunplayAuditElapsed < 7.2f) break;
        Verify(TEXT("switch_chain_finishes_in_idle"), WeaponState == EAKMWeaponState::Idle && !ActiveActionAnimation
            && GunplayAnimation && GunplayAnimation->ActionAlpha == 0.0f && WeaponADSFactor == 0.0f);
        Verify(TEXT("equip_never_visits_center_frame"), EquipPoseSamples > 20 && MaxEquipFraming < 0.0001f && MaxEquipHipOffsetCM < 0.5f);
        Verify(TEXT("equip_does_not_change_ammo"), MagazineAmmo == 15 && ReserveAmmo == 90);
        if (FParse::Param(FCommandLine::Get(), TEXT("GunplayCaptureAudio")))
            UAudioMixerBlueprintLibrary::StopRecordingOutput(this, EAudioRecordingExportType::WavFile, TEXT("GunplayAudio"), GunplayAuditDirectory, nullptr);
        Record(FString::Printf(TEXT("EQUIP_FRAMING_MEASURE samples=%d max_alpha=%.6f max_xy_drift_cm=%.6f"), EquipPoseSamples, MaxEquipFraming, MaxEquipHipOffsetCM));
        Record(FString::Printf(TEXT("GUNPLAY_ACCEPTANCE_COMPLETE failures=%d elapsed=%.3f"), GunplayAuditFailures, GunplayAuditElapsed));
        bRunGunplayAcceptance = false;
        FPlatformMisc::RequestExitWithStatus(false, GunplayAuditFailures ? 1 : 0);
        return;
    }
    if (FParse::Param(FCommandLine::Get(), TEXT("GunplayCaptureFrames")))
    {
        int32 CaptureHz = 10;
        FParse::Value(FCommandLine::Get(), TEXT("GunplayCaptureHz="), CaptureHz);
        CaptureHz = FMath::Clamp(CaptureHz, 10, 60);
        const int32 Frame = FMath::FloorToInt(GunplayAuditElapsed * CaptureHz);
        if (Frame != FMath::FloorToInt((GunplayAuditElapsed-DeltaSeconds)*CaptureHz))
            FScreenshotRequest::RequestScreenshot(GunplayAuditDirectory / TEXT("Frames") / FString::Printf(TEXT("Frame_%04d.png"),Frame), false, false);
    }
}
