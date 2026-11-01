#pragma once
#include "CoreMinimal.h"
struct FColdSteelItem;
struct FColdSteelSkillShot;
class AWarhammerShockwave;

namespace ThunderHammerZhenTing
{
    inline constexpr const TCHAR* Pommel=TEXT("zhen_ting_pommel");
    bool Installed(const FColdSteelItem* Item);
    void Commit(FColdSteelSkillShot& Shot,const FColdSteelItem* Item,const FVector& Forward);
    void ContinueLightning(AWarhammerShockwave* Origin,const FColdSteelSkillShot& Shot,float Radius,float Magic,bool ThunderCall);
}
