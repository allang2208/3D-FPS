#include "ChapelCourtyardDressing.h"
#include "VillageMasonry.h"
#include "TemperateChapelSite.h"
#include "Engine/StaticMesh.h"

namespace ChapelCourtyardDressing
{
namespace
{
    struct FDetailMesh
    {
        FName Role;
        FString Path;
    };

    const FDetailMesh Palette[] = {
        {TEXT("CourtyardGrass"), TEXT("/Game/WorldGeneration/TemperateHills/WetForest/ScannedGrass/SM_SoftWildGrassTuft.SM_SoftWildGrassTuft")},
        {TEXT("CourtyardHerb"), TEXT("/Game/UnrealNormandy/StaticMeshes/SM_PlantTypeB_01A.SM_PlantTypeB_01A")},
        {TEXT("CourtyardRoughGrass"), TEXT("/Game/UnrealNormandy/StaticMeshes/SM_GrassTall_00A.SM_GrassTall_00A")},
        {TEXT("CourtyardHazel"), TEXT("/Game/WorldGeneration/TemperateHills/ForestSpecies20261110/Meshes/SM_Hazel_B.SM_Hazel_B")},
        {TEXT("CourtyardFlower"), TEXT("/Game/PN_FoliageCollection/Meshes/flowerMesh/flower_07_01.flower_07_01")},
        {TEXT("CourtyardFieldstone"), TEXT("/Game/UnrealNormandy/StaticMeshes/SM_Stone_01A.SM_Stone_01A")},
        {TEXT("CourtyardChips"), VillageMasonry::Mesh(TEXT("SM_VillageWallRubbleA")).ToString()}
    };

}

void AddMeshPaths(TArray<FSoftObjectPath>& Paths)
{
    for(const auto& Item : Palette) Paths.AddUnique(FSoftObjectPath(Item.Path));
}

void ResolveMeshes(TMap<FName,UStaticMesh*>& Meshes)
{
    for(const auto& Item : Palette)
        if(auto* Mesh=Cast<UStaticMesh>(FSoftObjectPath(Item.Path).ResolveObject())) Meshes.Add(Item.Role,Mesh);
}

bool IsDetail(FName Role)
{
    for(const auto& Item : Palette) if(Role==Item.Role) return true;
    return false;
}

void Place(const FTemperateChapelSite& Chapel, int32 Seed, FPlaceOnSoil PlaceOnSoil)
{
    FRandomStream Random(Seed ^ 0x106A19F);
    constexpr double Size=FTemperateChapelSite::AssemblyScale;
    const auto& Graves=FTemperateChapelSite::Graves;

    auto Plant=[&](FName Kind,FVector2D P,double Width,double Height)
    {
        const FVector2D At=Chapel.World(P.X*Size,P.Y*Size);
        if(Chapel.Clears(At.X,At.Y,Width*.45)) return false;
        PlaceOnSoil(Kind,P,Width,Height,Random.FRandRange(0.f,360.f),1.5);
        return true;
    };

    const FVector2D YardMin=Chapel.Local(Chapel.YardNodes[4])/Size;
    const FVector2D YardMax=Chapel.Local(Chapel.YardNodes[2])/Size;
    const FVector2D NoiseOffset(Random.FRandRange(-90.f,90.f),Random.FRandRange(-90.f,90.f));
    const auto BoxDistance=[](FVector2D Local,double HalfX,double HalfY)
    {
        return FVector2D(FMath::Max(0.,FMath::Abs(Local.X)-HalfX),
                         FMath::Max(0.,FMath::Abs(Local.Y)-HalfY)).Size();
    };

    // The whole enclosure is sampled in area. A damp footprint runs around the
    // nave and into the court corners; the crest and the worn tracks stay open.
    // A second, smaller wavelength breaks the edges within each stand.
    for(int32 I=0;I<2300;++I)
    {
        const FVector2D P(Random.FRandRange(YardMin.X+31.,YardMax.X-31.),
                          Random.FRandRange(YardMin.Y+31.,YardMax.Y-31.));
        const double Nave=BoxDistance(P,815.,417.);
        if(Nave<9.)continue;
        const double YardX=FMath::Min(P.X-YardMin.X,YardMax.X-P.X);
        const double YardY=FMath::Min(P.Y-YardMin.Y,YardMax.Y-P.Y);
        const double YardWall=FMath::Min(YardX,YardY);
        const double Corner=1.-FMath::SmoothStep(140.,670.,FMath::Max(YardX,YardY));
        const double Broad=FMath::PerlinNoise2D(P/287.+NoiseOffset);
        const double Fine=FMath::PerlinNoise2D(P/79.-NoiseOffset);
        const double WallReach=290.+205.*Broad+85.*Fine+210.*Corner;
        const double YardCover=1.-FMath::SmoothStep(38.,WallReach,YardWall);
        const double NaveCover=1.-FMath::SmoothStep(20.,335.+170.*Broad+60.*Fine,Nave);
        const double Shelter=FMath::Max(YardCover,NaveCover*.91);
        const FVector2D At=Chapel.World(P.X*Size,P.Y*Size);
        double Along=0.;
        const double DoorTrack=Chapel.PathOffset(At,Along)/Size-53.;
        const double GraveTrack=Chapel.GraveWalkDistance(P)-27.;
        const double Tread=FMath::Min(DoorTrack,GraveTrack);
        const double WalkFringe=FMath::SmoothStep(-4.,65.,Tread);
        if(WalkFringe==0.)continue;
        const double LeafCover=FMath::Clamp(.84*Shelter+.27+Broad*.95+Fine*.38,0.,1.);
        if(Random.FRand()>WalkFringe*(.025+.77*LeafCover*LeafCover))continue;

        // Each rooted tussock has a few touching satellites. Some carry seed
        // heads or broadleaf herbs, and others are grazed down to fine blades.
        const double LongGrass=WalkFringe*Shelter*(.70+.30*LeafCover);
        const double Width=Random.FRandRange(38.f,72.f)*(1.+.35*LeafCover);
        const bool Coarse=Random.FRand()<LongGrass*.68;
        if(!Plant(Coarse?TEXT("CourtyardRoughGrass"):TEXT("CourtyardGrass"),P,
                  Width,Random.FRandRange(12.f,22.f)+LongGrass*(Coarse?30.:8.)))continue;
        const int32 Shoots=Random.RandRange(1,3);
        for(int32 J=0;J<Shoots;++J)
        {
            const double Angle=Random.FRandRange(0.f,2.f*PI);
            const double Spread=Width/Size*Random.FRandRange(.30f,.81f);
            const FVector2D Shoot=P+FVector2D(FMath::Cos(Angle),FMath::Sin(Angle))*Spread;
            if(Shoot.X<YardMin.X+30.||Shoot.X>YardMax.X-30.||
               Shoot.Y<YardMin.Y+30.||Shoot.Y>YardMax.Y-30.)continue;
            const bool Herb=Random.FRand()<LongGrass*.27;
            Plant(Herb?TEXT("CourtyardHerb"):TEXT("VergeGrass"),Shoot,
                  Width*Random.FRandRange(.46f,.84f),Random.FRandRange(6.f,13.f)+(Herb?17.:8.)*LongGrass);
        }
    }

    // Two suckers share the shelter of the rear wall return, well away from the pew.
    const FVector2D RearCorner=Chapel.Local(Chapel.YardNodes[2])/Size;
    Plant(TEXT("CourtyardHazel"),RearCorner-FVector2D(124.,108.),153.,98.);
    Plant(TEXT("CourtyardHazel"),RearCorner-FVector2D(179.,87.),83.,55.);

    // Fallen faces catch on the bearing plinth. A little gravel spills through
    // either end of a deposit, getting smaller and more embedded as it runs out.
    struct FFoot { double Pier, Side, Hand, Width; int32 Fragments; };
    const FFoot Pockets[]={{-754.,-1.,-1.,43.,11},{0.,-1.,1.,29.,5},
                           {400.,1.,-1.,37.,7},{-754.,1.,1.,48.,13}};
    for(const FFoot& Foot : Pockets)
    {
        const FVector2D Corner(Foot.Pier+Foot.Hand*48.,Foot.Side*423.);
        const FVector2D Along(Foot.Hand,0.),Out(0.,Foot.Side);
        const FVector2D Litter=Corner+Along*(Foot.Width*.37/Size)+Out*16.;
        PlaceOnSoil(TEXT("CourtyardChips"),Litter,Foot.Width,6.5,Foot.Hand*21.,3.2);
        for(int32 I=0;I<Foot.Fragments;++I)
        {
            const double Drift=Random.FRand();
            const double Spread=Random.FRandRange(-.42f,.76f);
            const FVector2D P=Litter+Along*(8.+Drift*Foot.Width*(.65+Spread))+Out*(Spread*11.+Drift*Drift*38.);
            const double Width=Random.FRandRange(7.f,17.f)*(1.-.58*Drift);
            PlaceOnSoil(TEXT("YardPathStone"),P,Width,Width*Random.FRandRange(.32f,.48f),
                        Random.FRandRange(-180.f,180.f),Width*(.16+.12*Drift));
        }
        Plant(TEXT("CourtyardGrass"),Corner+Along*46.+Out*28.,35.,16.);
        Plant(TEXT("CourtyardHerb"),Corner+Along*20.+Out*49.,24.,21.);
    }

    // At the north-east return, pieces of the same cap as the enclosure have
    // settled at the pier toe. Their size and exposure fall away from the joint.
    PlaceOnSoil(TEXT("YardPathStone"),RearCorner-FVector2D(41.,32.),32.,8.,12.,3.9);
    PlaceOnSoil(TEXT("YardPathStone"),RearCorner-FVector2D(62.,31.),18.,5.,-22.,3.0);
    PlaceOnSoil(TEXT("CourtyardFieldstone"),RearCorner-FVector2D(51.,44.),13.,6.,35.,3.7);

    // The exposed end of the bottom stair sheds grit into the unwalked side of
    // the landing. Keep the centre and the route around the pew free.
    const FVector2D StairToe(-916.,101.);
    for(int32 I=0;I<16;++I)
    {
        const double Run=Random.FRand();
        const double Width=Random.FRandRange(4.5f,12.f)*(1.-.48*Run);
        const FVector2D P=StairToe+FVector2D(-Run*61.+Random.FRandRange(-8.f,9.f),
                9.+Run*29.+Random.FRandRange(-11.f,15.f));
        PlaceOnSoil(TEXT("YardPathStone"),P,Width,Width*.42,
                    Random.FRandRange(-180.f,180.f),Width*(.17+.10*Run));
    }

    // A burial plot extends behind its marker. Leave the visitor's side bare
    // and keep the newer grave clipped; only the older plots carry taller grass.
    for(int32 G=0;G<UE_ARRAY_COUNT(Graves);++G)
    {
        const auto& Grave=Graves[G];
        const int32 Count=G==0?8:(G==1?15:13);
        for(int32 I=0;I<Count;++I)
        {
            const double Along=Random.FRandRange(0.f,1.f);
            const double Side=Random.FRandRange(-1.f,1.f)*(33.-Along*13.);
            const FVector2D P=Grave.FromFace(-21.-Along*98.,Side);
            const bool Tall=(G==1 && Along>.45);
            Plant(Tall?TEXT("CourtyardRoughGrass"):TEXT("CourtyardGrass"),P,
                  Random.FRandRange(23.f,39.f),Tall?Random.FRandRange(21.f,34.f):Random.FRandRange(8.f,16.f));
        }
    }
    // A rooted planting nestles beside one edge of the tended marker;
    // stems and leaves share the terrain support at the foot of the stone.
    const FVector2D Flowers=Graves[0].FromFace(7.,32.);
    PlaceOnSoil(TEXT("CourtyardFlower"),Flowers,22.,16.,-19.,1.3);
    PlaceOnSoil(TEXT("CourtyardFlower"),Graves[0].FromFace(13.,42.),15.,12.,37.,1.1);
    PlaceOnSoil(TEXT("VergeGrass"),Graves[0].FromFace(-2.,46.),24.,11.,77.,1.3);

    // Walkers leave the common path at different points. A single kneeling
    // slab serves the tended grave, two bedded flats cross to the deeper middle grave.
    const auto& Walk=FTemperateChapelSite::GraveWalk;
    const FVector2D A=Walk[UE_ARRAY_COUNT(Walk)-2],D=Walk[UE_ARRAY_COUNT(Walk)-1]-A;
    for(int32 G=0;G<2;++G)
    {
        const FVector2D Stop=Graves[G].FromFace(41.);
        const double T=FMath::Clamp(FVector2D::DotProduct(Stop-A,D)/D.SizeSquared(),0.,1.);
        const FVector2D Turn=A+D*T;
        PlaceOnSoil(TEXT("YardPathStone"),Stop,G==0?64.:52.,9.,Graves[G].Yaw-90.,6.);
        if(G==1) PlaceOnSoil(TEXT("YardPathStone"),FMath::Lerp(Turn,Stop,.51),38.,7.,-11.,5.);
    }
}
}
