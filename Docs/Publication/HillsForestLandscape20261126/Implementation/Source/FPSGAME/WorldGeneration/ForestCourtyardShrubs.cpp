#include "ForestCourtyardShrubs.h"
#if WITH_EDITOR
#include "ForestVillageMap.h"
#include "ForestVillageRegion.h"
#include "ForestRootFit.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"

namespace ForestCourtyardShrubs
{
namespace
{
// Mesh and leaf slots from the village's three Normandy planting families; slot 1 is the mesh's own bark.
struct FVariant { const TCHAR* Name; const TCHAR* Leaf; };
const FVariant Variants[]={
    {TEXT("SM_PlantTypeA_00A"),TEXT("MI_Leaf_4f3a42edc511")}, {TEXT("SM_PlantTypeA_01A"),TEXT("MI_Leaf_091d476864b6")}, {TEXT("SM_PlantTypeA_02A"),TEXT("MI_Leaf_3358f0599b31")},
    {TEXT("SM_PlantTypeB_00A"),TEXT("MI_Leaf_2761e974c7dd")}, {TEXT("SM_PlantTypeB_01A"),TEXT("MI_Leaf_8eed6424d21a")}, {TEXT("SM_PlantTypeB_02A"),TEXT("MI_Leaf_2b1e4ad7d8d1")},
    {TEXT("SM_PlantTypeC_00A"),TEXT("MI_Leaf_8fafd42902fb")}, {TEXT("SM_PlantTypeC_01A"),TEXT("MI_Leaf_fa3dbcc37a09")}, {TEXT("SM_PlantTypeC_02A"),TEXT("MI_Leaf_ad37a5c637fe")}
};

struct FDisc { FVector2D Center; double Radius; };
struct FFootprints
{
    explicit FFootprints(double InCell):Cell(InCell){}
    const double Cell;
    TMap<FIntPoint,TArray<FDisc>> Bins;
    FIntPoint Key(FVector2D P) const {return {FMath::FloorToInt32(P.X/Cell),FMath::FloorToInt32(P.Y/Cell)};}
    void Add(FVector2D P,double Radius)
    {
        const FIntPoint Lo=Key(P-FVector2D(Radius)),Hi=Key(P+FVector2D(Radius));
        for(int32 Y=Lo.Y;Y<=Hi.Y;++Y)
            for(int32 X=Lo.X;X<=Hi.X;++X)Bins.FindOrAdd({X,Y}).Add({P,Radius});
    }
    bool Contains(FVector2D P) const
    {
        if(const auto* Bin=Bins.Find(Key(P)))
            for(const auto& D:*Bin)
                if(FVector2D::DistSquared(D.Center,P)<D.Radius*D.Radius)return true;
        return false;
    }
};
}

const TCHAR* LeafOverride(const UStaticMesh* Mesh)
{
    if(!Mesh || !Mesh->GetOutermost()->GetName().StartsWith(TEXT("/Game/UnrealNormandy/StaticMeshes/SM_PlantType")))return nullptr;
    for(const auto& Item:Variants)if(Mesh->GetFName()==Item.Name)return Item.Leaf;
    return nullptr;
}

bool Place(const AForestVillageRegion& Region,const TArray<UInstancedStaticMeshComponent*>& Study,
    TConstArrayView<uint8> CliffMask,const TMap<FIntPoint,FVector4f>& HarvestTrees,
    TArray<UStaticMesh*>& Meshes,TArray<TArray<FTransform>>& Hills,TArray<TArray<FTransform>>& Road)
{
    const int32 Target=Hills[2].Num()+Hills[3].Num();
    if(Target==0 || Hills[12].IsEmpty())return true;
    FFootprints Canopy(1000.),Occupied(300.);
    auto Tree=[&](FVector2D XY){Canopy.Add(XY,850.);Occupied.Add(XY,110.);};
    // The same hills point set is available in both a combined bake and a hills-only bake.
    for(int32 Slot=0;Slot<4;++Slot)
        for(const FTransform& T:Hills[Slot])
        {
            const FVector2D P(T.GetLocation());
            if(Slot<2)Tree(P);else Occupied.Add(P,125.);
        }
    for(const auto& Site:HarvestTrees)Tree(FVector2D(Site.Value.X,Site.Value.Y));
    for(auto* Component:Study)
    {
        const UStaticMesh* Mesh=Component?Component->GetStaticMesh().Get():nullptr;
        if(!Mesh)continue;
        const bool Trunk=Mesh->GetName().StartsWith(TEXT("SM_EuropeanHornbeam_Forest_"));
        if(!Trunk && !Mesh->GetName().StartsWith(TEXT("SM_CommonHazel_Forest_")))continue;
        FTransform T;
        for(int32 I=0;I<Component->GetInstanceCount();++I)
            if(Component->GetInstanceTransform(I,T,true))
            {
                const FVector2D P(T.GetLocation());
                if(Trunk)Tree(P);else Occupied.Add(P,125.);
            }
    }
    for(int32 Slot=16;Slot<Meshes.Num();++Slot)
    {
        if(!Meshes[Slot] || Hills[Slot].IsEmpty())continue;
        const FString Path=Meshes[Slot]->GetOutermost()->GetName();
        if(!Path.Contains(TEXT("/Granite/")) && !Path.Contains(TEXT("/Scans/")) && !Path.Contains(TEXT("/Cliff")))continue;
        const FBox Box=Meshes[Slot]->GetBoundingBox();
        for(const FTransform& T:Hills[Slot])
        {
            const double Radius=Box.GetExtent().GetMax()*T.GetScale3D().GetMax();
            if(Radius>=60.)Occupied.Add(FVector2D(T.TransformPosition(Box.GetCenter())),Radius+35.);
        }
    }
    struct FCandidate {FVector2D Position; uint32 Seed; double Priority;};
    TArray<FCandidate> Sites;
    const FIntPoint Town=Region.GetSettlementMinM();
    constexpr int32 Width=ForestVillageMap::SideMeters+1;
    const auto Water=Region.GetWoodlandWater();
    // Existing low-grass points already carry the quarry, path and terrain suitability masks.
    for(const auto& Grass:Hills[12])
    {
        const FVector2D P(Grass.GetLocation());
        const FIntPoint XY(FMath::RoundToInt(P.X),FMath::RoundToInt(P.Y));
        const uint32 Seed=HashCombineFast(GetTypeHash(XY),0xd2a7e19bU);
        if((Seed&3u)!=0 || !Canopy.Contains(P) || Occupied.Contains(P))continue;
        const FVector2D M=P*.01;
        if(M.X>Town.X-4 && M.X<Town.X+122 && M.Y>Town.Y-4 && M.Y<Town.Y+149)continue;
        if(Region.MapRoadWeight(P.X,P.Y)>.06)continue;
        const int32 X=FMath::Clamp(FMath::RoundToInt(M.X)-ForestVillageMap::West,0,Width-1);
        const int32 Y=FMath::Clamp(FMath::RoundToInt(M.Y)-ForestVillageMap::South,0,Width-1);
        if(CliffMask.Num()==Width*Width && CliffMask[Y*Width+X]>55)continue;
        const double DX=Region.GroundHeight(P.X+70.,P.Y)-Region.GroundHeight(P.X-70.,P.Y);
        const double DY=Region.GroundHeight(P.X,P.Y+70.)-Region.GroundHeight(P.X,P.Y-70.);
        if(DX*DX+DY*DY>FMath::Square(140.*.67))continue;
        if(Water && (Water->Sample(P.X,P.Y).Wet || Water->ShoreMoistureAt(P.X,P.Y)>.28))continue;
        const double Patch=FMath::PerlinNoise2D(P/950.+FVector2D(19.34,-41.67));
        FRandomStream R(Seed);
        Sites.Add({P,Seed,Patch+R.FRandRange(-.38f,.38f)});
    }
    Sites.Sort([](const FCandidate& A,const FCandidate& B)
    {
        if(A.Priority!=B.Priority)return A.Priority>B.Priority;
        if(A.Position.X!=B.Position.X)return A.Position.X<B.Position.X;
        return A.Position.Y<B.Position.Y;
    });
    const int32 First=Meshes.Num();
    TArray<FVector2D,TInlineAllocator<9>> Roots;
    for(const auto& V:Variants)
    {
        FString Path=FString::Printf(TEXT("/Game/UnrealNormandy/StaticMeshes/%s.%s"),V.Name,V.Name);
        auto* Mesh=LoadObject<UStaticMesh>(nullptr,*Path);
        if(!Mesh){UE_LOG(LogTemp,Error,TEXT("Missing village shrub %s"),*Path);return false;}
        Meshes.Add(Mesh);Hills.AddDefaulted();Road.AddDefaulted();
        Roots.Add(ForestRootFit::Measure(Mesh));
    }
    int32 Added=0;
    for(const FCandidate& Site:Sites)
    {
        const FVector2D P=Site.Position;
        if(Occupied.Contains(P))continue;
        FRandomStream R(HashCombineFast(Site.Seed,0x35be6fa9u));
        const float Choice=R.FRand();
        const int32 Family=Choice<.46f?0:Choice<.82f?1:2;
        const int32 Variant=Family*3+R.RandRange(0,2);
        const double Scale=R.FRandRange(.62f,.97f);
        const double Z=ForestRootFit::Seat(P,Roots[Variant].X*Scale,Roots[Variant].Y*Scale,
            [&Region](double X,double Y){return Region.GroundHeight(X,Y);});
        Hills[First+Variant].Emplace(FRotator(0,R.FRandRange(-180.f,180.f),0),FVector(P,Z),FVector(Scale));
        Occupied.Add(P,R.FRandRange(115.f,190.f));
        if(++Added>=Target)break;
    }
    UE_LOG(LogTemp,Display,TEXT("Forest courtyard shrubs: %d added to %d existing hills hazels"),Added,Target);
    return true;
}
}
#endif
