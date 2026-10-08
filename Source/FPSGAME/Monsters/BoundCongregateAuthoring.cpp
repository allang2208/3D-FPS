#include "BoundCongregate.h"
#include "Engine/SkeletalMesh.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#if WITH_EDITOR
#include "ClothingAssetFactory.h"
#include "ClothingAsset.h"
#include "WitchRebuiltClothingAsset.h"
#include "ChaosCloth/ChaosClothConfig.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#endif

float ABoundCongregate::ReferenceFacingYaw(USkeletalMesh* Mesh)
{
    if(!Mesh)return 0;
    const auto& Ref=Mesh->GetRefSkeleton();auto Frames=Ref.GetRefBonePose();
    for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
    const int32 F=Ref.FindBoneIndex(TEXT("body_front")),B=Ref.FindBoneIndex(TEXT("body_rear"));
    return F>=0&&B>=0?-(Frames[F].GetLocation()-Frames[B].GetLocation()).Rotation().Yaw:0;
}
void ABoundCongregate::PrepareCorpseMesh(USkeletalMesh* Mesh)
{
#if WITH_EDITOR
    if(!Mesh||!Mesh->GetImportedModel()||Mesh->GetImportedModel()->LODModels.IsEmpty())return;
    const auto Assets=Mesh->GetMeshClothingAssets();
    for(const auto& Cloth:Assets)Cloth->UnbindFromSkeletalMesh(Mesh,0,INDEX_NONE);
    Mesh->SetMeshClothingAssets({});
    auto& LOD=Mesh->GetImportedModel()->LODModels[0];
    for(auto& S:LOD.Sections)
    {
        const bool Proxy=Mesh->GetMaterials()[S.MaterialIndex].ImportedMaterialSlotName.ToString().Contains(TEXT("_Proxy"));
        S.bDisabled=Proxy;S.CorrespondClothAssetIndex=INDEX_NONE;S.ClothingData.AssetGuid=FGuid();S.ClothingData.AssetLodIndex=INDEX_NONE;
        auto& User=LOD.UserSectionsData.FindOrAdd(S.OriginalDataSectionIndex);User.bDisabled=Proxy;
        User.CorrespondClothAssetIndex=INDEX_NONE;User.ClothingData.AssetGuid=FGuid();User.ClothingData.AssetLodIndex=INDEX_NONE;
    }
    Mesh->InvalidateDeriveDataCacheGUID();Mesh->MarkPackageDirty();
#endif
}
bool ABoundCongregate::BuildSurfacePhysics(USkeletalMesh* Mesh,UPhysicsAsset* Physics)
{
#if WITH_EDITOR
    if(!Mesh||!Physics||!Mesh->GetImportedModel()||Mesh->GetImportedModel()->LODModels.IsEmpty())return false;
    const auto& Ref=Mesh->GetRefSkeleton();auto Frames=Ref.GetRefBonePose();
    for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
    TArray<TArray<FVector>> Points;Points.SetNum(Ref.GetNum());
    for(const auto& Section:Mesh->GetImportedModel()->LODModels[0].Sections)
    {
        const FString Material=Mesh->GetMaterials()[Section.MaterialIndex].ImportedMaterialSlotName.ToString();
        if(!Material.Contains(TEXT("Flesh"))&&Material!=TEXT("BC_AttackTentacle"))continue;
        for(const auto& V:Section.SoftVertices)
        {
            int32 Best=0;for(int32 J=1;J<MAX_TOTAL_INFLUENCES;++J)if(V.InfluenceWeights[J]>V.InfluenceWeights[Best])Best=J;
            const int32 Bone=Section.BoneMap[V.InfluenceBones[Best]];
            Points[Bone].Add(Frames[Bone].InverseTransformPosition(FVector(V.Position)));
        }
    }
    Physics->SkeletalBodySetups.Reset();Physics->ConstraintSetup.Reset();Physics->CollisionDisableTable.Reset();
    for(int32 I=0;I<Points.Num();++I)
    {
        if(Points[I].Num()<8)continue;
        auto* Body=NewObject<USkeletalBodySetup>(Physics,NAME_None,RF_Transactional);Body->BoneName=Ref.GetBoneName(I);
        Body->PhysicsType=PhysType_Kinematic;Body->CollisionTraceFlag=CTF_UseSimpleAsComplex;
        FKConvexElem Hull;
        for(int32 X=-1;X<=1;++X)for(int32 Y=-1;Y<=1;++Y)for(int32 Z=-1;Z<=1;++Z)
        {
            if(!X&&!Y&&!Z)continue;const FVector D(X,Y,Z);float Best=-MAX_flt;FVector Point;
            for(const auto& V:Points[I])if(FVector::DotProduct(V,D)>Best){Best=FVector::DotProduct(V,D);Point=V;}
            Hull.VertexData.AddUnique(Point);
        }
        Hull.UpdateElemBox();Body->AggGeom.ConvexElems.Add(Hull);
        Body->DefaultInstance.SetCollisionProfileName(TEXT("Ragdoll"));
        Body->InvalidatePhysicsData();Body->CreatePhysicsMeshes();Physics->SkeletalBodySetups.Add(Body);
    }
    Physics->UpdateBodySetupIndexMap();Physics->UpdateBoundsBodiesArray();Physics->SetPreviewMesh(Mesh,false);
    Mesh->SetPhysicsAsset(Physics);Physics->MarkPackageDirty();Mesh->MarkPackageDirty();return true;
#else
    return false;
#endif
}
bool ABoundCongregate::BuildGarmentSimulation(USkeletalMesh* Mesh)
{
#if WITH_EDITOR
    if(!Mesh||!Mesh->GetImportedModel()||Mesh->GetImportedModel()->LODModels.IsEmpty())return false;
    // Bind/unbind each requests PostEditChange. Defer the rebuild until section
    // mappings AND UserSectionsData agree, and keep LOD references valid.
    FScopedSkeletalMeshPostEditChange GarmentEdit(Mesh);
    auto& LOD=Mesh->GetImportedModel()->LODModels[0];
    for(const auto& Old:Mesh->GetMeshClothingAssets())Old->UnbindFromSkeletalMesh(Mesh,0,INDEX_NONE);
    Mesh->SetMeshClothingAssets({});
    // SurfaceFitV12 uses skin-relative backstops for detailed contact, with
    // interior capsules for moving neighbouring flesh. Inflated convex shells
    // would push the newly fitted cloth away from its anatomical support.
    const bool RebuiltGarment=Mesh->GetName().Contains(TEXT("GarmentRebuildV19"));
    const bool TailoredDrape=RebuiltGarment||Mesh->GetName().Contains(TEXT("GarmentDrapeV18"));
    const bool SurfaceFit=TailoredDrape||Mesh->GetName().Contains(TEXT("SurfaceFitV12"));
    const auto& Ref=Mesh->GetRefSkeleton();auto Frames=Ref.GetRefBonePose();
    for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
    TArray<TArray<FVector>> FleshPoints;FleshPoints.SetNum(Ref.GetNum());
    for(const auto& S:LOD.Sections)
    {
        const FString Name=Mesh->GetMaterials()[S.MaterialIndex].ImportedMaterialSlotName.ToString();
        if(Name!=TEXT("BC_Flesh")&&Name!=TEXT("BC_AttackTentacle"))continue;
        for(const auto& V:S.SoftVertices)
        {
            int32 Best=0;for(int32 J=1;J<MAX_TOTAL_INFLUENCES;++J)if(V.InfluenceWeights[J]>V.InfluenceWeights[Best])Best=J;
            FleshPoints[S.BoneMap[V.InfluenceBones[Best]]].Add(FVector(V.Position));
        }
    }
    int32 ClothCapsules=0;
    FBox ActiveClothBounds(ForceInit);
    auto SurfaceHull=[&](UPhysicsAsset* Collision,int32 Bone)
    {
        if(TailoredDrape&&ClothCapsules>=16)return;
        const auto& All=FleshPoints[Bone];if(All.Num()<8)return;
        const FString BoneName=Ref.GetBoneName(Bone).ToString();
        const bool Torso=BoneName==TEXT("body")||BoneName==TEXT("body_front")||BoneName==TEXT("body_rear");
        FVector Center=FVector::ZeroVector;for(const auto& P:All)Center+=P;Center/=All.Num();
        auto* Body=NewObject<USkeletalBodySetup>(Collision);Body->BoneName=Ref.GetBoneName(Bone);
        Body->PhysicsType=PhysType_Kinematic;Body->CollisionTraceFlag=CTF_UseSimpleAsComplex;
        // Overlapping torso quadrants retain under-arm spaces that a single
        // convex enclosing the entire fused body would incorrectly fill.
        for(int32 Patch=0;Patch<(Torso?4:1);++Patch)
        {
            if(TailoredDrape&&ClothCapsules>=16)break;
            TArray<FVector> Points;
            for(const auto& P:All)
                if(!Torso||((P.X-Center.X)*(Patch&1?1.:-1.)>=-8.&&(P.Y-Center.Y)*(Patch&2?1.:-1.)>=-8.))Points.Add(P);
            // Match the Witch's dedicated under-garment contact volume. A fused
            // donor bone may also own distant flesh outside this garment.
            if(RebuiltGarment)Points.RemoveAll([&](const FVector& P){return !ActiveClothBounds.IsInsideOrOn(P);});
            if(Points.Num()<8)continue;
            FVector PatchCenter=FVector::ZeroVector;for(const auto& P:Points)PatchCenter+=P;PatchCenter/=Points.Num();
            if(SurfaceFit)
            {
                FBox Bounds(ForceInit);for(const auto& P:Points)Bounds+=P;
                const FVector Size=Bounds.GetSize();
                FVector Axis=Size.X>Size.Y&&Size.X>Size.Z?FVector::ForwardVector:Size.Y>Size.Z?FVector::RightVector:FVector::UpVector;
                for(int32 Pass=0;Pass<8;++Pass)
                {
                    FVector Next=FVector::ZeroVector;
                    for(const auto& P:Points){const FVector D=P-PatchCenter;Next+=D*FVector::DotProduct(D,Axis);}
                    if(!Next.IsNearlyZero())Axis=Next.GetSafeNormal();
                }
                TArray<double> Axial,Radial;Axial.Reserve(Points.Num());Radial.Reserve(Points.Num());
                for(const auto& P:Points)
                {
                    const FVector D=P-PatchCenter;const double Along=FVector::DotProduct(D,Axis);
                    Axial.Add(Along);Radial.Add((D-Axis*Along).Size());
                }
                Axial.Sort();Radial.Sort();
                const double Low=Axial[Axial.Num()/10],High=Axial[Axial.Num()*9/10];
                FKSphylElem Capsule;
                const double MeshRadius=FMath::Max(1.,RebuiltGarment?
                    Radial[Radial.Num()*3/4]*(Torso?.8:.9):Radial[Radial.Num()/2]*(Torso?.65:.72));
                // Flesh samples are in mesh centimetres, while PhysicsAsset
                // dimensions are bone-local. The imported rig carries scale
                // 100 and Chaos applies that root scale to collision shapes.
                // Convert dimensions just as we already convert the centre.
                const double BoneScale=Frames[Bone].GetScale3D().GetAbsMax();
                Capsule.Radius=MeshRadius/BoneScale;
                Capsule.Length=FMath::Max(0.,High-Low-2.*MeshRadius)/BoneScale;
                Capsule.Center=Frames[Bone].InverseTransformPosition(PatchCenter+Axis*((Low+High)*.5));
                Capsule.Rotation=FQuat::FindBetweenNormals(FVector::UpVector,Frames[Bone].InverseTransformVectorNoScale(Axis)).Rotator();
                Body->AggGeom.SphylElems.Add(Capsule);++ClothCapsules;continue;
            }
            FKConvexElem Hull;
            for(int32 X=-1;X<=1;++X)for(int32 Y=-1;Y<=1;++Y)for(int32 Z=-1;Z<=1;++Z)
            {
                if(!X&&!Y&&!Z)continue;const FVector Direction(X,Y,Z);double Best=-MAX_dbl;FVector Point;
                for(const auto& P:Points)if(FVector::DotProduct(P,Direction)>Best){Best=FVector::DotProduct(P,Direction);Point=P;}
                Point+=(Point-PatchCenter).GetSafeNormal()*2.f;
                Hull.VertexData.AddUnique(Frames[Bone].InverseTransformPosition(Point));
            }
            Hull.UpdateElemBox();Body->AggGeom.ConvexElems.Add(Hull);
        }
        if(Body->AggGeom.ConvexElems.IsEmpty()&&Body->AggGeom.SphylElems.IsEmpty())return;
        Body->InvalidatePhysicsData();Body->CreatePhysicsMeshes();Collision->SkeletalBodySetups.Add(Body);
    };
    int32 Count=0;
    for(int32 SectionIndex=0;SectionIndex<LOD.Sections.Num();++SectionIndex)
    {
        const auto& Section=LOD.Sections[SectionIndex];
        const FString Mat=Mesh->GetMaterials()[Section.MaterialIndex].ImportedMaterialSlotName.ToString();
        if(!Mat.Contains(TEXT("_Proxy")))continue;
        const FString RenderMat=Mat.Left(Mat.Find(TEXT("_Proxy")));
        const bool RootLining=RenderMat==TEXT("BC_Lining");
        const bool LongDrape=RootLining||RenderMat==TEXT("BC_RagFabric");
        ClothCapsules=0;
        auto* Collision=NewObject<UPhysicsAsset>(Mesh,
            MakeUniqueObjectName(Mesh,UPhysicsAsset::StaticClass(),FName(*FString::Printf(TEXT("BC_ClothContactV9_%d"),Count))),RF_Transactional);
        const bool Left=RenderMat==TEXT("BC_RagFabric")||RenderMat==TEXT("BC_SleeveLeft");
        const FString SleeveStem=Left?TEXT("leg_L2_"):TEXT("leg_R4_");
        FBox ClothBounds(ForceInit);for(const auto& V:Section.SoftVertices)ClothBounds+=FVector(V.Position);
        ClothBounds=ClothBounds.ExpandBy(16.f);
        ActiveClothBounds=ClothBounds.ExpandBy(10.f);
        TArray<TPair<double,int32>> CollisionCandidates;
        for(int32 Bone=0;Bone<Ref.GetNum();++Bone)
        {
            const FString Name=Ref.GetBoneName(Bone).ToString();
            const bool Torso=Name==TEXT("body")||Name==TEXT("body_front")||Name==TEXT("body_rear");
            const bool Limb=Name.StartsWith(LongDrape?TEXT("leg_"):*SleeveStem)&&
                (!TailoredDrape||(!LongDrape?(Name==SleeveStem+TEXT("lower")||(RebuiltGarment&&Name==SleeveStem+TEXT("upper"))):!Name.EndsWith(TEXT("_foot"))));
            const bool Root=LongDrape&&(!TailoredDrape||RootLining)&&Name.StartsWith(TEXT("attack_tentacle_"))&&FCString::Atoi(*Name.Right(2))<=(TailoredDrape?5:9);
            if((Torso&&LongDrape)||Limb||Root)
            {
                if(SurfaceFit)
                {
                    FBox FleshBounds(ForceInit);for(const auto& P:FleshPoints[Bone])FleshBounds+=P;
                    if(!FleshBounds.IsValid||!ClothBounds.Intersect(FleshBounds))continue;
                }
                if(TailoredDrape)
                {
                    // Root/torso contact first, then nearby limb surfaces.
                    // Bound offline collider count without adding runtime work.
                    FVector Center=FVector::ZeroVector;
                    for(const auto& P:FleshPoints[Bone])Center+=P;
                    Center/=FMath::Max(1,FleshPoints[Bone].Num());
                    const double Priority=Torso?-2.e8:Root?-1.e8:FVector::DistSquared(Center,ClothBounds.GetCenter());
                    CollisionCandidates.Emplace(Priority,Bone);
                }
                else SurfaceHull(Collision,Bone);
            }
        }
        if(TailoredDrape)
        {
            CollisionCandidates.Sort([](const auto& A,const auto& B){return A.Key<B.Key;});
            for(const auto& Candidate:CollisionCandidates)SurfaceHull(Collision,Candidate.Value);
        }
        Collision->UpdateBodySetupIndexMap();Collision->SetPreviewMesh(Mesh,false);
        int32 RenderSection=INDEX_NONE;
        for(int32 R=0;R<LOD.Sections.Num();++R)
            if(Mesh->GetMaterials()[LOD.Sections[R].MaterialIndex].ImportedMaterialSlotName.ToString()==RenderMat){RenderSection=R;break;}
        if(RenderSection==INDEX_NONE)return false;
        TArray<FVector> Locations;TArray<float> Travels,AttachmentDrive;
        // Blender FLOAT_COLOR is exported to sRGB vertex bytes by FBX. Decode
        // before using it as a distance, otherwise 1-2 cm becomes 7-10 cm.
        for(const auto& V:Section.SoftVertices)
        {const FLinearColor Masks(V.Color);Locations.Add(FVector(V.Position));Travels.Add(Masks.R*45.f);AttachmentDrive.Add(Masks.A);}
        FSkeletalMeshClothBuildParams Params;Params.AssetName=FString::Printf(TEXT("BC_DrapeV9_%d_Extract"),Count);
        Params.LodIndex=0;Params.SourceSection=SectionIndex;Params.bRemoveFromMesh=true;Params.PhysicsAsset=Collision;
        auto* Extracted=Cast<UClothingAssetCommon>(NewObject<UClothingAssetFactory>()->CreateFromSkeletalMesh(Mesh,Params));
        if(!Extracted||Extracted->LodData.IsEmpty())return false;
        auto* Cloth=NewObject<UWitchRebuiltClothingAsset>(Mesh,
            MakeUniqueObjectName(Mesh,UWitchRebuiltClothingAsset::StaticClass(),FName(*FString::Printf(TEXT("BC_DrapeV9_%d"),Count))),RF_Transactional);
        Cloth->InitializeSimulationFrom(Extracted);
        auto& Layer=Cloth->LodData[0];Layer.PointWeightMaps.Reset();Layer.bUseMultipleInfluences=false;Layer.bSmoothTransition=true;
        FPointWeightMap Distance(Layer.PhysicalMeshData.Vertices.Num());
        FPointWeightMap Drive(Layer.PhysicalMeshData.Vertices.Num());
        Drive.Name=TEXT("SeamToHemAttachmentDrive");Drive.bEnabled=true;Drive.CurrentTarget=uint8(EWeightMapTargetCommon::AnimDriveStiffness);
        Distance.Name=TEXT("PinnedSeamsFreeTornHem");Distance.bEnabled=true;Distance.CurrentTarget=uint8(EWeightMapTargetCommon::MaxDistance);
        for(int32 I=0;I<Distance.Num();++I)
        {
            const FVector P(Layer.PhysicalMeshData.Vertices[I]);int32 Closest=0;double Best=MAX_dbl;
            for(int32 J=0;J<Locations.Num();++J){const double D=FVector::DistSquared(P,Locations[J]);if(D<Best){Best=D;Closest=J;}}
            Distance[I]=Travels[Closest]<(TailoredDrape?.02f:.75f)?0.f:Travels[Closest];
            Drive[I]=AttachmentDrive[Closest];
        }
        Layer.PointWeightMaps.Add(MoveTemp(Distance));
        if(TailoredDrape)Layer.PointWeightMaps.Add(MoveTemp(Drive));
        for(const auto Target:{EWeightMapTargetCommon::BackstopDistance,EWeightMapTargetCommon::BackstopRadius})
        {
            FPointWeightMap Backstop(Layer.PhysicalMeshData.Vertices.Num());
            Backstop.Name=Target==EWeightMapTargetCommon::BackstopDistance?TEXT("FleshContactOffset"):TEXT("FleshContactRadius");
            Backstop.bEnabled=true;Backstop.CurrentTarget=uint8(Target);
            for(int32 I=0;I<Backstop.Num();++I)
                Backstop[I]=Target==EWeightMapTargetCommon::BackstopDistance?(TailoredDrape?.4f:0.f):(TailoredDrape?(LongDrape?14.f:8.f):20.f);
            Layer.PointWeightMaps.Add(MoveTemp(Backstop));
        }
        Cloth->PhysicsAsset=Collision;
        auto* Config=NewObject<UChaosClothConfig>(Cloth);
        Config->Density=.38f;Config->EdgeStiffnessWeighted={.95f,.95f};Config->AreaStiffnessWeighted={.95f,.95f};
        Config->bUseBendingElements=true;Config->BendingStiffnessWeighted={.06f,.06f};
        Config->TetherStiffness={1,1};Config->TetherScale={1.01f,1.01f};Config->bUseGeodesicDistance=true;
        Config->AnimDriveStiffness=LongDrape?FChaosClothWeightedValue{.12f,.12f}:FChaosClothWeightedValue{.22f,.22f};
        if(SurfaceFit)Config->AnimDriveStiffness={.35f,.35f};
        Config->AnimDriveDamping={.3f,.3f};Config->bUseLegacyBackstop=false;
        Config->CollisionThickness=1.8f;Config->FrictionCoefficient=.2f;Config->DampingCoefficient=.035f;
        if(SurfaceFit)Config->CollisionThickness=.7f;
        // These fitted garments move within short skin-relative travel limits.
        // Keep convex contact and backstops, but use discrete contact: legacy
        // Chaos CCD intersects every dynamic vertex with every convex face on
        // each solver iteration, which made V9/V10 stall continuously.
        Config->LocalDampingCoefficient=.18f;Config->bUseSelfCollisions=false;Config->bUseCCD=false;
        Config->bUseSelfCollisionSpheres=LongDrape;Config->SelfCollisionSphereRadius=.65f;
        Config->SelfCollisionSphereRadiusCullMultiplier=2.f;Config->SelfCollisionSphereStiffness=.8f;
        Config->LinearVelocityScale=FVector(.65f);Config->AngularVelocityScale=.6f;
        if(TailoredDrape)
        {
            // Heavy worn fabric: fixed seams, a soft travelling hem, and less
            // inherited whip acceleration. Keep the existing V11 CCD fix.
            Config->Density=.52f;Config->BendingStiffnessWeighted={.12f,.12f};
            Config->TetherScale={1.02f,1.02f};
            Config->AnimDriveStiffness=LongDrape?FChaosClothWeightedValue{.025f,.42f}:FChaosClothWeightedValue{.08f,.48f};
            Config->AnimDriveDamping={.36f,.36f};Config->DampingCoefficient=.055f;
            Config->LocalDampingCoefficient=.22f;Config->FrictionCoefficient=.25f;
            Config->LinearVelocityScale=FVector(.5f);Config->AngularVelocityScale=.4f;
        }
        if(RebuiltGarment)
        {
            // Reuse Witch Drape06's bounded solver, stable capture and pinned
            // seams. The new surface needs no second cloth layer or custom Tick.
            Config->TetherScale={1.f,1.f};
            Config->AnimDriveStiffness=LongDrape?FChaosClothWeightedValue{.10f,.50f}:FChaosClothWeightedValue{.25f,.65f};
        }
        Cloth->ClothConfigs.Add(Config->GetClass()->GetFName(),Config);
        auto* Shared=NewObject<UChaosClothSharedSimConfig>(Cloth);Shared->IterationCount=6;Shared->MaxIterationCount=8;Shared->SubdivisionCount=2;
        if(RebuiltGarment){Shared->IterationCount=4;Shared->MaxIterationCount=6;Shared->SubdivisionCount=1;}
        Cloth->ClothConfigs.Add(Shared->GetClass()->GetFName(),Shared);
        Cloth->ApplyParameterMasks(true);Cloth->InvalidateAllCachedData();Mesh->AddClothingAsset(Cloth);
        if(!Cloth->BindToSkeletalMesh(Mesh,0,RenderSection,0))return false;
        auto& User=LOD.UserSectionsData.FindOrAdd(LOD.Sections[RenderSection].OriginalDataSectionIndex);
        User.CorrespondClothAssetIndex=Count;User.ClothingData.AssetGuid=Cloth->GetAssetGuid();User.ClothingData.AssetLodIndex=0;
        LOD.Sections[SectionIndex].bDisabled=true;
        LOD.UserSectionsData.FindOrAdd(LOD.Sections[SectionIndex].OriginalDataSectionIndex).bDisabled=true;
        ++Count;
    }
    Mesh->InvalidateDeriveDataCacheGUID();Mesh->MarkPackageDirty();return Count>0;
#else
    return false;
#endif
}
