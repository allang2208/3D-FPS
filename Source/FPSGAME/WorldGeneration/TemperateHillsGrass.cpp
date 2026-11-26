#include "TemperateHillsWorld.h"
#include "TemperateQuarryYard.h"
#include "TemperateHillsSurface.h"
#include "TemperateForestHabitat.h"
#include "TemperateWoodlandFloor.h"
#include "Engine/StaticMesh.h"

namespace
{
// A neighbouring run of flowering patches shares a species; the transition
// between two dominant populations is broad enough for occasional mixing.
uint32 ClearingFamilyKey(int32 GX,int32 GY,double TileSize,int32 Seed,uint32 PatchKey)
{
    using namespace TemperateHillsSurface;
    constexpr double StandSize=3700.;
    const double X=(GX+.5)*TileSize/StandSize,Y=(GY+.5)*TileSize/StandSize;
    int32 CX=FMath::FloorToInt(X),CY=FMath::FloorToInt(Y);
    if(Unit(PatchKey+83)<FMath::SmoothStep(.18,.82,X-CX))++CX;
    if(Unit(PatchKey+89)<FMath::SmoothStep(.18,.82,Y-CY))++CY;
    return Unit(PatchKey+97)<.15?Mix(PatchKey+11):Key(CX,CY,Seed,4093);
}
}

