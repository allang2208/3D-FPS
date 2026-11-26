#include "ForestReferenceBoulders.h"
#if WITH_EDITOR
#include "ForestVillageRegion.h"
#include "Engine/StaticMesh.h"
#include "MeshDescription.h"

namespace ForestReferenceBoulders
{
// The study places these three as StaticMeshActors outside its exported PCG point sets.
static const TCHAR* const ScanIds[]={TEXT("wc1kedt"),TEXT("rgAsy"),TEXT("rgfoh")};

bool IsReferenceMesh(const UStaticMesh* Mesh)
{
    return Mesh && Mesh->GetOutermost()->GetName().StartsWith(TEXT("/Game/ForestPathStudy/Scans/"))
        && (Mesh->GetFName()==TEXT("wc1kedt_tier_1") || Mesh->GetFName()==TEXT("rgAsy_tier_1") || Mesh->GetFName()==TEXT("rgfoh_tier_1"));
}

bool Place(const AForestVillageRegion& Region,TArray<UStaticMesh*>& Meshes,
           TArray<TArray<FTransform>>& Hills,TArray<TArray<FTransform>>& Road)
{
    const int32 First=Meshes.Num();
    struct FSite {int32 Slot,Index; FVector Position; double Width; uint32 Rank;};
    TArray<FSite> Sites;
    for(int32 Slot=0;Slot<First;++Slot)
    {
        if(Hills[Slot].IsEmpty() || !Meshes[Slot])continue;
        const FString Path=Meshes[Slot]->GetOutermost()->GetName();
        if(!Path.StartsWith(TEXT("/Game/ForestPathStudy/VillageRegion/Granite/")) &&
           !Path.Contains(TEXT("/vikrdcnaw/")) && !Path.Contains(TEXT("/vimrfjsaw/")) &&
           !Path.Contains(TEXT("/xisffer/")) && !Path.Contains(TEXT("/xiemca1/")) && !Path.Contains(TEXT("/xjijdiz/")))continue;
        const FBox Box=Meshes[Slot]->GetBoundingBox();
        for(int32 I=0;I<Hills[Slot].Num();++I)
        {
            const FTransform& T=Hills[Slot][I];
            const double Width=FMath::Max(Box.GetSize().X,Box.GetSize().Y)*T.GetScale3D().X;
            if(Width<130.)continue;
            const FVector P=T.TransformPosition(FVector(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z));
            if(FMath::Max(FMath::Abs(P.X),FMath::Abs(P.Y))<25200.+Width)continue;
            const FIntPoint XY(FMath::RoundToInt(P.X),FMath::RoundToInt(P.Y));
            const uint32 Rank=HashCombineFast(0x8acb31d5u,GetTypeHash(XY));
            Sites.Add({Slot,I,P,Width,Rank});
        }
    }
    if(Sites.IsEmpty())
    {
        // Keep downstream cliff/talus slot indices identical on a road-only bake.
        Meshes.AddZeroed(UE_ARRAY_COUNT(ScanIds));
        Hills.AddDefaulted(UE_ARRAY_COUNT(ScanIds));
        Road.AddDefaulted(UE_ARRAY_COUNT(ScanIds));
        return true;
    }
    TArray<double,TInlineAllocator<3>> BaseHeights;
    for(const TCHAR* Id:ScanIds)
    {
        const FString Path=FString::Printf(TEXT("/Game/ForestPathStudy/Scans/%s/%s_tier_1/StaticMeshes/%s_tier_1.%s_tier_1"),Id,Id,Id,Id);
        UStaticMesh* Mesh=LoadObject<UStaticMesh>(nullptr,*Path);
        if(!Mesh)
        {
            UE_LOG(LogTemp,Error,TEXT("Forest boulder missing %s"),*Path);
            return false;
        }
        const FMeshDescription* Desc=Mesh->GetMeshDescription(0);
        if(!Desc || !Desc->Vertices().Num())return false;
        TArray<double> Heights;
        const auto Positions=Desc->GetVertexPositions();
        const double BuildZ=Mesh->GetSourceModel(0).BuildSettings.BuildScale3D.Z;
        for(FVertexID Vertex:Desc->Vertices().GetElementIDs())Heights.Add(Positions[Vertex].Z*BuildZ);
        Heights.Sort();
        BaseHeights.Add(Heights[Heights.Num()/10]);
        Meshes.Add(Mesh); Hills.AddDefaulted(); Road.AddDefaulted();
    }
    Sites.Sort([](const FSite& A,const FSite& B)
    {
        if(A.Rank!=B.Rank)return A.Rank<B.Rank;
        if(A.Position.X!=B.Position.X)return A.Position.X<B.Position.X;
        return A.Position.Y<B.Position.Y;
    });
    TArray<FVector2D> Placed;
    TArray<TArray<int32>> Replacements;
    Replacements.SetNum(First);
    for(const FSite& Site:Sites)
    {
        const FVector2D XY(Site.Position);
        if(Placed.ContainsByPredicate([&](FVector2D P){return FVector2D::DistSquared(P,XY)<FMath::Square(4800.);}))continue;
        const int32 Slot=First+Site.Rank%UE_ARRAY_COUNT(ScanIds);
        const FBox Box=Meshes[Slot]->GetBoundingBox();
        const FVector Size=Box.GetSize();
        const double Scale=Site.Width/FMath::Max(Size.X,Size.Y);
        const FQuat Rotation=Hills[Site.Slot][Site.Index].GetRotation();
        FVector Anchor(XY,Region.GroundHeight(XY.X,XY.Y));
        const double Radius=Site.Width*.28;
        for(const FVector2D Offset:{FVector2D(Radius,0),FVector2D(-Radius,0),FVector2D(0,Radius),FVector2D(0,-Radius)})
        {
            const FVector2D P=XY+Offset;
            const FVector Up=Rotation.GetUpVector();
            const double PlaneDZ=-(Offset.X*Up.X+Offset.Y*Up.Y)/FMath::Max(.1,Up.Z);
            Anchor.Z=FMath::Min(Anchor.Z,Region.GroundHeight(P.X,P.Y)-PlaneDZ);
        }
        Anchor.Z-=FMath::Clamp(Size.Z*Scale*.15,6.,24.);
        const FVector LocalFoot(Box.GetCenter().X,Box.GetCenter().Y,BaseHeights[Slot-First]);
        Hills[Slot].Emplace(Rotation,Anchor-Rotation.RotateVector(LocalFoot*Scale),FVector(Scale));
        Replacements[Site.Slot].Add(Site.Index);
        Placed.Add(XY);
    }
    for(int32 Slot=0;Slot<First;++Slot)
    {
        Replacements[Slot].Sort(TGreater<int32>());
        for(int32 I:Replacements[Slot])Hills[Slot].RemoveAtSwap(I,1,EAllowShrinking::No);
    }
    return true;
}
}
#endif
