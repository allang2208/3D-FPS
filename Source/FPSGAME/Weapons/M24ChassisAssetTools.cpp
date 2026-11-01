#include "M24ChassisAssetTools.h"
#include "M24Attachments.h"
#include "Engine/SkeletalMesh.h"
#include "Components/SkeletalMeshComponent.h"
#if WITH_EDITOR
#include "MeshDescription.h"
#include "SkeletalMeshAttributes.h"
#include "Engine/StaticMesh.h"
#include "StaticMeshResources.h"
#include "StaticMeshAttributes.h"
#include "StaticMeshCompiler.h"
#endif

bool UM24ChassisAssetTools::BakeStockTangentBasis(UStaticMesh* Mesh)
{
#if WITH_EDITOR
    if(!Mesh)return false;
    FStaticMeshCompilingManager::Get().FinishCompilation({Mesh});
    const auto* Render=Mesh->GetRenderData();if(!Render)return false;
    TArray<FMeshDescription> Descriptions;
    for(int32 L=0;L<Render->LODResources.Num();++L)
    {
        const auto& Lod=Render->LODResources[L];const auto& VB=Lod.VertexBuffers;
        auto& Description=Descriptions.AddDefaulted_GetRef();FStaticMeshAttributes Attributes(Description);Attributes.Register();
        auto Positions=Attributes.GetVertexPositions();auto Normals=Attributes.GetVertexInstanceNormals();
        auto Tangents=Attributes.GetVertexInstanceTangents();auto Signs=Attributes.GetVertexInstanceBinormalSigns();
        auto UVs=Attributes.GetVertexInstanceUVs();auto Colors=Attributes.GetVertexInstanceColors();
        auto Slots=Attributes.GetPolygonGroupMaterialSlotNames();UVs.SetNumChannels(VB.StaticMeshVertexBuffer.GetNumTexCoords());
        TArray<FVertexID> Vertices;
        for(uint32 I=0;I<VB.PositionVertexBuffer.GetNumVertices();++I)
        {const auto V=Description.CreateVertex();Positions[V]=VB.PositionVertexBuffer.VertexPosition(I);Vertices.Add(V);}
        TArray<FPolygonGroupID> Groups;
        for(const auto& Material:Mesh->GetStaticMaterials())
        {const auto G=Description.CreatePolygonGroup();Slots[G]=Material.MaterialSlotName;Groups.Add(G);}
        int32 Repaired=0;
        for(const auto& Section:Lod.Sections)
        {
            if(!Groups.IsValidIndex(Section.MaterialIndex))return false;
            for(uint32 T=0;T<Section.NumTriangles;++T)
            {
                TArray<FVertexInstanceID,TInlineAllocator<3>> Corners;
                for(uint32 C=0;C<3;++C)
                {
                    const uint32 Index=Lod.IndexBuffer.GetIndex(Section.FirstIndex+T*3+C);
                    const auto V=Description.CreateVertexInstance(Vertices[Index]);Corners.Add(V);
                    FVector3f N=VB.StaticMeshVertexBuffer.VertexTangentZ(Index).GetSafeNormal();
                    FVector3f X=VB.StaticMeshVertexBuffer.VertexTangentX(Index);
                    const FVector3f Y=VB.StaticMeshVertexBuffer.VertexTangentY(Index);
                    if(N.IsNearlyZero())N=FVector3f::UpVector;
                    X=(X-N*FVector3f::DotProduct(X,N)).GetSafeNormal();
                    if(X.IsNearlyZero())
                    {
                        const FVector3f Axis=FMath::Abs(N.Z)<.9f?FVector3f::UpVector:FVector3f::RightVector;
                        X=FVector3f::CrossProduct(Axis,N).GetSafeNormal();++Repaired;
                    }
                    Normals[V]=N;Tangents[V]=X;
                    Signs[V]=FVector3f::DotProduct(FVector3f::CrossProduct(N,X),Y)<0?-1.f:1.f;
                    for(int32 U=0;U<UVs.GetNumChannels();++U)UVs.Set(V,U,VB.StaticMeshVertexBuffer.GetVertexUV(Index,U));
                    if(VB.ColorVertexBuffer.GetNumVertices()>Index)
                    {const auto Color=VB.ColorVertexBuffer.VertexColor(Index).ReinterpretAsLinear();Colors[V]=FVector4f(Color.R,Color.G,Color.B,Color.A);}
                    else Colors[V]=FVector4f(1,1,1,1);
                }
                Description.CreatePolygon(Groups[Section.MaterialIndex],Corners);
            }
        }
        UE_LOG(LogTemp,Display,TEXT("SNIPER_STOCK_BASIS: LOD%d retained %d triangles; repaired %d corner tangents"),L,Description.Polygons().Num(),Repaired);
    }
    Mesh->Modify();Mesh->SetNumSourceModels(Descriptions.Num());
    for(int32 L=0;L<Descriptions.Num();++L)
    {
        auto* Description=Mesh->CreateMeshDescription(L);*Description=MoveTemp(Descriptions[L]);Mesh->CommitMeshDescription(L);
        auto& Source=Mesh->GetSourceModel(L);
        Source.BuildSettings.bRecomputeNormals=false;Source.BuildSettings.bRecomputeTangents=false;
        Source.BuildSettings.bUseHighPrecisionTangentBasis=true;Source.BuildSettings.bUseFullPrecisionUVs=true;
        Source.ReductionSettings.BaseLODModel=L;Source.ReductionSettings.PercentTriangles=1;Source.ReductionSettings.PercentVertices=1;Source.ReductionSettings.MaxDeviation=0;
    }
    Mesh->PostEditChange();FStaticMeshCompilingManager::Get().FinishCompilation({Mesh});Mesh->MarkPackageDirty();return true;
#else
    return false;
#endif
}

