#pragma once
#include "GameFramework/Pawn.h"
#include "Perception/AISense_Hearing.h"
#include "SniperSuppressorAssets.h"

namespace WeaponShotNoise
{
inline bool PistolSuppressed(const FString& Definition, const FString& Muzzle)
{
    return Muzzle == TEXT("tactical_suppressor") || Muzzle == TEXT("true") || Muzzle == TEXT("multi_caliber_suppressor")
        || (Definition == TEXT("ue_rsh12") && Muzzle == TEXT("rsh12_heavy_suppressor"));
}
inline void Report(APawn* Shooter,const FString& Definition,const FString& Muzzle,bool Suppressed)
{
    if(SniperSuppressorAssets::Supports(Definition)&&Muzzle==SniperSuppressorAssets::Part)return;
    UAISense_Hearing::ReportNoiseEvent(Shooter,Shooter->GetActorLocation(),1.f,Shooter,Suppressed?1000.f:3600.f,
        Suppressed?TEXT("GunshotSuppressed"):TEXT("Gunshot"));
}
}
