#pragma once
#include "CoreMinimal.h"
#include "Super90ForegripAssets.h"
#include "M870OpticAssets.h"
#include "Saiga12KSpecialStockAssets.h"

class AActor;
class UStaticMeshComponent;
class USkeletalMeshComponent;
namespace Saiga12KAttachments
{
inline FString MeshPath(const FString& Key)
{
 if(Key==Saiga12KSpecialStockAssets::Part)return Saiga12KSpecialStockAssets::MeshPath;
 return TEXT("/Game/Weapons/Saiga12K/Detail20261018/Attachments/SM_Saiga12K_")+Key;
}
// Private inspect layers retain the installed grip's contact and route the
// complete support arm outside the handguard while the gun rolls over.
inline FString ProfilePath(FName Family)
{ return TEXT("/Game/Weapons/Saiga12K/InspectClearance20261018/Profiles/DA_")+Family.ToString(); }
inline FString ForegripFamily(const FString& Variant){return Super90ForegripAssets::Family(Variant);}
inline bool SupportsOptic(const FString& Variant){return M870OpticAssets::Supports(Variant);}
inline bool SupportsStock(const FString& V)
{ return V==Saiga12KSpecialStockAssets::Part||V==TEXT("skeleton")||V==TEXT("core_stock")||V==TEXT("qr_performance")||V==TEXT("tactical_telescopic")||V==TEXT("legendary_adjustable_tactical_stock"); }
inline bool SupportsRearGrip(const FString& V)
{ return V==TEXT("phantom_reargrip")||V==TEXT("stable_antislip_reargrip")||V==TEXT("balanced_reargrip"); }
inline bool SupportsMuzzle(const FString& V)
{ return V==TEXT("shotgun_choke")||V==TEXT("shotgun_birdcage_flash_hider")||V==TEXT("shotgun_suppressor")||V==TEXT("shotgun_duckbill"); }
inline FTransform RootCentimetres(){return FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f));}
// The fitted receiver rail has a 19.28 mm wing, matching the shared saddles.
inline FTransform RailMount(){return FTransform(FRotator(0,90,0),FVector(.0008,.06,.092),FVector(.01f));}
inline FTransform OpticMount(const FString& V)
{
 FVector Offset(0,0,.15f);
 if(V==TEXT("holographic"))Offset.X=1.386495f;
 else if(V==TEXT("eoth_holographic"))Offset=FVector(-.315245f,0,.55f);
 else if(V==TEXT("lpvo_1_6x"))Offset.X=1.4f;
 else if(V==TEXT("thermal_scope"))Offset.Z=.35f;
 return FTransform(Offset)*RailMount();
}
UStaticMeshComponent* Configure(AActor* Owner,USkeletalMeshComponent* Host,UStaticMeshComponent* Existing,
 const FString& Key,bool Enabled,const FTransform& Mount=RootCentimetres());
void FactorySection(USkeletalMeshComponent* Host,FName Slot,bool Visible);
}
