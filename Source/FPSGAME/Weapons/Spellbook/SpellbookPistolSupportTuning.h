#pragma once
#include "CoreMinimal.h"

// V4 author controls: SourceAssets/PistolBookPoseV4_20261020/pose_controls.json.
// Camera-relative centimetres, first person only. Preserve native hand contacts.
namespace SpellbookPistolSupport
{
inline const FVector HipFraming(4.f,8.f,9.f);
inline const FVector AimFraming(0.f,0.f,0.f);
inline const FVector HipWrist(32.f,-17.f,-18.f);
inline const FVector WristFromGunHand(8.f,9.f,-8.f);
inline const FVector HipShoulder(-10.f,-22.f,-24.f);
inline const FVector AimShoulder(-9.f,-23.f,-24.f);
inline const FVector HipPole(16.f,-34.f,-32.f);
inline const FVector AimPoleFromWrist(-6.f,-35.f,7.f);
inline const FVector RightShoulder(-10.f,22.f,-24.f);
inline const FVector RightHipPole(8.f,36.f,-32.f);
inline const FVector RightAimPole(8.f,25.f,-48.f);
inline const FVector HipFingerDirection(.30f,.82f,.25f);
inline const FVector HipDorsalDirection(-1.f,.1f,.1f);
inline const FVector AimFingerDirection(.24f,1.f,-.05f);
inline const FVector AimDorsalDirection(-.6f,.05f,-.8f);
// User's follow-up: rotate the left hand/book down around the forearm, with
// exactly the same shoulder, elbow, wrist position and right arm as the preview.
inline constexpr float AimHandRollDegrees=65.f;
inline constexpr float BlendSeconds=.24f;
inline constexpr float AimInSeconds=.32f,AimOutSeconds=.28f;
inline constexpr float ContactReturnSeconds=.18f;
inline constexpr float TransferForwardCm=4.f,TransferLiftCm=5.f;
inline float Ease(float X) {return X*X*(3.f-2.f*X);}
}