bool UM24ChassisAssetTools::SplitFactoryChassis(USkeletalMesh* Mesh,const TArray<FVector>& SourceVerticesCM)
{
#if WITH_EDITOR
    if(!Mesh||SourceVerticesCM.IsEmpty())return false;
    for(const auto& M:Mesh->GetMaterials())if(M.MaterialSlotName==TEXT("M24_FactoryChassis"))return true;
    auto* Description=Mesh->GetMeshDescription(0);if(!Description)return false;
    int32 MaterialIndex=INDEX_NONE;
    for(int32 I=0;I<Mesh->GetMaterials().Num();++I)if(Mesh->GetMaterials()[I].MaterialSlotName==TEXT("M24_Body"))MaterialIndex=I;
    if(MaterialIndex==INDEX_NONE)return false;
    auto* Host=NewObject<USkeletalMeshComponent>();Host->SetSkeletalMeshAsset(Mesh);
    const auto& Ref=Mesh->GetRefSkeleton();FTransform Root=FTransform::Identity;
    for(int32 I=Ref.FindBoneIndex(TEXT("WPN_root"));I!=INDEX_NONE;I=Ref.GetParentIndex(I))Root*=Ref.GetRefBonePose()[I];
    const FTransform SourceToComponent=M24Attachments::Mount(Host)*Root;
    constexpr double Cell=.03;
    auto Key=[](const FVector& P){return FIntVector(FMath::RoundToInt(P.X/Cell),FMath::RoundToInt(P.Y/Cell),FMath::RoundToInt(P.Z/Cell));};
    TMultiMap<FIntVector,FVector> Positions;
    for(const auto& P:SourceVerticesCM)Positions.Add(Key(P),P);
    FSkeletalMeshAttributes Attributes(*Description);
    const auto Vertices=Attributes.GetVertexPositions();auto Slots=Attributes.GetPolygonGroupMaterialSlotNames();
    TSet<FVertexID> SelectedVertices;
    for(const FVertexID V:Description->Vertices().GetElementIDs())
    {
        const FVector P=SourceToComponent.InverseTransformPosition(FVector(Vertices[V]));const FIntVector K=Key(P);
        bool Match=false;
        for(int32 X=-1;X<=1&&!Match;++X)for(int32 Y=-1;Y<=1&&!Match;++Y)for(int32 Z=-1;Z<=1&&!Match;++Z)
        {
            const FIntVector CandidateKey=K+FIntVector(X,Y,Z);
            for(auto It=Positions.CreateConstKeyIterator(CandidateKey);It;++It)
                if(FVector::DistSquared(P,It.Value())<=Cell*Cell){Match=true;break;}
        }
        if(Match)SelectedVertices.Add(V);
    }
    TArray<FPolygonID> Selected;
    for(const FPolygonID P:Description->Polygons().GetElementIDs())
    {
        if(Slots[Description->GetPolygonPolygonGroup(P)]!=TEXT("M24_Body"))continue;
        bool All=true;
        for(const FVertexInstanceID V:Description->GetPolygonVertexInstances(P))All&=SelectedVertices.Contains(Description->GetVertexInstanceVertex(V));
        if(All)Selected.Add(P);
    }
    if(Selected.Num()<100)return false;
    Mesh->Modify();const FPolygonGroupID Group=Description->CreatePolygonGroup();Slots[Group]=TEXT("M24_FactoryChassis");
    auto Material=Mesh->GetMaterials()[MaterialIndex];Material.MaterialSlotName=TEXT("M24_FactoryChassis");Material.ImportedMaterialSlotName=Material.MaterialSlotName;
    Mesh->GetMaterials().Add(Material);
    for(const auto P:Selected)Description->SetPolygonPolygonGroup(P,Group);
    if(!Mesh->CommitMeshDescription(0))return false;
    Mesh->PostEditChange();Mesh->MarkPackageDirty();
    UE_LOG(LogTemp,Display,TEXT("M24_CHASSIS: assigned %d native stock polygons; vertex data and morph attributes retained"),Selected.Num());
    return true;
#else
    return false;
#endif
}

