#include "HillsTavernInterior.h"
#include "VillageInteriorLighting.h"
#include "VillageShopTorches.h"

#include "Components/InstancedStaticMeshComponent.h"
#include "Components/MaterialBillboardComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInterface.h"
#include "Misc/PackageName.h"

namespace
{
// Objects with no blocking collision are tabletop dressing and wall-mounted fixtures.
enum class EProp : uint8
{
    Table, Stool, Counter, Rack, BrokenTable, BrokenStool, BrokenCounter, Cask, TapCask,
    Cup, Jug, Dish, Sherd, Bread, Baguette, Sausage, Chicken, Ribs, Lantern, Timber,
    GameBoard, AbandonedBoard, DryingRack, EmptyDryingRack,
    Screen, DamagedScreen, Hearth, ColdHearth, PrepBench, BrokenPrepBench, WashStand, BrokenWashStand,
    Carrots, Bowl, StewBowl, BrokenBowl, Chopsticks, WoodSpoon, Count
};
struct FPropModel { const TCHAR* Package; bool bBlocks; };
constexpr FPropModel Models[] = {
    {TEXT("/Game/WorldGeneration/VillageTavern/Furniture/SM_TavernTable"),true},
    {TEXT("/Game/WorldGeneration/VillageTavern/Furniture/SM_TavernStool"),true},
    {TEXT("/Game/WorldGeneration/VillageTavern/Furniture/SM_TavernCounter_Service"),true},
    {TEXT("/Game/WorldGeneration/VillageTavern/Furniture/SM_TavernBackbar"),true},
    {TEXT("/Game/WorldGeneration/VillageTavern/Furniture/SM_TavernBrokenTable"),true},
    {TEXT("/Game/WorldGeneration/VillageTavern/Furniture/SM_TavernBrokenStool"),true},
    {TEXT("/Game/WorldGeneration/VillageTavern/Furniture/SM_TavernBrokenCounter"),true},
    {TEXT("/Game/WorldGeneration/VillageTavern/Service/SM_TavernAleCask"),true},
    {TEXT("/Game/WorldGeneration/VillageTavern/Service/SM_TavernTapCask"),true},
    {TEXT("/Game/WorldGeneration/VillageTavern/StonewareDetail/SM_TavernTankard"),false},
    {TEXT("/Game/WorldGeneration/VillageTavern/StonewareDetail/SM_TavernPitcher"),false},
    {TEXT("/Game/WorldGeneration/VillageTavern/StonewareDetail/SM_TavernDish"),false},
    {TEXT("/Game/WorldGeneration/VillageTavern/StonewareDetail/SM_TavernSherd"),false},
    {TEXT("/Game/Items/Consumables/Bread20261003/SM_Bread"),false},
    {TEXT("/Game/Items/Consumables/Baguette20261003/SM_Baguette"),false},
    {TEXT("/Game/Items/Consumables/Sausage20261014/Roasted/SM_RoastedSausage"),false},
    {TEXT("/Game/Items/Consumables/ChickenLeg20261014/Roasted/SM_RoastedChickenLeg"),false},
    {TEXT("/Game/Items/Consumables/LambRibs20261014/Roasted/SM_RoastedLambRibs"),false},
    {TEXT("/Game/UnrealNormandy/StaticMeshes/SM_Props_Lantern_02A"),false},
    {TEXT("/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Meshes/SM_VillageAbandonedTimber"),false},
    {TEXT("/Game/WorldGeneration/VillageTavern/TableGame/SM_TavernTablesBoard"),false},
    {TEXT("/Game/WorldGeneration/VillageTavern/TableGame/SM_TavernTablesBoardRuined"),false},
    {TEXT("/Game/WorldGeneration/VillageTavern/DryingRack/SM_TavernDryingRack"),false},
    {TEXT("/Game/WorldGeneration/VillageTavern/DryingRack/SM_TavernDryingRackRuined"),false},
    {TEXT("/Game/WorldGeneration/VillageTavern/KitchenScreen/SM_TavernKitchenScreen"),true},
    {TEXT("/Game/WorldGeneration/VillageTavern/KitchenScreen/SM_TavernKitchenScreenRuined"),true},
    {TEXT("/Game/WorldGeneration/VillageTavern/KitchenHearth/SM_TavernCookHearth"),true},
    {TEXT("/Game/WorldGeneration/VillageTavern/KitchenHearth/SM_TavernCookHearthRuined"),true},
    {TEXT("/Game/WorldGeneration/VillageTavern/KitchenStations/SM_TavernPrepBench"),true},
    {TEXT("/Game/WorldGeneration/VillageTavern/KitchenStations/SM_TavernPrepBenchRuined"),true},
    {TEXT("/Game/WorldGeneration/VillageTavern/KitchenStations/SM_TavernWashStand"),true},
    {TEXT("/Game/WorldGeneration/VillageTavern/KitchenStations/SM_TavernWashStandRuined"),true},
    {TEXT("/Game/Items/CropHarvest20261111/Meshes/SM_Harvest_Carrot"),false},
    {TEXT("/Game/WorldGeneration/VillageTavern/DiningBowls/SM_TavernEatingBowl"),false},
    {TEXT("/Game/WorldGeneration/VillageTavern/DiningBowls/SM_TavernStewBowl"),false},
    {TEXT("/Game/WorldGeneration/VillageTavern/DiningBowls/SM_TavernBrokenBowl"),false},
    {TEXT("/Game/WorldGeneration/VillageTavern/EatingUtensils/SM_TavernChopsticks"),false},
    {TEXT("/Game/WorldGeneration/VillageTavern/EatingUtensils/SM_TavernWoodSpoon"),false}
};
static_assert(UE_ARRAY_COUNT(Models) == int32(EProp::Count));

bool IsFood(EProp Prop)
{
    return Prop >= EProp::Bread && Prop <= EProp::Ribs;
}

FSoftObjectPath AssetPath(EProp Prop)
{
    const FString Package(Models[uint8(Prop)].Package);
    return FSoftObjectPath(Package + TEXT(".") + FPackageName::GetShortName(Package));
}

struct FPlacement
{
    EProp Prop;
    FVector Contact;
    double Yaw = 0.;
    // Positive fits a donor by its longest dimension. Negative fits its upright height.
    double FitCm = 0.;
    double Roll = 0.;

