#include "ColdSteelSignAtlasCommandlet.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "EditorFramework/AssetImportData.h"
#include "Engine/Texture2D.h"
#include "HAL/FileManager.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/SavePackage.h"
#endif

int32 UColdSteelSignAtlasCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    FString Manifest, Body, Output;
    TArray<TSharedPtr<FJsonValue>> Entries;
    if (!FParse::Value(*Params,TEXT("Manifest="),Manifest) || !FParse::Value(*Params,TEXT("Output="),Output)
        || !FFileHelper::LoadFileToString(Body,*Manifest)
        || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Body),Entries) || Entries.IsEmpty()) return 2;
    for (const auto& Value : Entries)
    {
        const auto& Row=Value->AsObject();
        const FString Package=Row->GetStringField(TEXT("package"));
        if (!Package.StartsWith(TEXT("/Game/")) || !FPackageName::IsValidLongPackageName(Package)) return 2;
        UTexture2D* Texture=LoadObject<UTexture2D>(nullptr,*Package);
        FImage Current, Old, New;
        const FString NewFile=Row->GetStringField(TEXT("new"));
        if (!Texture || Texture->Source.GetNumBlocks()!=1 || Texture->Source.GetNumLayers()!=1
            || Texture->Source.GetNumSlices()!=1 || Texture->Source.GetNumMips()!=1
            || !Texture->Source.GetMipImage(Current,0) || Current.Format!=ERawImageFormat::BGRA8
            || !FImageUtils::LoadImage(*Row->GetStringField(TEXT("old")),Old) || !FImageUtils::LoadImage(*NewFile,New)) return 3;
        if (Old.Format!=Current.Format || New.Format!=Current.Format || Old.SizeX!=Current.SizeX || Old.SizeY!=Current.SizeY
            || New.SizeX!=Current.SizeX || New.SizeY!=Current.SizeY || Current.RawData!=Old.RawData)
        {
            UE_LOG(LogTemp,Error,TEXT("SIGN_ATLAS source differs from the reference artwork: %s"),*Package);
            return 4;
        }
        Texture->PreEditChange(nullptr);
        uint8* Dest=Texture->Source.LockMip(0);
        FMemory::Memcpy(Dest,New.RawData.GetData(),New.RawData.Num());
        Texture->Source.UnlockMip(0);
        if (Texture->AssetImportData)
        {
            const FString Source=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/Row->GetStringField(TEXT("canonical")));
            Texture->AssetImportData->Update(Source,FMD5Hash::HashFile(*NewFile));
        }
        Texture->PostEditChange();
        FAssetCompilingManager::Get().FinishAllCompilation();
        const FString File=Output/TEXT("Content")/(Package.RightChop(6)+FPackageName::GetAssetPackageExtension());
        IFileManager::Get().MakeDirectory(*FPaths::GetPath(File),true);
        FSavePackageArgs Save;
        Save.TopLevelFlags=RF_Public|RF_Standalone;
        Save.SaveFlags=SAVE_NoError;
        if (!UPackage::SavePackage(Texture->GetOutermost(),Texture,*File,Save)) return 5;
        UE_LOG(LogTemp,Display,TEXT("SIGN_ATLAS staged %s (%dx%d)"),*Package,New.SizeX,New.SizeY);
    }
    return 0;
#else
    return 2;
#endif
}