bool UM24ChassisAssetTools::SplitFactoryFront(USkeletalMesh* Mesh,const TArray<FVector>& SourceFaceCentersCM)
{
#if WITH_EDITOR
    if(!Mesh||SourceFaceCentersCM.IsEmpty())return false;
    for(const auto& Material:Mesh->GetMaterials())
        if(Material.MaterialSlotName==TEXT("M24_FactoryFront"))return true;
    auto* Description=Mesh->GetMeshDescription(0);if(!Description)return false;
    int32 BodyIndex=INDEX_NONE;
    for(int32 I=0;I<Mesh->GetMaterials().Num();++I)
        if(Mesh->GetMaterials()[I].MaterialSlotName==TEXT("M24_Body"))BodyIndex=I;
    if(BodyIndex==INDEX_NONE)return false;
    auto* Host=NewObject<USkeletalMeshComponent>();Host->SetSkeletalMeshAsset(Mesh);
    const auto& Ref=Mesh->GetRefSkeleton();FTransform Root=FTransform::Identity;
    for(int32 I=Ref.FindBoneIndex(TEXT("WPN_root"));I!=INDEX_NONE;I=Ref.GetParentIndex(I))Root*=Ref.GetRefBonePose()[I];
    const FTransform SourceToComponent=M24Attachments::Mount(Host)*Root;
    constexpr double Cell=.015;
    auto Key=[](const FVector& P){return FIntVector(FMath::RoundToInt(P.X/Cell),FMath::RoundToInt(P.Y/Cell),FMath::RoundToInt(P.Z/Cell));};
    TMultiMap<FIntVector,FVector> Centers;
    for(const FVector& P:SourceFaceCentersCM)Centers.Add(Key(P),P);
    FSkeletalMeshAttributes Attributes(*Description);
    const auto Positions=Attributes.GetVertexPositions();auto Slots=Attributes.GetPolygonGroupMaterialSlotNames();
    TArray<FPolygonID> Selected;
    for(const FPolygonID Face:Description->Polygons().GetElementIDs())
    {
        const FName Slot=Slots[Description->GetPolygonPolygonGroup(Face)];
        if(Slot!=TEXT("M24_Body")&&Slot!=TEXT("M24_FactoryChassis"))continue;
        const auto Instances=Description->GetPolygonVertexInstances(Face);
        FVector Center=FVector::ZeroVector;
        for(const FVertexInstanceID V:Instances)Center+=FVector(Positions[Description->GetVertexInstanceVertex(V)]);
        Center=SourceToComponent.InverseTransformPosition(Center/Instances.Num());
        const FIntVector K=Key(Center);bool Match=false;
        for(int32 X=-1;X<=1&&!Match;++X)for(int32 Y=-1;Y<=1&&!Match;++Y)for(int32 Z=-1;Z<=1&&!Match;++Z)
        {
            const FIntVector Candidate=K+FIntVector(X,Y,Z);
            for(auto It=Centers.CreateConstKeyIterator(Candidate);It;++It)
                if(FVector::DistSquared(Center,It.Value())<=Cell*Cell){Match=true;break;}
        }
        if(Match)Selected.Add(Face);
    }
    // Refuse a partial authoring match; a half-hidden native forend is not a kit.
    if(Selected.Num()!=SourceFaceCentersCM.Num())
    {
        UE_LOG(LogTemp,Error,TEXT("M24_FRONT: matched %d of %d source faces; mesh retained"),Selected.Num(),SourceFaceCentersCM.Num());
        return false;
    }
    Mesh->Modify();const FPolygonGroupID Group=Description->CreatePolygonGroup();Slots[Group]=TEXT("M24_FactoryFront");
    auto Material=Mesh->GetMaterials()[BodyIndex];Material.MaterialSlotName=TEXT("M24_FactoryFront");Material.ImportedMaterialSlotName=Material.MaterialSlotName;
    Mesh->GetMaterials().Add(Material);
    for(const FPolygonID Face:Selected)Description->SetPolygonPolygonGroup(Face,Group);
    if(!Mesh->CommitMeshDescription(0))return false;
    Mesh->PostEditChange();Mesh->MarkPackageDirty();
    UE_LOG(LogTemp,Display,TEXT("M24_FRONT: partitioned %d native faces; stock, vertex data and morphs retained"),Selected.Num());
    return true;
#else
    return false;
#endif
}

