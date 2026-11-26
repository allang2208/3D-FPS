#include "VillageOilSpread.h"
#include "VillageHotOil.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Components/InstancedStaticMeshComponent.h"

namespace
{
constexpr int32 DX[]={1,1,0,-1,-1,-1,0,1},DY[]={0,1,1,1,0,-1,-1,-1};
int32 Direction(int X,int Y){for(int D=0;D<8;++D)if(DX[D]==X && DY[D]==Y)return D;return INDEX_NONE;}
float Grain(double X,double Y,float Seed)
{
    return FMath::PerlinNoise2D(FVector2D(X+Seed*7.,Y-Seed*13.));
}
}
namespace
{
double OilHeight(double Z){return FMath::RoundToDouble(Z*4.)*.25;}

bool SupportFrame(UPrimitiveComponent* Part,int32 Instance,FTransform& Frame)
{
    if(!IsValid(Part) || !Part->IsRegistered() || !Part->IsQueryCollisionEnabled() ||
       (Part->GetOwner() && Part->GetOwner()->IsActorBeingDestroyed()))return false;
    const ECollisionChannel Channel=Part->GetCollisionObjectType();
    if(Channel!=ECC_WorldStatic && Channel!=ECC_WorldDynamic)return false;
    if(Instance!=INDEX_NONE)
        if(auto* Instances=Cast<UInstancedStaticMeshComponent>(Part))
            return Instances->GetInstanceTransform(Instance,Frame,true);
    Frame=Part->GetComponentTransform();
    return true;
}
}

int32 FVillageOilSpread::TrackSupport(const FHitResult& Hit)
{
    auto* Part=Hit.GetComponent();
    const int Instance=Cast<UInstancedStaticMeshComponent>(Part)?Hit.Item:INDEX_NONE;
    for(int I=0;I<Supports.Num();++I)
        if(!Supports[I].Retired && Supports[I].Component.Get()==Part && Supports[I].Instance==Instance)return I;
    FTransform Frame;
    if(!SupportFrame(Part,Instance,Frame))return INDEX_NONE;
    const auto* Static=Cast<UStaticMeshComponent>(Part);
    return Supports.Add({Part,Frame,Instance,false,Static?Static->GetStaticMesh():nullptr});
}

void FVillageOilSpread::Grow(AActor& Field,FVector PourFrom,float Age,UDynamicMeshComponent* Mesh)
{
    // Synchronous entry for the isolated authoring fixtures. Live fields use the world scheduler.
    Incoming=FVector2D(Field.GetActorLocation()-PourFrom).GetSafeNormal();
    int32 Budget=MAX_int32;
    if(AdvanceSurvey(Field,Age,Budget) && Mesh)WriteMesh(*Mesh);
}

