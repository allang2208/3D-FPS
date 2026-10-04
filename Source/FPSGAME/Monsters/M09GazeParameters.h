#pragma once
// Seconds from the single M09 attack clock; UE distances are centimetres.
namespace M09Gaze
{
inline constexpr float Lock=.90f;
inline constexpr float FirstPulse=1.25f;
inline constexpr float PulseGap=.20f;
inline constexpr int PulseCount=3;
inline constexpr float FireEnd=1.85f;
inline constexpr float Duration=3.f;
inline constexpr float Range=1400.f;
// Horizontal separation: a high ceiling must not allow point-blank casting.
inline constexpr float MinimumRange=200.f;
inline constexpr float Radius=10.f;
inline constexpr float DamageMultiplier=.35f;
inline constexpr float Cooldown=7.f;
inline constexpr int Eyes=5;
inline constexpr int SegmentsPerEye=4;
}
