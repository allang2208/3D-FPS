#include "DealerPokerTypes.h"
#include <cstdlib>

namespace DealerPoker::Detail
{
    constexpr uint64 DeckMask=(uint64(1)<<52)-1;
    constexpr uint16 RankBit(int32 Rank){return uint16(1u<<(Rank-2));}

    struct FWindows{uint64 Masks[40]={};};
    constexpr FWindows MakeWindows()
    {
        FWindows Result;
        for(int32 Suit=0;Suit<4;++Suit)for(int32 Start=1;Start<=10;++Start)
        {
            for(int32 Step=0;Step<5;++Step)
            {
                const int32 Rank=(Start==1&&Step==0)?14:Start+Step;
                Result.Masks[Suit*10+Start-1]|=uint64(1)<<(Suit*13+Rank-2);
            }
        }
        return Result;
    }
    constexpr FWindows StraightFlushWindows=MakeWindows();

    int32 UniformIndex(int32 Count)
    {
        // Reject the short remainder bucket instead of rounding/scaling a random float.
        // FMath::Rand uses rand(), so its inclusive range is exactly RAND_MAX.
        constexpr uint32 Range=uint32(RAND_MAX)+1u;
        const uint32 Limit=Range-Range%uint32(Count);
        uint32 Value;
        do{Value=uint32(FMath::Rand());}while(Value>=Limit);
        return int32(Value%uint32(Count));
    }

    int32 StraightHigh(uint16 Ranks)
    {
        for(int32 High=14;High>=6;--High)
        {
            const uint16 Window=uint16(0x1fu<<(High-6));
            if((Ranks&Window)==Window)return High;
        }
        constexpr uint16 Wheel=RankBit(14)|RankBit(2)|RankBit(3)|RankBit(4)|RankBit(5);
        return (Ranks&Wheel)==Wheel?5:0;
    }

    EHand ChooseBest(const TArray<uint8>& Cards,TArray<uint8>* BestFive)
    {
        if(BestFive)BestFive->Reset(BoardCardCount);
        if(Cards.Num()<BoardCardCount||Cards.Num()>HoldemCardCount)return EHand::HighCard;
        uint8 Counts[15]={};
        uint16 Ranks=0,SuitRanks[4]={};
        uint64 Dealt=0;
        for(uint8 Card:Cards)
        {
            const int32 Rank=Card%13+2;
            ++Counts[Rank];Ranks|=RankBit(Rank);SuitRanks[Card/13]|=RankBit(Rank);
            Dealt|=uint64(1)<<Card;
        }
        const auto HighestGroup=[&](int32 Minimum,int32 Excluded=0)
        {
            for(int32 Rank=14;Rank>=2;--Rank)if(Rank!=Excluded&&Counts[Rank]>=Minimum)return Rank;
            return 0;
        };
        const auto AppendRank=[&](int32 Rank,int32 Count,int32 OnlySuit=-1)
        {
            if(!BestFive)return;
            for(int32 Suit=0;Suit<4&&Count>0;++Suit)
            {
                const uint8 Card=uint8(Suit*13+Rank-2);
                if((OnlySuit<0||Suit==OnlySuit)&&(Dealt&(uint64(1)<<Card)))
                {BestFive->Add(Card);--Count;}
            }
        };
        const auto AppendTop=[&](uint16 Mask,int32 Count,int32 OnlySuit=-1)
        {
            if(!BestFive)return;
            for(int32 Rank=14;Rank>=2&&Count>0;--Rank)if(Mask&RankBit(Rank))
            {AppendRank(Rank,1,OnlySuit);--Count;}
        };
        const auto AppendStraight=[&](int32 High,int32 OnlySuit=-1)
        {
            if(BestFive)for(int32 Step=0;Step<5;++Step)
            {const int32 Rank=High-Step;AppendRank(Rank==1?14:Rank,1,OnlySuit);}
        };

        int32 FlushSuit=-1;
        for(int32 Suit=0;Suit<4;++Suit)if(FMath::CountBits(uint32(SuitRanks[Suit]))>=5)
        {
            FlushSuit=Suit;
            if(const int32 High=StraightHigh(SuitRanks[Suit]);High>0)
            {AppendStraight(High,Suit);return EHand::StraightFlush;}
        }
        if(const int32 Four=HighestGroup(4);Four>0)
        {AppendRank(Four,4);AppendTop(uint16(Ranks&~RankBit(Four)),1);return EHand::Four;}
        const int32 Three=HighestGroup(3);
        if(Three>0)if(const int32 Pair=HighestGroup(2,Three);Pair>0)
        {AppendRank(Three,3);AppendRank(Pair,2);return EHand::FullHouse;}
        if(FlushSuit>=0)
        {AppendTop(SuitRanks[FlushSuit],5,FlushSuit);return EHand::Flush;}
        if(const int32 High=StraightHigh(Ranks);High>0)
        {AppendStraight(High);return EHand::Straight;}
        if(Three>0)
        {AppendRank(Three,3);AppendTop(uint16(Ranks&~RankBit(Three)),2);return EHand::Three;}
        if(const int32 Pair=HighestGroup(2);Pair>0)
        {
            AppendRank(Pair,2);
            if(const int32 SecondPair=HighestGroup(2,Pair);SecondPair>0)
            {
                AppendRank(SecondPair,2);AppendTop(uint16(Ranks&~(RankBit(Pair)|RankBit(SecondPair))),1);
                return EHand::TwoPair;
            }
            AppendTop(uint16(Ranks&~RankBit(Pair)),3);return EHand::Pair;
        }
        AppendTop(Ranks,5);return EHand::HighCard;
    }
}

uint8 DealerPoker::Draw(const TArray<uint8>& Cards,bool bCritical,int32 HandSize)
{
    uint64 Dealt=0;
    for(uint8 Card:Cards)Dealt|=uint64(1)<<Card;
    uint64 Candidates=0;
    if(bCritical)
    {
        const int32 RemainingSlots=HandSize-Cards.Num();
        for(uint64 Window:Detail::StraightFlushWindows.Masks)
        {
            const uint64 Missing=Window&~Dealt;
            // In seven-card Hold'em, two dealt cards may remain outside the winning five.
            // Keep all cards; prefer only windows whose missing cards fit the remaining slots.
            if(FMath::CountBits64(Missing)<=RemainingSlots)Candidates|=Missing;
        }
    }
    if(Candidates==0)Candidates=Detail::DeckMask&~Dealt;
    int32 Index=Detail::UniformIndex(FMath::CountBits64(Candidates));
    while(Index-- >0)Candidates&=Candidates-1;
    return uint8(FMath::CountTrailingZeros64(Candidates));
}

DealerPoker::EHand DealerPoker::Evaluate(const TArray<uint8>& Cards)
{
    return Detail::ChooseBest(Cards,nullptr);
}

DealerPoker::EHand DealerPoker::EvaluateBest(const TArray<uint8>& Cards,TArray<uint8>& BestFive)
{
    return Detail::ChooseBest(Cards,&BestFive);
}
