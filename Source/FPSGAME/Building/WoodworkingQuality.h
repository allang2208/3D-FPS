#pragma once
#include "CoreMinimal.h"
struct FColdSteelItem;
struct FColdSteelWoodworkingJob;

namespace ColdSteelWoodQuality
{
    enum class EChannel : uint8 { None, Physical, MagicAttack };
    EChannel Channel(const FColdSteelItem& Item);
    constexpr int32 Version=2;
    constexpr double MaxMaterialBonus=.10,MaxSkillBonus=.15;
    double FromScore(double Score); // Legacy curve.
    double SkillBonus(double Score);
    double FromJob(const FColdSteelWoodworkingJob& Job);
    bool UsesMaterials(const FColdSteelItem& Item);
    double MaterialBonus(const FColdSteelItem& Item);
    bool Read(const FColdSteelItem& Item,double& Score);
    double Multiplier(const FColdSteelItem& Item,EChannel Channel);
    FString StatLabel(const FColdSteelItem& Item);
    bool Apply(FColdSteelItem& Item,double Score,double MaterialBonus=0,FName Core=NAME_None,int32 QualityVersion=1);
    bool Apply(FColdSteelItem& Item,const FColdSteelWoodworkingJob& Job);
    void PreserveAuthoritative(TArray<FColdSteelItem>& Incoming,const TArray<FColdSteelItem>& Authority);
}
