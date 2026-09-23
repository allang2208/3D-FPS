#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"

namespace DungeonDressingTests
{
using namespace DungeonDressing;
static DungeonDressing::FGeometry Solid(const FBox& Box,const FTransform& Room,bool Floor=false,bool Wall=false)
{
    Chaos::FTriangleMeshImplicitObject::ParticlesType Vertices;Vertices.AddParticles(8);
    for(int32 I=0;I<8;++I) Vertices.SetX(I,FVector3f(I&1?Box.Max.X:Box.Min.X,I&2?Box.Max.Y:Box.Min.Y,I&4?Box.Max.Z:Box.Min.Z));
    TArray<Chaos::TVec3<int32>> Faces={{0,2,1},{1,2,3},{4,5,6},{5,7,6},
        {0,4,2},{2,4,6},{1,3,5},{3,7,5},{0,1,4},{1,5,4},{2,6,3},{3,6,7}};
    DungeonDressing::FGeometry G;G.Transform=Room;G.Bounds=Box.TransformBy(Room);G.Module=0;
    G.Name=TEXT("SyntheticStructure");G.Floor=Floor;G.Wall=Wall;
    G.Triangles.Add(Chaos::FTriangleMeshImplicitObjectPtr(new Chaos::FTriangleMeshImplicitObject(MoveTemp(Vertices),MoveTemp(Faces),TArray<uint16>())));
    return G;
}
static FObject Module()
{
    auto M=MakeShared<FJsonObject>();M->SetStringField(TEXT("id"),TEXT("Treasure"));
    auto Cell=MakeShared<FJsonObject>();Cell->SetArrayField(TEXT("min"),Array(FVector(-1000,-1000,-100)));
    Cell->SetArrayField(TEXT("max"),Array(FVector(1000,1000,900)));
    M->SetArrayField(TEXT("cells"),{MakeShared<FJsonValueObject>(Cell)});
    M->SetArrayField(TEXT("ports"),{});M->SetArrayField(TEXT("anchors"),{});return M;
}
static FObject Part(double Z=0,bool Wall=false)
{
    auto P=MakeShared<FJsonObject>();P->SetArrayField(TEXT("position"),Array(FVector(Wall?575:400,Wall?-400:-300,Z)));
    P->SetBoolField(TEXT("dressing_wall"),Wall);
    if(Wall) P->SetArrayField(TEXT("dressing_normal"),Array(FVector(-1,0,0)));
    return P;
}
static FPlacementScene Scene(const FTransform& Room=FTransform::Identity,double Z=0)
{
    FPlacementScene S;S.Geometry.Add(Solid(FBox(FVector(-900,-900,Z-20),FVector(900,900,Z)),Room,true));return S;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FAuthoredDungeonDressingClearanceTest,"FPSGAME.Dungeon.Dressing.Clearance",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FAuthoredDungeonDressingClearanceTest::RunTest(const FString&)
{
    using namespace DungeonDressing;using namespace DungeonDressingTests;
    const FBox Asset(FVector(-25,-30,-17),FVector(25,30,90));
    const auto M=Module();FString Reason;
    auto PlaceFloor=[&](FPlacementScene& S,const FTransform& Room=FTransform::Identity,double Z=0)
    {
        const auto P=Part(Z);FTransform T=FTransform(Vector(P,TEXT("position")))*Room;
        return S.Place(Asset,P,M,Room,0,T,Reason);
    };
    {
        auto S=Scene();const auto P=Part();FTransform T(Vector(P,TEXT("position")));
        TestTrue(TEXT("Flat slab accepts an asset whose pivot is below its geometry"),S.Place(Asset,P,M,FTransform::Identity,0,T,Reason));
        TestTrue(TEXT("Actual asset bottom sits 2 mm above the slab"),FMath::IsNearlyEqual(Asset.TransformBy(T).Min.Z,.2,.001));
        TestFalse(TEXT("A second prop cannot occupy the first prop"),PlaceFloor(S));
    }
    {
        const FTransform Room(FRotator(0,90,0),FVector(12345,-5678,94));auto S=Scene(Room);
        const auto P=Part();FTransform T=FTransform(Vector(P,TEXT("position")))*Room;
        TestTrue(TEXT("Rotated and elevated room accepts floor contact"),S.Place(Asset,P,M,Room,0,T,Reason));
        TestTrue(TEXT("Floor snap remains in world coordinates"),FMath::IsNearlyEqual(Asset.TransformBy(T).Min.Z,94.2,.001));
    }
    {
        auto S=Scene();TestFalse(TEXT("Missing gallery never falls through to the ground floor"),PlaceFloor(S,FTransform::Identity,360));
        S=Scene(FTransform::Identity,360);TestTrue(TEXT("Gallery supports its own storey"),PlaceFloor(S,FTransform::Identity,360));
        S=Scene();TestFalse(TEXT("A bad negative authored height cannot bury a prop"),PlaceFloor(S,FTransform::Identity,-50));
    }
    {
        FPlacementScene S;S.Geometry.Add(Solid(FBox(FVector(380,-900,-20),FVector(410,900,0)),FTransform::Identity,true));
        TestFalse(TEXT("Centre support alone cannot allow overhang at a platform edge"),PlaceFloor(S));
        S=Scene();S.Geometry.Add(Solid(FBox(FVector(400,-900,0),FVector(900,900,4)),FTransform::Identity,true));
        TestFalse(TEXT("A step under half of the footprint rejects the prop"),PlaceFloor(S));
    }
    {
        auto S=Scene();S.Geometry.Add(Solid(FBox(FVector(418,-390,55),FVector(420,-210,58)),FTransform::Identity));
        TestFalse(TEXT("Thin horizontal rail intersects the entire prop volume"),PlaceFloor(S));
        S=Scene();S.Geometry.Add(Solid(FBox(FVector(350,-360,-20),FVector(450,-240,300)),FTransform::Identity));
        TestFalse(TEXT("A prop fully enclosed by a solid column is rejected"),PlaceFloor(S));
        S=Scene();S.Geometry.Add(Solid(FBox(FVector(350,-360,130),FVector(450,-240,135)),FTransform::Identity));
        TestTrue(TEXT("A pipe above sufficient head clearance does not block the floor"),PlaceFloor(S));
        S=Scene();S.Geometry.Add(Solid(FBox(FVector(350,-360,100),FVector(450,-240,105)),FTransform::Identity));
        TestFalse(TEXT("A low pipe through the top of a prop is rejected"),PlaceFloor(S));
    }
    {
        auto S=Scene();auto Unknown=Solid(FBox(FVector(390,-340,20),FVector(410,-260,80)),FTransform::Identity);
        Unknown.Triangles.Reset();S.Geometry.Add(MoveTemp(Unknown));
        TestFalse(TEXT("Missing collision geometry does not count as empty space"),PlaceFloor(S));
    }
    {
        const FBox Web(FVector(-10,-25,0),FVector(10,25,60));const auto P=Part(280,true);
        auto S=Scene();FTransform T(Vector(P,TEXT("position")));
        TestFalse(TEXT("A web needs a real wall"),S.Place(Web,P,M,FTransform::Identity,0,T,Reason));
        S.Geometry.Add(Solid(FBox(FVector(600,-800,0),FVector(620,0,400)),FTransform::Identity,false,true));
        T=FTransform(Vector(P,TEXT("position")));
        TestTrue(TEXT("A supported web attaches without intersecting its support wall"),S.Place(Web,P,M,FTransform::Identity,0,T,Reason));
        TestTrue(TEXT("Web bounding box remains outside wall volume"),FMath::IsNearlyEqual(Web.TransformBy(T).Max.X,599.7,.001));
        S.Accepted.Reset();S.Geometry.Add(Solid(FBox(FVector(550,-800,320),FVector(650,0,330)),FTransform::Identity));
        T=FTransform(Vector(P,TEXT("position")));
        TestFalse(TEXT("Web cannot cut through a ceiling or beam"),S.Place(Web,P,M,FTransform::Identity,0,T,Reason));
    }
    return true;
}
#endif
