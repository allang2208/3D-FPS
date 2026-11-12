#pragma once
#include "CoreMinimal.h"
#include "M249WeaponAssets.h"
#include "LMGStabilityGrip.h"
class AActor;
class UStaticMeshComponent;
namespace M249Attachments
{
inline FString Key(const FString& Variant)
{
    if(Variant==TEXT("true"))return TEXT("suppressor");
    if(Variant==TEXT("prism_handstop"))return TEXT("prism");
    FString Result=Variant;Result.RemoveFromEnd(TEXT("_foregrip"));return Result;
}
inline bool IsStock(const FString& Key)
{return Key==TEXT("skeleton")||Key==TEXT("core_stock")||Key==TEXT("qr_performance")||Key==TEXT("tactical_telescopic")||Key==TEXT("legendary_adjustable_tactical_stock");}
inline bool IsRearGrip(const FString& Key)
{return Key==TEXT("phantom_reargrip")||Key==TEXT("stable_antislip_reargrip")||Key==TEXT("balanced_reargrip");}
inline bool IsForegrip(const FString& Key)
{return Key==TEXT("vertical")||Key==TEXT("tactical_vertical")||Key==TEXT("canted")||Key==TEXT("angled")||Key==TEXT("prism")||Key==TEXT("lmg_stability");}
inline bool IsMuzzle(const FString& Key)
{return Key==TEXT("suppressor")||Key==TEXT("tactical_suppressor")||Key==TEXT("brake")||Key==TEXT("titanium_brake")||Key==TEXT("multi_caliber_suppressor");}
inline bool Supports(const FString& Slot,const FString& Variant)
{const auto K=Key(Variant);return Slot==TEXT("stock")?IsStock(K):Slot==TEXT("reargrip")?IsRearGrip(K):Slot==TEXT("underbarrel")?IsForegrip(K):Slot==TEXT("muzzle")&&IsMuzzle(K);}
inline FString MeshPath(const FString& Variant)
{return Variant==LMGStabilityGrip::Id?LMGStabilityGrip::MeshPath(M249WeaponAssets::Definition):TEXT("/Game/Weapons/M249/CommonParts20261108/Meshes/SM_M249_")+Key(Variant);}
inline FString ProfilePath(FName Family)
{return Family==TEXT("handguard")?FString(LMGStabilityGrip::HandguardProfile):Family==TEXT("base")?FString(TEXT("/Game/Weapons/M249/Bipod/DA_M249_SupportGrip")):TEXT("/Game/Weapons/M249/CommonParts20261108/Profiles/DA_M249_")+Family.ToString();}
inline FString ForegripFamily(const FString& Variant)
{const auto K=Key(Variant);return K==TEXT("lmg_stability")?FString(TEXT("base")):K==TEXT("tactical_vertical")?FString(TEXT("vertical")):IsForegrip(K)?K:FString(TEXT("handguard"));}
inline constexpr const TCHAR* SuppressedSound=TEXT("/Game/Weapons/M249/CommonParts20261108/Audio/S_M249_Suppressed");
void FactorySection(USkeletalMeshComponent* Host,FName Slot,bool Visible);
UStaticMeshComponent* Configure(AActor* Owner,USkeletalMeshComponent* Host,UStaticMeshComponent* Existing,const FString& Variant,bool Enabled);
}
