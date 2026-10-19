#include "FPSModularOutfitComponent.h"
#include "../Monsters/WitchRebuiltClothingAsset.h"
#include "Engine/SkeletalMesh.h"
#if WITH_EDITOR
#include "ClothingAssetFactory.h"
#include "ClothingAsset.h"
#include "ChaosCloth/ChaosClothConfig.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "Materials/MaterialExpressionGetMaterialAttributes.h"
#include "Materials/MaterialExpressionSetMaterialAttributes.h"
#endif

int32 UFPSModularOutfitComponent::AddRobeHemOffsetPin(UObject* Expression)
{
#if WITH_EDITOR
    if(!Expression||!Expression->GetPathName().StartsWith(TEXT("/Game/Characters/ModularOutfit20260924/BlueMageRobe20261018/HemContinuity20261019/Materials/")))return INDEX_NONE;
    if(auto* Get=Cast<UMaterialExpressionGetMaterialAttributes>(Expression))
        return Get->CreateOrGetOutputAttribute(MP_WorldPositionOffset);
    if(auto* Set=Cast<UMaterialExpressionSetMaterialAttributes>(Expression))
        return Set->CreateOrGetInputAttribute(MP_WorldPositionOffset);
#endif
    return INDEX_NONE;
}

bool UFPSModularOutfitComponent::BuildMageRobeDrape(USkeletalMesh* Mesh)
{
#if WITH_EDITOR
    if(!Mesh||!Mesh->GetPathName().StartsWith(TEXT("/Game/Characters/ModularOutfit20260924/BlueMageRobe20261018/")))return false;
    if(!Mesh->GetImportedModel()||Mesh->GetImportedModel()->LODModels.IsEmpty())return false;
    // ImportedMaterialSlotName is read-only in Python. Keep the isolated robe
    // import names aligned with the authored section names before extraction.
    for(auto& Material:Mesh->GetMaterials())Material.ImportedMaterialSlotName=Material.MaterialSlotName;
    auto Section=[Mesh](const TCHAR* Name)
    {
        const auto& Sections=Mesh->GetImportedModel()->LODModels[0].Sections;
        for(int32 I=0;I<Sections.Num();++I)
            if(Mesh->GetMaterials().IsValidIndex(Sections[I].MaterialIndex)&&
                Mesh->GetMaterials()[Sections[I].MaterialIndex].ImportedMaterialSlotName==FName(Name))return I;
        return int32(INDEX_NONE);
    };
    if(Section(TEXT("RobeSimulationProxy"))==INDEX_NONE||Section(TEXT("RobeSkirt"))==INDEX_NONE)return false;
    Mesh->Modify();
    for(UClothingAssetBase* Old:Mesh->GetMeshClothingAssets())Old->UnbindFromSkeletalMesh(Mesh,0,INDEX_NONE);
    Mesh->SetMeshClothingAssets({});
    const auto& Ref=Mesh->GetRefSkeleton();TArray<FTransform> Frames=Ref.GetRefBonePose();
    for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
    const int32 Thigh=Ref.FindBoneIndex(TEXT("thigh_l")),Calf=Ref.FindBoneIndex(TEXT("calf_l"));
    if(Thigh==INDEX_NONE||Calf==INDEX_NONE)return false;
    const float BodyScale=FVector::Dist(Frames[Thigh].GetLocation(),Frames[Calf].GetLocation())/39.1f;
    auto* Collision=NewObject<UPhysicsAsset>(Mesh,MakeUniqueObjectName(Mesh,UPhysicsAsset::StaticClass(),TEXT("MageRobeBodyCollision")),RF_Transactional);
    auto Capsule=[&](const TCHAR* Name,const TCHAR* EndName,float Radius,bool CoverJoints=false)
    {
        const int32 B=Ref.FindBoneIndex(Name),E=Ref.FindBoneIndex(EndName);if(B==INDEX_NONE||E==INDEX_NONE)return;
        const FVector A=Frames[B].GetLocation(),End=Frames[E].GetLocation();
        const float BoneScale=FMath::Max(.001f,static_cast<float>(Frames[B].GetScale3D().GetAbsMax()));
        auto* Body=NewObject<USkeletalBodySetup>(Collision);Body->BoneName=FName(Name);
        FKSphylElem Shape;Shape.Center=Frames[B].InverseTransformPosition((A+End)*.5);
        Shape.Rotation=FRotationMatrix::MakeFromZ(Frames[B].InverseTransformVectorNoScale(End-A)).Rotator();
        Shape.Radius=Radius*BodyScale/BoneScale;
        // Leg capsule centres reach the actual joint centres. Subtracting two
        // radii leaves zero collision cross-section at the knee and hip.
        Shape.Length=FMath::Max(0.f,static_cast<float>((End-A).Size())-(CoverJoints?0.f:2.f*Radius*BodyScale))/BoneScale;
        Body->AggGeom.SphylElems.Add(Shape);Collision->SkeletalBodySetups.Add(Body);
    };
    Capsule(TEXT("pelvis"),TEXT("spine_02"),9.5f);Capsule(TEXT("spine_02"),TEXT("spine_04"),10.f);
    // A thigh's largest front/back radius is not its lateral hip radius.
    // The old 12.8 cm sphere reached six centimetres outside Jason's hip and
    // inflated the skirt. Two offset tapered capsules retain depth without
    // turning the entire thigh and its upper joint into that oversized sphere.
    const bool Jason=Mesh->GetName().StartsWith(TEXT("SK_Jason"));
    const float CalfRadius=Jason?9.3f:11.0f;
    auto FittedThigh=[&](const FString& Side)
    {
        const int32 B=Ref.FindBoneIndex(FName(*(TEXT("thigh_")+Side)));
        const int32 E=Ref.FindBoneIndex(FName(*(TEXT("calf_")+Side)));
        if(B==INDEX_NONE||E==INDEX_NONE)return;
        const FVector Hip=Frames[B].GetLocation(),Knee=Frames[E].GetLocation();
        const float BoneScale=FMath::Max(.001f,static_cast<float>(Frames[B].GetScale3D().GetAbsMax()));
        auto* Body=NewObject<USkeletalBodySetup>(Collision);Body->BoneName=Ref.GetBoneName(B);
        const float Inward=Jason?-.9f:0.f;
        for(const float Depth:{Jason?-3.8f:-2.f,Jason?2.6f:1.3f})
        {
            const FVector Start=FMath::Lerp(Hip,Knee,.12f)+FVector(FMath::Sign(Hip.X)*Inward,Depth,0);
            const FVector End=FMath::Lerp(Hip,Knee,.95f)+FVector(FMath::Sign(Hip.X)*Inward,Depth*.6f,0);
            FKTaperedCapsuleElem Shape;Shape.Center=Frames[B].InverseTransformPosition((Start+End)*.5);
            // Chaos maps Radius0 to +Z and Radius1 to -Z; point +Z at the hip.
            Shape.Rotation=FRotationMatrix::MakeFromZ(Frames[B].InverseTransformVectorNoScale(Start-End)).Rotator();
            Shape.Radius0=(Jason?7.1f:7.7f)/BoneScale;Shape.Radius1=(Jason?5.1f:5.4f)/BoneScale;
            Shape.Length=static_cast<float>(FVector::Dist(Start,End))/BoneScale;
            Body->AggGeom.TaperedCapsuleElems.Add(Shape);
        }
        Collision->SkeletalBodySetups.Add(Body);
    };
    for(const TCHAR* Side:{TEXT("l"),TEXT("r")})
    {
        const FString S(Side);
        FittedThigh(S);
        Capsule(*(TEXT("calf_")+S),*(TEXT("foot_")+S),CalfRadius/BodyScale,true);
        Capsule(*(TEXT("foot_")+S),*(TEXT("ball_")+S),4.f);
        Capsule(*(TEXT("lowerarm_")+S),*(TEXT("hand_")+S),3.7f);
        Capsule(*(TEXT("hand_")+S),*(TEXT("middle_01_")+S),3.f);
    }
    Collision->UpdateBodySetupIndexMap();Collision->SetPreviewMesh(Mesh,false);
    FSkeletalMeshClothBuildParams Params;Params.AssetName=TEXT("MageRobeProxyExtract");Params.LodIndex=0;
    Params.SourceSection=Section(TEXT("RobeSimulationProxy"));Params.bRemoveFromMesh=true;Params.PhysicsAsset=Collision;
    auto* Extracted=Cast<UClothingAssetCommon>(NewObject<UClothingAssetFactory>()->CreateFromSkeletalMesh(Mesh,Params));
    if(!Extracted||Extracted->LodData.IsEmpty())return false;
    auto* Cloth=NewObject<UWitchRebuiltClothingAsset>(Mesh,MakeUniqueObjectName(Mesh,UWitchRebuiltClothingAsset::StaticClass(),TEXT("MageRobeContinuousDrape")),RF_Transactional);
    Cloth->InitializeSimulationFrom(Extracted);
    auto& Lod=Cloth->LodData[0];Lod.bUseMultipleInfluences=false;Lod.bSmoothTransition=true;Lod.PointWeightMaps.Reset();
    float Top=-MAX_flt,Bottom=MAX_flt;
    for(const auto& V:Lod.PhysicalMeshData.Vertices){Top=FMath::Max(Top,V.Z);Bottom=FMath::Min(Bottom,V.Z);}
    FPointWeightMap Distance(Lod.PhysicalMeshData.Vertices.Num());Distance.Name=TEXT("FixedWaist_ContinuousSkirt_GradualRelease");
    Distance.bEnabled=true;Distance.CurrentTarget=static_cast<uint8>(EWeightMapTargetCommon::MaxDistance);
    for(int32 I=0;I<Distance.Num();++I)
    {
        const float Drop=Top-Lod.PhysicalMeshData.Vertices[I].Z;
        const float Free=FMath::Max(0.f,Drop-10.f*BodyScale);
        const float HemLimit=FMath::Lerp(30.f,40.f,FMath::Clamp((Lod.PhysicalMeshData.Vertices[I].Z-Bottom)/(25.f*BodyScale),0.f,1.f))*BodyScale;
        Distance[I]=FMath::Min(HemLimit,Free*.9f);
    }
    Lod.PointWeightMaps.Add(MoveTemp(Distance));
    auto* Config=NewObject<UChaosClothConfig>(Cloth);
    Config->Density=.32f;Config->EdgeStiffnessWeighted={.98f,.98f};Config->AreaStiffnessWeighted={.96f,.96f};
    Config->bUseBendingElements=true;Config->BendingStiffnessWeighted={.07f,.07f};
    Config->BucklingRatio=.5f;Config->BucklingStiffnessWeighted={.035f,.035f};
    Config->TetherStiffness={1.f,1.f};Config->TetherScale={1.005f,1.005f};Config->bUseGeodesicDistance=true;
    Config->AnimDriveStiffness={.012f,.012f};Config->AnimDriveDamping={.1f,.1f};
    Config->CollisionThickness=.35f*BodyScale;Config->FrictionCoefficient=.2f;
    Config->DampingCoefficient=.035f;Config->LocalDampingCoefficient=.18f;
    Config->bUseCCD=true;Config->bUseSelfCollisions=false;Config->bUseSelfCollisionSpheres=true;
    Config->SelfCollisionSphereRadius=.5f*BodyScale;Config->SelfCollisionSphereRadiusCullMultiplier=2.f;Config->SelfCollisionSphereStiffness=.8f;
    Config->LinearVelocityScale=FVector(.85);Config->AngularVelocityScale=.8f;
    Cloth->ClothConfigs.Add(Config->GetClass()->GetFName(),Config);
    auto* Shared=NewObject<UChaosClothSharedSimConfig>(Cloth);Shared->IterationCount=6;Shared->MaxIterationCount=8;Shared->SubdivisionCount=2;
    Cloth->ClothConfigs.Add(Shared->GetClass()->GetFName(),Shared);
    Cloth->ApplyParameterMasks(true);Cloth->InvalidateAllCachedData();Mesh->AddClothingAsset(Cloth);
    {
        FScopedSkeletalMeshPostEditChange Change(Mesh);
        const int32 Render=Section(TEXT("RobeSkirt"));
        if(Render==INDEX_NONE||!Cloth->BindToSkeletalMesh(Mesh,0,Render,0))return false;
        auto& LOD=Mesh->GetImportedModel()->LODModels[0];auto& User=LOD.UserSectionsData.FindOrAdd(LOD.Sections[Render].OriginalDataSectionIndex);
        User.CorrespondClothAssetIndex=0;User.ClothingData.AssetGuid=Cloth->GetAssetGuid();User.ClothingData.AssetLodIndex=0;
        for(auto& MeshLOD:Mesh->GetImportedModel()->LODModels)
            for(auto& S:MeshLOD.Sections)
                if(Mesh->GetMaterials().IsValidIndex(S.MaterialIndex)&&Mesh->GetMaterials()[S.MaterialIndex].ImportedMaterialSlotName==FName(TEXT("RobeSimulationProxy")))
                {S.bDisabled=true;MeshLOD.UserSectionsData.FindOrAdd(S.OriginalDataSectionIndex).bDisabled=true;}
        Mesh->InvalidateDeriveDataCacheGUID();Mesh->MarkPackageDirty();
    }
    UE_LOG(LogTemp,Display,TEXT("BLUE_MAGE_ROBE_DRAPE saved binding input: %s particles=%d body_capsules=%d"),*Mesh->GetName(),Lod.PhysicalMeshData.Vertices.Num(),Collision->SkeletalBodySetups.Num());
    return true;
#else
    return false;
#endif
}
