#pragma once
#include "CoreMinimal.h"
#include "Engine/NetSerialization.h"
#include "IceArmorTypes.generated.h"

struct FIceArmorTuning
{
    float PhysicalBase=18,PhysicalPerLevel=2,PhysicalMagic=.2f;
    float MagicBase=5,MagicPerLevel=.5f,MagicMagic=.05f;
    float DurationBase=12,DurationGrowth=12,ManaBase=30,ManaPerLevel=1.2f,Cooldown=32,CooldownReduction=4;
    float RadiusBase=175,RadiusGrowth=75,PulseSeconds=2,ChillSeconds=2.5f,ChillGrowth=1,SlowPerStack=.03f;
    float TrainingSourceInterval=1.f;
    int32 CastExperience=2,MeleeExperience=3,RangedExperience=2,ExperienceCap=36;
};
USTRUCT()
struct FIceArmorCast
{
    GENERATED_BODY()
    UPROPERTY() float PhysicalDefense=0;
    UPROPERTY() float MagicDefense=0;
    UPROPERTY() float Duration=12;
    UPROPERTY() float ManaCost=30;
    UPROPERTY() float Cooldown=32;
    UPROPERTY() float Radius=175;
    UPROPERTY() float PulseSeconds=2;
    UPROPERTY() float ChillSeconds=2.5f;
    UPROPERTY() float SlowPerStack=.03f;
    UPROPERTY() float CastSpeed=1;
    UPROPERTY() float TrainingSourceInterval=1.f;
    UPROPERTY() int32 CastExperience=2;
    UPROPERTY() int32 MeleeExperience=3;
    UPROPERTY() int32 RangedExperience=2;
    UPROPERTY() int32 ExperienceCap=36;
};
USTRUCT()
struct FIceArmorState
{
    GENERATED_BODY()
    UPROPERTY() FIceArmorCast Cast;
    UPROPERTY() uint32 CastId=0;
    UPROPERTY() uint32 Serial=0;
    UPROPERTY() double StartedAt=0;
    UPROPERTY() bool bActive=false;
};

namespace IceArmorAssets
{
inline constexpr const TCHAR* Shells[]={
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Torso_0.SK_IceArmorV6_Torso_0"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Torso_1.SK_IceArmorV6_Torso_1"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Torso_2.SK_IceArmorV6_Torso_2"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Arms_0_0.SK_IceArmorV6_Arms_0_0"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Arms_0_1.SK_IceArmorV6_Arms_0_1"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Arms_0_2.SK_IceArmorV6_Arms_0_2"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Arms_1_0.SK_IceArmorV6_Arms_1_0"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Arms_1_1.SK_IceArmorV6_Arms_1_1"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Arms_1_2.SK_IceArmorV6_Arms_1_2"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Arms_2_0.SK_IceArmorV6_Arms_2_0"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Arms_2_1.SK_IceArmorV6_Arms_2_1"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Arms_2_2.SK_IceArmorV6_Arms_2_2"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Legs_0_0.SK_IceArmorV6_Legs_0_0"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Legs_0_1.SK_IceArmorV6_Legs_0_1"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Legs_0_2.SK_IceArmorV6_Legs_0_2"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Legs_1_0.SK_IceArmorV6_Legs_1_0"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Legs_1_1.SK_IceArmorV6_Legs_1_1"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Legs_1_2.SK_IceArmorV6_Legs_1_2"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Legs_2_0.SK_IceArmorV6_Legs_2_0"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Legs_2_1.SK_IceArmorV6_Legs_2_1"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Legs_2_2.SK_IceArmorV6_Legs_2_2"),
    TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/SK_IceArmorV6_Helmet.SK_IceArmorV6_Helmet")};
inline constexpr int32 ArmShellOffset=3,LegShellOffset=12,HelmetShellIndex=21,WorldPartCount=4;
inline constexpr const TCHAR* Lens=TEXT("/Game/Skills/IceArmor20261017/HelmetV5/SM_IceHelmet_FirstPerson.SM_IceHelmet_FirstPerson");
inline constexpr const TCHAR* Material=TEXT("/Game/Skills/IceArmor20261017/ThirdPersonV6/M_IceArmorV6_World.M_IceArmorV6_World");
inline constexpr const TCHAR* LensMaterial=TEXT("/Game/Skills/IceArmor20261017/HelmetV5/M_IceHelmet_FirstPerson.M_IceHelmet_FirstPerson");
inline constexpr const TCHAR* Chip=TEXT("/Game/Skills/IceArmor20261017/CrystalV2/SM_IceArmor_Chip.SM_IceArmor_Chip");
inline constexpr const TCHAR* ChipMaterial=TEXT("/Game/Skills/IceArmor20261017/CrystalV2/M_IceArmor_Chip.M_IceArmor_Chip");
inline constexpr const TCHAR* Mist=TEXT("/Game/Skills/IceArmor20261017/CrystalV2/NS_IceArmor_Condensation.NS_IceArmor_Condensation");
inline constexpr const TCHAR* CastSound=TEXT("/Game/Skills/IceWall/BlockV1/S_IceWallCast.S_IceWallCast");
}

USTRUCT()
struct FIceArmorImpact
{
    GENERATED_BODY()
    UPROPERTY() uint32 Serial=0;
    UPROPERTY() uint32 CastSerial=0;
    UPROPERTY() double At=0;
    UPROPERTY() FVector_NetQuantizeNormal LocalDirection=FVector::ForwardVector;
};
