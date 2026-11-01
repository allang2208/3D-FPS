#pragma once
#include "CoreMinimal.h"

class AActor;
class UStaticMeshComponent;
class USkeletalMeshComponent;
namespace M24Attachments
{
inline constexpr const TCHAR* Scope=TEXT("m24_custom_scope_6x");
inline constexpr const TCHAR* IronSight=TEXT("m24_palma_iron");
inline constexpr const TCHAR* Suppressor=TEXT("m24_factory_suppressor");
inline constexpr const TCHAR* CheekRest=TEXT("m24_cheekrest");
inline constexpr const TCHAR* ExtendedMagazine=TEXT("m24_extended_mag_10");
inline constexpr const TCHAR* CarbonBolt=TEXT("m24_carbon_light_bolt");
inline constexpr const TCHAR* AdvancedAction=TEXT("m24_advanced_action");
inline bool RearGripUnlocked(const TMap<FString,FString>& Parts)
{return Parts.FindRef(TEXT("body"))==AdvancedAction;}
void FactoryChassisSections(USkeletalMeshComponent* Host,bool Visible);
inline constexpr const TCHAR* CarbonBoltMaterial=TEXT("/Game/Weapons/M24/CarbonBolt20261029/Materials/MI_M24_CarbonBolt");
void SetBoltMaterial(USkeletalMeshComponent* Host,const FString& Key);
inline constexpr float IronEyeDistanceCM=12.f;
inline FString OpticPart(const FString& Variant)
{return Variant.IsEmpty()||Variant==TEXT("none")||Variant==TEXT("false")?FString(IronSight):Variant;}
bool IsSharedOptic(const FString& Key);
bool IsRearGrip(const FString& Key);
bool IsOptic(const FString& Key);
FString MovingOpticPart(const FString& Key);
FString MeshPath(const FString& Key);
// Preserve the accepted receiver/arms depth while aligning the installed ocular.
float EyeDistanceCM(const FString& Key,float FactoryEyeDistanceCM);
bool IsPart(const FString& Key);
void FactoryMagazineSections(USkeletalMeshComponent* Host,bool Visible);
// Static exports and the installed skeleton use different root/unit conventions.
// Register the actual sight pair and magazine marker, then attach in root space.
FTransform Mount(const USkeletalMeshComponent* Host);
FVector BareMuzzle(const USkeletalMeshComponent* Host);
UStaticMeshComponent* Configure(AActor* Owner,USkeletalMeshComponent* Host,
    UStaticMeshComponent* Existing,const FString& Key,bool Enabled);
}