bool FVillageOilSpread::AdvanceSurvey(AActor& Field,float Age,int32& Budget)
{
    if(Target<0)
    {
        const int Want=FMath::Clamp(3+FMath::FloorToInt(FMath::Max(0.f,Age)*14.f),3,Half);
        if(Built>=Want)return false;
        Target=FMath::Min(Want,Built<0?1:Built+2);
        ColumnCursor=LinkCursor=CutCursor=0;bCutsPlanned=false;NeededCuts.Reset();
        if(Cells.IsEmpty())Cells.SetNum(Side*Side);
    }
    const int Width=Target*2+1,Total=Width*Width;
    const FVector Center=Field.GetActorLocation();
    FCollisionQueryParams Q(SCENE_QUERY_STAT(OilSurfaceSurvey),false,&Field);
    Q.AddIgnoredActor(Field.GetInstigator());
    FCollisionObjectQueryParams Surface(ECC_WorldStatic);Surface.AddObjectTypesToQuery(ECC_WorldDynamic);
    auto Id=[](int X,int Y){return (Y+Half)*Side+X+Half;};

    while(ColumnCursor<Total)
    {
        if(Budget<1)return false;
        const int K=ColumnCursor++,X=K%Width-Target,Y=K/Width-Target;
        if(FMath::Max(FMath::Abs(X),FMath::Abs(Y))<=Built)continue;
        const FVector2D XY(X*Step,Y*Step);
        if(XY.Size()>VillageHotOil::Radius+Step*1.6)continue;
        const FVector At=Center+FVector(XY,0);FHitResult H;
        --Budget;
        if(!Field.GetWorld()->LineTraceSingleByObjectType(H,At+FVector(0,0,83),At-FVector(0,0,450),Surface,Q)
            || !H.IsValidBlockingHit() || H.ImpactNormal.Z<.6 || (Cast<APawn>(H.GetActor()) && !Cast<AVillageDefenseSection>(H.GetActor())))continue;
        auto& C=Cells[Id(X,Y)];
        C.Support=TrackSupport(H);if(C.Support==INDEX_NONE)continue;
        C.bGround=true;C.P=FVector(XY,OilHeight(H.ImpactPoint.Z-Center.Z));C.N=H.ImpactNormal;
        C.Edge=EdgeDistance(C.P);
    }
    while(LinkCursor<Total*8)
    {
        if(Budget<2)return false;
        const int K=LinkCursor/8,D=LinkCursor++%8,X=K%Width-Target,Y=K/Width-Target;
        if(FMath::Max(FMath::Abs(X),FMath::Abs(Y))<=Built)continue;
        const int I=Id(X,Y);auto& C=Cells[I];if(!C.bGround)continue;
        const int NX=X+DX[D],NY=Y+DY[D],Band=FMath::Max(FMath::Abs(NX),FMath::Abs(NY));
        if(Band>Target)continue;
        const int J=Id(NX,NY);if(Band>Built && J>I)continue;
        auto& B=Cells[J];if(!B.bGround)continue;
        const FVector V=B.P-C.P;
        if(FMath::Abs(V.Z)>V.Size2D()*1.22+4.)continue;
        const FVector Mid=Center+(C.P+B.P)*.5;FHitResult Bed;
        --Budget;
        if(!Field.GetWorld()->LineTraceSingleByObjectType(Bed,Mid+FVector(0,0,16),Mid-FVector(0,0,16),Surface,Q)
            || !Bed.IsValidBlockingHit() || Bed.ImpactNormal.Z<.6)continue;
        --Budget;
        if(Field.GetWorld()->LineTraceTestByObjectType(Center+C.P+FVector(0,0,5),Center+B.P+FVector(0,0,5),Surface,Q))continue;
        const int Support=TrackSupport(Bed);if(Support==INDEX_NONE)continue;
        if(Support!=C.Support && Support!=B.Support)ExtraLinkSupports.Add(I*8+D,Support);
        C.Links|=1<<D;B.Links|=1<<((D+4)%8);
    }
    if(!bCutsPlanned)
    {
        Solve(Age);TSet<int32> Missing;BuildShores(Target,&Missing);
        NeededCuts=Missing.Array();bCutsPlanned=true;
    }
    while(CutCursor<NeededCuts.Num())
    {
        if(Budget<10)return false;
        const int Key=NeededCuts[CutCursor++],Good=Key/Cells.Num(),Other=Key%Cells.Num();
        const FCell& C=Cells[Good];
        const FVector2D Delta((Other%Side-Good%Side)*Step,(Other/Side-Good/Side)*Step);
        const FVector From=Center+C.P;
        double Lo=0.,Hi=1.,Z=C.P.Z;int Support=C.Support;
        for(int It=0;It<5;++It)
        {
            const double T=(Lo+Hi)*.5;const FVector2D XY=Delta*T;
            const FVector At=From+FVector(XY,-(XY.X*C.N.X+XY.Y*C.N.Y)/C.N.Z);
            FHitResult H;
            --Budget;
            if(Field.GetWorld()->LineTraceSingleByObjectType(H,At+FVector(0,0,12),At-FVector(0,0,15),Surface,Q) &&
                H.IsValidBlockingHit() && H.ImpactNormal.Z>=.6 &&
                (!Cast<APawn>(H.GetActor()) || Cast<AVillageDefenseSection>(H.GetActor())))
            {
                --Budget;
                if(!Field.GetWorld()->LineTraceTestByObjectType(From+FVector(0,0,4),H.ImpactPoint+FVector(0,0,4),Surface,Q))
                {
                    Lo=T;Z=OilHeight(H.ImpactPoint.Z-Center.Z);Support=TrackSupport(H);continue;
                }
            }
            Hi=T;
        }
        EdgeCuts.Add(Key,FVector(FVector2D(C.P)+Delta*Lo,Z));
        if(Support!=INDEX_NONE && Support!=C.Support)CutSupports.Add(Key,Support);
    }
    Built=Target;Target=-1;
    SettleFilm();BuildShores(Built);UpdateBounds();
    return true;
}

