#pragma once
#include "CoreMinimal.h"
struct FColdSteelItem;

namespace ColdSteelWoodQuality
{
    enum class EChannel : uint8 { None, Physical, MagicAttack };
    EChannel Channel(const FColdSteelItem& Item);
    double FromScore(double Score);
    bool Read(const FColdSteelItem& Item,double& Score);
    double Multiplier(const FColdSteelItem& Item,EChannel Channel);
    FString StatLabel(const FColdSteelItem& Item);
    bool Apply(FColdSteelItem& Item,double Score);
    void PreserveAuthoritative(TArray<FColdSteelItem>& Incoming,const TArray<FColdSteelItem>& Authority);
}
