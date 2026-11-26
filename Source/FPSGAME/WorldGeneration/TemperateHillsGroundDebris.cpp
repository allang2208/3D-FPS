#include "TemperateHillsWorld.h"
#include "TemperateHillsSurface.h"
#include "TemperateForestHabitat.h"
#include "TemperateWoodlandFloor.h"
#include "Engine/StaticMesh.h"

// Small stones bedded into the surface. The ground material paints its dry and
// gravel layers from a slope plus patch-noise weight, so this pass uses the same
// two inputs: debris appears on the shallow, dry-looking ground and fades out of
// meadow, path and riverbank ground instead of dusting the whole world evenly.
void ATemperateHillsWorld::GetGroundDebrisPlacements(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const
{
    if(!Assets)return;
    using namespace TemperateHillsSurface;
    const double Spacing=FMath::Clamp(Assets->GroundDebrisSpacingCm,90.f,600.f);
    const double Coverage=FMath::Clamp(Assets->GroundDebrisCoverage,0.f,1.f);
    const double TargetSize=FMath::Clamp(Assets->GroundDebrisSizeCm,4.f,120.f);
    // Dry, slope and path factors are <= 1. Reject impossible mineral
    // candidates before evaluating surface normals, moisture and groves.
    const double UpperChance=Coverage*(1.+.68*EcologyProfile().UplandStoneStrength);
    // Two mineral slots per tile. Exposed slopes can use both for one small
    // break and its downhill chip; the remaining terrain keeps scattered stones.
    const double Tile=Spacing*2;
    const double Half=SizeMeters*50-500;
    const FVector2D Start(GetStartLocation());
    auto Smooth=[](double T){T=FMath::Clamp(T,0.0,1.0);return T*T*(3-2*T);};
    for(int32 GY=FMath::FloorToInt(Bounds.Min.Y/Tile);GY<=FMath::FloorToInt(Bounds.Max.Y/Tile);++GY)
    for(int32 GX=FMath::FloorToInt(Bounds.Min.X/Tile);GX<=FMath::FloorToInt(Bounds.Max.X/Tile);++GX)
    {
        const uint32 TileKey=Key(GX,GY,Seed,1451);
        const bool ForestTile=RainforestWeight((GX+.5)*Tile,(GY+.5)*Tile)>.01;
        const bool WoodlandPocket=!Assets->RainforestTwigs.IsEmpty() && Unit(TileKey+97)<.48;
        if(ForestTile || WoodlandPocket)
        {
            // Related stones and twigs accumulate in small pockets. Every
            // final XY owns its PCG cell even where the tile crosses a seam.
            const double PocketX=.24+.52*Unit(TileKey+27),PocketY=.24+.52*Unit(TileKey+31);
            const double CenterX=(GX+PocketX)*Tile,CenterY=(GY+PocketY)*Tile;
            const double Shelter=TemperateForestHabitat::UnderstoryPatch(CenterX,CenterY,Seed, EcologyProfile());
            const double Canopy=ForestWeight(CenterX,CenterY);
            const auto& E=EcologyProfile();
            const double Edge=E.EdgeEnter.Weight(Canopy)*(1.-E.EdgeLeave.Weight(Canopy));
            const double Trail=1.-FMath::SmoothStep(360.,900.,PathDistance(CenterX,CenterY));
            const auto ShoreSample=RiverPlan?RiverPlan->Sample(CenterX,CenterY):TemperateRiver::FSample();
            const double Bank=ShoreSample.Bank;
            const double Fringe=E.EdgeDebrisStrength*Edge*(.25+.75*FMath::Max(Trail,4.*Bank*(1.-Bank)));
            const double Finish=(1.-FMath::SmoothStep(0.,.02,Bank))*(1.-ShoreSample.CliffWeight);
            const double FloorPatch=TemperateWoodlandFloor::Patch(CenterX,CenterY,Seed);
            const double Wood=WoodlandPocket?FMath::Clamp(FMath::SmoothStep(.32,.82,Canopy)*(.24+.76*Shelter)+Fringe,0.,1.)
                *FMath::Lerp(1.,FMath::Lerp(.55,1.35,FloorPatch),Finish):0.;
            FVector2D Gradient=FVector2D::ZeroVector;
            if(ForestWaterPlan&&ForestWaterPlan->ShoreMoistureAt(CenterX,CenterY)>0.)
            {
                Gradient.X=ForestWaterPlan->ShoreMoistureAt(CenterX+60.,CenterY)-ForestWaterPlan->ShoreMoistureAt(CenterX-60.,CenterY);
                Gradient.Y=ForestWaterPlan->ShoreMoistureAt(CenterX,CenterY+60.)-ForestWaterPlan->ShoreMoistureAt(CenterX,CenterY-60.);
            }
            const int32 PieceCount=ForestTile?8:(Wood>0.?5:0);
            // The forest floor's leaf drifts run along (.82,.57). Wood catches
            // within those drifts inland and along the strandline beside water.
            const bool HasShoreDirection=Gradient.SizeSquared()>.008;
            double Heading=HasShoreDirection?FMath::Atan2(Gradient.Y,Gradient.X)+UE_HALF_PI:
                (FloorPatch>.42?.607:Unit(TileKey+73)*2.*PI);
            Heading+=(Unit(TileKey+79)-.5)*1.14;
            const FVector2D Along(FMath::Cos(Heading),FMath::Sin(Heading)),Across(-Along.Y,Along.X);
            for(int32 Piece=0;Piece<PieceCount;++Piece)
            {
                const uint32 K=Key(GX,GY,uint32(Seed),2813+Piece*17);
                const bool Twig=Piece<3;
                const double Station=2.*Unit(K+1)-1.;
                const double Offset=(Unit(K+2)-.5)*(Twig?.15:.21)+(Twig?-.025:.035)*(1.-FMath::Abs(Station));
                const FVector2D XY=FVector2D(CenterX,CenterY)+Tile*(Along*(Station*.18)+Across*Offset);
                const double X=XY.X,Y=XY.Y;
                if(X<Bounds.Min.X||X>=Bounds.Max.X||Y<Bounds.Min.Y||Y>=Bounds.Max.Y||
                    FMath::Abs(X)>Half||FMath::Abs(Y)>Half||PathDistance(X,Y)<290)continue;
                const double Region=RainforestWeight(X,Y);
                if(Region<1. && FVector2D::DistSquared(FVector2D(X,Y),Start)<1600.*1600.)continue;
                const double Shore=ForestWaterPlan?ForestWaterPlan->ShoreMoistureAt(X,Y):0.;
                // Expose mineral pockets along the shore and let deadwood
                // gather there and beneath the established understory patches.
                const double Cover=Twig?FMath::Lerp(.29+.35*Shelter,.81,Shore):
                    FMath::Lerp(.30+.23*(1.-Shelter),.93,Shore);
                // Temperate tree groups get both broken wood and mineral
                // fragments; previously their pocket emitted only three twigs.
                const double WoodCover=(Twig?.56:.34)*Wood*EcologyProfile().UplandShelterStrength;
                if(Unit(K+3)>FMath::Lerp(WoodCover,Cover,Region))continue;
                if(Region>0. && SampleForestWater(X,Y).Depth>14)continue;
                if(RiverPlan&&RiverPlan->Sample(X,Y).Bank>.35)continue;
                // Wet margins carry rounded gravel. Broken hillside stones
                // belong to upland woodland and its dry shoulders.
                const bool Rounded=Shore>.12||Bank>.08||Assets->Rocks.IsEmpty();
                const auto& Palette=Twig?Assets->RainforestTwigs:(Rounded?Assets->RiverPebbles:Assets->Rocks);
                if(Palette.IsEmpty())continue;
                const auto& Ref=Palette[K%Palette.Num()];
                const auto* Mesh=Ref.Get();if(!Mesh)continue;
                FBox Box=Mesh->GetBoundingBox();
                Box.Min+=Mesh->GetNegativeBoundsExtension();Box.Max-=Mesh->GetPositiveBoundsExtension();
                const FVector Size=Box.GetSize();
                const FVector N=SurfaceNormal(X,Y);
                if(N.Z<.86)continue;
                const FVector Base(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z);
                const double Span=Twig?22.+Unit(K+4)*58.:6.+Unit(K+4)*20.;
                const double Scale=Span/FMath::Max(1.,FMath::Max(Size.X,Size.Y));
                double Yaw=Unit(K+5)*2*PI;
                if(Twig&&Unit(K+7)<.55+.23*Shore)
                {
                    const double Trapped=!HasShoreDirection&&N.SizeSquared2D()>.018?FMath::Atan2(N.X,-N.Y):Heading;
                    Yaw=Trapped+(Unit(K+5)-.5)*1.15;
                    if(Size.Y>Size.X)Yaw-=UE_HALF_PI;
                    if(Unit(K+9)<.5)Yaw+=PI;
                }
                const FQuat Rotation=FQuat(N,Yaw)*FQuat::FindBetweenNormals(FVector::UpVector,N);
                const FVector Anchor(X,Y,Height(X,Y));
                if(Twig)
                {
                    const FVector End=Rotation.RotateVector((Size.X>Size.Y?FVector::ForwardVector:FVector::RightVector)*(.46*Span));
                    if(FMath::Abs(Anchor.Z+End.Z-Height(X+End.X,Y+End.Y))>3.||
                       FMath::Abs(Anchor.Z-End.Z-Height(X-End.X,Y-End.Y))>3.)continue;
                }
                const FVector Location=Anchor-Rotation.RotateVector(Base*Scale)-N*(Twig?.6:Size.Z*Scale*.21);
                auto& P=Out.Emplace_GetRef();P.Mesh=Ref.ToSoftObjectPath();P.Key=K;
                P.Transform=FTransform(Rotation,Location,FVector(Scale));
                P.CandidateId=(uint64(uint32(GX)&0x00ffffffU)<<32)|(uint64(uint32(GY)&0x00ffffffU)<<8)|uint64(0x50+Piece);
            }
        }
        if(Assets->Rocks.IsEmpty())continue;
        const uint32 FirstKey=Mix(TileKey^0x9e3779b9U),SecondKey=Mix(TileKey^(2U*0x9e3779b9U));
        const double FirstRoll=Unit(FirstKey+3),SecondRoll=Unit(SecondKey+3);
        if(FMath::Min(FirstRoll,SecondRoll)>UpperChance)continue;
        const FVector2D Nucleus((GX+.31+.38*Unit(TileKey+107))*Tile,(GY+.31+.38*Unit(TileKey+109))*Tile);
        FVector FaceNormal=FVector::UpVector;
        bool BrokenPair=false;
        if(!ForestTile&&Unit(TileKey+113)<.46)
        {
            FaceNormal=SurfaceNormal(Nucleus.X,Nucleus.Y);
            BrokenPair=FaceNormal.Z>.80&&FaceNormal.Z<.98;
        }
        for(int32 Candidate=0;Candidate<2;++Candidate)
        {
            const uint32 K=Candidate==0?FirstKey:SecondKey;
            const bool Chip=BrokenPair&&Candidate==1;
            const double Roll=Candidate==0||(Chip&&Unit(TileKey+127)<.64)?FirstRoll:SecondRoll;
            if(Roll>UpperChance)continue;
            FVector2D XY((GX+Unit(K+1))*Tile,(GY+Unit(K+2))*Tile);
            if(BrokenPair)
            {
                XY=Nucleus;
                if(Chip)
                {
                    const FVector2D Down=FVector2D(FaceNormal).GetSafeNormal();
                    XY+=Tile*(Down*(.08+.12*Unit(K+1))+FVector2D(-Down.Y,Down.X)*(.10*(Unit(K+2)-.5)));
                }
            }
            const double X=XY.X,Y=XY.Y;
            if(X<Bounds.Min.X||X>=Bounds.Max.X||Y<Bounds.Min.Y||Y>=Bounds.Max.Y)continue;
            if(FMath::Abs(X)>Half||FMath::Abs(Y)>Half)continue;
            // Keep the spawn clearing and the walked paths readable.
            if(FVector2D::DistSquared(FVector2D(X,Y),Start)<1600.0*1600.0)continue;
            const double Path=PathDistance(X,Y);
            if(Path<300)continue;
            const auto Bank=RiverPlan?RiverPlan->Sample(X,Y):TemperateRiver::FSample();
            if(Bank.Bank>.30)continue;
            const FVector N=BrokenPair&&!Chip?FaceNormal:SurfaceNormal(X,Y);
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
            const double Region=RainforestWeight(X,Y);
            const double Forest=TemperateForestHabitat::Canopy(X,Y,Seed,Region,
                Region>0 ? TemperateForestHabitat::RainforestOpening(X,Y,Seed, EcologyProfile()) : 0., EcologyProfile());
            const auto Site=TemperateForestHabitat::Upland(N,Forest,
                TemperateForestHabitat::Moisture(X,Y,Seed,Region, EcologyProfile()),Region, EcologyProfile());
            const double Legacy=(.25+.75*Dry)*(.40+.60*Slope);
            const double Chance=Coverage*(Legacy*(1.-.72*Site.Meadow)+.68*Site.Stony)*
                Smooth((Path-300)/420.0);
            if(Roll>Chance)continue;
            const uint32 Form=Chip&&Unit(K+11)<.68?FirstKey:K;
            // The lower shelf receives water-worn gravel from the active
            // shore palette; upland breaks share the local rough rock set.
            const auto& Stones=Bank.Bank>.03&&N.Z>.90&&!Assets->RiverPebbles.IsEmpty()?Assets->RiverPebbles:Assets->Rocks;
            const auto& Mesh=Stones[Form%Stones.Num()];
            const UStaticMesh* Loaded=Mesh.Get();
            if(!Loaded)continue;
            FBox Box=Loaded->GetBoundingBox();
            Box.Min+=Loaded->GetNegativeBoundsExtension();Box.Max-=Loaded->GetPositiveBoundsExtension();
            const FVector Size=Box.GetSize();
            // Fit one nominal stone size onto whatever rock mesh is registered, so
            // the layer keeps working if the rock set is swapped for another pack.
            const double Longest=FMath::Max(1.0,FMath::Max(Size.X,Size.Y));
            const double Foot=TargetSize*(Chip?.41+.32*Unit(K+4):(.55+Unit(K+4)*.90));
            const double Scale=Foot/Longest;
            const FQuat Rotation=FQuat(N,Unit(K+5)*2*PI)*FQuat::FindBetweenNormals(FVector::UpVector,N);
            // Sink by the mesh's own base plus a share of the stone height: the
            // reference look is stones bedded in the surface, not pebbles on top.
            const FVector BaseCenter(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z);
            // Use thickness for the buried share. A wide, shallow fragment
            // otherwise disappears entirely under a flat patch of soil.
            const double Sink=Size.Z*Scale*(.26+Unit(K+6)*.22);
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
