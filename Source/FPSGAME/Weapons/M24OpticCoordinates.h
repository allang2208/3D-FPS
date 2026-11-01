#pragma once
#include "CoreMinimal.h"

// SourceAssets/M24CommonOptics20261028/fit_recipe.json; centimetres, +X optic to -Y M24.
namespace M24OpticCoordinates
{
inline FTransform InSource(const FString& Key)
{
    FVector Position=FVector::ZeroVector;
    if(Key==TEXT("holographic"))Position=FVector(0.0000000f,-20.9573870f,14.2900465f);
    if(Key==TEXT("panoramic_red_dot"))Position=FVector(0.0000000f,-19.5708895f,14.2329880f);
    if(Key==TEXT("prism_scope_2x"))Position=FVector(0.0000000f,-19.5708895f,14.3579880f);
    if(Key==TEXT("lpvo_1_6x"))Position=FVector(0.0000000f,-23.9708895f,14.3579880f);
    if(Key==TEXT("eoth_holographic"))Position=FVector(0.0000000f,-16.8847630f,14.3455880f);
    if(Key==TEXT("kv_scope_4x"))Position=FVector(0.0000000f,-19.4199690f,14.4764880f);
    if(Key==TEXT("thermal_scope"))Position=FVector(0.0000000f,-19.5708895f,14.4829880f);
    return FTransform(FQuat(FVector::UpVector,-PI*.5f),Position);
}
inline float OcularForwardCM(const FString& Key)
{
    if(Key==TEXT("holographic"))return 20.4855275f;
    if(Key==TEXT("panoramic_red_dot"))return 21.8778120f;
    if(Key==TEXT("prism_scope_2x"))return 13.6028120f;
    if(Key==TEXT("lpvo_1_6x"))return 12.0028120f;
    if(Key==TEXT("eoth_holographic"))return 15.7866835f;
    if(Key==TEXT("kv_scope_4x"))return 6.5523724f;
    if(Key==TEXT("thermal_scope"))return 14.2528120f;
    return 0.f;
}
}
