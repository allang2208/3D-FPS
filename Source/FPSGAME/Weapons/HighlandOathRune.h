#pragma once
#include "GunsmithSystem.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "HighlandOathRune.generated.h"

/** Replicated presentation only. Combat receipts remain on the authority. */
USTRUCT()
struct FHighlandOathPresentation
{
    GENERATED_BODY()
    UPROPERTY() FString Weapon;
    UPROPERTY() uint8 Phase=0; // 0 idle, 1 charge, 2 precise release
    UPROPERTY() double FullAt=0.;
    UPROPERTY() double ReleaseAt=0.;
    UPROPERTY() float Duration=1.f;
};

namespace HighlandOathRune
{
    inline constexpr const TCHAR* Id=TEXT("highland_oath_rune");
    inline constexpr const TCHAR* Root=TEXT("/Game/Weapons/HighlandClaymore20260922/OathRune20261106/");
    inline constexpr double Window=.35;
    inline constexpr float TrailSeconds=.82f;
    inline constexpr float HeavyPhysical=1.15f,JudgmentPhysical=1.35f,JudgmentToughness=1.5f,Drain=.8f,Refund=.25f;
    inline bool Installed(const UGunsmithSystem* G,const FColdSteelItem* Item)
    {return G&&Item&&Item->Definition==TEXT("ue_highland_claymore")&&G->Installed(*Item).FindRef(TEXT("blade_2"))==Id;}
    inline bool InWindow(double Release,double Full){return Release>=Full&&Release<Full+Window;}
}
