#include "ProductionOreRocks.h"
#include "Engine/StaticMesh.h"

int32 ProductionOreRocks::Shape(uint32 Seed)
{
    // Independent of the mineral-selection bits; stable across cell reloads.
    FRandomStream Random(int32(Seed^0x61c88647U));
    return int32(Random.GetUnsignedInt()%ShapeCount);
}

FSoftObjectPath ProductionOreRocks::Mesh(const FString& Definition,int32 Form)
{
    const TCHAR* Mineral=Definition==TEXT("iron_ore")?TEXT("Iron"):
        Definition==TEXT("copper_ore")?TEXT("Copper"):
        Definition==TEXT("silver_ore")?TEXT("Silver"):
        Definition==TEXT("gold_ore")?TEXT("Gold"):nullptr;
    if(!Mineral)return FSoftObjectPath();
    const FString Name=FString::Printf(TEXT("SM_LS_Rock_0%dA_%s"),FMath::Clamp(Form,0,ShapeCount-1),Mineral);
    return FSoftObjectPath(FString::Printf(TEXT("/Game/WorldGeneration/TemperateHills/OreRocks/%s.%s"),*Name,*Name));
}

const TArray<FSoftObjectPath>& ProductionOreRocks::AllMeshes()
{
    static const TArray<FSoftObjectPath> Paths=[]
    {
        TArray<FSoftObjectPath> Result;
        for(const FString Ore:{TEXT("iron_ore"),TEXT("copper_ore"),TEXT("silver_ore"),TEXT("gold_ore")})
            for(int32 Form=0;Form<ShapeCount;++Form)Result.Add(Mesh(Ore,Form));
        return Result;
    }();
    return Paths;
}

FTransform ProductionOreRocks::Placement(const UStaticMesh& Rock,uint32 Seed,
    const FVector& Ground,const FVector& Normal,bool River)
{
    FRandomStream Random(int32(Seed^0xb5297a4dU));
    const double Tier=Random.FRand();
    // 25% small, 60% medium, 15% large. Units are physical centimetres,
    // not a multiplier inherited from a multi-metre landscape boulder.
    double Width=Tier<.25?Random.FRandRange(65.f,105.f):
        Tier<.85?Random.FRandRange(105.f,160.f):Random.FRandRange(160.f,210.f);
    if(River)Width*=.85;
    const FVector Proportion(Random.FRandRange(.90f,1.10f),Random.FRandRange(.90f,1.10f),Random.FRandRange(.82f,1.0f));
    const FBox Box=Rock.GetBoundingBox();
    const FVector Size=Box.GetSize()*Proportion;
    const double Scale=FMath::Min(Width/FMath::Max(1.,FMath::Max(Size.X,Size.Y)),145./FMath::Max(1.,Size.Z));
    const FVector Scale3D=Proportion*Scale;
    const FVector Up=Normal.GetSafeNormal();
    const FQuat Rotation=FQuat(Up,Random.FRandRange(0.f,2.f*PI))*FQuat::FindBetweenNormals(FVector::UpVector,Up);
    const double Burial=FMath::Clamp(Size.Z*Scale*(River?.22:.16),6.,25.);
    // Align the mesh's actual local bottom with the tangent ground plane.
    // Offset only Z, retaining XY for mining's stable candidate lookup.
    const double Lift=(Box.Min.Z*Scale3D.Z+Burial)/FMath::Max(.1,Up.Z);
    return FTransform(Rotation,Ground-FVector(0,0,Lift),Scale3D);
}

bool ProductionOreRocks::FitToSurface(const UStaticMesh& Rock,FTransform& Placement,
    TFunctionRef<bool(const FVector&,double&)> Sample,double BurialCm,double MaxReliefCm)
{
    const FBox Box=Rock.GetBoundingBox();
    const FVector Center=Box.GetCenter(),Extent=Box.GetExtent();
    const FVector Origin=Placement.GetLocation();
    double Low=DBL_MAX,High=-DBL_MAX;
    for(int32 Y=-1;Y<=1;++Y)for(int32 X=-1;X<=1;++X)
    {
        const FVector Offset=Placement.TransformVector(FVector(
            Center.X+X*Extent.X*.85,Center.Y+Y*Extent.Y*.85,Box.Min.Z));
        double GroundZ=0;
        if(!Sample(Origin+Offset,GroundZ)||!FMath::IsFinite(GroundZ))return false;
        const double Support=GroundZ-Offset.Z;
        Low=FMath::Min(Low,Support);High=FMath::Max(High,Support);
    }
    // A rock cannot bridge a step/hollow: all bottom probes must remain close
    // to the same plane. Bury towards the lowest support instead of balancing
    // the whole mesh on its highest corner, which leaves the other side in air.
    if(High-Low>MaxReliefCm)return false;
    Placement.SetLocation(FVector(Origin.X,Origin.Y,Low-BurialCm));
    return true;
}
