#include "TemperateHillsWorld.h"
#include "TemperateHillsSurface.h"
#include "Engine/StaticMesh.h"

// Small stones bedded into the surface. The ground material paints its dry and
// gravel layers from a slope plus patch-noise weight, so this pass uses the same
// two inputs: debris appears on the shallow, dry-looking ground and fades out of
// meadow, path and riverbank ground instead of dusting the whole world evenly.
void ATemperateHillsWorld::GetGroundDebrisPlacements(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const
{
    if(!Assets||Assets->Rocks.IsEmpty())return;
    using namespace TemperateHillsSurface;
    const double Spacing=FMath::Clamp(Assets->GroundDebrisSpacingCm,90.f,600.f);
    const double Coverage=FMath::Clamp(Assets->GroundDebrisCoverage,0.f,1.f);
    const double TargetSize=FMath::Clamp(Assets->GroundDebrisSizeCm,4.f,120.f);
    // A tile is an enumeration bucket, not a planting grid: two independent
    // candidates per tile average the spacing while leaving bare pockets.
    const double Tile=Spacing*2;
    const double Half=SizeMeters*50-500;
    const FVector2D Start(GetStartLocation());
    auto Smooth=[](double T){T=FMath::Clamp(T,0.0,1.0);return T*T*(3-2*T);};
    for(int32 GY=FMath::FloorToInt(Bounds.Min.Y/Tile);GY<=FMath::FloorToInt(Bounds.Max.Y/Tile);++GY)
    for(int32 GX=FMath::FloorToInt(Bounds.Min.X/Tile);GX<=FMath::FloorToInt(Bounds.Max.X/Tile);++GX)
    {
        const uint32 TileKey=Key(GX,GY,Seed,1451);
        for(int32 Candidate=0;Candidate<2;++Candidate)
        {
            const uint32 K=Mix(TileKey^((uint32(Candidate)+1)*0x9e3779b9U));
            const double X=(GX+Unit(K+1))*Tile, Y=(GY+Unit(K+2))*Tile;
            if(X<Bounds.Min.X||X>=Bounds.Max.X||Y<Bounds.Min.Y||Y>=Bounds.Max.Y)continue;
            if(FMath::Abs(X)>Half||FMath::Abs(Y)>Half)continue;
            // Keep the spawn clearing and the walked paths readable.
            if(FVector2D::DistSquared(FVector2D(X,Y),Start)<1600.0*1600.0)continue;
            const double Path=PathDistance(X,Y);
            if(Path<300)continue;
            const auto Bank=RiverPlan?RiverPlan->Sample(X,Y):TemperateRiver::FSample();
            if(Bank.Bank>.30)continue;
            const FVector N=SurfaceNormal(X,Y);
            // Not on ground steeper than ~38 degrees: the stones would read as
            // floating grit instead of bedded surface material.
            if(N.Z<.78)continue;
            // Broad 250 m patch field: the material paints its pale, stony dry
            // layer on the same scale, so stones arrive with the dry ground
            // rather than dusting every square metre evenly.
            const double WX=X+Noise(X*.0004,Y*.0004,1411)*650;
            const double WY=Y+Noise(X*.0004,Y*.0004,1417)*650;
            const double Patch=Noise(WX*.0000405,WY*.0000405,1459)*.5+.5;
            const double Dry=Smooth((.58-Patch)/.40);
            // Mid slopes carry the gravel layer; very flat ground is meadow.
            const double Slope=Smooth((.97-N.Z)/.16);
            const double Chance=Coverage*(.25+.75*Dry)*(.40+.60*Slope)*Smooth((Path-300)/420.0);
            if(Unit(K+3)>Chance)continue;
            const auto& Mesh=Assets->Rocks[K%Assets->Rocks.Num()];
            const UStaticMesh* Loaded=Mesh.Get();
            if(!Loaded)continue;
            const FBox Box=Loaded->GetBoundingBox();
            const FVector Size=Box.GetSize();
            // Fit one nominal stone size onto whatever rock mesh is registered, so
            // the layer keeps working if the rock set is swapped for another pack.
            const double Longest=FMath::Max(1.0,FMath::Max(Size.X,Size.Y));
            const double Foot=TargetSize*(.55+Unit(K+4)*.90);
            const double Scale=Foot/Longest;
            const FQuat Rotation=FQuat(N,Unit(K+5)*2*PI)*FQuat::FindBetweenNormals(FVector::UpVector,N);
            // Sink by the mesh's own base plus a share of the stone height: the
            // reference look is stones bedded in the surface, not pebbles on top.
            const FVector BaseCenter(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z);
            const double Sink=Foot*(.30+Unit(K+6)*.24);
            const FVector Location=FVector(X,Y,Height(X,Y))-Rotation.RotateVector(BaseCenter*Scale)-N*(Sink+1);
            FTemperatePlacement& P=Out.Emplace_GetRef();
            P.Transform=FTransform(Rotation,Location,FVector(Scale));P.Mesh=Mesh.ToSoftObjectPath();P.Key=K;
            // Decorative stones share the grass PCG layer, so they keep the grass
            // namespace shape (tile coordinates plus a reserved pass byte) and stay
            // out of the harvest identities owned by the tree and rock layers.
            P.CandidateId=(uint64(uint32(GX)&0x00ffffffU)<<32)|
                (uint64(uint32(GY)&0x00ffffffU)<<8)|uint64(0x40|Candidate);
        }
    }
}
