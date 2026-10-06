#pragma once
#include "CoreMinimal.h"

// RSH-exclusive exteriors share the original native muzzle registration.
namespace RSH12MuzzleAssets
{
inline constexpr const TCHAR* Part = TEXT("rsh12_heavy_suppressor");
inline constexpr const TCHAR* MeshPath = TEXT("/Game/Weapons/RSH12/CubeSuppressor20261004/SM_RSH12_CubeSuppressor_Long");
inline constexpr float LengthCM = 18.555000f;
inline constexpr const TCHAR* BrakePart = TEXT("rsh12_large_caliber_brake");
inline constexpr const TCHAR* BrakeMeshPath = TEXT("/Game/Weapons/RSH12/MuzzleBrake20261005/SM_RSH12_MuzzleBrake");
inline constexpr float BrakeLengthCM = 7.555000f;
inline bool Supports(const FString& Variant)
{
    return Variant == Part || Variant == BrakePart;
}
inline const TCHAR* FittedMeshPath(const FString& Variant)
{
    return Variant == BrakePart ? BrakeMeshPath : MeshPath;
}
inline float TipLengthCM(const FString& Variant)
{
    return Variant == BrakePart ? BrakeLengthCM : LengthCM;
}
inline FTransform Mount()
{
    return FTransform(FRotationMatrix::MakeFromXZ(FVector(0.0000000000f,0.9980492592f,-0.0624317825f), FVector(0.0000000000f,0.0624317825f,0.9980492592f)).ToQuat(), FVector(-0.0005591564f,0.2806221929f,0.0070725177f), FVector(.01f));
}
}
