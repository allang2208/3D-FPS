#include "TemperateHillsWorld.h"
#include "TemperateHillsSurface.h"

void ATemperateHillsWorld::GetGrassPlacements(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const
{
    using namespace TemperateHillsSurface;
    const double Half=SizeMeters*50;
    const double MinX=FMath::Max(-Half+500,Bounds.Min.X),MinY=FMath::Max(-Half+500,Bounds.Min.Y);
    const double MaxX=FMath::Min(Half-500,Bounds.Max.X),MaxY=FMath::Min(Half-500,Bounds.Max.Y);
    if(MinX>=MaxX||MinY>=MaxY)return;
    auto Smooth=[](double T){T=FMath::Clamp(T,0.0,1.0);return T*T*(3-2*T);};

    // Cache actual trunks once per batch, using the same candidates as the tree
    // layer. Grass needs no traces, physics objects or synchronous asset loads.
    TArray<FVector2D> TrunksInBatch;
    for(int32 TY=FMath::FloorToInt(MinY/1200)-1;TY<=FMath::FloorToInt(MaxY/1200)+1;++TY)
    for(int32 TX=FMath::FloorToInt(MinX/1200)-1;TX<=FMath::FloorToInt(MaxX/1200)+1;++TX)
    {
        FTemperatePlacement Tree;
        if(TreeCandidate(TX,TY,Tree))TrunksInBatch.Add(FVector2D(Tree.Transform.GetLocation()));
    }

    for(int32 Pass=0;Pass<2;++Pass)
    {
        const bool Accent=Pass==1;
        const auto& Meshes=Accent?Assets->GrassAccents:Assets->Grass;
        if(Meshes.IsEmpty())continue;
        const double Spacing=Accent?FMath::Clamp(Assets->GrassAccentSpacingCm,120.f,500.f):FMath::Clamp(Assets->GrassSpacingCm,45.f,200.f);
        const double Coverage=FMath::Clamp(Accent?Assets->GrassAccentCoverage:Assets->GrassCoverage,0.f,1.f);
        // A tile is only an enumeration bucket, not a one-plant planting grid.
        // Its 2..6 independent candidates average the previous candidate density
        // while allowing adjacent tufts, empty pockets and uneven spacing.
        const double TileSize=Spacing*2;
        for(int32 GY=FMath::FloorToInt(MinY/TileSize);GY<=FMath::FloorToInt(MaxY/TileSize);++GY)
        for(int32 GX=FMath::FloorToInt(MinX/TileSize);GX<=FMath::FloorToInt(MaxX/TileSize);++GX)
        {
            const uint32 TileKey=Key(GX,GY,uint32(Seed),Accent?1427:1401);
            const int32 Count=2+int32(Unit(TileKey+11)*5);
            for(int32 Candidate=0;Candidate<Count;++Candidate)
            {
            const uint32 K=Mix(TileKey^((uint32(Candidate)+1)*0x9e3779b9U));
            const double X=(GX+Unit(K+1))*TileSize;
            const double Y=(GY+Unit(K+2))*TileSize;
            if(X<MinX||X>=MaxX||Y<MinY||Y>=MaxY)continue;
            const double Path=PathDistance(X,Y);
            if(Path<240)continue;
            const auto Bank=RiverPlan?RiverPlan->Sample(X,Y):TemperateRiver::FSample();
            if(Bank.Bank>.08)continue;
            // Warp the larger fields so species and density transitions do not
            // follow the rectangular PCG grid or the enumeration tile edges.
            const double WX=X+Noise(X*.0004,Y*.0004,1411)*650;
            const double WY=Y+Noise(X*.0004,Y*.0004,1417)*650;
            const double Meadow=Noise(WX*.00028,WY*.00028,1309)*.5+.5;
            const double Tuft=Noise(WX*.0031,WY*.0031,1423)*.5+.5;
            const double Forest=ForestWeight(X,Y);
            // Dense tufts connect through thinner ground cover, with small
            // irregular gaps instead of a nearly uniform lawn everywhere.
            const double Clump=Smooth((Meadow*.35+Tuft*.65-.27)/.46);
            const double Patch=Accent?Smooth((Meadow-.32)/.42)*Clump:(.28+.72*Clump);
            const double PathBlend=Smooth((Path-240)/(Accent?550.0:180.0));
            const double BankBlend=1-Smooth(Bank.Bank/.08);
            const double Chance=Coverage*Patch*(1-Forest*(Accent?.45:.16))*PathBlend*BankBlend;
            if(Unit(K+3)>Chance)continue;
            const FVector N=SurfaceNormal(X,Y);
            if(N.Z<.83||Unit(K+9)>Smooth((N.Z-.83)/.10))continue;
            bool Overlap=false;
            for(const FVector2D& Trunk:TrunksInBatch)
                if(FVector2D::DistSquared(FVector2D(X,Y),Trunk)<100*100){Overlap=true;break;}
            if(Overlap)continue;

            // Select species from a smoothly blended 40 m field. Neighbours
            // share a few dominant species, independent of PCG cell boundaries.
            const double PX=WX/4000.0,PY=WY/4000.0;
            int32 IX=FMath::FloorToInt(PX),IY=FMath::FloorToInt(PY);
            if(Unit(K+6)<Smooth(PX-IX))++IX;
            if(Unit(K+7)<Smooth(PY-IY))++IY;
            const uint32 Species=Key(IX,IY,uint32(Seed),Accent?1367:1361);
            const FSoftObjectPath Mesh=Meshes[Species%Meshes.Num()].ToSoftObjectPath();
            if(Mesh.IsNull())continue;
            const double Scale=Accent?(.65+Unit(K+5)*.55+Clump*.10):(.78+Unit(K+5)*.40+Clump*.12);
            const FQuat Rotation=FQuat(N,Unit(K+4)*2*PI)*FQuat::FindBetweenNormals(FVector::UpVector,N);
            FTemperatePlacement& P=Out.Emplace_GetRef();
            P.Transform=FTransform(Rotation,FVector(X,Y,Height(X,Y)-1.5),FVector(Scale));
            P.Mesh=Mesh;P.Key=K;
            // Signed coordinates fit well within 24 bits in this bounded world;
            // the low byte reserves a pass bit and the tile-local candidate ID.
            P.CandidateId=(uint64(uint32(GX)&0x00ffffffU)<<32)|
                (uint64(uint32(GY)&0x00ffffffU)<<8)|uint64((Accent?0x80:0)|Candidate);
            }
        }
    }
}
