#pragma once
#include "CoreMinimal.h"
struct FColdSteelItem;
struct FColdSteelSkillShot;
class UColdSteelStatusModel;
class AActor;

namespace ThunderHammerCoil
{
    inline constexpr const TCHAR* Grip=TEXT("coil_grip");
    inline constexpr float RadiusCM=3000.f,CallRadiusCM=1000.f,PulseSeconds=6.f;
    bool Installed(const FColdSteelItem* Item);
    void Commit(FColdSteelSkillShot& Shot,const FColdSteelItem* Item,const UColdSteelStatusModel* Profile);
    void Released(AActor* Source,const FColdSteelSkillShot& Shot,bool ReplacedHeavy);
    void Discharge(AActor* Source,const FVector& Center,const FColdSteelSkillShot& Shot,float Radius,int32 Bolts);
}