float FVillageOilSpread::EdgeDistance(FVector P) const
{
    const FVector2D XY(P);
    const double A=FMath::Atan2(XY.Y,XY.X);
    const double Lobes=.055*FMath::Sin(3*A+Seed)+.045*FMath::Sin(5*A-Seed*.9)+.022*FMath::Sin(8*A+Seed*1.7);
    const double Boundary=VillageHotOil::Radius*FMath::Clamp(.91+Lobes+.075*(XY.GetSafeNormal()|Incoming)
        -.00065*FMath::Clamp(P.Z,-120.,120.)+.034*Grain(P.X*.35/Step,P.Y*.35/Step,Seed),.62,1.);
    return Boundary-XY.Size();
}

void FVillageOilSpread::Solve(float KeepWetUntil)
{
    struct FVisit{float Time;int32 Id;};
    const auto Earlier=[](const FVisit& A,const FVisit& B){return A.Time<B.Time;};
    TArray<FVisit> Queue;
    for(int I=0;I<Cells.Num();++I)
    {
        auto& C=Cells[I];
        if(C.bGround && C.Arrival<=KeepWetUntil)Queue.HeapPush(FVisit{C.Arrival,I},Earlier);
        else C.Arrival=1000.f;
    }
    const int Origin=Half*Side+Half;
    if(Cells[Origin].bGround && Cells[Origin].Arrival!=0.f)
    {Cells[Origin].Arrival=0;Cells[Origin].Flow=Incoming;Queue.HeapPush(FVisit{0,Origin},Earlier);}
    while(!Queue.IsEmpty())
    {
        FVisit V;Queue.HeapPop(V,Earlier,EAllowShrinking::No);
        const FCell& C=Cells[V.Id];if(V.Time>C.Arrival)continue;
        for(int D=0;D<8;++D)
        {
            if(!(C.Links&(1<<D)))continue;
            const int J=V.Id+DX[D]+DY[D]*Side;auto& B=Cells[J];
            if(B.Edge < -Step*1.5)continue;
            const FVector L=B.P-C.P;const FVector2D Dir=FVector2D(L).GetSafeNormal();
            const double Len=L.Size2D(),Slope=L.Z/FMath::Max(1.,Len);
            const double Drag=FMath::Clamp(1.+2.8*Slope-.22*(Dir|Incoming)+.16*Grain(B.P.X*.009,B.P.Y*.009,Seed),.43,3.);
            // Impact momentum decays with distance; uphill costs more time and hollows retain coverage.
            const float Time=C.Arrival+Len*Drag*(1.+.85*B.P.Size2D()/500.)/390.;
            if(Time>=B.Arrival)continue;
            B.Arrival=Time;B.Flow=Dir;Queue.HeapPush(FVisit{Time,J},Earlier);
        }
    }
}

