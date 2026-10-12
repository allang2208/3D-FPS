#pragma once

// Native 60 Hz authoring: Super90LoaderRelease20261012/author_release.py.
// The loader feed retains its R25 clock; these values describe source frames.
namespace Super90ReleaseTiming
{
inline constexpr float Withdrawal=125.f/60.f;
inline constexpr float Press=160.f/60.f;
inline constexpr float Closed=174.f/60.f;
inline constexpr float End=224.f/60.f;
inline constexpr float CycleClosed=30.f/60.f;
}