bool UM24ChassisAssetTools::SplitFactoryRearSeat(USkeletalMesh* Mesh,const TArray<FVector>& ComponentFaceCentersCM)
{
#if WITH_EDITOR
    if(!Mesh||ComponentFaceCentersCM.IsEmpty())return false;
    for(const auto& Material:Mesh->GetMaterials())
        if(Material.MaterialSlotName==TEXT("M24_FactoryRearSeat"))return true;
    auto* Description=Mesh->GetMeshDescription(0);if(!Description)return false;
    int32 FrontIndex=INDEX_NONE;
    for(int32 I=0;I<Mesh->GetMaterials().Num();++I)
        if(Mesh->GetMaterials()[I].MaterialSlotName==TEXT("M24_FactoryFront"))FrontIndex=I;
    if(FrontIndex==INDEX_NONE)return false;
    constexpr double Cell=.015;
    auto Key=[](const FVector& P){return FIntVector(FMath::RoundToInt(P.X/Cell),FMath::RoundToInt(P.Y/Cell),FMath::RoundToInt(P.Z/Cell));};
    TMultiMap<FIntVector,FVector> Centers;
    for(const FVector& P:ComponentFaceCentersCM)Centers.Add(Key(P),P);
    FSkeletalMeshAttributes Attributes(*Description);
    const auto Positions=Attributes.GetVertexPositions();auto Slots=Attributes.GetPolygonGroupMaterialSlotNames();
    TArray<FPolygonID> Selected;
    for(const FPolygonID Face:Description->Polygons().GetElementIDs())
    {
        if(Slots[Description->GetPolygonPolygonGroup(Face)]!=TEXT("M24_FactoryFront"))continue;
        const auto Instances=Description->GetPolygonVertexInstances(Face);
        FVector Center=FVector::ZeroVector;
        for(const FVertexInstanceID V:Instances)Center+=FVector(Positions[Description->GetVertexInstanceVertex(V)]);
        Center/=Instances.Num();const FIntVector K=Key(Center);bool Match=false;
        for(int32 X=-1;X<=1&&!Match;++X)for(int32 Y=-1;Y<=1&&!Match;++Y)for(int32 Z=-1;Z<=1&&!Match;++Z)
        {
            const FIntVector Candidate=K+FIntVector(X,Y,Z);
            for(auto It=Centers.CreateConstKeyIterator(Candidate);It;++It)
                if(FVector::DistSquared(Center,It.Value())<=Cell*Cell){Match=true;break;}
        }
        if(Match)Selected.Add(Face);
    }
    if(Selected.Num()!=ComponentFaceCentersCM.Num())
    {
        UE_LOG(LogTemp,Error,TEXT("M24_REAR_SEAT: matched %d of %d source faces; mesh retained"),Selected.Num(),ComponentFaceCentersCM.Num());return false;
    }
    Mesh->Modify();const FPolygonGroupID Group=Description->CreatePolygonGroup();Slots[Group]=TEXT("M24_FactoryRearSeat");
    auto Material=Mesh->GetMaterials()[FrontIndex];Material.MaterialSlotName=TEXT("M24_FactoryRearSeat");Material.ImportedMaterialSlotName=Material.MaterialSlotName;
    Mesh->GetMaterials().Add(Material);
    for(const FPolygonID Face:Selected)Description->SetPolygonPolygonGroup(Face,Group);
    if(!Mesh->CommitMeshDescription(0))return false;
    Mesh->PostEditChange();Mesh->MarkPackageDirty();
    UE_LOG(LogTemp,Display,TEXT("M24_REAR_SEAT: partitioned %d native faces; vertex attributes retained"),Selected.Num());return true;
#else
    return false;
#endif
}

