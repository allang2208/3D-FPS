#pragma once
#include "RuneSwordUppercutMotion.h"

// A normal third combo: reuse the uppercut pose path, not its skill formula.
namespace RuneSwordRisingDragon
{
    inline constexpr float WindupScale=.5f;
    inline constexpr float WindupEnd=RuneSwordUppercutMotion::ReleaseStart*WindupScale;
    inline constexpr float AttackSeconds=WindupEnd+RuneSwordUppercutMotion::End-RuneSwordUppercutMotion::ReleaseStart;
    inline constexpr float LaunchForwardCM=180.f,LaunchUpCM=420.f,ControlSeconds=.75f;

    inline float PlaybackTime(float SourceTime)
    {
        return SourceTime<=RuneSwordUppercutMotion::ReleaseStart?SourceTime*WindupScale:
            WindupEnd+SourceTime-RuneSwordUppercutMotion::ReleaseStart;
    }
    inline float SourceTime(float PlaybackTime)
    {
        return PlaybackTime<=WindupEnd?PlaybackTime/WindupScale:
            RuneSwordUppercutMotion::ReleaseStart+PlaybackTime-WindupEnd;
    }
}
