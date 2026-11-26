#include "RoadCanopyCommandlet.h"
#include "Modules/ModuleManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/Skeleton.h"
#include "StaticToSkeletalMeshConverter.h"
#include "ReferenceSkeleton.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "UObject/SavePackage.h"
#include "Misc/PackageName.h"
#include "AssetCompilingManager.h"

IMPLEMENT_PRIMARY_GAME_MODULE(FDefaultGameModuleImpl,CanopyAuthor,"CanopyAuthor");
namespace
{
constexpr TCHAR Folder[]=TEXT("/Game/WorldGeneration/TemperateHills/EastRiverRoad/CanopyR2/");
template<typename T> T* Create(const FString& Name)
{
    return NewObject<T>(CreatePackage(*(FString(Folder)+Name)),FName(*Name),RF_Public|RF_Standalone);
}
bool Save(UObject* Asset)
{
    FAssetCompilingManager::Get().FinishAllCompilation();
    FAssetRegistryModule::AssetCreated(Asset);
    auto* Pkg=Asset->GetOutermost();
    const FString Path=FPackageName::LongPackageNameToFilename(Pkg->GetName(),FPackageName::GetAssetPackageExtension());
    FSavePackageArgs Args;Args.TopLevelFlags=RF_Public|RF_Standalone;
    return UPackage::SavePackage(Pkg,Asset,*Path,Args);
}
}
int32 URoadCanopyCommandlet::Main(const FString&)
{
    USkeleton* Skeleton=Create<USkeleton>(TEXT("SKEL_RoadHornbeam"));
    const FName Root(TEXT("Root"));
    {FReferenceSkeletonModifier Modifier(Skeleton);Modifier.Add(FMeshBoneInfo(Root,TEXT("Root"),INDEX_NONE),FTransform::Identity);}
    if(!Save(Skeleton))return 1;
    for(const TCHAR* Form:{TEXT("04"),TEXT("05")})
    {
        const FString Src=FString(TEXT("/Game/EuropeanHornbeam/Geometry/SimpleWind/SM_EuropeanHornbeam_Forest_"))+Form;
        auto* Tree=LoadObject<UStaticMesh>(nullptr,*(Src+TEXT(".")+FPackageName::GetShortName(Src)));
        if(!Tree)return 2;
        auto* Mesh=Create<USkeletalMesh>(FString(TEXT("SK_RoadHornbeam_"))+Form);
        if(!FStaticToSkeletalMeshConverter::InitializeSkeletalMeshFromStaticMesh(Mesh,Tree,Skeleton->GetReferenceSkeleton(),Root))return 3;
        Mesh->SetSkeleton(Skeleton);
        if(!Save(Mesh))return 4;
    }
    return 0;
}