void FVillageOilSpread::SettleFilm()
{
    // Centimetre units: a 2.3 litre pour (the filled hand bowl) distributed over connected columns.
    constexpr float Volume=2300.f;
    TArray<float> Mass,Change;Mass.SetNumZeroed(Cells.Num());Change.SetNumZeroed(Cells.Num());
    double Sum=0.;
    for(int I=0;I<Cells.Num();++I)
    {
        const auto& C=Cells[I];if(C.Arrival>=999. || C.Edge<=0.)continue;
        const double Core=FMath::Exp(-C.P.Size2D()/140.);
        Mass[I]=FMath::Clamp(C.Edge/Step,0.,1.)*(.35+1.7*Core+.14*Grain(C.P.X*.011,C.P.Y*.011,Seed));
        Sum+=Mass[I];
    }
    if(Sum<=0.)return;
    for(float& V:Mass)V*=Volume/Sum;
    // Four bounded, conservative exchanges. The residual coats high spots while mobile oil pools on the low side.
    for(int Pass=0;Pass<4;++Pass)
    {
        for(int I=0;I<Cells.Num();++I)
        {
            if(Mass[I]<=0.)continue;
            float Drop[8]={};float Total=0.f;
            for(int D=0;D<8;++D)if(Cells[I].Links&(1<<D))
            {
                const int J=I+DX[D]+DY[D]*Side;if(Cells[J].Arrival>=999. || Cells[J].Edge<=0.)continue;
                const double Head=Cells[I].P.Z-Cells[J].P.Z+(Mass[I]-Mass[J])/(Step*Step);
                Drop[D]=FMath::Clamp(Head/8.,0.,1.);Total+=Drop[D];
            }
            if(Total<.001f)continue;
            const float Out=Mass[I]*.25f*FMath::Min(1.f,Total);
            Change[I]-=Out;
            for(int D=0;D<8;++D)if(Drop[D]>0.)Change[I+DX[D]+DY[D]*Side]+=Out*Drop[D]/Total;
        }
        for(int I=0;I<Mass.Num();++I){Mass[I]+=Change[I];Change[I]=0.;}
    }
    for(int I=0;I<Cells.Num();++I)Cells[I].FilmMM=10.f*Mass[I]/(Step*Step);
}

bool FVillageOilSpread::Triangle(int A,int B,int C) const
{
    if(Cells[A].Arrival>=999 || Cells[B].Arrival>=999 || Cells[C].Arrival>=999)return false;
    const auto Joined=[&](int I,int J){return (Cells[I].Links & (1<<Direction(J%Side-I%Side,J/Side-I/Side)))!=0;};
    return Joined(A,B)&&Joined(B,C)&&Joined(C,A);
}

int32 FVillageOilSpread::UpstreamOnWetFace(int32 Index) const
{
    const FCell& C=Cells[Index];
    // The six edges of the actual film triangulation. Both vertices must be wet
    // and the connecting edge must belong to a supported face, including at ledges.
    const int Offsets[]={1,1+Side,Side,-1,-1-Side,-Side};
    int32 Best=Index;
    double BestScore=-2.;
    for(int K=0;K<6;++K)
    {
        const int J=Index+Offsets[K];
        if(!Cells.IsValidIndex(J))continue;
        const FCell& Up=Cells[J];
        if(!Up.bGround || Up.Edge<=0.f || Up.Arrival>=C.Arrival)continue;
        const int Left=Index+Offsets[(K+5)%6],Right=Index+Offsets[(K+1)%6];
        if(!(Cells.IsValidIndex(Left) && Triangle(Index,J,Left)) &&
           !(Cells.IsValidIndex(Right) && Triangle(Index,J,Right)))continue;
        const double Score=FVector2D(C.P-Up.P).GetSafeNormal()|C.Flow;
        if(Score>BestScore){Best=J;BestScore=Score;}
    }
    return Best;
}

void FVillageOilSpread::BuildShores(int Extent,TSet<int32>* Missing)
{
    Shores.Reset();
    auto Cut=[&](int Good,int Other)
    {
        const int Key=Good*Cells.Num()+Other;
        FCell V=Cells[Good];
        if(const FVector* P=EdgeCuts.Find(Key))V.P=*P;
        else if(Missing)Missing->Add(Key);
        V.Arrival+=FVector::Dist(V.P,Cells[Good].P)/280.;
        V.Edge=FMath::Min(1.f,EdgeDistance(V.P));return V;
    };
    auto Face=[&](int Tile,int A,int B,int C)
    {
        if(Triangle(A,B,C))return;
        const int Indices[]={A,B,C};
        auto Wet=[&](int I){return Cells[I].Arrival<999 && Cells[I].Edge>-Step;};
        auto Linked=[&](int I,int J){return Wet(I) && Wet(J) && (Cells[I].Links&(1<<Direction(J%Side-I%Side,J/Side-I/Side)));};
        auto Emit=[&](const FCell& X,const FCell& Y,const FCell& Z)
        {
            if(FMath::Abs(FVector2D(Y.P-X.P)^FVector2D(Z.P-X.P))<.02)return;
            FShoreTri T{{X,Y,Z}};Shores.FindOrAdd(Tile).Add(T);
        };
        for(int K=0;K<3;++K)
        {
            const int I=Indices[K],J=Indices[(K+1)%3],L=Indices[(K+2)%3];if(!Wet(I))continue;
            if(Linked(I,J) && !Linked(I,L) && !Linked(J,L))
            {
                const FCell End=Cut(J,L),Start=Cut(I,L);
                Emit(Cells[I],Cells[J],End);Emit(Cells[I],End,Start);
            }
            else if(!Linked(I,J) && !Linked(I,L))
                Emit(Cells[I],Cut(I,J),Cut(I,L));
        }
    };
    for(int Y=Half-Extent;Y<Half+Extent;++Y)for(int X=Half-Extent;X<Half+Extent;++X)
    {
        const int I=Y*Side+X;Face(I,I,I+1,I+1+Side);Face(I,I,I+Side+1,I+Side);
    }
}

