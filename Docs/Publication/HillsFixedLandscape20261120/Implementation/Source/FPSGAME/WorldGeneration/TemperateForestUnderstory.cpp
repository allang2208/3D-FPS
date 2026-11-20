#include "TemperateHillsWorld.h"
#include "TemperateForestHabitat.h"
#include "TemperateHillsLandform.h"
#include "TemperateWestVerge.h"
#include "Engine/SkeletalMesh.h"

void ATemperateHillsWorld::GetForestUnderstoryPlacements(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const
{
    if(!Assets)return;
    const auto& Ecology=EcologyProfile();
    using namespace TemperateHillsSurface;
    const double Half=SizeMeters*50-500;
    const double MinX=FMath::Max(-Half,Bounds.Min.X),MinY=FMath::Max(-Half,Bounds.Min.Y);
    const double MaxX=FMath::Min(Half,Bounds.Max.X),MaxY=FMath::Min(Half,Bounds.Max.Y);
    if(MinX>=MaxX||MinY>=MaxY)return;
    const FVector2D Start(GetStartLocation());
    TemperateWestVerge::Gather(*this,Bounds,Out,true);

    for(int32 Pass=0;Pass<3;++Pass)
    {
        const auto& Meshes=Pass==0?Assets->ForestSaplings:(Pass==1?Assets->ForestShrubs:Assets->ForestFerns);
        const auto& Rule=Pass==0?Ecology.Saplings:(Pass==1?Ecology.Hazel:Ecology.Ferns);
        if(Meshes.IsEmpty()||Rule.Density<=0)continue;
        const double Tile=Pass==0?850:(Pass==1?550:760);
        // Include neighbouring colony anchors: a frond may cross the anchor's
        // cell, but the final half-open bounds own each point exactly once.
        for(int32 GY=FMath::FloorToInt(MinY/Tile)-1;GY<=FMath::FloorToInt(MaxY/Tile)+1;++GY)
        for(int32 GX=FMath::FloorToInt(MinX/Tile)-1;GX<=FMath::FloorToInt(MaxX/Tile)+1;++GX)
        {
        const uint32 Colony=Key(GX,GY,uint32(Seed),3203+Pass*17);
        const int32 Candidates=Pass==2?6+int32(Unit(Colony+53)*4):(Pass==0?2:1);
        const double CX=(GX+.225+Unit(Colony+29)*.55)*Tile;
        const double CY=(GY+.225+Unit(Colony+31)*.55)*Tile;
        // Both the woody pairs and the fern bed stay within 3 m of their anchor.
        // Do not sample an adjacent colony whose reach misses this work strip.
        if(CX+300.<MinX||CX-300.>=MaxX||CY+300.<MinY||CY-300.>=MaxY)continue;
        double Heading=Unit(Colony+43)*2.*PI;
        if(Pass==2)
        {
            const FVector Normal=SurfaceNormal(CX,CY);
            if(Normal.SizeSquared2D()>.006)
                Heading=FMath::Atan2(Normal.X,-Normal.Y)+(Unit(Colony+67)-.5)*.86;
        }
        const FVector2D Along(FMath::Cos(Heading),FMath::Sin(Heading)),Across(-Along.Y,Along.X);
        const double TipSide=Unit(Colony+71)<.5?-1.:1.;
        for(int32 I=0;I<Candidates;++I)
        {
            const uint32 K=Mix(Colony^uint32(I+1)*0x9e3779b9U);
            FVector2D Offset;
            const bool Tip=Pass==2&&I%3==0;
            if(Pass==2)
            {
                // Rhizomes spread along a ledge. Keep an older, wider bed and
                // a smaller tongue at one end with open soil between the two.
                const double Station=TipSide*(Tip?110.+105.*Unit(K+1):-145.+176.*Unit(K+1));
                const double Width=Tip?82.:170.;
                Offset=Along*Station+Across*((Unit(K+2)-.5)*Width+TipSide*(Tip?21.:-11.));
            }
            else
            {
                const double Radius=FMath::Sqrt((I+.35)/Candidates)*260.*(.85+.30*Unit(K+1));
                const FVector2D Direction=I==0?Along:FVector2D(FMath::Cos(Heading+2.3999632297),FMath::Sin(Heading+2.3999632297));
                Offset=Direction*Radius;
            }
            const double X=CX+Offset.X,Y=CY+Offset.Y;
            if(X<MinX||X>=MaxX||Y<MinY||Y>=MaxY)continue;
            const double Path=PathDistance(X,Y);
            if(Path<650)continue;
            const double StartDistance=FVector2D::Distance(FVector2D(X,Y),Start);
            if(StartDistance<1400)continue;
            const auto Bank=RiverPlan?RiverPlan->Sample(X,Y):TemperateRiver::FSample();
            if(Bank.Bank>.22||(Bank.Bank>0&&Height(X,Y)<Bank.WaterZ+35))continue;
            const FVector N=SurfaceNormal(X,Y);
            const double SlopeWeight=Rule.SlopeWeight(N.Z);
            if(SlopeWeight<=0)continue;
            const double Region=RainforestWeight(X,Y);
            const double Opening=Region>0?TemperateForestHabitat::RainforestOpening(X,Y,Seed, EcologyProfile()):0.;
            const double Forest=TemperateForestHabitat::Canopy(X,Y,Seed,Region,Opening, EcologyProfile());
            const auto Site=TemperateForestHabitat::Understory(X,Y,Seed,Forest,Region,N, EcologyProfile());
            const double Fringe=FMath::SmoothStep(650.0,1300.0,Path)*FMath::SmoothStep(1400.0,2200.0,StartDistance)
                *(1.0-FMath::SmoothStep(.01,.22,Bank.Bank))*SlopeWeight;
            const double Shore=Region>0&&ForestWaterPlan?Region*ForestWaterPlan->ShoreMoistureAt(X,Y):0.;
            // Keep the immediate lip low. Fern beds sit a little further up the
            // bank, interrupted by the existing understory patches.
            const double FernFringe=4.*Shore*(1.-Shore);
            const double BankDensity=Pass==2?1.+.95*FernFringe-.70*Shore*Shore:1.-.72*Shore;
            const double LocalDensity=FMath::Lerp(1.0,Pass==0?Ecology.Rainforest.SaplingDensityMultiplier:
                (Pass==1?Ecology.Rainforest.ShrubDensityMultiplier:Ecology.Rainforest.FernDensityMultiplier),Region);
            double Habitat=Pass==0?Site.Sapling:(Pass==1?Site.Shrub:Site.Fern);
            if(Pass==2)
            {
                const double DampBed=Site.Moist*Site.Patch;
                Habitat=Habitat*(.86+.14*DampBed)+.31*Site.Edge*DampBed*(1.-.55*Site.Shade);
            }
            else if(Pass==1)
            {
                // Hazel occupies the better-lit rim of a fern bed. Leave its
                // damp centre low enough to read the ledge from the trail.
                const double Margin=4.*Site.Patch*(1.-Site.Patch);
                Habitat=Habitat*(1.-.22*Site.Moist*Site.Patch)+.26*Margin*Site.Edge*(1.-.58*Site.Moist);
            }
            if(RiverPlan&&RiverPlan->bVillageRainforest&&Bank.Bank<=0.&&Bank.CliffWeight<=0.)
            {
                const auto SlopeSite=TemperateHillsLandform::SlopeSite(RiverPlan->UplandOffset(X,Y));
                // Moist folds carry bracken through canopy gaps. Hazel and young
                // beech form a broken margin where the two regional palettes meet.
                const double Border=4.*Region*(1.-Region);
                const double FringePatch=Border*Site.Patch*(1.-Site.Shade);
                if(Pass==2)
                    Habitat=Habitat*(1.-.60*SlopeSite.Shoulder)+.44*SlopeSite.Swale*(.30+.70*Site.Moist)*Site.Patch;
                else if(Pass==1)
                    Habitat+=.42*FringePatch+.14*SlopeSite.Swale*Site.Edge;
                else
                    Habitat+=.18*FringePatch*Site.Edge;
            }
            const double Chance=Rule.Density*LocalDensity*BankDensity*Habitat*Fringe;
            if(Unit(K+3)>Chance)continue;
            const uint32 Cohort=TemperateForestHabitat::Cohort(X,Y,Seed,K,3247+Pass*13, EcologyProfile());
            const uint32 Form=Unit(K+19)<.72?Cohort:K;
            const auto& Chosen=Meshes[Form%Meshes.Num()];
            const USkeletalMesh* Mesh=Chosen.Get();
            if(!Mesh)continue;
            const FBox Box=Mesh->GetImportedBounds().GetBox();
            double Vigor=.55*Unit(Cohort+7)+.45*Unit(K+5);
            if(Region>0&&Pass==0)
                Vigor=FMath::Lerp(Vigor,.68*Vigor+.32*Opening,Region);
            if(Pass==0)
                Vigor=I==0?.38+.62*Vigor:.80*Vigor;
            else if(Pass==2)
                Vigor=Tip?.62*Vigor:.20+.80*Vigor;
            const double TargetHeight=Pass==0?95+Vigor*180:
                (Pass==1?100+Vigor*135:42+(Vigor*.55+Site.Moist*.45)*63);
            const double Scale=TargetHeight/FMath::Max(1.0,Box.GetSize().Z);
            const FVector Up=FMath::Lerp(FVector::UpVector,N,Pass==2?.25:.12).GetSafeNormal();
            const FQuat Rot=FQuat(Up,Unit(K+4)*2*PI)*FQuat::FindBetweenNormals(FVector::UpVector,Up);
            const FVector Root=Rot.RotateVector(FVector(0,0,Box.Min.Z)*Scale);
            FTemperatePlacement& P=Out.Emplace_GetRef();
            P.Transform=FTransform(Rot,FVector(X,Y,Height(X,Y)-Root.Z-2),FVector(Scale));
            P.Mesh=Chosen.ToSoftObjectPath();P.Key=K;
            P.CandidateId=(uint64(uint32(GX)&0x00ffffffU)<<32)|
                (uint64(uint32(GY)&0x00ffffffU)<<8)|uint64(0x20+Pass*16+I);
        }
        }
    }
}
