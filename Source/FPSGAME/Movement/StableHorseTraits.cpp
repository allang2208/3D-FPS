#include "StableHorseTraits.h"
#include "StableHorseAffixes.h"
#include "Math/RandomStream.h"

namespace
{
constexpr const TCHAR* Names[]={
    TEXT("豆包"), TEXT("栗子"), TEXT("芝麻"), TEXT("核桃"), TEXT("松果"),
    TEXT("麦芽"), TEXT("可可"), TEXT("糖霜"), TEXT("胡椒"), TEXT("团子"),
    TEXT("阿福"), TEXT("铃铛"), TEXT("布丁"), TEXT("奶酪"), TEXT("小满"),
    TEXT("点点"), TEXT("琥珀"), TEXT("乌云"), TEXT("白露"), TEXT("月牙"),
    TEXT("星野"), TEXT("流萤"), TEXT("晨曦"), TEXT("晚霞"), TEXT("晴川"),
    TEXT("雪团"), TEXT("薄荷"), TEXT("青梅"), TEXT("小麦"), TEXT("枫糖"),
    TEXT("松针"), TEXT("麦穗"), TEXT("苔米"), TEXT("山雀"), TEXT("雨滴"),
    TEXT("踏雪"), TEXT("逐风"), TEXT("飞燕"), TEXT("赤豆"), TEXT("青岚"),
    TEXT("墨点"), TEXT("银杏"), TEXT("花生"), TEXT("小葵"), TEXT("秋栗"),
    TEXT("云帆"), TEXT("河谷"), TEXT("铜铃"), TEXT("桃酥"), TEXT("星尘")
};
static_assert(UE_ARRAY_COUNT(Names)==FStableHorseTraits::NameCount);
// Fixed integer mixer rather than a shared RNG: inserting a roll in the name pool
// cannot advance the stat, growth or R30 coat stream.
uint32 Seed(const FGuid& Id,uint32 Domain)
{
    for(uint32 Word:{Id.A,Id.B,Id.C,Id.D})
    {
        Domain^=Word;
        Domain^=Domain>>16; Domain*=0x7feb352du;
        Domain^=Domain>>15; Domain*=0x846ca68bu;
        Domain^=Domain>>16;
    }
    return Domain;
}
}

int32 FStableHorseTraits::NameIndex(const FGuid& Id,uint8 BirthVersion)
{
    if(!BirthVersion)return Id.D%NameCount;
    return FRandomStream(int32(Seed(Id,0x4e414d45u))).RandRange(0,NameCount-1);
}

const TCHAR* FStableHorseTraits::Name(const FGuid& Id,uint8 BirthVersion)
{
    return Id.IsValid()?Names[NameIndex(Id,BirthVersion)]:TEXT("战马");
}

FStableHorseTraits FStableHorseTraits::Growth(const FGuid& Id)
{
    FRandomStream Rng(int32(Seed(Id,0x47524f57u)));
    auto Roll=[&Rng]{return Rng.RandRange(1,5)/10.f;};
    return {Roll(),Roll(),Roll(),Roll(),Roll(),Roll()};
}

FStableHorseTraits FStableHorseTraits::EffectiveGrowth(const FGuid& Id)
{
    const auto G=Growth(Id);
    const float Mult=StableHorseAffixes::Bonuses(Id).StatAllMultiplier;
    return {G.Strength*Mult,G.Agility*Mult,G.Intelligence*Mult,G.Constitution*Mult,G.Spirit*Mult,G.Luck*Mult};
}

FStableHorseTraits FStableHorseTraits::FromId(const FGuid& Id,uint8 BirthVersion,int32 Level)
{
    if(!Id.IsValid())return {};
    FStableHorseTraits Base;
    if(BirthVersion)
    {
        FRandomStream Rng(int32(Seed(Id,0x42415345u)));
        auto Roll=[&Rng]{return float(Rng.RandRange(6,14));};
        Base={Roll(),Roll(),Roll(),Roll(),Roll(),Roll()};
    }
    else
    {
        auto Roll=[](uint32 Word){return float(6+(Word&0xffffu)%9u);};
        Base={Roll(Id.A),Roll(Id.A>>16),Roll(Id.B),Roll(Id.B>>16),Roll(Id.C),Roll(Id.C>>16)};
    }
    FStableHorseTraits Result=Base;
    if(Level>1)
    {
        const auto G=Growth(Id);
        const int32 Steps=FMath::Min(Level,MaxLevel)-1;
        Result={Base.Strength+Steps*G.Strength,Base.Agility+Steps*G.Agility,Base.Intelligence+Steps*G.Intelligence,
                Base.Constitution+Steps*G.Constitution,Base.Spirit+Steps*G.Spirit,Base.Luck+Steps*G.Luck};
    }
    // 「多面手」: 所有六维属性 +10%，随等级成长同步乘算
    const float Mult=StableHorseAffixes::Bonuses(Id).StatAllMultiplier;
    if(!FMath::IsNearlyEqual(Mult,1.f))
    {
        Result.Strength*=Mult;
        Result.Agility*=Mult;
        Result.Intelligence*=Mult;
        Result.Constitution*=Mult;
        Result.Spirit*=Mult;
        Result.Luck*=Mult;
    }
    return Result;
}

int32 FStableHorseTraits::MarketPrice(const FStableHorseTraits& G) const
{
    // Soul value per point. Price birth ability plus five levels of growth above the minimum.
    auto Value=[](float Base,float Rate,int32 Weight){return Weight*((Base-6.f)+5.f*(Rate-.1f));};
    return 1000+FMath::RoundToInt(Value(Strength,G.Strength,36)+Value(Agility,G.Agility,48)+
        Value(Intelligence,G.Intelligence,18)+Value(Constitution,G.Constitution,42)+
        Value(Spirit,G.Spirit,24)+Value(Luck,G.Luck,12));
}

FString FStableHorseTraits::RatingsText() const
{
    return FString::Printf(TEXT("力量  %.1f      敏捷  %.1f      智力  %.1f\n体质  %.1f      精神  %.1f      幸运  %.1f"),
        Strength,Agility,Intelligence,Constitution,Spirit,Luck);
}
FString FStableHorseTraits::PerformanceText() const
{
    return FString::Printf(TEXT("疾驰  %.1f 米/秒      跃高  %.2f 米\n转向  %.0f°/秒      体力恢复  %.0f%%\n静养回血  %.1f / 秒"),
        CanterSpeed()/100.f,JumpRise()/100.f,88.f*TurnScale(),100.f*RecoveryScale(),HealthLimit()*.025f*HealingScale());
}
