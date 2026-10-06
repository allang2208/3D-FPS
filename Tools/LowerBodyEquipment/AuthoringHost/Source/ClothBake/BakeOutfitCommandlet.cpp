#include "BakeOutfitCommandlet.h"
#include "Modules/ModuleManager.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "UObject/SavePackage.h"
#include "ChaosClothAsset/ClothAssetBase.h"
#include "Engine/SkeletalMesh.h"
#include "AssetCompilingManager.h"
IMPLEMENT_PRIMARY_GAME_MODULE(FDefaultGameModuleImpl, ClothBake, "ClothBake");
UBakeOutfitCommandlet::UBakeOutfitCommandlet() { IsClient=false; IsServer=false; IsEditor=true; LogToConsole=true; }
int32 UBakeOutfitCommandlet::Main(const FString& Params) {
 FPackageName::RegisterMountPoint(TEXT("/Game/Outfits/"),TEXT("D:/FPS3D/FPSGAME/Content/Outfits/"));
 FModuleManager::LoadModuleChecked<IModuleInterface>(TEXT("ChaosClothAssetTools"));
 TArray<FString> Sources={TEXT("/Game/Outfits/Jeans/Jeans/ClothAssets/CA_jeans_m_med_nrw"),TEXT("/Game/Outfits/Cargopants/Cargopants/ClothAssets/CA_Cargopants_m_med_nrw"),TEXT("/Game/Outfits/CasualSneakers/CasualSneakers/ClothAssets/CA_casualsneakers_m_med_nrw")};
 TArray<FString> Names={TEXT("SK_Jeans_Donor"),TEXT("SK_Cargo_Donor"),TEXT("SK_Sneakers_Donor")};
 FString Source,Name,Destination=TEXT("/Game/Characters/ModularOutfit20260924/LowerBodyEquipment20261003/Donors");
 if(FParse::Value(*Params,TEXT("Source="),Source)) {
  if(!FParse::Value(*Params,TEXT("Name="),Name))return 4;
  Sources={Source};Names={Name};
  FParse::Value(*Params,TEXT("Destination="),Destination);
 }
 for(int32 I=0;I<Sources.Num();++I) {
  const UChaosClothAssetBase* Cloth=LoadObject<UChaosClothAssetBase>(nullptr,*Sources[I]);
  if(!Cloth) { UE_LOG(LogTemp,Error,TEXT("Cannot load %s"),*Sources[I]); return 1; }
  const FString Path=Destination+TEXT("/")+Names[I];
  UPackage* Package=CreatePackage(*Path);
  USkeletalMesh* Mesh=NewObject<USkeletalMesh>(Package,*Names[I],RF_Public|RF_Standalone);
  if(!Cloth->ExportToSkeletalMesh(*Mesh)) return 2;
  FAssetCompilingManager::Get().FinishAllCompilation();
  FSavePackageArgs Save; Save.TopLevelFlags=RF_Public|RF_Standalone; Save.SaveFlags=SAVE_NoError;
  const FString File=FPackageName::LongPackageNameToFilename(Path,FPackageName::GetAssetPackageExtension());
  if(!UPackage::SavePackage(Package,Mesh,*File,Save)) return 3;
  UE_LOG(LogTemp,Display,TEXT("CLOTH_BAKED %s"),*File);
 }
 return 0;
}
