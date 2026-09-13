#include "ExportProductionIconsCommandlet.h"
#if WITH_EDITOR
#include "Engine/Texture2D.h"
#include "Exporters/Exporter.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "Misc/ObjectThumbnail.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "ObjectTools.h"
#endif

int32 UExportProductionIconsCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    const FString Folder=FPaths::ProjectContentDir()/TEXT("ColdSteelData/ProductionTools");
    IFileManager::Get().MakeDirectory(*Folder,true);
    const TCHAR* Textures[]={TEXT("Hatchet"),TEXT("Pickaxe")};
    const TCHAR* Names[]={TEXT("axe.png"),TEXT("pickaxe.png")};
    for (int32 I=0;I<2;++I)
    {
        const FString Path=FString::Printf(TEXT("/Game/EasyBuildingSystem/Textures/Icons/Tools/T_Icon_Tools_%s.T_Icon_Tools_%s"),Textures[I],Textures[I]);
        auto* Texture=LoadObject<UTexture2D>(nullptr,*Path);
        if (!Texture || UExporter::ExportToFile(Texture,nullptr,*(Folder/Names[I]),false,false,false)<=0) return 1;
    }
    const FName Shovel(TEXT("StaticMesh /Game/MilitaryTrench/Assets/3D/Ind_Mine_Tool_Shovel_Old_01/StaticMeshes/SM_Ind_Mine_Tool_Shovel_Old_01.SM_Ind_Mine_Tool_Shovel_Old_01"));
    FThumbnailMap Thumbnails;
    if (!ThumbnailTools::ConditionallyLoadThumbnailsForObjects({Shovel},Thumbnails)) return 2;
    const FObjectThumbnail* Thumbnail=Thumbnails.Find(Shovel);
    if (!Thumbnail || Thumbnail->GetImageWidth()<=0 || Thumbnail->GetImageHeight()<=0) return 3;
    const auto& Pixels=Thumbnail->GetUncompressedImageData();
    const int64 Count=int64(Thumbnail->GetImageWidth())*Thumbnail->GetImageHeight();
    if (Pixels.Num()!=Count*sizeof(FColor)) return 4;
    TArray64<uint8> PNG;
    FImageUtils::PNGCompressImageArray(Thumbnail->GetImageWidth(),Thumbnail->GetImageHeight(),
        TArrayView64<const FColor>(reinterpret_cast<const FColor*>(Pixels.GetData()),Count),PNG);
    if (!FFileHelper::SaveArrayToFile(PNG,*(Folder/TEXT("shovel.png")))) return 5;
    UE_LOG(LogTemp,Display,TEXT("PRODUCTION_ICONS_EXPORTED %s"),*Folder);
    return 0;
#else
    return 1;
#endif
}
