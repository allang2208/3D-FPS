#include "UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "FPSGAMECharacter.h"

#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "HAL/PlatformTime.h"
#include "HAL/PlatformProcess.h"
#include "HighResScreenshot.h"
#include "InputCoreTypes.h"
#include "InputKeyEventArgs.h"
#include "Misc/CommandLine.h"
#include "Misc/App.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Weapons/FPSWeaponFXComponent.h"
#include "AudioMixerBlueprintLibrary.h"
#include "Animation/AnimSequence.h"
#include "Sound/SoundBase.h"

// This audit is opt-in in a separate game process. Inputs pass through the real
// PlayerController/PlayerInput route; only ammunition and the temporary query wall
// are fixtures. Movement, action clocks, animation, aim and recoil are never forced.
void AFPSGAMECharacter::RunGunplayAcceptance(float DeltaSeconds)
{
    if (FParse::Param(FCommandLine::Get(), TEXT("EquipFramingAudit")))
    {
        RunEquipFramingAcceptance(DeltaSeconds);
        return;
    }
    GunplayAuditElapsed += DeltaSeconds;
    GunplayAuditMaxDelta = FMath::Max(GunplayAuditMaxDelta, DeltaSeconds);
    ++GunplayAuditTicks;
    APlayerController* PC = Cast<APlayerController>(Controller);
    // Exercise the authoritative backpack owner, not the former cached reserve counter.
    auto SetAuditAmmo = [this](int32 Magazine, int32 Reserve)
    {
        auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        if (!Profile || !Profile->IsAudit())
        {
            UE_LOG(LogTemp, Error, TEXT("GUNPLAY_FIXTURE_UNAVAILABLE profile=%s audit=%d"), *GetNameSafe(Profile), Profile && Profile->IsAudit());
            return;
        }
        auto State=Profile->Snapshot();const FString Definition=Profile->AmmoDefinition();
        State.Items.RemoveAll([&](const auto& Item){return Item.Place==0&&Item.Definition==Definition;});
        if(Reserve>0)ColdSteelInventory::Insert(State.Items,Profile->CreateItem(Definition,Reserve));
        for(auto& Item:State.Items)if(Item.Place==1&&Item.Cell==State.ActiveWeaponSlot)Item.Magazine=Magazine;
        if (!Profile->CommitState(State))
        {
            UE_LOG(LogTemp, Error, TEXT("GUNPLAY_FIXTURE_REJECTED %s"), *Profile->ResultMessage());
        }
        else
        {
            UE_LOG(LogTemp, Display, TEXT("GUNPLAY_FIXTURE_COMMITTED requested=%d/%d actual=%d/%d slot=%d"), Magazine, Reserve, MagazineAmmo, ReserveAmmo, State.ActiveWeaponSlot);
        }
    };

    if (GunplayAuditDirectory.IsEmpty())
    {
        GunplayAuditWallStarted = FPlatformTime::Seconds();
        GunplayAuditWorldStarted = GetWorld()->GetTimeSeconds();
        FString Label = TEXT("default");
        FParse::Value(FCommandLine::Get(), TEXT("GunplayLabel="), Label);
        Label = FPaths::MakeValidFileName(Label);
        if (Label.IsEmpty()) Label = TEXT("default");
        GunplayAuditDirectory = FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("GunplayUpgrade"), Label));
        IFileManager::Get().MakeDirectory(*GunplayAuditDirectory, true);
        if (FParse::Param(FCommandLine::Get(), TEXT("GunplayCaptureFrames")))
            IFileManager::Get().MakeDirectory(*FPaths::Combine(GunplayAuditDirectory, TEXT("Frames")), true);
        FFileHelper::SaveStringToFile(TEXT("Gunplay acceptance: simulated controller inputs; ammunition and query-wall fixtures only.\n"),
            *FPaths::Combine(GunplayAuditDirectory, TEXT("assertions.log")));
        if (FParse::Param(FCommandLine::Get(), TEXT("GunplayCaptureAudio")))
            UAudioMixerBlueprintLibrary::StartRecordingOutput(this, 32.0f);
    }
    const auto Record = [&](const FString& Line)
    {
        UE_LOG(LogTemp, Display, TEXT("%s"), *Line);
        FFileHelper::SaveStringToFile(Line + TEXT("\n"), *FPaths::Combine(GunplayAuditDirectory, TEXT("assertions.log")),
            FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append);
    };
    const auto Verify = [&](const TCHAR* Name, bool bPassed, const FString& Detail)
    {
        if (!bPassed) ++GunplayAuditFailures;
        Record(FString::Printf(TEXT("GUNPLAY_ASSERT %s %s t=%.3f %s"), bPassed ? TEXT("PASS") : TEXT("FAIL"), Name, GunplayAuditElapsed, *Detail));
    };
    const auto Key = [&](const FKey& InputKey, EInputEvent Event)
    {
        if (PC) PC->InputKey(FInputKeyEventArgs::CreateSimulated(InputKey, Event, Event == IE_Released ? 0.0f : 1.0f));
        Record(FString::Printf(TEXT("GUNPLAY_INPUT key=%s event=%s t=%.3f"), *InputKey.ToString(), Event == IE_Released ? TEXT("release") : TEXT("press"), GunplayAuditElapsed));
    };
    const auto Capture = [&](const TCHAR* Name)
    {
        FScreenshotRequest::RequestScreenshot(FPaths::Combine(GunplayAuditDirectory, Name), false, false);
        Record(FString::Printf(TEXT("GUNPLAY_CAPTURE %s stage=%d ads=%.4f camera_ads=%.4f ammo=%d reserve=%d shots=%d speed=%.2f reload=%d sprint=%d slide=%d"),
            Name, GunplayAuditStage, WeaponADSFactor, CameraADSFactor, MagazineAmmo, ReserveAmmo, ShotsFired, HorizontalSpeed(), IsReloading(), bIsSprinting, bIsSliding));
    };
    const auto ReleaseMovement = [&]()
    {
        Key(EKeys::W, IE_Released);
        Key(EKeys::LeftShift, IE_Released);
        Key(EKeys::LeftControl, IE_Released);
        Key(EKeys::SpaceBar, IE_Released);
    };
    if (!PC)
    {
        if (GunplayAuditElapsed < 3.0f) return;
        Verify(TEXT("controller_available"), false, TEXT("No PlayerController after 3 seconds"));
        Record(FString::Printf(TEXT("GUNPLAY_ACCEPTANCE_COMPLETE failures=%d"), GunplayAuditFailures));
        bRunGunplayAcceptance = false;
        FPlatformMisc::RequestExitWithStatus(false, 1);
        return;
    }

    // Read the evaluated mesh pose, so this covers compression, blending and action transitions.
    // The trigger rotates about its fixed hinge; the sights must remain rigid on the receiver.
    if (bUsingM4Infima && AKMViewmodel && AKMViewmodel->DoesSocketExist(TEXT("WPN_root")))
    {
        const FTransform Receiver = AKMViewmodel->GetSocketTransform(TEXT("WPN_root"), RTS_Component);
        for (const FName Bone : {FName(TEXT("WPN_Trigger")), FName(TEXT("WPN_RearSight")), FName(TEXT("WPN_FrontSight"))})
        {
            const FVector Offset = Receiver.InverseTransformPosition(AKMViewmodel->GetSocketTransform(Bone, RTS_Component).GetLocation());
            if (const FVector* Baseline = AuditRigidBoneOffsets.Find(Bone))
            {
                const float DriftCM = Receiver.TransformVector(Offset - *Baseline).Size();
                AuditMaxRigidBoneDriftCM = FMath::Max(AuditMaxRigidBoneDriftCM, DriftCM);
            }
            else AuditRigidBoneOffsets.Add(Bone, Offset);
        }
        ++AuditRigidPoseSamples;
        const FVector BoltOffset = Receiver.InverseTransformPosition(AKMViewmodel->GetSocketTransform(TEXT("WPN_bolt"), RTS_Component).GetLocation());
        // Measure within the empty clip: the held animation has its own 0.25 cm
        // bolt offset, which must not be counted as the release stroke.
        if (IsReloading() && bPendingEmptyReload)
        {
            const float SourceTime = ReloadSourceTime(WeaponStateElapsed);
            if (SourceTime > 0.5f && SourceTime < 2.1f)
                AuditRigidBoneOffsets.Add(TEXT("EmptyBoltOpen"), BoltOffset);
            else if (SourceTime >= 2.3f)
                if (const FVector* OpenBolt = AuditRigidBoneOffsets.Find(TEXT("EmptyBoltOpen")))
                    AuditMaxEmptyBoltTravelCM = FMath::Max(AuditMaxEmptyBoltTravelCM, Receiver.TransformVector(BoltOffset - *OpenBolt).Size());
        }
    }

    // Optional longer rendered sprint sample in the existing quiet interval.
    // Keep the normal acceptance timeline and all profile/gameplay fixtures intact.
    const bool bSprintPreview = FParse::Param(FCommandLine::Get(), TEXT("SprintPoseAudit"));
    if (bSprintPreview && GunplayAuditStage == 30 && GunplayAuditElapsed >= 19.90f && bSprintHeld)
    {
        Verify(TEXT("sprint_pose_active_at_speed"), bIsSprinting && SprintPoseFactor > 0.90f,
            FString::Printf(TEXT("speed=%.2f alpha=%.4f"), HorizontalSpeed(), SprintPoseFactor));
        ReleaseMovement();
        Key(EKeys::RightMouseButton, IE_Pressed);
    }
    if (bSprintPreview && GunplayAuditStage == 30 && GunplayAuditElapsed >= 20.25f && bAimHeld)
    {
        Verify(TEXT("sprint_pose_yields_to_ads"), !bIsSprinting && SprintPoseFactor < 0.01f && WeaponADSFactor > 0.98f,
            FString::Printf(TEXT("sprint_alpha=%.5f ads=%.5f"), SprintPoseFactor, WeaponADSFactor));
        Key(EKeys::RightMouseButton, IE_Released);
    }
    if (bSprintPreview && GunplayAuditElapsed >= 17.0f && GunplayAuditElapsed <= 20.35f)
    {
        const FVector SightAxis = FirstPersonCamera->GetComponentTransform().InverseTransformVectorNoScale(
            AKMViewmodel->GetSocketLocation(TEXT("WPN_FrontSight")) - AKMViewmodel->GetSocketLocation(TEXT("WPN_RearSight"))).GetSafeNormal();
        const FTransform Receiver = AKMViewmodel->GetSocketTransform(TEXT("WPN_root"), RTS_Component);
        const FVector Support = Receiver.InverseTransformPosition(AKMViewmodel->GetSocketTransform(TEXT("hand_l"), RTS_Component).GetLocation());
        const FVector Pose = AKMViewmodel->GetRelativeLocation();
        const FString Sample = FString::Printf(TEXT("%.6f,%.5f,%.3f,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f\n"),
            GunplayAuditElapsed, SprintPoseFactor, HorizontalSpeed(), Pose.X, Pose.Y, Pose.Z,
            FMath::RadiansToDegrees(FMath::Asin(SightAxis.Z)), Support.X, Support.Y, Support.Z);
        FFileHelper::SaveStringToFile(Sample, *FPaths::Combine(GunplayAuditDirectory, TEXT("sprint_samples.csv")),
            FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append);
    }

    switch (GunplayAuditStage)
    {
    case 0:
        if (GunplayAuditElapsed < 0.08f) break;
        Verify(TEXT("controller_available"), true, PC->GetName());
        Verify(TEXT("fx_assets_and_sockets"), WeaponFX && WeaponFX->IsReady(), TEXT("Required actual materials and WPN sockets"));
        Verify(TEXT("replacement_mesh"), bUsingReplacement, AKMViewmodel->GetSkeletalMeshAsset() ? AKMViewmodel->GetSkeletalMeshAsset()->GetPathName() : TEXT("missing"));
        if (bUsingM4Infima)
        {
            Verify(TEXT("m4_empty_reload_distinct_clip"), ReloadEmptyAnimation && ReloadAnimation
                && ReloadEmptyAnimation != ReloadAnimation && FMath::IsNearlyEqual(ReloadEmptyAnimation->GetPlayLength(), 2.7f, 0.001f),
                TEXT("163 source runtime frames at 60 Hz, adapted HK416 wrist and fingers"));
            Verify(TEXT("m4_hk416_audio_bank"), FireSound && MagOutSound && MagInsertSound && MagSeatSound && BoltReleaseSound
                && FireSound->GetPathName().Contains(TEXT("M4HK416Audio")) && BoltReleaseSound->GetPathName().Contains(TEXT("M4AnimationAuditFinal/S_HK416_BoltRelease")),
                TEXT("HK416 firing and four contact sounds loaded"));
            Verify(TEXT("m4_rigid_hierarchy"), AKMViewmodel->GetParentBone(TEXT("WPN_Trigger")) == TEXT("WPN_root")
                && AKMViewmodel->GetParentBone(TEXT("WPN_SOCKET_Magazine")) == TEXT("WPN_root")
                && AKMViewmodel->GetParentBone(TEXT("index_03_r")) == TEXT("index_02_r"), TEXT("Receiver parts and finger chain retain parents"));
        }
        Key(EKeys::RightMouseButton, IE_Pressed);
        ++GunplayAuditStage;
        break;
    case 1:
        if (GunplayAuditElapsed < 0.30f) break;
        Verify(TEXT("equip_blocks_held_ads"), WeaponState == EAKMWeaponState::Equipping && bAimHeld && !bIsAiming,
            FString::Printf(TEXT("state=%d held=%d aiming=%d"), static_cast<int32>(WeaponState), bAimHeld, bIsAiming));
        Capture(TEXT("00_Equip.png"));
        ++GunplayAuditStage;
        break;
    case 2:
        if (GunplayAuditElapsed < 3.35f) break;
        Verify(TEXT("equip_held_ads_resumes"), !IsWeaponBusy() && bAimHeld && bIsAiming && WeaponADSFactor > 0.98f,
            FString::Printf(TEXT("busy=%d held=%d aiming=%d ads=%.4f"), IsWeaponBusy(), bAimHeld, bIsAiming, WeaponADSFactor));
        Verify(TEXT("ads_calibration_available"), bSightCalibrated, TEXT("Two explicit new-model sight bones"));
        for (const FName Sight : {FName(TEXT("WPN_RearSight")), FName(TEXT("WPN_FrontSight"))})
        {
            const bool bExists = AKMViewmodel->DoesSocketExist(Sight);
            const FVector Local = bExists ? FirstPersonCamera->GetComponentTransform().InverseTransformPosition(AKMViewmodel->GetSocketLocation(Sight)) : FVector::ZeroVector;
            int32 Width = 0, Height = 0;
            PC->GetViewportSize(Width, Height);
            const float TransverseCM = FVector2D(Local.Y, Local.Z).Size();
            const float FocalPixels = (FMath::Max(Width, 1) * 0.5f) / FMath::Tan(FMath::DegreesToRadians(FirstPersonCamera->FieldOfView) * 0.5f);
            const float ErrorPixels = Local.X > 0.01f ? TransverseCM * FocalPixels / Local.X : BIG_NUMBER;
            const bool bCentered = bExists && Local.X > 0.0f && (TransverseCM <= 0.25f || (Width > 0 && ErrorPixels <= 3.0f));
            Verify(*FString::Printf(TEXT("ads_center_%s"), *Sight.ToString()), bCentered,
                FString::Printf(TEXT("local_cm=%s transverse_cm=%.5f pixel_error=%.3f viewport=%dx%d"), *Local.ToCompactString(), TransverseCM, ErrorPixels, Width, Height));
        }
        Capture(TEXT("01_ADS_Aligned.png"));
        ++GunplayAuditStage;
        break;
    case 3:
        if (GunplayAuditElapsed < 3.60f) break;
        AuditSavedShots = ShotsFired;
        AuditSavedAmmo = MagazineAmmo;
        AuditSavedActionTime = GunplayAuditElapsed;
        Key(EKeys::LeftMouseButton, IE_Pressed);
        ++GunplayAuditStage;
        break;
    case 4:
        if (GunplayAuditElapsed < 3.75f) break;
        Verify(TEXT("trigger_routes_to_shot"), ShotsFired > AuditSavedShots, FString::Printf(TEXT("shot_delta=%d"), ShotsFired - AuditSavedShots));
        Verify(TEXT("fx_spawned_and_bounded"), WeaponFX && WeaponFX->GetActiveParticleCount() > 0 && WeaponFX->GetActiveParticleCount() <= 64,
            FString::Printf(TEXT("active=%d"), WeaponFX ? WeaponFX->GetActiveParticleCount() : -1));
        Capture(TEXT("02_ADS_Fire_FX.png"));
        {
            int32 HitchMs = 0;
            if (FParse::Value(FCommandLine::Get(), TEXT("GunplayHitchMs="), HitchMs) && HitchMs > 0)
            {
                HitchMs = FMath::Clamp(HitchMs, 1, 300);
                Record(FString::Printf(TEXT("GUNPLAY_INJECT_REAL_HITCH milliseconds=%d"), HitchMs));
                FPlatformProcess::Sleep(static_cast<float>(HitchMs) / 1000.0f);
            }
        }
        ++GunplayAuditStage;
        break;
    case 5:
        if (GunplayAuditElapsed < AuditSavedActionTime + 1.0f) break;
        Key(EKeys::LeftMouseButton, IE_Released);
        ++GunplayAuditStage;
        break;
    case 6:
        if (GunplayAuditElapsed < 4.80f) break;
        Verify(TEXT("one_second_500rpm_cadence"), FMath::Abs((ShotsFired - AuditSavedShots) - FMath::RoundToInt(1.0f / FireInterval)) <= 1,
            FString::Printf(TEXT("shot_delta=%d interval=%.4f expected=%d tolerance=1"), ShotsFired - AuditSavedShots, FireInterval, FMath::RoundToInt(1.0f / FireInterval)));
        Verify(TEXT("one_ammo_per_actual_shot"), AuditSavedAmmo - MagazineAmmo == ShotsFired - AuditSavedShots,
            FString::Printf(TEXT("ammo_delta=%d shot_delta=%d"), AuditSavedAmmo - MagazineAmmo, ShotsFired - AuditSavedShots));
        Verify(TEXT("released_trigger_stops"), !bFireHeld, TEXT("Release delivered through PlayerInput"));
        Capture(TEXT("03_Burst_Smoke.png"));
        ++GunplayAuditStage;
        break;
    case 7:
        if (GunplayAuditElapsed < 5.65f) break;
        Verify(TEXT("recoil_springs_recover"), GunKickPosition.Size() < 0.002f && GunKickRotation.Size() < 0.003f && FMath::Abs(GunFlip) < 0.003f
            && CameraJitterRotation.Size() < 0.002f && FMath::Abs(CameraKickPitch) < 0.003f,
            FString::Printf(TEXT("gun_pos_m=%.6f gun_rot_rad=%.6f flip=%.6f camera_pitch=%.6f"), GunKickPosition.Size(), GunKickRotation.Size(), GunFlip, CameraKickPitch));
        Key(EKeys::RightMouseButton, IE_Released);
        SetAuditAmmo(15, 20);
        AuditSavedShots = ShotsFired;
        Key(EKeys::R, IE_Pressed);
        ++GunplayAuditStage;
        break;
    case 8:
        if (GunplayAuditElapsed < 5.78f) break;
        Key(EKeys::R, IE_Released);
        Key(EKeys::W, IE_Pressed);
        Key(EKeys::LeftShift, IE_Pressed);
        Verify(TEXT("normal_reload_started"), WeaponState == EAKMWeaponState::Reloading && MagazineAmmo == 15,
            FString::Printf(TEXT("state=%d elapsed=%.3f ammo=%d"), static_cast<int32>(WeaponState), WeaponStateElapsed, MagazineAmmo));
        ++GunplayAuditStage;
        break;
    case 9:
        if (GunplayAuditElapsed < 6.02f) break;
        AuditSavedActionTime = WeaponStateElapsed;
        Key(EKeys::R, IE_Pressed);
        ++GunplayAuditStage;
        break;
    case 10:
        if (GunplayAuditElapsed < 6.14f) break;
        Key(EKeys::R, IE_Released);
        Verify(TEXT("repeat_r_does_not_restart"), IsReloading() && WeaponStateElapsed >= AuditSavedActionTime + 0.05f,
            FString::Printf(TEXT("before=%.4f after=%.4f"), AuditSavedActionTime, WeaponStateElapsed));
        ++GunplayAuditStage;
        break;
    case 11:
        if (GunplayAuditElapsed < 6.62f) break;
        Verify(TEXT("reload_and_sprint_coexist"), IsReloading() && bIsSprinting && HorizontalSpeed() >= SlideMinimumSpeed,
            FString::Printf(TEXT("reload=%d sprint=%d speed=%.2f minimum=%.2f grounded=%d"), IsReloading(), bIsSprinting, HorizontalSpeed(), SlideMinimumSpeed, GetCharacterMovement()->IsMovingOnGround()));
        Capture(TEXT("04_Reload_Sprint.png"));
        // C is intercepted by the character sheet; use the existing Slide binding.
        Key(EKeys::LeftControl, IE_Pressed);
        ++GunplayAuditStage;
        break;
    case 12:
        if (GunplayAuditElapsed < 6.76f) break;
        Key(EKeys::LeftControl, IE_Released);
        Verify(TEXT("reload_and_slide_coexist"), IsReloading() && bIsSliding,
            FString::Printf(TEXT("reload=%d slide=%d speed=%.2f"), IsReloading(), bIsSliding, HorizontalSpeed()));
        Capture(TEXT("05_Reload_Slide.png"));
        ++GunplayAuditStage;
        break;
    case 13:
        if (GunplayAuditElapsed < 7.04f) break;
        Key(EKeys::SpaceBar, IE_Pressed);
        ++GunplayAuditStage;
        break;
    case 14:
        if (GunplayAuditElapsed < 7.18f) break;
        Verify(TEXT("reload_slide_jump"), IsReloading() && !GetCharacterMovement()->IsMovingOnGround() && !bIsSliding && GetVelocity().Z > 0.0f,
            FString::Printf(TEXT("reload=%d grounded=%d slide=%d vz=%.2f horizontal=%.2f"), IsReloading(), GetCharacterMovement()->IsMovingOnGround(), bIsSliding, GetVelocity().Z, HorizontalSpeed()));
        Verify(TEXT("reload_blocks_ammo_and_shots"), MagazineAmmo == 15 && ShotsFired == AuditSavedShots,
            FString::Printf(TEXT("ammo=%d shots_delta=%d"), MagazineAmmo, ShotsFired - AuditSavedShots));
        Capture(TEXT("06_Reload_SlideJump.png"));
        ReleaseMovement();
        ++GunplayAuditStage;
        break;
    case 15:
        if (GunplayAuditElapsed < 8.62f) break;
        Verify(TEXT("normal_reload_settlement"), !IsReloading() && MagazineAmmo == 30 && ReserveAmmo == 5,
            FString::Printf(TEXT("reload=%d magazine=%d reserve=%d total=%d"), IsReloading(), MagazineAmmo, ReserveAmmo, MagazineAmmo + ReserveAmmo));
        AuditSavedAmmo = MagazineAmmo;
        ++GunplayAuditStage;
        break;
    case 16:
        if (GunplayAuditElapsed < 8.85f) break;
        Verify(TEXT("reload_settles_once"), MagazineAmmo == AuditSavedAmmo && MagazineAmmo + ReserveAmmo == 35,
            FString::Printf(TEXT("magazine=%d reserve=%d previous=%d"), MagazineAmmo, ReserveAmmo, AuditSavedAmmo));
        SetAuditAmmo(0, 7);
        Key(EKeys::R, IE_Pressed);
        ++GunplayAuditStage;
        break;
    case 17:
        if (GunplayAuditElapsed < 9.02f) break;
        Key(EKeys::R, IE_Released);
        Verify(TEXT("empty_reload_started"), WeaponState == EAKMWeaponState::ReloadingEmpty && bPendingEmptyReload,
            FString::Printf(TEXT("state=%d empty=%d duration=%.4f"), static_cast<int32>(WeaponState), bPendingEmptyReload, WeaponStateDuration));
        ++GunplayAuditStage;
        break;
    case 18:
        if (GunplayAuditElapsed < 10.45f) break;
        Verify(TEXT("empty_reload_in_progress"), IsReloading() && MagazineAmmo == 0 && ReserveAmmo == 7,
            FString::Printf(TEXT("elapsed=%.4f ammo=%d reserve=%d"), WeaponStateElapsed, MagazineAmmo, ReserveAmmo));
        Capture(TEXT("07_EmptyReload_Charge.png"));
        ++GunplayAuditStage;
        break;
    case 19:
        if (GunplayAuditElapsed < 12.60f) break;
        Verify(TEXT("insufficient_reserve_conserved"), !IsReloading() && MagazineAmmo == 7 && ReserveAmmo == 0,
            FString::Printf(TEXT("reload=%d ammo=%d reserve=%d"), IsReloading(), MagazineAmmo, ReserveAmmo));
        SetAuditAmmo(0, 0);
        AuditSavedShots = ShotsFired;
        Key(EKeys::LeftMouseButton, IE_Pressed);
        ++GunplayAuditStage;
        break;
    case 20:
        if (GunplayAuditElapsed < 12.80f) break;
        Key(EKeys::LeftMouseButton, IE_Released);
        Verify(TEXT("dry_fire_no_phantom_round"), ShotsFired == AuditSavedShots && MagazineAmmo == 0 && ReserveAmmo == 0 && !IsReloading(),
            FString::Printf(TEXT("shot_delta=%d ammo=%d reserve=%d reload=%d"), ShotsFired - AuditSavedShots, MagazineAmmo, ReserveAmmo, IsReloading()));
        SetAuditAmmo(30, 90);
        Key(EKeys::RightMouseButton, IE_Pressed);
        ++GunplayAuditStage;
        break;
    case 21:
        if (GunplayAuditElapsed < 13.25f) break;
        {
            const FVector Start = FirstPersonCamera->GetComponentLocation();
            const FVector Muzzle = AKMViewmodel->GetSocketLocation(TEXT("WPN_SOCKET_Muzzle"));
            const FVector Direction = (Muzzle - Start).GetSafeNormal();
            FActorSpawnParameters Params;
            Params.ObjectFlags |= RF_Transient;
            Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            AStaticMeshActor* Wall = GetWorld()->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), FMath::Lerp(Start, Muzzle, 0.55f), Direction.Rotation(), Params);
            if (Wall)
            {
                UStaticMeshComponent* Component = Wall->GetStaticMeshComponent();
                Component->SetMobility(EComponentMobility::Movable);
                Component->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube")));
                Component->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
                Component->SetCollisionResponseToAllChannels(ECR_Ignore);
                Component->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
                Component->SetGenerateOverlapEvents(false);
                Wall->SetActorScale3D(FVector(0.02f, 2.0f, 2.0f));
                Wall->SetActorHiddenInGame(true);
                GunplayAuditWall = Wall;
            }
            FHitResult Probe;
            FCollisionQueryParams Query(SCENE_QUERY_STAT(GunplayAuditWall), true, this);
            const bool bProbeHit = GetWorld()->LineTraceSingleByChannel(Probe, Start, Muzzle, ECC_Visibility, Query);
            Verify(TEXT("near_wall_fixture_intersects_muzzle"), Wall && bProbeHit && Probe.GetActor() == Wall,
                FString::Printf(TEXT("wall=%d hit_fixture=%d camera_muzzle_cm=%.3f"), Wall != nullptr, Probe.GetActor() == Wall, FVector::Distance(Start, Muzzle)));
        }
        ++GunplayAuditStage;
        break;
    case 22:
        if (GunplayAuditElapsed < 13.42f) break;
        AuditSavedShots = ShotsFired;
        Key(EKeys::LeftMouseButton, IE_Pressed);
        ++GunplayAuditStage;
        break;
    case 23:
        if (GunplayAuditElapsed < 13.55f) break;
        Key(EKeys::LeftMouseButton, IE_Released);
        Verify(TEXT("shot_uses_muzzle_obstruction"), ShotsFired > AuditSavedShots && bLastShotMuzzleBlocked,
            FString::Printf(TEXT("shot_delta=%d muzzle_blocked=%d"), ShotsFired - AuditSavedShots, bLastShotMuzzleBlocked));
        Capture(TEXT("08_MuzzleObstruction.png"));
        ++GunplayAuditStage;
        break;
    case 24:
        if (GunplayAuditElapsed < 13.78f) break;
        if (GunplayAuditWall.IsValid()) GunplayAuditWall->Destroy();
        GunplayAuditWall.Reset();
        ++GunplayAuditStage;
        break;
    case 25:
        if (GunplayAuditElapsed < 14.30f) break;
        Key(EKeys::RightMouseButton, IE_Released);
        Key(EKeys::W, IE_Pressed);
        Key(EKeys::LeftShift, IE_Pressed);
        ++GunplayAuditStage;
        break;
    case 26:
        if (GunplayAuditElapsed < 15.20f) break;
        Verify(TEXT("sprint_before_trigger"), bIsSprinting, FString::Printf(TEXT("sprint=%d speed=%.3f grounded=%d"), bIsSprinting, HorizontalSpeed(), GetCharacterMovement()->IsMovingOnGround()));
        AuditSavedShots = ShotsFired;
        AuditSavedActionTime = GunplayAuditElapsed;
        AuditSprintFireDeadline = GetWorld()->GetTimeSeconds() + SprintToFireDuration;
        Key(EKeys::LeftMouseButton, IE_Pressed);
        ++GunplayAuditStage;
        break;
    case 27:
        if (GunplayAuditElapsed < AuditSavedActionTime + 0.06f) break;
        // A real render hitch can skip the entire early observation window.
        // Check the shot timestamp against the gate instead of calling a late
        // sample an early shot. This does not alter the gate or force state.
        Verify(TEXT("sprint_to_fire_blocks_early_shot"), ShotsFired == AuditSavedShots || TriggerFirstShotWorldTime + 0.0001 >= AuditSprintFireDeadline,
            FString::Printf(TEXT("shot_delta=%d lock_remaining=%.4f observed_after_press=%.4f first_shot=%.4f earliest_legal=%.4f"),
                ShotsFired - AuditSavedShots, SprintToFireLeft, GunplayAuditElapsed - AuditSavedActionTime, TriggerFirstShotWorldTime, AuditSprintFireDeadline));
        ++GunplayAuditStage;
        break;
    case 28:
        if (GunplayAuditElapsed < 15.52f) break;
        Verify(TEXT("held_trigger_fires_after_sprint_gate"), ShotsFired > AuditSavedShots && !bIsSprinting,
            FString::Printf(TEXT("shot_delta=%d sprint=%d lock=%.4f"), ShotsFired - AuditSavedShots, bIsSprinting, SprintToFireLeft));
        Key(EKeys::LeftMouseButton, IE_Released);
        ReleaseMovement();
        Capture(TEXT("09_SprintToFire.png"));
        ++GunplayAuditStage;
        break;
    case 29:
        if (GunplayAuditElapsed < 17.00f) break;
        Verify(TEXT("all_action_inputs_released"), !bFireHeld && !bAimHeld && !bSprintHeld,
            FString::Printf(TEXT("fire=%d aim=%d sprint=%d"), bFireHeld, bAimHeld, bSprintHeld));
        if (bSprintPreview)
        {
            Key(EKeys::W, IE_Pressed);
            Key(EKeys::LeftShift, IE_Pressed);
        }
        ++GunplayAuditStage;
        break;
    case 30:
        if (GunplayAuditElapsed < 20.40f) break;
        Verify(TEXT("fx_particles_expire"), WeaponFX && WeaponFX->IsReady() && WeaponFX->GetActiveParticleCount() == 0,
            FString::Printf(TEXT("active=%d"), WeaponFX ? WeaponFX->GetActiveParticleCount() : -1));
        Verify(TEXT("camera_and_viewmodel_finite"), !FirstPersonCamera->GetComponentTransform().ContainsNaN() && !AKMViewmodel->GetComponentTransform().ContainsNaN(),
            FString::Printf(TEXT("camera=%s viewmodel=%s"), *FirstPersonCamera->GetComponentLocation().ToCompactString(), *AKMViewmodel->GetComponentLocation().ToCompactString()));
        // Keep the real trigger down across the last round and automatic empty reload.
        SetAuditAmmo(1, 2);
        AuditSavedShots = ShotsFired;
        Key(EKeys::LeftMouseButton, IE_Pressed);
        ++GunplayAuditStage;
        break;
    case 31:
        if (GunplayAuditElapsed < 20.70f) break;
        Verify(TEXT("held_last_round_starts_empty_reload"), bFireHeld && WeaponState == EAKMWeaponState::ReloadingEmpty
            && ShotsFired - AuditSavedShots == 1 && MagazineAmmo == 0 && ReserveAmmo == 2,
            FString::Printf(TEXT("held=%d state=%d shot_delta=%d ammo=%d reserve=%d elapsed=%.4f"),
                bFireHeld, static_cast<int32>(WeaponState), ShotsFired - AuditSavedShots, MagazineAmmo, ReserveAmmo, WeaponStateElapsed));
        Capture(TEXT("11_HeldTrigger_AutoReload.png"));
        ++GunplayAuditStage;
        break;
    case 32:
        if (GunplayAuditElapsed < 24.65f) break;
        Verify(TEXT("held_trigger_resumes_after_empty_reload"), ShotsFired - AuditSavedShots == 3 && MagazineAmmo == 0
            && ReserveAmmo == 0 && !IsReloading(),
            FString::Printf(TEXT("shot_delta=%d expected=3 ammo=%d reserve=%d reload=%d held=%d"),
                ShotsFired - AuditSavedShots, MagazineAmmo, ReserveAmmo, IsReloading(), bFireHeld));
        Key(EKeys::LeftMouseButton, IE_Released);
        ++GunplayAuditStage;
        break;
    case 33:
        if (GunplayAuditElapsed < 24.85f) break;
        SetAuditAmmo(10, 0);
        AuditSavedShots = ShotsFired;
        AuditSavedActionTime = GunplayAuditElapsed;
        Key(EKeys::LeftMouseButton, IE_Pressed);
        ++GunplayAuditStage;
        break;
    case 34:
        // Observe the actual shot after the queued input is processed, then release.
        if (ShotsFired == AuditSavedShots && GunplayAuditElapsed < AuditSavedActionTime + 0.20f) break;
        Verify(TEXT("tap_fixture_single_initial_shot"), ShotsFired - AuditSavedShots == 1,
            FString::Printf(TEXT("shot_delta=%d response_seconds=%.4f"), ShotsFired - AuditSavedShots, GunplayAuditElapsed - AuditSavedActionTime));
        Key(EKeys::LeftMouseButton, IE_Released);
        AuditSavedActionTime = GunplayAuditElapsed;
        ++GunplayAuditStage;
        break;
    case 35:
        if (GunplayAuditElapsed < AuditSavedActionTime + 0.13f) break;
        Verify(TEXT("tap_release_delivered_before_repress"), !bFireHeld,
            FString::Printf(TEXT("held=%d release_gap_seconds=%.4f"), bFireHeld, GunplayAuditElapsed - AuditSavedActionTime));
        AuditSavedShots = ShotsFired;
        AuditSavedAmmo = MagazineAmmo;
        AuditSavedActionTime = GunplayAuditElapsed;
        Key(EKeys::LeftMouseButton, IE_Pressed);
        ++GunplayAuditStage;
        break;
    case 36:
        if (ShotsFired == AuditSavedShots && GunplayAuditElapsed < AuditSavedActionTime + 0.20f) break;
        Verify(TEXT("repress_no_same_frame_double_shot"), ShotsFired - AuditSavedShots == 1,
            FString::Printf(TEXT("shot_delta=%d response_seconds=%.4f frame_seconds=%.4f"),
                ShotsFired - AuditSavedShots, GunplayAuditElapsed - AuditSavedActionTime, DeltaSeconds));
        AuditSavedActionTime = GunplayAuditElapsed;
        ++GunplayAuditStage;
        break;
    case 37:
        {
            const float SinceFirstShot = GunplayAuditElapsed - AuditSavedActionTime;
            const int32 ShotDelta = ShotsFired - AuditSavedShots;
            const bool bEarlyRepeat = ShotDelta > 1 && SinceFirstShot + 0.001f < FireInterval;
            // At 30 FPS this samples at about 0.10 s; at 60/144 FPS it samples
            // closer to 0.12 s. Release on the last available frame before the
            // next legitimate shot. A hitch beyond the interval permits only
            // the number of shots justified by the elapsed time.
            const bool bLastFrameBeforeDeadline = SinceFirstShot + DeltaSeconds + 0.001f >= FireInterval;
            if (!bEarlyRepeat && !bLastFrameBeforeDeadline) break;
            const int32 MaximumLegalShots = 1 + FMath::FloorToInt((SinceFirstShot + 0.0001f) / FireInterval);
            Verify(TEXT("repress_respects_full_fire_interval"), !bEarlyRepeat && ShotDelta <= MaximumLegalShots,
                FString::Printf(TEXT("shot_delta=%d elapsed_since_first=%.4f fire_interval=%.4f frame=%.4f legal_max=%d early=%d"),
                    ShotDelta, SinceFirstShot, FireInterval, DeltaSeconds, MaximumLegalShots, bEarlyRepeat));
            Key(EKeys::LeftMouseButton, IE_Released);
            // Retain the measured count for the following release/consumption check.
            AuditSavedShots = ShotsFired;
            AuditSavedActionTime = GunplayAuditElapsed;
            ++GunplayAuditStage;
        }
        break;
    case 38:
        if (GunplayAuditElapsed < AuditSavedActionTime + 0.16f) break;
        Verify(TEXT("repress_release_stops_further_shots"), !bFireHeld && ShotsFired == AuditSavedShots,
            FString::Printf(TEXT("held=%d shots_after_release=%d ammo=%d before_repress=%d"), bFireHeld, ShotsFired - AuditSavedShots, MagazineAmmo, AuditSavedAmmo));
        ++GunplayAuditStage;
        break;
    case 39:
        if (GunplayAuditElapsed < 29.60f) break;
        if (FParse::Param(FCommandLine::Get(), TEXT("GunplayCaptureAudio")))
            UAudioMixerBlueprintLibrary::StopRecordingOutput(this, EAudioRecordingExportType::WavFile, TEXT("GunplayAudio"), GunplayAuditDirectory + TEXT("/"));
        Verify(TEXT("fx_expire_after_input_regressions"), WeaponFX && WeaponFX->IsReady() && WeaponFX->GetActiveParticleCount() == 0,
            FString::Printf(TEXT("active=%d held=%d"), WeaponFX ? WeaponFX->GetActiveParticleCount() : -1, bFireHeld));
        Capture(TEXT("10_Final_Recovered.png"));
        ++GunplayAuditStage;
        break;
    case 40:
    {
        if (GunplayAuditElapsed < 29.85f) break;
        // Sample matching clock origins before synchronous audit logging.
        const double WallSeconds = FPlatformTime::Seconds() - GunplayAuditWallStarted;
        const double WorldSeconds = GetWorld()->GetTimeSeconds() - GunplayAuditWorldStarted;
        Key(EKeys::LeftMouseButton, IE_Released);
        Key(EKeys::RightMouseButton, IE_Released);
        Key(EKeys::R, IE_Released);
        ReleaseMovement();
        if (GunplayAuditWall.IsValid()) GunplayAuditWall->Destroy();
        GunplayAuditWall.Reset();
        if (bUsingM4Infima)
        {
            Verify(TEXT("m4_rigid_pose_stability"), AuditRigidPoseSamples > 100 && AuditMaxRigidBoneDriftCM < 0.02f,
                FString::Printf(TEXT("samples=%d max_drift_cm=%.8f"), AuditRigidPoseSamples, AuditMaxRigidBoneDriftCM));
            Verify(TEXT("m4_reload_cues_once_per_contact"), AuditNormalMechanicalCues == 3 && AuditEmptyMechanicalCues == 8 && AuditBoltReleaseCues == 2,
                FString::Printf(TEXT("normal=%d empty=%d bolt_release=%d"), AuditNormalMechanicalCues, AuditEmptyMechanicalCues, AuditBoltReleaseCues));
            Verify(TEXT("m4_cues_follow_animation_clock"), AuditMaxMechanicalLateness <= GunplayAuditMaxDelta + 0.001f,
                FString::Printf(TEXT("max_lateness=%.6f maximum_frame=%.6f"), AuditMaxMechanicalLateness, GunplayAuditMaxDelta));
            Verify(TEXT("m4_empty_bolt_moves"), AuditMaxEmptyBoltTravelCM > 3.4f && AuditMaxEmptyBoltTravelCM < 3.6f,
                FString::Printf(TEXT("travel_cm=%.6f"), AuditMaxEmptyBoltTravelCM));
        }
        if (FParse::Param(FCommandLine::Get(), TEXT("GunplayCaptureAudio")))
            Verify(TEXT("m4_runtime_audio_recorded"), IFileManager::Get().FileSize(*FPaths::Combine(GunplayAuditDirectory, TEXT("GunplayAudio.wav"))) > 44,
                TEXT("Actual mixer output exported before process exit"));
        Record(FString::Printf(TEXT("GUNPLAY_ACCEPTANCE_COMPLETE failures=%d elapsed=%.3f shots=%d screenshots=%s"),
            GunplayAuditFailures, GunplayAuditElapsed, ShotsFired, *GunplayAuditDirectory));
        Record(FString::Printf(TEXT("GUNPLAY_CLOCK fixed_step=%d game_seconds=%.4f wall_seconds=%.4f ticks=%d max_delta=%.4f"),
            FApp::UseFixedTimeStep(), WorldSeconds, WallSeconds,
            GunplayAuditTicks, GunplayAuditMaxDelta));
        bRunGunplayAcceptance = false;
        ++GunplayAuditStage;
        FPlatformMisc::RequestExitWithStatus(false, GunplayAuditFailures == 0 ? 0 : 1);
        break;
    }
    default:
        break;
    }
    // Derive the sample index from per-pawn elapsed time, without process-global
    // mutable state. Named acceptance screenshots take priority over video frames.
    const float CaptureEnd = bSprintPreview ? 20.35f : 17.0f;
    float CaptureHz = bSprintPreview ? 30.0f : 10.0f;
    FParse::Value(FCommandLine::Get(), TEXT("GunplayCaptureHz="), CaptureHz);
    CaptureHz = FMath::Clamp(CaptureHz, 10.0f, 60.0f);
    if (GunplayAuditElapsed >= 2.8f && GunplayAuditElapsed <= CaptureEnd
        && FParse::Param(FCommandLine::Get(), TEXT("GunplayCaptureFrames"))
        && !FScreenshotRequest::IsScreenshotRequested())
    {
        const int32 Frame = FMath::FloorToInt((GunplayAuditElapsed - 2.8f) * CaptureHz);
        const int32 PreviousFrame = FMath::FloorToInt((GunplayAuditElapsed - DeltaSeconds - 2.8f) * CaptureHz);
        if (Frame != PreviousFrame)
            FScreenshotRequest::RequestScreenshot(FPaths::Combine(GunplayAuditDirectory, TEXT("Frames"), FString::Printf(TEXT("Frame_%04d.png"), Frame)), false, false);
    }
}
