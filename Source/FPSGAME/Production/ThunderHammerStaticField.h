#pragma once
#include "CoreMinimal.h"
struct FColdSteelItem;
struct FColdSteelSkillShot;
class AActor;

namespace ThunderHammerStaticField
{
    inline constexpr const TCHAR* Grip=TEXT("static_field_grip");
    inline constexpr float RadiusCM=3000.f,CallRadiusCM=1000.f,PulseSeconds=3.f;
    bool Installed(const FColdSteelItem* Item);
    void Commit(FColdSteelSkillShot& Shot,const FColdSteelItem* Item);
    void Released(AActor* Source,const FColdSteelSkillShot& Shot,bool ReplacedHeavy);
    void Pulse(AActor* Source,const FVector& Center,const FColdSteelSkillShot& Shot,float Radius,int32 Stacks);
}
