#include "ColdSteelStatusModel.h"
int32 UColdSteelStatusModel::Attribute(FName Key) const { const int32* Value = Attributes.Find(Key); return (Value ? *Value : 0)+(Key==TEXT("wis")?RifleEffect().Wisdom:0); }
bool UColdSteelStatusModel::AllocateAttribute(FName Key)
{
    SyncRuntime(); auto Next=Snapshot(); int32* Value=Next.Attributes.Find(Key);
    if (!Value || Next.Points <= 0 || *Value >= 1000000) return false;
    ++*Value; --Next.Points; return CommitState(Next);
}
void UColdSteelStatusModel::GrantAttributePoints(int32 Amount)
{
    if (Amount <= 0) return;
    SyncRuntime(); auto Next=Snapshot(); Next.Points=static_cast<int32>(FMath::Min<int64>(int64(Next.Points)+Amount,1000000)); CommitState(Next);
}
float UColdSteelStatusModel::Derived(FName Key) const
{
    const float S = Attribute(TEXT("str")), D = Attribute(TEXT("dex")), I = Attribute(TEXT("intt"));
    const float C = Attribute(TEXT("con")), W = Attribute(TEXT("wis"));
    if (Key == TEXT("atk")) return FMath::RoundToInt(10 + S * .05f + D * .1f);
    if (Key == TEXT("def")) return FMath::FloorToInt(C * 1.2f + S * .3f);
    if (Key == TEXT("matk")) return FMath::FloorToInt(I * 1.5f + W * .5f);
    if (Key == TEXT("mdef")) return FMath::FloorToInt(W * 1.2f + I * .3f);
    if (Key == TEXT("critRes")) return C;
    if (Key == TEXT("aspd")) return 1 + D * .02f;
    if (Key == TEXT("staminaRegen")) return 1 + D * .01f;
    if (Key == TEXT("maxHp")) return 100 + C * 10;
    if (Key == TEXT("maxMp")) return 100 + W * 10 + I * 5;
    return 0;
}
