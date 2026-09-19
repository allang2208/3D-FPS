#include "TemperateHillsWorld.h"
#include "TemperateHillsSurface.h"
#include "Engine/StaticMesh.h"

void ATemperateHillsWorld::GetRiverPebblePlacements(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const
{
    if(!RiverPlan||!Assets||Assets->RiverPebbles.IsEmpty()||!RiverPlan->IntersectsCell(Bounds.Min.X,Bounds.Min.Y,
        FMath::Max(Bounds.Max.X-Bounds.Min.X,Bounds.Max.Y-Bounds.Min.Y)))return;
    using namespace TemperateHillsSurface;
    const double Tile=2*FMath::Clamp(Assets->RiverPebbleSpacingCm,45.f,180.f);
    const double Coverage=FMath::Clamp(Assets->RiverPebbleCoverage,0.f,1.f);
    const double Half=SizeMeters*50-500;
    const FVector2D Start(GetStartLocation());
    for(int32 Y=FMath::FloorToInt(Bounds.Min.Y/Tile);Y<=FMath::FloorToInt(Bounds.Max.Y/Tile);++Y)
    for(int32 X=FMath::FloorToInt(Bounds.Min.X/Tile);X<=FMath::FloorToInt(Bounds.Max.X/Tile);++X)
    for(int32 Index=0;Index<4;++Index)
    {
        const uint32 K=Mix(Key(X,Y,Seed,2333)^uint32(Index+1)*0x9e3779b9U);
        const double PX=(X+Unit(K+1))*Tile,PY=(Y+Unit(K+2))*Tile;
        if(PX<Bounds.Min.X||PX>=Bounds.Max.X||PY<Bounds.Min.Y||PY>=Bounds.Max.Y||FMath::Abs(PX)>Half||FMath::Abs(PY)>Half)continue;
        if(FVector2D::DistSquared(FVector2D(PX,PY),Start)<2400*2400)continue;
        const auto River=RiverPlan->Sample(PX,PY);
        const double Cover=TemperateRiver::PebbleCover(PX,PY,Seed,River);
        if(Unit(K+3)>Coverage*Cover)continue;
        const double Z=Height(PX,PY),Above=Z-River.WaterZ;
        if(Above<-4||Above>240)continue;
        const FVector N=SurfaceNormal(PX,PY);if(N.Z<.85)continue;
        // First variant is wet; dry bars use the remaining colour variants.
        const int32 Variant=Above<18||Assets->RiverPebbles.Num()==1?0:1+K%(Assets->RiverPebbles.Num()-1);
        const auto& Mesh=Assets->RiverPebbles[Variant];
        const UStaticMesh* Loaded=Mesh.Get();if(!Loaded)continue;
        const FBox Box=Loaded->GetBoundingBox();
        const FVector Size=Box.GetSize();
        const double Length=7+FMath::Pow(Unit(K+4),1.6)*15;
        const double Width=Length*(.62+Unit(K+5)*.30);
        const double StoneHeight=Length*(.30+Unit(K+6)*.22);
        const FVector Scale(Length/FMath::Max(1.0,Size.X),Width/FMath::Max(1.0,Size.Y),StoneHeight/FMath::Max(1.0,Size.Z));
        const FQuat Rotation=FQuat(N,Unit(K+7)*2*PI)*FQuat::FindBetweenNormals(FVector::UpVector,N);
        // Align the mesh's base centre with the shared terrain and bury a
        // portion of each stone. No floating flat-bottom pebbles on slopes.
        const FVector BaseCenter(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z);
        const FVector Location=FVector(PX,PY,Z)-Rotation.RotateVector(BaseCenter*Scale)
            -N*(StoneHeight*(.22+Unit(K+8)*.16)+1);
        FTemperatePlacement& P=Out.Emplace_GetRef();
        P.Transform=FTransform(Rotation,Location,Scale);P.Mesh=Mesh.ToSoftObjectPath();P.Key=K;
        // Decorative stones use a distinct low-byte namespace in the grass PCG
        // layer, without harvest identities or per-stone collision bodies.
        P.CandidateId=(uint64(uint32(X)&0xffffffU)<<32)|(uint64(uint32(Y)&0xffffffU)<<8)|uint64(0x60+Index);
    }
}
