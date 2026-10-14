#include "DungeonMaterialUsageRepairCommandlet.h"

#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "Dom/JsonObject.h"
#include "HAL/FileManager.h"
#include "Materials/Material.h"
#include "Materials/MaterialInterface.h"
#include "MaterialShared.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "ShaderCompiler.h"
#include "UObject/SavePackage.h"
#endif

int32 UDungeonMaterialUsageRepairCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    FString Manifest, Output;
    if (!FParse::Value(*Params, TEXT("Manifest="), Manifest) || !FParse::Value(*Params, TEXT("Output="), Output)) return 1;
    FString Input;
    TSharedPtr<FJsonObject> Requests;
    if (!FFileHelper::LoadFileToString(Input, *Manifest) ||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Input), Requests) || !Requests) return 2;
    IFileManager::Get().MakeDirectory(*Output, true);
    struct FFix { UMaterial* Material = nullptr; TSet<EMaterialUsage> Usages; };
    TMap<FString, FFix> Fixes;
    auto Report = MakeShared<FJsonObject>();
    TArray<TSharedPtr<FJsonValue>> Mappings, Saved;
    // Resolve instances to their base material before changing or saving any package.
    for (const auto& Request : Requests->Values)
    {
        auto* Interface = LoadObject<UMaterialInterface>(nullptr, *Request.Key);
        UMaterial* Material = Interface ? Interface->GetMaterial() : nullptr;
        if (!Material || !Material->GetPathName().StartsWith(TEXT("/Game/")))
        { UE_LOG(LogTemp, Error, TEXT("Material repair cannot resolve %s"), *Request.Key); return 3; }
        auto& Fix = Fixes.FindOrAdd(Material->GetPathName());
        Fix.Material = Material;
        for (const auto& Usage : Request.Value->AsArray())
        {
            const FString Name = Usage->AsString();
            if (Name == TEXT("Nanite")) Fix.Usages.Add(MATUSAGE_Nanite);
            else if (Name == TEXT("InstancedStaticMeshes")) Fix.Usages.Add(MATUSAGE_InstancedStaticMeshes);
            else { UE_LOG(LogTemp, Error, TEXT("Unsupported material usage %s"), *Name); return 4; }
        }
        auto Mapping = MakeShared<FJsonObject>();
        Mapping->SetStringField(TEXT("requested"), Request.Key);
        Mapping->SetStringField(TEXT("base_material"), Material->GetPathName());
        Mappings.Add(MakeShared<FJsonValueObject>(Mapping));
    }
    // Preserve original on-disk packages, including external bulk data, before edits.
    for (const auto& Pair : Fixes)
    {
        const FString Package = Pair.Value.Material->GetOutermost()->GetName();
        const FString Filename = FPackageName::LongPackageNameToFilename(Package, FPackageName::GetAssetPackageExtension());
        for (const TCHAR* Extension : {TEXT(".uasset"), TEXT(".uexp"), TEXT(".ubulk")})
        {
            const FString Source = FPaths::ChangeExtension(Filename, Extension);
            if (!IFileManager::Get().FileExists(*Source)) continue;
            const FString Backup = Output / TEXT("backup") / (Package.RightChop(6) + Extension);
            IFileManager::Get().MakeDirectory(*FPaths::GetPath(Backup), true);
            if (!IFileManager::Get().FileExists(*Backup) && IFileManager::Get().Copy(*Backup, *Source, false) != COPY_OK)
                return 5;
        }
    }
    for (auto& Pair : Fixes)
    {
        UMaterial* Material = Pair.Value.Material;
        Material->Modify();
        for (EMaterialUsage Usage : Pair.Value.Usages) Material->SetMaterialUsage(Usage);
        Material->PostEditChange();
    }
    // Offline production: finish derived data/shaders before saving the corrected packages.
    FAssetCompilingManager::Get().FinishAllCompilation();
    if (GShaderCompilingManager) GShaderCompilingManager->FinishAllCompilation();
    for (auto& Pair : Fixes)
    {
        UMaterial* Material = Pair.Value.Material;
        for (EMaterialUsage Usage : Pair.Value.Usages)
            if (!Material->GetUsageByFlag(Usage)) return 6;
        if (const FMaterialResource* Resource = Material->GetMaterialResource(GMaxRHIShaderPlatform))
            if (!Resource->GetCompileErrors().IsEmpty())
            { UE_LOG(LogTemp, Error, TEXT("Material compile failed: %s"), *Material->GetPathName()); return 7; }
        FSavePackageArgs Args;
        Args.TopLevelFlags = RF_Public | RF_Standalone;
        Args.SaveFlags = SAVE_NoError;
        const FString Filename = FPackageName::LongPackageNameToFilename(Material->GetOutermost()->GetName(), FPackageName::GetAssetPackageExtension());
        if (!UPackage::SavePackage(Material->GetOutermost(), Material, *Filename, Args)) return 8;
        Saved.Add(MakeShared<FJsonValueString>(Material->GetPathName()));
        UE_LOG(LogTemp, Display, TEXT("DUNGEON_MATERIAL_SAVED %s"), *Material->GetPathName());
    }
    UPackage::WaitForAsyncFileWrites();
    Report->SetArrayField(TEXT("requested_to_base"), Mappings);
    Report->SetArrayField(TEXT("saved_materials"), Saved);
    Report->SetStringField(TEXT("status"), TEXT("compiled_and_saved"));
    FString Json;
    FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json));
    return FFileHelper::SaveStringToFile(Json, *(Output / TEXT("receipt.json"))) ? 0 : 9;
#else
    return 1;
#endif
}