void FVillageOilSpread::UpdateBounds()
{
    WetBounds.Init();
    auto AddFace=[this](const FCell& A,const FCell& B,const FCell& C)
    {
        if(FMath::Max3(A.Edge,B.Edge,C.Edge)<=0.f)return;
        WetBounds+=A.P;WetBounds+=B.P;WetBounds+=C.P;
    };
    for(int Y=Half-Built;Y<Half+Built;++Y)for(int X=Half-Built;X<Half+Built;++X)
    {
        const int I=Y*Side+X;
        if(Triangle(I,I+1,I+Side+1))AddFace(Cells[I],Cells[I+1],Cells[I+Side+1]);
        if(Triangle(I,I+Side+1,I+Side))AddFace(Cells[I],Cells[I+Side+1],Cells[I+Side]);
    }
    for(const auto& Tile:Shores)for(const auto& T:Tile.Value)AddFace(T.V[0],T.V[1],T.V[2]);
}

bool FVillageOilSpread::RemoveLostSupports(float Age)
{
    bool Changed=false;
    for(auto& S:Supports)
    {
        if(S.Retired)continue;
        FTransform Now;
        auto* Part=S.Component.Get();
        const auto* Static=Cast<UStaticMeshComponent>(Part);
        if(SupportFrame(Part,S.Instance,Now) &&
           Now.GetLocation().Equals(S.Frame.GetLocation(),.05) &&
           Now.GetRotation().Equals(S.Frame.GetRotation(),.0001) &&
           Now.GetScale3D().Equals(S.Frame.GetScale3D(),.0001) &&
           (!Static || (Static->GetStaticMesh() && Static->GetStaticMesh()==S.Mesh.Get())))continue;
        S.Retired=true;Changed=true;
    }
    if(!Changed)return false;
    ++SupportRevision;
    for(int I=0;I<Cells.Num();++I)
    {
        FCell& C=Cells[I];
        if(!C.bGround || !Supports[C.Support].Retired)continue;
        for(int D=0;D<8;++D)if(C.Links&(1<<D))
            Cells[I+DX[D]+DY[D]*Side].Links&=~(1<<((D+4)%8));
        C.Links=0;C.bGround=false;C.Arrival=1000.f;C.FilmMM=0.f;
    }
    for(auto It=ExtraLinkSupports.CreateIterator();It;++It)if(Supports[It.Value()].Retired)
    {
        const int I=It.Key()/8,D=It.Key()%8;
        Cells[I].Links&=~(1<<D);Cells[I+DX[D]+DY[D]*Side].Links&=~(1<<((D+4)%8));
        It.RemoveCurrent();
    }
    for(auto It=CutSupports.CreateIterator();It;++It)if(Supports[It.Value()].Retired)
    {EdgeCuts.Remove(It.Key());It.RemoveCurrent();}
    for(auto It=EdgeCuts.CreateIterator();It;++It)
    {
        const int A=It.Key()/Cells.Num(),B=It.Key()%Cells.Num();
        if(!Cells[A].bGround || (Cells[B].Support!=INDEX_NONE && Supports[Cells[B].Support].Retired))
        {
            CutSupports.Remove(It.Key());
            It.RemoveCurrent();
        }
    }
    // Retain oil that already crossed a bridge; future arrivals still require a connected route.
    Solve(Age);BuildShores(Built);UpdateBounds();
    return true;
}

