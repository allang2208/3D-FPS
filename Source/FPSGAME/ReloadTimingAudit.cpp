#include "FPSGAMECharacter.h"
#include "UI/ColdSteelStatusModel.h"
#include "Weapons/GunsmithSystem.h"
#include "Weapons/FPSGunplayAnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Engine/GameInstance.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "HighResScreenshot.h"
#include "AudioMixerBlueprintLibrary.h"

// Opt-in, fresh-process regression using a separate inventory save. The three
// multipliers simulate future attachment tuning without editing the live catalog.
void AFPSGAMECharacter::RunReloadTimingAudit()
{
    auto* P = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* G = GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    if (!P || !G || !P->IsAudit() || !P->ProfileSlot().Contains(TEXT("ReloadTiming"))) return;
    struct FRun
    {
        int32 Case = 0, Stage = 0, Failures = 0, Shots = 0, Cues = 0, Captures = 0;
        double Deadline = 0;
        float Duration = 0, LastVideoTime = -1;
        bool SawPose = false, ClockOK = true, ShotLockOK = true;
        FString Out;
    };
    static FRun R;
    const double Now = GetWorld()->GetTimeSeconds();
    const auto Check = [&](bool OK, const TCHAR* Label)
    {
        if (!OK) ++R.Failures;
        UE_LOG(LogTemp, Display, TEXT("RELOAD_TIMING %s case=%d %s"), OK ? TEXT("PASS") : TEXT("FAIL"), R.Case, Label);
    };
    const auto Capture = [&](const TCHAR* Label)
    {
        if (!FParse::Param(FCommandLine::Get(), TEXT("ReloadTimingCapture"))) return;
        const FString Name = FString::Printf(TEXT("case%02d_%s.png"), R.Case, Label);
        FScreenshotRequest::RequestScreenshot(R.Out / Name, true, false);
        UE_LOG(LogTemp, Display, TEXT("RELOAD_TIMING_FRAME name=%s world=%.6f elapsed=%.6f duration=%.6f"), *Name, Now, WeaponStateElapsed, R.Duration);
    };
    if (Now < 4) return;
    if (R.Out.IsEmpty())
    {
        R.Out = FPaths::ProjectSavedDir() / TEXT("ReloadTiming") / P->ProfileSlot();
        IFileManager::Get().MakeDirectory(*R.Out, true);
        if (FParse::Param(FCommandLine::Get(), TEXT("ReloadTimingAudio")))
        {
            UAudioMixerBlueprintLibrary::StartRecordingOutput(this, 240.f);
            UE_LOG(LogTemp, Display, TEXT("RELOAD_TIMING_AUDIO_START world=%.6f"), Now);
        }
    }
    if (R.Case >= 24)
    {
        if (FParse::Param(FCommandLine::Get(), TEXT("ReloadTimingAudio")))
            UAudioMixerBlueprintLibrary::StopRecordingOutput(this, EAudioRecordingExportType::WavFile, TEXT("mix"), R.Out, nullptr);
        UE_LOG(LogTemp, Display, TEXT("RELOAD_TIMING COMPLETE cases=%d failures=%d"), R.Case, R.Failures);
        FPlatformMisc::RequestExitWithStatus(false, R.Failures ? 1 : 0);
        return;
    }
    const bool bAKM = R.Case >= 12;
    const bool bDrum = (R.Case / 6) % 2 != 0;
    const bool bEmpty = (R.Case / 3) % 2 != 0;
    constexpr float Multipliers[] = {1.f, .8f, 1.25f};
    const float Multiplier = Multipliers[R.Case % 3];
    if (R.Stage == 0)
    {
        FireReleased(); AimReleased();
        auto S = P->Snapshot(); S.Items.Reset(); S.Hotbar.Init(TEXT(""), 4); S.HotbarDefinitions.Init(TEXT(""), 4);
        auto W = P->CreateItem(bAKM ? TEXT("ue_akm") : TEXT("ue_m4a1"));
        W.Place = 1; W.Cell = 9; W.Magazine = bEmpty ? 0 : 15;
        S.Items.Add(W); S.ActiveWeaponSlot = 9;
        auto Ammo = P->CreateItem(bAKM ? TEXT("ammo_762") : TEXT("ammo_556"), 200);
        Check(ColdSteelInventory::Insert(S.Items, Ammo) && P->CommitState(S), TEXT("isolated inventory fixture"));
        R.Stage = 1; return;
    }
    if (R.Stage == 1)
    {
        if (IsWeaponBusy()) return;
        const auto Install = [&](const TCHAR* Slot, const TCHAR* Value)
        {
            Check(G->Begin(P->Equipped()->InstanceId) && G->Select(Slot, Value) && G->Apply(), TEXT("real attachment apply"));
            G->Close();
        };
        if (bDrum) Install(TEXT("magazine"), TEXT("large_drum"));
        constexpr const TCHAR* Grips[] = {TEXT("false"), TEXT("angled_foregrip"), TEXT("canted_foregrip"), TEXT("vertical_foregrip"), TEXT("prism_handstop")};
        if (R.Case % 5) Install(TEXT("underbarrel"), Grips[R.Case % 5]);
        const auto Stats = G->Calculate(P->Equipped()->Definition, G->Installed(*P->Equipped()));
        Check(FMath::IsNearlyEqual(ReloadDuration, static_cast<float>(Stats.Reload), .001f)
            && FMath::IsNearlyEqual(EmptyReloadDuration, static_cast<float>(Stats.EmptyReload), .001f), TEXT("displayed catalog timings equal runtime"));
        // Set once before starting. Profile autosave during a reload must not
        // change the snapshotted action duration or its contact clock.
        ReloadDuration *= Multiplier; EmptyReloadDuration *= Multiplier;
        R.Shots = ShotsFired; R.Captures = 0; R.LastVideoTime = -1; R.SawPose = false; R.ClockOK = R.ShotLockOK = true;
        ReloadPressed();
        Check(IsReloading() && ActiveActionAnimation && GunplayAnimation, TEXT("reload uses loaded animation"));
        R.Duration = WeaponStateDuration; R.Deadline = WeaponActionStartedAt + R.Duration;
        R.Cues = MechanicalCueTimes.Num();
        UE_LOG(LogTemp, Display, TEXT("RELOAD_TIMING START case=%d weapon=%s drum=%d empty=%d duration_mult=%.3f duration=%.6f clip=%s clip_length=%.6f rate=%.6f deadline=%.6f"),
            R.Case, bAKM ? TEXT("AKM") : TEXT("M4"), bDrum, bEmpty, Multiplier, R.Duration,
            *GetNameSafe(ActiveActionAnimation), ActiveActionAnimation ? ActiveActionAnimation->GetPlayLength() : 0.f, ActionPlayRate, R.Deadline);
        // Simulate input arriving at the end of a 400 ms frame. The elapsed
        // interval before that input must not be charged to this new animation.
        UpdateActionPose(.4f);
        Check(FMath::IsNearlyZero(ActionElapsed) && ActiveActionAnimation, TEXT("hitch before reload input does not advance or retire pose"));
        Check(FMath::IsNearlyEqual(ActionDuration, R.Duration, .0001f), TEXT("animation and fire lock share deadline"));
        const double Start = WeaponActionStartedAt;
        ReloadPressed();
        Check(WeaponActionStartedAt == Start, TEXT("repeat reload preserves deadline"));
        FirePressed();
        Check(ShotsFired == R.Shots, TEXT("trigger blocked during reload"));
        for (float Cue : MechanicalCueTimes)
        {
            const float Runtime = bUsingM4Infima ? ReloadRuntimeTime(Cue) : Cue;
            Check(Runtime >= 0 && Runtime < R.Duration, TEXT("contact inside scaled animation"));
        }
        Capture(TEXT("start")); R.Stage = 2; return;
    }
    if (R.Stage == 2)
    {
        if (IsReloading())
        {
            if (FParse::Param(FCommandLine::Get(), TEXT("ReloadTimingVideo"))
                && (R.Case == 0 || R.Case == 1 || R.Case == 15 || R.Case == 16 || R.Case == 21 || R.Case == 22)
                && WeaponStateElapsed - R.LastVideoTime >= .05f)
            {
                R.LastVideoTime = WeaponStateElapsed;
                Capture(*FString::Printf(TEXT("video%05d"), FMath::RoundToInt(WeaponStateElapsed * 1000)));
            }
            R.SawPose |= GunplayAnimation && GunplayAnimation->ActionAlpha > .5f;
            R.ClockOK &= ActiveActionAnimation && FMath::IsNearlyEqual(ActionElapsed, WeaponStateElapsed, .0001f)
                && GunplayAnimation && FMath::IsNearlyEqual(GunplayAnimation->ActionTime, ReloadSourceTime(WeaponStateElapsed), .0001f);
            R.ShotLockOK &= ShotsFired == R.Shots;
            if (WeaponStateElapsed > R.Duration * (.25f + .35f * R.Captures) && R.Captures < 3)
            { Capture(*FString::Printf(TEXT("pose%d"), R.Captures)); ++R.Captures; }
            if (Now > R.Deadline + 1) { Check(false, TEXT("reload deadline timeout")); FPlatformMisc::RequestExitWithStatus(false, 1); }
            return;
        }
        Check(R.SawPose && R.ClockOK, TEXT("pose remains on state clock until completion"));
        Check(R.ShotLockOK && ShotsFired > R.Shots, TEXT("held trigger fires on completion tick without extra wait"));
        Check(Now - R.Deadline <= GetWorld()->GetDeltaSeconds() + .001, TEXT("completion within one simulation tick"));
        Check(MagazineAmmo + ReserveAmmo + (ShotsFired - R.Shots) == 200 + (bEmpty ? 0 : 15), TEXT("ammo conserved through completion and held fire"));
        UE_LOG(LogTemp, Display, TEXT("RELOAD_TIMING END case=%d delay=%.6f dt=%.6f shots=%d"), R.Case, Now - R.Deadline, GetWorld()->GetDeltaSeconds(), ShotsFired - R.Shots);
        FireReleased(); Capture(TEXT("complete")); ++R.Case; R.Stage = 0;
    }
}
