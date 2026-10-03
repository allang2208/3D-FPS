#include "M10Mawcrawler.h"
#include "Animation/Skeleton.h"
#include "Animation/MorphTarget.h"
#include "Engine/SkeletalMesh.h"

bool AM10Mawcrawler::ConfigureSurfaceRig(USkeletalMesh* Mesh)
{
#if WITH_EDITOR
    if(!Mesh||!Mesh->GetSkeleton())return false;
    // FBX exporters may prefix a blend-shape channel with its mesh/deformer.
    // Canonicalize only these two targets on the newly authored V5 asset.
    for(const TCHAR* Name:{TEXT("M10_MouthOpenTissue"),TEXT("M10_MouthWideTissue")})
    {
        UMorphTarget* Target=nullptr;
        for(const auto& Morph:Mesh->GetMorphTargets())if(Morph&&Morph->GetName().EndsWith(Name)){Target=Morph;break;}
        if(!Target)return false;
        if(Target->GetFName()!=FName(Name)&&!Target->Rename(Name,Mesh))return false;
        Mesh->GetSkeleton()->AccumulateCurveMetaData(FName(Name),false,true);
    }
    Mesh->InitMorphTargets();Mesh->MarkPackageDirty();Mesh->GetSkeleton()->MarkPackageDirty();
    return true;
#else
    return false;
#endif
}