void ATemperateHillsWorld::AddClearingFlowerPatch(int32 GX,int32 GY,double TileSize,const FBox2D& Bounds,
    const FTemperateFlowerFamily& Family,uint32 PatchKey,TArray<FTemperatePlacement>& Out) const
{
    using namespace TemperateHillsSurface;
    const FVector2D Center((GX+.21+.58*Unit(PatchKey+1))*TileSize,(GY+.21+.58*Unit(PatchKey+2))*TileSize);
    const double Region=RainforestWeight(Center.X,Center.Y);
    // Keep a whole patch in its source tile, even when a PCG strip cuts through it.
    const FVector2D TileOffset=Center-FVector2D(GX*TileSize,GY*TileSize);
    const double EdgeRoom=FMath::Min(FMath::Min(TileOffset.X,TileSize-TileOffset.X),
                                      FMath::Min(TileOffset.Y,TileSize-TileOffset.Y));
    const double Reach=FMath::Min(EdgeRoom,FMath::Lerp(175.,85.,Region)+FMath::Lerp(105.,65.,Region)*Unit(PatchKey+3));
    if(!Bounds.ExpandBy(Reach).IsInsideOrOn(Center))return;
    const double Opening=Region>0 ? TemperateForestHabitat::RainforestOpening(Center.X,Center.Y,Seed, EcologyProfile()) : 0.;
    double BankLight=0.;
    if(Region>0 && ForestWaterPlan&&!ForestWaterPlan->Pools.IsEmpty())
    {
        // The forest visit lands beside this pond. Favour its dry approaches,
        // gradually returning to the normal clearing frequency further inland.
        const double Distance=FMath::Sqrt(ForestWaterPlan->Pools[0].Bounds.ComputeSquaredDistanceToPoint(Center));
        BankLight=1.-FMath::SmoothStep(1200.,3200.,Distance);
    }
    const auto& Ecology=EcologyProfile();
    const double Density=Ecology.MeadowFlowers.Density*Ecology.Rainforest.FlowerDensityMultiplier;
    const double Light=.47*Opening+.20*BankLight*(.5+.5*Opening);
    const double RainforestChance=Region*FMath::Min(.78,Density*Light);
    const double Roll=Unit(PatchKey+4);
    FVector ContourNormal=FVector::ZeroVector;
    if(Roll>=RainforestChance)
    {
        // Broader drifts occupy open grassland and taper off on exposed stony slopes.
        const double Budget=.90*Ecology.MeadowFlowers.Density;
        if(Roll>=RainforestChance+(1.-Region)*Budget || PathDistance(Center.X,Center.Y)<400.)return;
        const double Forest=TemperateForestHabitat::Canopy(Center.X,Center.Y,Seed,Region,Opening, EcologyProfile());
        ContourNormal=SurfaceNormal(Center.X,Center.Y);
        const auto Site=TemperateForestHabitat::Upland(ContourNormal,Forest,
            TemperateForestHabitat::Moisture(Center.X,Center.Y,Seed,Region, EcologyProfile()),Region, EcologyProfile());
        const double Colony=TemperateForestHabitat::UnderstoryPatch(Center.X,Center.Y,Seed, EcologyProfile());
        if(Roll>=RainforestChance+Budget*Site.Meadow*(.35+.65*Colony))return;
    }
    if(SampleForestWater(Center.X,Center.Y).Wet)return;

    const int32 Count=FMath::FloorToInt(FMath::Lerp(7.,3.,Region)+Unit(PatchKey+5)*FMath::Lerp(5.,4.,Region));
    const int32 FirstVariant=int32(Unit(PatchKey+6)*Family.Variants.Num());
    if(ContourNormal.IsZero())ContourNormal=SurfaceNormal(Center.X,Center.Y);
    const double Grade=ContourNormal.SizeSquared2D();
    const double Heading=Grade>.0025?FMath::Atan2(ContourNormal.X,-ContourNormal.Y)+(Unit(PatchKey+7)-.5)*.85:2.*PI*Unit(PatchKey+7);
    const FVector2D Along(FMath::Cos(Heading),FMath::Sin(Heading));
    const FVector2D Across(-Along.Y,Along.X);
    const double SatelliteSide=Unit(PatchKey+17)<.5?-1.:1.;
    const double SatelliteOffset=.42+.18*Unit(PatchKey+19);
    const double SatelliteShare=.16+.18*Unit(PatchKey+23);
    for(int32 I=0;I<Count;++I)
    {
        const uint32 K=Mix(PatchKey^((uint32(I)+1U)*0x9e3779b9U));
        const bool Satellite=Unit(K+11)<SatelliteShare;
        const double Radius=FMath::Sqrt(Unit(K+1));
        const double Angle=2.*PI*Unit(K+2);
        // The larger colony follows the contour; a smaller group takes root
        // beyond one end. Both stay inside the original tile ownership radius.
        const double AlongOffset=SatelliteSide*(Satellite?SatelliteOffset:-.20)
            +(Satellite?.28:.69)*Radius*FMath::Cos(Angle);
        const double AcrossOffset=(Satellite?.13:-.06)+(Satellite?.18:FMath::Lerp(.30,.46,Region))*Radius*FMath::Sin(Angle);
        const FVector2D XY=Center+Reach*(Along*AlongOffset+Across*AcrossOffset);
        const double X=XY.X,Y=XY.Y;
        // Keep half-open PCG strip ownership even when a group spans a boundary.
        if(X<Bounds.Min.X||X>=Bounds.Max.X||Y<Bounds.Min.Y||Y>=Bounds.Max.Y)continue;
        if(PathDistance(X,Y)<300.)continue;
        if(SampleForestWater(X,Y).Wet||(ForestWaterPlan&&ForestWaterPlan->ShoreMoistureAt(X,Y)>.20))continue;
        if(RiverPlan&&RiverPlan->Sample(X,Y).Bank>.12)continue;
        const FVector Normal=SurfaceNormal(X,Y);
        if(Unit(K+3)>=Ecology.MeadowFlowers.SlopeWeight(Normal.Z))continue;

        const FVector Up=FMath::Lerp(FVector::UpVector,Normal,.38).GetSafeNormal();
        const FQuat Rotation=FQuat(Up,2.*PI*Unit(K+4))*FQuat::FindBetweenNormals(FVector::UpVector,Up);
        const auto& Variant=Family.Variants[(FirstVariant+I)%Family.Variants.Num()];
        const UStaticMesh* Mesh=Variant.Get();
        const double MeshHeight=Mesh->GetBoundingBox().GetSize().Z
            -Mesh->GetPositiveBoundsExtension().Z-Mesh->GetNegativeBoundsExtension().Z;
        const double HeightCm=FMath::Lerp(28.,22.,Region)+(Satellite?4.:11.)*(1.-Radius)+14.*Unit(K+5);
        const double Scale=FMath::Min(1.25,HeightCm/FMath::Max(1.,MeshHeight));
        FTemperatePlacement& P=Out.Emplace_GetRef();
        P.Mesh=Variant.ToSoftObjectPath();
        P.Key=K;
        P.Transform=FTransform(Rotation,FVector(X,Y,Height(X,Y)-1.5),FVector(Scale));
        P.CandidateId=(uint64(uint32(GX)&0x00ffffffU)<<32)|
            (uint64(uint32(GY)&0x00ffffffU)<<8)|uint64(0xE0+I);
    }
}

