#pragma once
#include "CoreMinimal.h"

namespace DanWesson715WeaponAssets
{
    inline constexpr const TCHAR* Definition = TEXT("ue_dan_wesson715");
    inline constexpr const TCHAR* MeshPath = TEXT("/Game/Weapons/DanWesson715/Chrome20260914/SK_DW715_Manny.SK_DW715_Manny");
    inline constexpr const TCHAR* WetMaterialsPath = TEXT("/Game/Weapons/DanWesson715/AccessoryPolymer20260914/DA_DW715_WetMaterials.DA_DW715_WetMaterials");
    inline constexpr float ViewmodelBoundsScale = 5.f;
    inline FString AttachmentPath(const FString& Part)
    {
        const bool bOwnPolymer = Part == TEXT("laser") || Part == TEXT("flashlight") || Part == TEXT("holographic");
        const FString Root = bOwnPolymer
            ? TEXT("/Game/Weapons/DanWesson715/AccessoryPolymer20260914/Attachments/")
            : TEXT("/Game/Weapons/DanWesson715/Chrome20260914/Attachments/");
        if (Part == TEXT("laser") || Part == TEXT("flashlight"))
            return Root + Part + TEXT("/SM_TacticalDevice");
        return Root + TEXT("Meshes/SM_DW715_") + Part;
    }
    // The authored contact table uses 3.60 s; installed speedloaders always use
    // the 3.85 s empty-action clip, with contacts mapped by their duration ratio.
    inline constexpr float NormalReload = 3.6f;
    inline constexpr float EmptyReload = 3.85f;
    inline constexpr float Open = .48f;
    inline constexpr float Eject = 1.03f;
    inline constexpr float RoundsVisible = 1.44f;
    inline constexpr float Insert = 2.20f;
    inline constexpr float Seat = 2.42f;
    inline constexpr float Close = 3.05f;
    struct FSpeedloaderSoundCue
    {
        const TCHAR* Name;
        float Contact;
        float LeadSeconds;
        bool bEmptyOnly;
    };
    // Edited from the user's 715-reloading.mp3. Contact is animation source
    // time; LeadSeconds is unpitched audio pre-roll from the cut to its impact.
    // Source cuts and inferred phase identities: RecordedAudio20260914/manifest.json.
    inline constexpr FSpeedloaderSoundCue SpeedloaderSoundCues[] =
    {
        {TEXT("Open"), Open, .1075f, false},
        {TEXT("Eject"), Eject, .2575f, true},
        {TEXT("Retrieve"), RoundsVisible, .0675f, false},
        {TEXT("Insert"), Insert, .4225f, false},
        {TEXT("Release"), Seat, .0425f, false},
        {TEXT("Withdraw"), 2.68f, .2025f, false},
        {TEXT("Close"), Close, .0675f, false},
    };
    inline FString SpeedloaderSoundPath(const TCHAR* Cue)
    {
        return FString::Printf(TEXT("/Game/Weapons/DanWesson715/RecordedAudio20260914/S_DW715_Loader_%s.S_DW715_Loader_%s"), Cue, Cue);
    }
    inline constexpr const TCHAR* ReloadDeviceSlot = TEXT("reload_device");
    inline constexpr const TCHAR* Speedloader = TEXT("dw715_speedloader");
    inline constexpr float EmptyCaseClear = 1.28f;
    inline constexpr float SingleBegin = .60f;
    inline constexpr float SingleEmptyBegin = 1.50f;
    inline constexpr float SingleStep = 1.10f;
    inline constexpr float SingleVisible = .10f;
    inline constexpr float SingleSeat = .64f;
    inline constexpr float SingleCloseTail = .70f;
    inline constexpr float SingleLoopBegin(bool bEmpty) { return bEmpty ? SingleEmptyBegin : SingleBegin; }
    inline constexpr float SingleDuration(int32 Count, bool bEmpty = false) { return SingleLoopBegin(bEmpty) + SingleStep * Count + SingleCloseTail; }
    inline constexpr float SingleSeatTime(int32 Index, bool bEmpty) { return SingleLoopBegin(bEmpty) + SingleStep * Index + SingleSeat; }
    inline FString SingleAnimationPath(int32 StartLive, int32 Count)
    {
        return FString::Printf(TEXT("/Game/Weapons/DanWesson715/LeftRecovery20260914/Animations/A_DW715_single_%d_%d.A_DW715_single_%d_%d"), StartLive, Count, StartLive, Count);
    }
    inline FString SpeedAnimationPath()
    {
        // The installed speedloader always empties the cylinder before loading.
        return TEXT("/Game/Weapons/DanWesson715/LeftRecovery20260914/LoaderStow/A_DW715_speed_0.A_DW715_speed_0");
    }
    inline FString AnimationPath(const TCHAR* Clip)
    {
        if (FCString::Strcmp(Clip, TEXT("reload")) == 0) return SpeedAnimationPath();
        if (FCString::Strcmp(Clip, TEXT("reload_empty")) == 0) return SpeedAnimationPath();
        return FString::Printf(TEXT("/Game/Weapons/DanWesson715/Upgrade20260914/Animations/A_DW715_%s.A_DW715_%s"), Clip, Clip);
    }
    inline FString SoundPath(const FString& Cue)
    {
        if (Cue == TEXT("Fire"))
            return TEXT("/Game/Weapons/DanWesson715/RecordedAudio20260914/S_DW715_Fire_Recorded.S_DW715_Fire_Recorded");
        return TEXT("/Game/Weapons/DanWesson715/Integrated20260913/Audio/S_DW715_") + Cue;
    }
}