    FTransform LocalTransform(const UStaticMesh& Mesh) const
    {
        const FQuat YawRotation = FRotator(0., Yaw, 0.).Quaternion();
        if (FitCm == 0. && Roll == 0.) return FTransform(YawRotation, Contact);
        const FBox Bounds = Mesh.GetBoundingBox();
        const FVector Size = Bounds.GetSize();
        FQuat Rest = FRotator(0.,0.,Roll).Quaternion();
        if (IsFood(Prop) || Prop == EProp::Carrots)
        {
            // Handheld food usually has its long axis vertical. Lay its broad side on the dish.
            if (Size.X < Size.Y && Size.X < Size.Z) Rest = FRotator(90.,0.,0.).Quaternion();
            else if (Size.Y < Size.Z) Rest = FRotator(0.,0.,90.).Quaternion();
        }
        const double Scale = FitCm == 0. ? 1. : FMath::Abs(FitCm) /
            FMath::Max(1.e-3, FitCm < 0. ? Size.Z : Size.GetMax());
        const FBox Rotated = Bounds.TransformBy(FTransform(Rest,FVector::ZeroVector,FVector(Scale)));
        const FVector Base(Rotated.GetCenter().X, Rotated.GetCenter().Y, Rotated.Min.Z);
        return FTransform(YawRotation*Rest, Contact-YawRotation.RotateVector(Base), FVector(Scale));
    }
};

struct FSeat
{
    double Angle;
    double Radius;
    double FloorZ;
};

// Support Z is sampled under the feet on the finished deck. Tableware inherits its table height.
void SeatGroup(TArray<FPlacement>& Out, FVector Center, double GrainYaw,
    std::initializer_list<FSeat> Seats, std::initializer_list<FPlacement> Setting)
{
    Out.Add({EProp::Table,Center,GrainYaw});
    for (const FSeat Seat : Seats)
    {
        const double Rad = FMath::DegreesToRadians(Seat.Angle);
        const FVector Foot(Center.X+Seat.Radius*FMath::Cos(Rad),Center.Y+Seat.Radius*FMath::Sin(Rad),Seat.FloorZ);
        Out.Add({EProp::Stool,Foot,Seat.Angle+174.});
    }
    for (FPlacement Item : Setting)
    {
        Item.Contact += Center+FVector(0.,0.,76.);
        if (IsFood(Item.Prop))
        {
            Out.Add({EProp::Dish,Item.Contact,Item.Yaw-23.});
            Item.Contact.Z += 1.25;
        }
        Out.Add(Item);
    }
}

void FurnishTaproom(TArray<FPlacement>& Out)
{
    // The east rear bay is the kitchen. Keep the entrance and the right end of the bar clear.
    // Pull the aisle-side stool out of the diagonal from the doorway to the middle of the bar.
    SeatGroup(Out,{-222.,-121.,-2.7},12.,{{63.,80.,-3.3},{169.,82.,-1.2},{276.,79.,-2.1}},{
        {EProp::Jug,{-3.,-1.,0.},114.}, {EProp::Cup,{-8.,37.,0.},-28.},
        {EProp::Cup,{-38.,-14.,0.},145.}, {EProp::Cup,{27.,-24.,0.},215.},
        {EProp::StewBowl,{15.,29.,0.},-14.}, {EProp::WoodSpoon,{30.,24.,0.},67.},
        {EProp::Bowl,{-32.,7.,0.},73.}, {EProp::Chopsticks,{-29.,23.,0.},-9.},
        {EProp::Bread,{3.,-31.,0.},-35.,16.}});
    // Opposing seats face the two players' edges of the open board.
    SeatGroup(Out,{-408.,119.,-2.1},82.,{{67.,79.,-2.1},{238.,80.,-2.8}},{
        {EProp::GameBoard,{-2.,0.,0.},-24.}, {EProp::Lantern,{34.,-13.,0.},28.,-26.},
        {EProp::Cup,{-30.,-19.,0.},173.}, {EProp::Cup,{5.,32.,0.},38.}});
    SeatGroup(Out,{335.,-207.,-1.7},-13.,{{26.,85.,-1.6},{165.,80.,-2.3},{257.,83.,-1.3}},{
        {EProp::Jug,{0.,1.,0.},84.}, {EProp::Cup,{18.,35.,0.},18.},
        {EProp::Cup,{16.,-33.,0.},195.}, {EProp::Chicken,{28.,13.,0.},25.,20.5},
        {EProp::Chopsticks,{35.,-6.,0.},-151.}, {EProp::StewBowl,{-32.,9.,0.},-48.},
        {EProp::WoodSpoon,{-29.,26.,0.},165.}, {EProp::Bread,{-7.,-28.,0.},-77.,15.},
        {EProp::Chopsticks,{-26.,-24.,0.},77.}});
    SeatGroup(Out,{-457.,-213.,-1.2},36.,{{65.,84.,-1.0},{220.,82.,-1.4},{299.,86.,-1.3}},{
        {EProp::Lantern,{0.,3.,0.},-8.,-26.}, {EProp::Cup,{-9.,33.,0.},177.},
        {EProp::Cup,{16.,-30.,0.},-55.}, {EProp::Ribs,{13.,27.,0.},18.,23.5},
        {EProp::Chopsticks,{31.,18.,0.},-116.}, {EProp::Bowl,{-25.,-18.,0.},117.},
        {EProp::WoodSpoon,{-34.,-4.,0.},-148.}});
    constexpr double CounterFloor = -2.3;
    constexpr double CounterTop = CounterFloor+105.;
    constexpr double RackFloor = -2.6;
    // Plate food at the west end and drain the cups beside the tap cask at the east end.
    // Guests at the central service point can see the keeper and set down a plate.
    Out.Append({
        {EProp::Counter,{-120.,182.,CounterFloor},-90.}, {EProp::Rack,{-87.,354.,RackFloor},-90.},
        {EProp::Cask,{-285.,342.,-.7},16.}, {EProp::Cask,{-355.,335.,-2.7},-43.},
        {EProp::TapCask,{62.,344.,-2.0},-90.},
        {EProp::Jug,{-54.,169.,CounterTop},-48.},
        {EProp::Cup,{-34.,191.,CounterTop-.02},-55.}, {EProp::Cup,{-15.,191.,CounterTop-.02},24.},
        {EProp::Baguette,{-186.,196.,CounterTop},8.,34.},
        {EProp::Dish,{-227.,165.,CounterTop},51.}, {EProp::Chicken,{-227.,165.,CounterTop+1.25},74.,21.},
        {EProp::Dish,{-189.,165.,CounterTop},-14.}, {EProp::Sausage,{-189.,165.,CounterTop+1.25},-8.,20.},
        {EProp::Chopsticks,{-211.,192.,CounterTop},81.}
    });

    // The upper bay has only 24.3 cm of headroom. The taller pulled jug spouts go a shelf lower.
    Out.Append({
        {EProp::Jug,{-38.,353.,RackFloor+110.85},17.}, {EProp::Jug,{-148.,351.,RackFloor+110.85},-36.},
        {EProp::Cup,{-161.,354.,RackFloor+152.85},-52.}, {EProp::Cup,{-143.,350.,RackFloor+152.85},58.},
        {EProp::Cup,{-49.,351.,RackFloor+152.85},15.}, {EProp::Cup,{-31.,355.,RackFloor+152.85},-30.},
        {EProp::Dish,{-98.,352.,RackFloor+66.85},-8.},
        {EProp::Dish,{-98.,352.,RackFloor+68.60},12.}, {EProp::Dish,{-98.,352.,RackFloor+70.35},40.},
        {EProp::Bowl,{-47.,350.,RackFloor+66.85},32.},
        {EProp::Bowl,{-73.,350.,RackFloor+66.85},-21.}
    });
}

void FurnishRuin(TArray<FPlacement>& Out)
{
    Out.Append({
        {EProp::BrokenTable,{-280.,-143.,-1.2},34.}, {EProp::BrokenStool,{-196.,-194.,-2.2},-64.},
        {EProp::BrokenStool,{-337.,-215.,-0.6},85.}, {EProp::BrokenCounter,{-98.,177.,-2.3},-83.},
        {EProp::Table,{-408.,119.,-1.8},48.}, {EProp::Stool,{-333.,166.,-.9},124.},
        {EProp::Stool,{-441.,44.,-1.5},42.,0.,90.}, {EProp::BrokenTable,{273.,-200.,-1.8},-22.},
        {EProp::Cask,{-475.,318.,-2.6},32.,0.,90.}, {EProp::Cask,{62.,344.,-2.},21.},
        {EProp::Timber,{-526.,214.,-1.5},32.,106.}, {EProp::Timber,{-121.,329.,0.},-12.,176.},
        {EProp::Sherd,{-218.,-164.,0.},60.,14.}, {EProp::Sherd,{-230.,-174.,0.},188.,9.},
        {EProp::Sherd,{271.,-246.,0.},-42.,10.}, {EProp::AbandonedBoard,{-412.,120.,74.2},-18.},
        {EProp::BrokenBowl,{-380.,140.,74.2},-47.}, {EProp::Sherd,{-372.,121.,74.2},16.,6.5},
        {EProp::Cup,{-430.,94.,74.2},23.,0.,82.},
        {EProp::Jug,{46.,295.,-1.5},117.,0.,90.}
    });
}

void FurnishKitchen(TArray<FPlacement>& Out, bool bRepaired)
{
    // Room-space pivot on the L-shaped partition. The staff opening is in the west
    // return behind the bar; its south opening has a sill 104 cm above the sole.
    constexpr double ScreenBase = -3.;
    constexpr double PassHeight = ScreenBase + 104.;
    Out.Append({
        {bRepaired ? EProp::Screen : EProp::DamagedScreen, {0.,0.,ScreenBase}},
        {bRepaired ? EProp::Hearth : EProp::ColdHearth, {615.,79.,-2.1},180.},
        {bRepaired ? EProp::PrepBench : EProp::BrokenPrepBench, {337.,335.,-1.3},-90.},
        {bRepaired ? EProp::WashStand : EProp::BrokenWashStand, {579.,246.,-2.},180.},
        {bRepaired ? EProp::DryingRack : EProp::EmptyDryingRack, {390.,262.,305.}}
    });
    if (!bRepaired)
    {
        Out.Append({
            {EProp::Cask,{197.,362.,-1.2},-82.,0.,90.},
            {EProp::Sherd,{290.,-37.,PassHeight},28.,11.},
            {EProp::Sherd,{303.,-39.,PassHeight},-43.,6.5},
            {EProp::Timber,{165.,61.,-2.},88.,92.},
            {EProp::BrokenBowl,{549.,291.,-2.},56.}
        });
        return;
    }

    // Crockery and stores are reachable from the prep side. The centre of the room
    // remains clear between the staff door, cutting board, hearth and serving ledge.
    constexpr double PantryFloor = -3.4;
    Out.Append({
        {EProp::Rack,{158.,74.,PantryFloor}},
        {EProp::Cask,{195.,362.,-1.2},38.},
        {EProp::Dish,{161.,34.,PantryFloor+66.85},18.},
        {EProp::Dish,{161.,34.,PantryFloor+68.60},-7.},
        {EProp::Dish,{161.,34.,PantryFloor+70.35},42.},
        {EProp::Bowl,{161.,73.,PantryFloor+66.85},79.},
        {EProp::Jug,{161.,108.,PantryFloor+66.85},-25.},
        {EProp::Jug,{161.,135.,PantryFloor+66.85},33.},
        {EProp::Cup,{162.,113.,PantryFloor+110.85},-72.},
        {EProp::Cup,{162.,134.,PantryFloor+110.85},61.},
        {EProp::Bread,{160.,31.,PantryFloor+110.85},79.,27.},
        {EProp::Baguette,{162.,75.,PantryFloor+110.85},91.,36.},
        {EProp::Carrots,{337.,335.,89.7},17.,23.},
        {EProp::Dish,{276.,-35.,PassHeight},12.}, {EProp::Sausage,{276.,-35.,PassHeight+1.25},34.,20.},
        {EProp::StewBowl,{321.,-34.,PassHeight},34.}, {EProp::WoodSpoon,{345.,-38.,PassHeight},12.},
        {EProp::Jug,{370.,-34.,PassHeight},-7.}
    });
}

void LightFixture(AActor& Host, USceneComponent& Root, const FPlacement& Fixture)
{
    const bool bHearth = Fixture.Prop == EProp::Hearth;
    UPointLightComponent* Light = NewObject<UPointLightComponent>(&Host);
    Host.AddInstanceComponent(Light);
    Light->SetupAttachment(&Root);
    Light->SetMobility(EComponentMobility::Movable);
    // The ember bed is recessed in the west-facing firebox, beneath the suspended pot.
    const FVector Offset = bHearth ? FVector(-52.,0.,39.) : FVector(0.,0.,FMath::Abs(Fixture.FitCm)*.44);
    Light->SetRelativeLocation(Fixture.Contact+Offset);
    UVillageInteriorLighting::Configure(Light);
    Light->MaxDrawDistance=2200.f;
    Light->MaxDistanceFadeRange=450.f;
    Light->RegisterComponent();
}

const FSoftObjectPath WickPath(TEXT("/Game/WorldGeneration/TemperateHills/ShopLighting/MI_StaffLampWick.MI_StaffLampWick"));
const FSoftObjectPath EmberPath(TEXT("/Game/WorldGeneration/TemperateHills/ShopLighting/M_StaffHearthEmber.M_StaffHearthEmber"));
const FSoftObjectPath TorchBodyPath(TEXT("/Game/Props/RomanColumn20260915/SM_BronzeTorch.SM_BronzeTorch"));
const FSoftObjectPath TorchSocketPath(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
const FSoftObjectPath ForgedIronPath(TEXT("/Game/Props/CastingStation20260926/RealismV5/MI_DarkForgedIron.MI_DarkForgedIron"));
const FSoftObjectPath TorchFlamePath(TEXT("/Game/WorldGeneration/TemperateHills/ShopLighting/M_StaffTorchCard.M_StaffTorchCard"));

void InstallEntryTorches(AActor& Host, USceneComponent& Root, bool bRepaired)
{
    UStaticMesh* Body = Cast<UStaticMesh>(TorchBodyPath.ResolveObject());
    UStaticMesh* Socket = Cast<UStaticMesh>(TorchSocketPath.ResolveObject());
    UMaterialInterface* Iron = Cast<UMaterialInterface>(ForgedIronPath.ResolveObject());
    UMaterialInterface* FlameMaterial = bRepaired ? Cast<UMaterialInterface>(TorchFlamePath.ResolveObject()) : nullptr;
    if (!Body || !Socket || !Iron) return;

    const auto Mount = [&](UStaticMesh* Mesh, const FTransform& Placement, UMaterialInterface* Finish)
    {
        auto* Part = NewObject<UStaticMeshComponent>(&Host);
        Host.AddInstanceComponent(Part);
        Part->SetupAttachment(&Root);
        Part->SetMobility(Root.Mobility);
        Part->SetStaticMesh(Mesh);
        if (Finish) Part->SetMaterial(0,Finish);
        Part->SetRelativeTransform(Placement);
        Part->SetCollisionProfileName(TEXT("NoCollision"));
        Part->SetCanEverAffectNavigation(false);
        Part->LDMaxDrawDistance = 3000.f;
        Part->RegisterComponent();
    };

    struct FWallTorch { FVector Wall; double InwardYaw; };
    // Enter facing +Y: the left turn leads toward +X, between the door and the east dining table.
    // The front pier survives in the ruin. The adjoining gable bay is rebuilt with the tavern.
    const FWallTorch Torches[] = {
        {{197.,-408.,179.},90.},
        {{629.,-235.,179.},180.}
    };
    const int32 NumTorches = bRepaired ? int32(UE_ARRAY_COUNT(Torches)) : 1;
    for (int32 Index=0; Index<NumTorches; ++Index)
    {
        const FWallTorch& Torch = Torches[Index];
        const FRotator Facing(0.,Torch.InwardYaw,0.);
        const FTransform BodyPose(Facing,Torch.Wall,FVector(.9));
        // The bronze shank starts 14.4 cm in front of the pivot. Seat it in an
        // iron socket that extends back through the uneven inner face of the stone.
        const FVector Inward = Facing.Vector();
        Mount(Socket,FTransform(FQuat::FindBetweenNormals(FVector::UpVector,Inward),
            Torch.Wall+2.*Inward,FVector(.14,.14,.38)),Iron);
        Mount(Body,BodyPose,bRepaired ? nullptr : Iron);
        if (!FlameMaterial) continue;

        const FVector FlameCentre = BodyPose.TransformPosition(FVector(50.,0.,62.));
        auto* Flame = NewObject<UMaterialBillboardComponent>(&Host);
        Host.AddInstanceComponent(Flame);
        Flame->SetupAttachment(&Root);
        Flame->SetMobility(Root.Mobility);
        Flame->SetRelativeLocation(FlameCentre);
        Flame->AddElement(FlameMaterial,nullptr,false,25.f,22.f,nullptr);
        Flame->SetCollisionProfileName(TEXT("NoCollision"));
        Flame->SetCanEverAffectNavigation(false);
        Flame->SetCastShadow(false);
        Flame->LDMaxDrawDistance = 2600.f;
        Flame->RegisterComponent();

        auto* Light = NewObject<UPointLightComponent>(&Host);
        Host.AddInstanceComponent(Light);
        Light->SetupAttachment(&Root);
        Light->SetMobility(EComponentMobility::Movable);
        Light->SetRelativeLocation(FlameCentre);
        UVillageInteriorLighting::Configure(Light);
        Light->MaxDrawDistance = 2600.f;
        Light->MaxDistanceFadeRange = 500.f;
        Light->RegisterComponent();
    }
}

void Install(AActor& Host, USceneComponent& Root, const TArray<FPlacement>& Layout)
{
    const bool bDedicated = Host.GetNetMode()==NM_DedicatedServer;
    TMap<EProp,TArray<FTransform>> Instances;
    TMap<EProp,UStaticMesh*> Meshes;
    for (const FPlacement& Piece : Layout)
    {
        UStaticMesh*& Mesh = Meshes.FindOrAdd(Piece.Prop);
        if (!Mesh) Mesh = Cast<UStaticMesh>(AssetPath(Piece.Prop).ResolveObject());
        if (!Mesh) continue;
        Instances.FindOrAdd(Piece.Prop).Add(Piece.LocalTransform(*Mesh));
        if (!bDedicated && (Piece.Prop==EProp::Lantern || Piece.Prop==EProp::Hearth))
            LightFixture(Host,Root,Piece);
    }
    for (const auto& Group : Instances)
    {
        const bool bSolid = Models[uint8(Group.Key)].bBlocks;
        UStaticMesh* Mesh = Meshes.FindChecked(Group.Key);
        auto AttachMesh = [&](UStaticMeshComponent& Part)
        {
            Host.AddInstanceComponent(&Part);
            Part.SetupAttachment(&Root);
            Part.SetMobility(Root.Mobility);
            Part.SetStaticMesh(Mesh);
            if (Group.Key==EProp::Stool) Part.ComponentTags.Add(TEXT("VillageTavern.RestStool"));
            if (Group.Key==EProp::Lantern)
            {
                if (auto* Wick = Cast<UMaterialInterface>(WickPath.ResolveObject())) Part.SetMaterial(0, Wick);
                Part.SetCastShadow(false);
            }
            if (Group.Key == EProp::Hearth)
            {
                const int32 Slot = Mesh->GetMaterialIndex(TEXT("Ember"));
                if (Slot != INDEX_NONE)
                    if (auto* Ember = Cast<UMaterialInterface>(EmberPath.ResolveObject())) Part.SetMaterial(Slot, Ember);
            }
            Part.SetCollisionProfileName(bSolid ? TEXT("BlockAll") : TEXT("NoCollision"));
            if (bSolid) Part.ComponentTags.Add(TEXT("HillsStaticSupport"));
            Part.SetGenerateOverlapEvents(false);
            Part.SetCanEverAffectNavigation(bSolid);
        };
        // Inventory food uses its original static-mesh material permutation in cooked games.
        if (Group.Value.Num()==1 || IsFood(Group.Key))
        {
            for (const FTransform& At : Group.Value)
            {
                auto* Part = NewObject<UStaticMeshComponent>(&Host);
                AttachMesh(*Part);
                Part->SetRelativeTransform(At);
                if (!bSolid) Part->LDMaxDrawDistance=3100.f;
                Part->RegisterComponent();
            }
            continue;
        }
        auto* Batch = NewObject<UInstancedStaticMeshComponent>(&Host);
        AttachMesh(*Batch);
        if (!bSolid) Batch->SetCullDistances(2200,3100);
        Batch->AddInstances(Group.Value,false,false);
        Batch->RegisterComponent();
    }
}
}

void FHillsTavernInterior::AddBlockingMeshPaths(TArray<FSoftObjectPath>& Paths)
{
    Paths.AddUnique(EmberPath);
    for (int32 I=0; I<int32(EProp::Count); ++I)
        if (Models[I].bBlocks) Paths.AddUnique(AssetPath(static_cast<EProp>(I)));
}

bool FHillsTavernInterior::AreBlockingMeshesLoaded()
{
    for (int32 I=0; I<int32(EProp::Count); ++I)
    {
        if (Models[I].bBlocks && !Cast<UStaticMesh>(AssetPath(static_cast<EProp>(I)).ResolveObject()))
        {
            UE_LOG(LogTemp, Error, TEXT("Missing tavern collision mesh %s"), Models[I].Package);
            return false;
        }
    }
    return true;
}

void FHillsTavernInterior::Populate(AActor& Host, USceneComponent& RoomRoot, bool bRepaired)
{
    TArray<FPlacement> Layout;
    if (bRepaired) FurnishTaproom(Layout);
    else FurnishRuin(Layout);
    FurnishKitchen(Layout,bRepaired);
    const bool bDedicated = Host.GetNetMode()==NM_DedicatedServer;
    TArray<FPlacement> Blocking, Dressing;
    TArray<FSoftObjectPath> Paths;
    for (const FPlacement& Piece : Layout)
    {
        if (Models[uint8(Piece.Prop)].bBlocks)
            Blocking.Add(Piece);
        else if (!bDedicated)
        {
            Dressing.Add(Piece);
            Paths.AddUnique(AssetPath(Piece.Prop));
        }
    }
    // Both states' collision assets are held by the hills entry stream. Apply the
    // current state's walkable surfaces in the same update as the shell.
    Install(Host,RoomRoot,Blocking);
    if (bDedicated) return;
    Paths.Append({TorchBodyPath,TorchSocketPath,ForgedIronPath});
    if (bRepaired) Paths.Append({TorchFlamePath,WickPath});
    // A repair or streamed-level unload can retire this actor while a load is in flight.
    UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateWeakLambda(&Host,
        [WeakRoot=TWeakObjectPtr<USceneComponent>(&RoomRoot),Dressing=MoveTemp(Dressing),bRepaired]()
        {
            USceneComponent* Root = WeakRoot.Get();
            if (!Root || !IsValid(Root->GetOwner()) || Root->GetOwner()->IsActorBeingDestroyed()) return;
            Install(*Root->GetOwner(),*Root,Dressing);
            InstallEntryTorches(*Root->GetOwner(),*Root,bRepaired);
        }));
}
