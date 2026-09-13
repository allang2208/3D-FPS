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
        for(int32 GY=FMath::FloorToInt(MinY/Spacing);GY<=FMath::FloorToInt(MaxY/Spacing);++GY)
        for(int32 GX=FMath::FloorToInt(MinX/Spacing);GX<=FMath::FloorToInt(MaxX/Spacing);++GX)
        {
            const uint32 K=Key(GX,GY,uint32(Seed),Accent?1327:1301);
            // Each jittered candidate stays inside its global lattice cell.
            const double X=(GX+.5+(Unit(K+1)-.5)*.6)*Spacing;
            const double Y=(GY+.5+(Unit(K+2)-.5)*.6)*Spacing;
            if(X<MinX||X>=MaxX||Y<MinY||Y>=MaxY)continue;
            const double Path=PathDistance(X,Y);
            if(Path<240)continue;
            const auto Bank=RiverPlan?RiverPlan->Sample(X,Y):TemperateRiver::FSample();
            if(Bank.Bank>.08)continue;
            const double Meadow=Noise(X*.00028,Y*.00028,1309)*.5+.5;
            const double Forest=ForestWeight(X,Y);
            // The low layer stays continuous between broad meadow patches.
            // Taller species concentrate in the patches and recede at paths.
            const double Patch=Accent?Smooth((Meadow-.32)/.42):(.88+.12*Meadow);
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
            const double PX=X/4000.0,PY=Y/4000.0;
            int32 IX=FMath::FloorToInt(PX),IY=FMath::FloorToInt(PY);
            if(Unit(K+6)<Smooth(PX-IX))++IX;
            if(Unit(K+7)<Smooth(PY-IY))++IY;
            const uint32 Species=Key(IX,IY,uint32(Seed),Accent?1367:1361);
            const FSoftObjectPath Mesh=Meshes[Species%Meshes.Num()].ToSoftObjectPath();
            if(Mesh.IsNull())continue;
            const double Scale=Accent?(.8+Unit(K+5)*.35):(.98+Unit(K+5)*.26);
            const FQuat Rotation=FQuat(N,Unit(K+4)*2*PI)*FQuat::FindBetweenNormals(FVector::UpVector,N);
            FTemperatePlacement& P=Out.Emplace_GetRef();
            P.Transform=FTransform(Rotation,FVector(X,Y,Height(X,Y)-1.5),FVector(Scale));
            P.Mesh=Mesh;P.Key=K;
            // Grid coordinates are small in this bounded world; bit 31 of Y
            // distinguishes accent candidates without colliding with base IDs.
            P.CandidateId=(uint64(uint32(GX))<<32)|(uint32(GY)^uint32(Accent?0x80000000U:0));
        }
    }
}