bool UM24ChassisAssetTools::SplitFactoryStock(USkeletalMesh* Mesh,const TArray<FVector>& SourceFaceCentersCM)
{
#if WITH_EDITOR
    if(!Mesh||SourceFaceCentersCM.IsEmpty())return false;
    for(const auto& Material:Mesh->GetMaterials())
        if(Material.MaterialSlotName==TEXT("M24_FactoryStock"))return true;
    auto* Description=Mesh->GetMeshDescription(0);if(!Description)return false;
    int32 BodyIndex=INDEX_NONE;
    for(int32 I=0;I<Mesh->GetMaterials().Num();++I)
        if(Mesh->GetMaterials()[I].MaterialSlotName==TEXT("M24_Body"))BodyIndex=I;
    if(BodyIndex==INDEX_NONE)return false;
    auto* Host=NewObject<USkeletalMeshComponent>();Host->SetSkeletalMeshAsset(Mesh);
    const auto& Ref=Mesh->GetRefSkeleton();FTransform Root=FTransform::Identity;
    for(int32 I=Ref.FindBoneIndex(TEXT("WPN_root"));I!=INDEX_NONE;I=Ref.GetParentIndex(I))Root*=Ref.GetRefBonePose()[I];
    const FTransform SourceToComponent=M24Attachments::Mount(Host)*Root;
    constexpr double Cell=.015;
    auto Key=[](const FVector& P){return FIntVector(FMath::RoundToInt(P.X/Cell),FMath::RoundToInt(P.Y/Cell),FMath::RoundToInt(P.Z/Cell));};
    TMultiMap<FIntVector,FVector> Centers;
    for(const FVector& P:SourceFaceCentersCM)Centers.Add(Key(P),P);
    FSkeletalMeshAttributes Attributes(*Description);
    const auto Positions=Attributes.GetVertexPositions();auto Slots=Attributes.GetPolygonGroupMaterialSlotNames();
    TArray<FPolygonID> Selected;
    for(const FPolygonID Face:Description->Polygons().GetElementIDs())
    {
        const FName Slot=Slots[Description->GetPolygonPolygonGroup(Face)];
        if(Slot!=TEXT("M24_Body")&&Slot!=TEXT("M24_FactoryChassis"))continue;
        const auto Instances=Description->GetPolygonVertexInstances(Face);
        FVector Center=FVector::ZeroVector;
        for(const FVertexInstanceID V:Instances)Center+=FVector(Positions[Description->GetVertexInstanceVertex(V)]);
        Center=SourceToComponent.InverseTransformPosition(Center/Instances.Num());
        const FIntVector K=Key(Center);bool Match=false;
        for(int32 X=-1;X<=1&&!Match;++X)for(int32 Y=-1;Y<=1&&!Match;++Y)for(int32 Z=-1;Z<=1&&!Match;++Z)
        {
            const FIntVector Candidate=K+FIntVector(X,Y,Z);
            for(auto It=Centers.CreateConstKeyIterator(Candidate);It;++It)
                if(FVector::DistSquared(Center,It.Value())<=Cell*Cell){Match=true;break;}
        }
        if(Match)Selected.Add(Face);
    }
    // Match the current shoulder shell exactly; retain all grip and arm data.
    if(Selected.Num()!=SourceFaceCentersCM.Num())
    {
        UE_LOG(LogTemp,Error,TEXT("M24_STOCK: matched %d of %d source faces; mesh retained"),Selected.Num(),SourceFaceCentersCM.Num());
        return false;
    }
    Mesh->Modify();const FPolygonGroupID Group=Description->CreatePolygonGroup();Slots[Group]=TEXT("M24_FactoryStock");
    auto Material=Mesh->GetMaterials()[BodyIndex];Material.MaterialSlotName=TEXT("M24_FactoryStock");Material.ImportedMaterialSlotName=Material.MaterialSlotName;
    Mesh->GetMaterials().Add(Material);
    for(const FPolygonID Face:Selected)Description->SetPolygonPolygonGroup(Face,Group);
    if(!Mesh->CommitMeshDescription(0))return false;
    Mesh->PostEditChange();Mesh->MarkPackageDirty();
    UE_LOG(LogTemp,Display,TEXT("M24_STOCK: partitioned %d shoulder faces; grip, vertex data and morphs retained"),Selected.Num());
    return true;
#else
    return false;
#endif
}