void ATemperateHillsWorld::GetGrassPlacements(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const
{
    using namespace TemperateHillsSurface;
    const auto& Ecology=EcologyProfile();
    const double Half=SizeMeters*50;
    const double MinX=FMath::Max(-Half+500,Bounds.Min.X),MinY=FMath::Max(-Half+500,Bounds.Min.Y);
    const double MaxX=FMath::Min(Half-500,Bounds.Max.X),MaxY=FMath::Min(Half-500,Bounds.Max.Y);
    if(MinX>=MaxX||MinY>=MaxY)return;
    const FBox2D PlantBounds(FVector2D(MinX,MinY),FVector2D(MaxX,MaxY));
    const auto& CarpetGrasses=Assets->RainforestCarpetGrass;
    const bool HasCarpet=CarpetGrasses.Num()>=3&&CarpetGrasses[0].IsValid()&&
        CarpetGrasses[1].IsValid()&&CarpetGrasses[2].IsValid();
    TArray<const FTemperateFlowerFamily*,TInlineAllocator<4>> FlowerFamilies;
    for(const auto& Family:Assets->ClearingFlowers)
        if(!Family.Variants.IsEmpty()&&!Family.Variants.ContainsByPredicate([](const auto& Mesh){return !Mesh.IsValid();}))
            FlowerFamilies.Add(&Family);
    auto Smooth=[](double T){T=FMath::Clamp(T,0.0,1.0);return T*T*(3-2*T);};

    for(int32 Pass=0;Pass<3;++Pass)
    {
        const bool Accent=Pass==1,Flower=Pass==2;
        const auto& Meshes=Pass==0?Assets->Grass:(Accent?Assets->GrassAccents:Assets->MeadowFlowers);
        const auto& Rule=Flower?Ecology.MeadowFlowers:(Accent?Ecology.GrassAccents:Ecology.Grass);
        if((Meshes.IsEmpty()&&(!Flower||FlowerFamilies.IsEmpty()))||Rule.Density<=0)continue;
        const double Spacing=Flower?FMath::Clamp(Assets->MeadowFlowerSpacingCm,200.f,1200.f)
            :(Accent?FMath::Clamp(Assets->GrassAccentSpacingCm,120.f,500.f):FMath::Clamp(Assets->GrassSpacingCm,45.f,200.f));
        const double Coverage=Rule.Density;
        // A tile is only an enumeration bucket, not a one-plant planting grid.
        // Its 2..6 independent candidates average the previous candidate density
        // while allowing adjacent tufts, empty pockets and uneven spacing.
        const double TileSize=Spacing*2;
        for(int32 GY=FMath::FloorToInt(MinY/TileSize);GY<=FMath::FloorToInt(MaxY/TileSize);++GY)
        for(int32 GX=FMath::FloorToInt(MinX/TileSize);GX<=FMath::FloorToInt(MaxX/TileSize);++GX)
        {
            const uint32 TileKey=Key(GX,GY,uint32(Seed),Flower?1431:(Accent?1427:1401));
            if(Flower&&!FlowerFamilies.IsEmpty())
            {
                const uint32 PatchKey=Key(GX,GY,uint32(Seed),4073);
                const auto* Family=FlowerFamilies[ClearingFamilyKey(GX,GY,TileSize,Seed,PatchKey)%FlowerFamilies.Num()];
                AddClearingFlowerPatch(GX,GY,TileSize,PlantBounds,*Family,PatchKey,Out);
                if(Meshes.IsEmpty())continue;
            }
            const int32 OldCount=2+int32(Unit(TileKey+11)*5);
            FVector2D VergeAxis=FVector2D::ZeroVector;
            FVector2D VergeCenter=FVector2D::ZeroVector;
            if(Accent&&OldCount>=3&&Unit(TileKey+149)<.64)
            {
                const double CX=(GX+.5)*TileSize,CY=(GY+.5)*TileSize;
                const double Trail=PathDistance(CX,CY);
                if(Trail>390.&&Trail<1750.&&RainforestWeight(CX,CY)<=0.)
                {
                    // Follow the local road edge even on a bend. Reserve the other
                    // slots for open grass between these groups of taller stems.
                    constexpr double Step=70.;
                    const double DX=PathDistance(CX+Step,CY)-PathDistance(CX-Step,CY);
                    const double DY=PathDistance(CX,CY+Step)-PathDistance(CX,CY-Step);
                    VergeAxis=FVector2D(-DY,DX).GetSafeNormal();
                    VergeCenter=FVector2D(.36+.28*Unit(TileKey+151),.36+.28*Unit(TileKey+157));
                }
            }
            const bool CarpetTile=Pass==0&&!Assets->RainforestGrass.IsEmpty()&&
                RainforestWeight((GX+.5)*TileSize,(GY+.5)*TileSize)>0;
            // Six forest infill candidates share the wet-ground palette. Four
            // further draws only fill terrestrial grass between existing tufts.
            const int32 Count=OldCount+(CarpetTile?(HasCarpet?10:6):0);
            for(int32 Candidate=0;Candidate<Count;++Candidate)
            {
            const uint32 K=Mix(TileKey^((uint32(Candidate)+1)*0x9e3779b9U));
            const bool Infill=Candidate>=OldCount;
            const int32 Quadrant=Candidate-OldCount;
            const bool Stratified=Infill&&Quadrant<4;
            FVector2D UV(Stratified?((Quadrant&1)+.15+.70*Unit(K+1))*.5:Unit(K+1),
                         Stratified?((Quadrant>>1)+.15+.70*Unit(K+2))*.5:Unit(K+2));
            const bool VergeTuft=Candidate<3&&VergeAxis.SizeSquared()>.5;
            if(VergeTuft)
            {
                const FVector2D Across(-VergeAxis.Y,VergeAxis.X);
                const double Along=(Candidate==0?0.:(Candidate==1?-.18:.23))+.11*(UV.X-.5);
                UV=VergeCenter+VergeAxis*Along+Across*((UV.Y-.5)*.19);
            }
            const double X=(GX+UV.X)*TileSize, Y=(GY+UV.Y)*TileSize;
            if(X<MinX||X>=MaxX||Y<MinY||Y>=MaxY)continue;
            const double Region=RainforestWeight(X,Y);
            if(Flower&&!FlowerFamilies.IsEmpty()&&Unit(K+73)<Region)continue;
            if(Infill&&Unit(K+39)>=Region)continue;
            const double Path=PathDistance(X,Y);
            if(Path<240)continue;
            const auto Bank=RiverPlan?RiverPlan->Sample(X,Y):TemperateRiver::FSample();
            if(Bank.Bank>.82 || (Bank.Bank>0 && Height(X,Y)<Bank.WaterZ+12))continue;
            const auto Pool=Region>0?SampleForestWater(X,Y):TemperateForestWater::FSample();
            const bool ExtraCarpet=Candidate>=OldCount+6;
            if(ExtraCarpet&&Pool.Wet)continue;
            // Leave the submerged leaf bed readable, with occasional sedges at the lip.
            if(Pool.Wet&&(Flower||Pool.Depth>9||!Assets->RainforestGrass.IsValidIndex(2)||Unit(K+17)>.20))continue;
            // Warp the larger fields so species and density transitions do not
            // follow the rectangular PCG grid or the enumeration tile edges.
            const double WX=X+Noise(X*.0004,Y*.0004,1411)*650;
            const double WY=Y+Noise(X*.0004,Y*.0004,1417)*650;
            const double Meadow=Noise(WX*.00028,WY*.00028,1309)*.5+.5;
            const double Tuft=Noise(WX*.0031,WY*.0031,1423)*.5+.5;
            const double Shore=Region>0&&ForestWaterPlan?ForestWaterPlan->ShoreMoistureAt(X,Y):0.;
            const double Opening=Region>0?TemperateForestHabitat::RainforestOpening(X,Y,Seed, EcologyProfile()):0;
            const double Forest=TemperateForestHabitat::Canopy(X,Y,Seed,Region,Opening, EcologyProfile());
            // Dense tufts connect through thinner ground cover, with small
            // irregular gaps instead of a nearly uniform lawn everywhere.
            const double Clump=Smooth((Meadow*.35+Tuft*.65-.27)/.46);
            const double BasePatch=Accent?Smooth((Meadow-.32)/.42)*Clump:
                (Flower?Smooth((Meadow-.48)/.34)*Smooth((Tuft-.32)/.5):(.28+.72*Clump));
            // The wet pocket has continuous low cover between fern beds. Keep
            // the same candidates/grid, with small gaps and the existing edge fade.
            const double WoodlandFinish=(1.-FMath::SmoothStep(0.,.02,Bank.Bank))*(1.-Bank.CliffWeight);
            const bool WetFloorPatch=!Accent&&!Flower&&Region>0.&&WoodlandFinish>0.&&Forest>.0;
            const double FloorPatch=WetFloorPatch?TemperateWoodlandFloor::Patch(X,Y,Seed):0.;
            const double ForestPatch=FMath::Lerp(.68+.32*Clump,
                (.25+.75*Clump)*FMath::Lerp(1.,.58,FloorPatch*Forest),WoodlandFinish);
            const double Patch=Flower?FMath::Lerp(BasePatch,(.10+.90*Opening)*(1.-.88*Shore),Region):
                (Accent?BasePatch:FMath::Lerp(BasePatch,ForestPatch,Region));
            const double PathBlend=Smooth((Path-240)/(Accent?550.0:(Flower?420.0:180.0)));
            const double BankBlend=1-Smooth(Bank.Bank/.82);
            // Flowers suppress in forest shade almost fully: a meadow species does
            // not survive under closed canopy, unlike grass which only thins.
            // Woodland now opens onto leaf litter; tall meadow stems stay at
            // the edge, while short grass survives in small brighter pockets.
            const double Shade=Ecology.GrassShade.Weight(Forest);
            const double BaseSuppression=Accent?Ecology.AccentShadeSuppression:
                (Flower?Ecology.FlowerShadeSuppression:Ecology.GrassShadeSuppression);
            const double LocalSuppression=Flower?(.72-.52*Opening):
                (Accent?.75:Ecology.Rainforest.GrassShadeSuppression);
            const double Suppression=FMath::Lerp(BaseSuppression,LocalSuppression,Region);
            const double LocalDensity=FMath::Lerp(1.0,Flower?Ecology.Rainforest.FlowerDensityMultiplier:
                (Accent?1.15:Ecology.Rainforest.GrassDensityMultiplier),Region);
            double Chance=Coverage*LocalDensity*Patch*(1-Shade*Suppression)*PathBlend*BankBlend;
            const double Roll=Unit(K+3);
            if(Roll>Chance*(1.+.32*(1.-Region)))continue;
            const FVector N=SurfaceNormal(X,Y);
            const double SlopeWeight=Rule.SlopeWeight(N.Z);
            if(SlopeWeight<=0||Unit(K+9)>SlopeWeight)continue;
            if(RiverPlan && Bank.CliffWeight>0.)
            {
                const auto Q=TemperateQuarry::Finish(RiverPlan->WhiteCliffs.Local(X,Y),N.Z,Meadow);
                const double Growth=(.09+.82*Q.Turf+.14*Q.Talus)*(1.-Q.Wear)*(1.-Q.Bed);
                if(Unit(K+87)>FMath::Lerp(1.,Growth,Bank.CliffWeight))continue;
            }
            TemperateForestHabitat::FUnderstory Site;
            if(Forest>.12)Site=TemperateForestHabitat::Understory(X,Y,Seed,Forest,Region,N, EcologyProfile());
            const double Moist=Forest>.12?Site.Moist:TemperateForestHabitat::Moisture(X,Y,Seed,Region, EcologyProfile());
            const auto Upland=TemperateForestHabitat::Upland(N,Forest,Moist,Region, EcologyProfile());
            Chance*=1.+(Flower?-.38:.32)*Upland.Meadow-(Accent||Flower?.80:.62)*Upland.Stony;
            if(Roll>Chance)continue;
            // The litter visible under a dry stand must continue into the
            // understory. Leave sparse low blades on deeper leaf beds; meadow
            // stems and flowers retreat first as the player enters the grove.
            if(Forest>.12&&Region<1.&&WoodlandFinish>0.&&RiverPlan&&RiverPlan->bVillageRainforest)
            {
                const double DryPatch=WetFloorPatch?FloorPatch:TemperateWoodlandFloor::Patch(X,Y,Seed);
                const double Deposit=TemperateWoodlandFloor::DryDeposit(X,Y,Seed,N,DryPatch);
                const double LeafBed=(1.-Region)*WoodlandFinish*FMath::SmoothStep(.12,.77,Forest)
                    *FMath::SmoothStep(.29,.76,Deposit);
                Chance*=1.-(Accent||Flower?.63:.34)*LeafBed;
            }
            // Actual fern/wood cores are excluded later by the placement pass.
            // Do not also erase most low grass across their entire habitat patch.
            if(Forest>.12)
            {
                const double BaseFreeGround=FMath::Clamp(1.0-.80*Site.Fern-.45*Site.Shrub,.08,1.0);
                const double FreeGround=Accent||Flower?BaseFreeGround:
                    FMath::Lerp(BaseFreeGround,.68+.32*BaseFreeGround,Region);
                if(Unit(K+3)>Chance*FreeGround)continue;
            }
            // Select species from a smoothly blended 40 m field. Neighbours
            // share a few dominant species, independent of PCG cell boundaries.
            const double PX=WX/4000.0,PY=WY/4000.0;
            int32 IX=FMath::FloorToInt(PX),IY=FMath::FloorToInt(PY);
            if(Unit(K+6)<Smooth(PX-IX))++IX;
            if(Unit(K+7)<Smooth(PY-IY))++IY;
            const uint32 Species=Key(IX,IY,uint32(Seed),Flower?1371:(Accent?1367:1361));
            const bool ForestTuft=!Flower&&!Assets->RainforestGrass.IsEmpty()&&
                (Pool.Wet||Infill||Unit(K+43)<Region);
            // A dominant meadow form still reads across the field. A second
            // form repeats at patch margins without turning each tuft into a
            // different species or requiring another grass pass.
            int32 Form=Species%Meshes.Num();
            if(Meshes.Num()>1&&!Flower&&Region<=0.&&Unit(K+163)<.08+.20*(1.-Clump))
                Form=(Form+1+int32(Mix(Species+167)%(Meshes.Num()-1)))%Meshes.Num();
            FSoftObjectPath Mesh=Meshes[Form].ToSoftObjectPath();
            if(ForestTuft)
            {
                // Bank sedges and broadleaf hummocks retain their original sites.
                const double Pick=Unit(K+47);
                const double SedgeShare=FMath::Lerp(.03+.06*Clump,.24+.42*Clump,Shore);
                const double LowShare=(.44+.17*(1.-Clump)+.17*Opening)*(1.-SedgeShare);
                const int32 Index=(Accent||Pool.Wet||Pick>=1.-SedgeShare)?2:(Pick<LowShare?0:1);
                const double HerbPatch=Smooth((Tuft+.18*Meadow-.48)/.36);
                // Ginger occupies sheltered hummocks just above the rushes.
                const double HerbFringe=4.*Shore*(1.-Shore);
                const double HerbChance=HerbPatch*(Accent?.86:.075)*(1.+1.4*HerbFringe)*(1.-.80*Shore*Shore);
                const bool Broadleaf=!Pool.Wet&&!Assets->RainforestHerbs.IsEmpty()&&
                    Unit(K+53)<HerbChance;
                if(ExtraCarpet&&(Broadleaf||Index==2))continue;
                const bool UseCarpet=HasCarpet&&!Broadleaf&&Index!=2&&
                    (ExtraCarpet||Unit(K+127)<.88);
                if(UseCarpet)
                {
                    // The taller blades favour lit patches among spreading grass.
                    const bool Tall=Index==1&&Unit(K+131)<.08+.48*Opening;
                    Mesh=CarpetGrasses[Tall?2:Index].ToSoftObjectPath();
                }
                else
                {
                    const auto& TuftMesh=Broadleaf?Assets->RainforestHerbs[Mix(K+59)%Assets->RainforestHerbs.Num()]:
                        Assets->RainforestGrass[Index%Assets->RainforestGrass.Num()];
                    if(!TuftMesh.IsValid())continue;
                    Mesh=TuftMesh.ToSoftObjectPath();
                }
            }
            // Dry hills retain the yellow meadow palette. Green rainforest
            // tufts are selected only through the region blend above.
            if(Mesh.IsNull())continue;
            const double VergeScale=VergeTuft&&Candidate>0?(Candidate==1?.88:.76):1.;
            const double Scale=VergeScale*(Accent?(.65+Unit(K+5)*.55+Clump*.10):
                (Flower?(.55+Unit(K+5)*.50+Clump*.08):(.78+Unit(K+5)*.40+Clump*.12)))*
                (1-((Accent||Flower)?.18:FMath::Lerp(.18,.06,Region))*Shade)*
                (1.+.08*Upland.Meadow-.22*Upland.Stony);
            const FVector Up=FMath::Lerp(FVector::UpVector,N,Accent?.40:.75).GetSafeNormal();
            const FQuat Rotation=FQuat(Up,Unit(K+4)*2*PI)*FQuat::FindBetweenNormals(FVector::UpVector,Up);
            FTemperatePlacement& P=Out.Emplace_GetRef();
            P.Transform=FTransform(Rotation,FVector(X,Y,Height(X,Y)-1.5),FVector(Scale));
            P.Mesh=Mesh;P.Key=K;
            // Signed coordinates fit well within 24 bits in this bounded world;
            // the low byte reserves a pass bit and the tile-local candidate ID.
            P.CandidateId=(uint64(uint32(GX)&0x00ffffffU)<<32)|
                (uint64(uint32(GY)&0x00ffffffU)<<8)|uint64((Accent?0x80:(Flower?0xC0:0))|Candidate);
            }
        }
    }
}
