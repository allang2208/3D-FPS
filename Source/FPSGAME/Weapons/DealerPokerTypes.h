#pragma once
#include "CoreMinimal.h"

/** Card ID: suit * 13 + rank - 2; suits clubs, diamonds, hearts, spades; ace = 14. */
namespace DealerPoker
{
    inline constexpr int32 HoleCardCount=2;
    inline constexpr int32 BoardCardCount=5;
    inline constexpr int32 HoldemCardCount=HoleCardCount+BoardCardCount;
    enum class EHand : uint8 { HighCard, Pair, TwoPair, Three, Straight, Flush, FullHouse, Four, StraightFlush };
    struct FShot
    {
        bool Enabled=false;
        float Multipliers[9]={1.f,1.5f,1.75f,2.f,2.5f,3.f,4.f,5.f,7.f};
    };
    /** Draw without replacement; critical windows must be completable within HandSize. */
    FPSGAME_API uint8 Draw(const TArray<uint8>& Cards,bool bCritical,int32 HandSize=BoardCardCount);
    /** Highest five-card category from five to seven cards. */
    FPSGAME_API EHand Evaluate(const TArray<uint8>& Cards);
    /** Also return the actual best five cards, with deterministic rank/kicker selection. */
    FPSGAME_API EHand EvaluateBest(const TArray<uint8>& Cards,TArray<uint8>& BestFive);
}