void FVillageOilSpread::WriteMesh(UDynamicMeshComponent& Output) const
{
    using namespace UE::Geometry;
    FDynamicMesh3 Mesh;Mesh.EnableAttributes();Mesh.Attributes()->SetNumUVLayers(4);
    auto* Normals=Mesh.Attributes()->PrimaryNormals();auto* UV=Mesh.Attributes()->GetUVLayer(0);
    auto* Depth=Mesh.Attributes()->GetUVLayer(3);auto* Timing=Mesh.Attributes()->GetUVLayer(1);auto* Velocity=Mesh.Attributes()->GetUVLayer(2);
    TArray<int32> Vertex;Vertex.Init(INDEX_NONE,Cells.Num());
    auto AddPoint=[&](const FCell& C){
        UV->AppendElement(FVector2f(.5+C.P.X/1000.,.5+C.P.Y/1000.));
        Timing->AppendElement(FVector2f(C.Arrival,C.Edge));Velocity->AppendElement(FVector2f(.5+.5*C.Flow.X,.5+.5*C.Flow.Y));
        Depth->AppendElement(FVector2f(C.FilmMM,0));Normals->AppendElement(FVector3f(C.N));
        return Mesh.AppendVertex(C.P+FVector(0,0,1.15));
    };
    auto Add=[&](int I){if(Vertex[I]==INDEX_NONE)Vertex[I]=AddPoint(Cells[I]);return Vertex[I];};
    auto Submit=[&](FIndex3i V){
        const int T=Mesh.AppendTriangle(V);
        if(T>=0){Normals->SetTriangle(T,V);UV->SetTriangle(T,V);Timing->SetTriangle(T,V);Velocity->SetTriangle(T,V);Depth->SetTriangle(T,V);}
    };
    auto Face=[&](int A,int B,int C){
        if(!Triangle(A,B,C))return;
        Submit(FIndex3i(Add(A),Add(C),Add(B)));
    };
    for(int Y=Half-Built;Y<Half+Built;++Y)for(int X=Half-Built;X<Half+Built;++X){
        const int I=Y*Side+X;Face(I,I+1,I+Side+1);Face(I,I+Side+1,I+Side);
    }
    for(const auto& Tile:Shores)for(const auto& T:Tile.Value)
        Submit(FIndex3i(AddPoint(T.V[0]),AddPoint(T.V[2]),AddPoint(T.V[1])));
    Output.SetMesh(MoveTemp(Mesh));
}
bool FVillageOilSpread::WetAt(FVector P,float Age) const
{
    if(Age<0 || Cells.IsEmpty() || P.SizeSquared2D()>FMath::Square(VillageHotOil::Radius))return false;
    const double GX=P.X/Step+Half,GY=P.Y/Step+Half;
    const int X=FMath::FloorToInt(GX),Y=FMath::FloorToInt(GY);
    if(X<0||Y<0||X+1>=Side||Y+1>=Side)return false;
    const double U=GX-X,V=GY-Y;const int A=Y*Side+X,C=A+Side+1,B=U>=V?A+1:A+Side;
    const auto Covers=[&](const FCell& M,const FCell& N,const FCell& O,double L0,double L1,double L2)
    {
        return Age>=M.Arrival*L0+N.Arrival*L1+O.Arrival*L2 &&
            M.Edge*L0+N.Edge*L1+O.Edge*L2>0. && FMath::Abs(P.Z-(M.P.Z*L0+N.P.Z*L1+O.P.Z*L2))<=16.;
    };
    if(Triangle(A,B,C))return Covers(Cells[A],Cells[B],Cells[C],1.-FMath::Max(U,V),FMath::Abs(U-V),FMath::Min(U,V));
    if(const auto* Cut=Shores.Find(A))for(const auto& T:*Cut)
    {
        const FVector2D AB(T.V[1].P-T.V[0].P),AC(T.V[2].P-T.V[0].P),AP(P-T.V[0].P);
        const double Area=AB^AC;
        const double L1=(AP^AC)/Area,L2=(AB^AP)/Area,L0=1.-L1-L2;
        if(L0>=0 && L1>=0 && L2>=0 && Covers(T.V[0],T.V[1],T.V[2],L0,L1,L2))return true;
    }
    return false;
}
