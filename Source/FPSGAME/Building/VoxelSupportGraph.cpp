#include "VoxelSupportGraph.h"
#include "FPSBlast.h"

namespace
{
    FIntVector Bucket(FVector P){return FIntVector(FMath::FloorToInt(P.X/20),FMath::FloorToInt(P.Y/20),FMath::FloorToInt(P.Z/20));}
}

TArray<FVoxelBuildKey> FVoxelSupportGraph::Near(const FVector& Min) const
{
    TArray<FVoxelBuildKey> Result;const FIntVector C=Bucket(Min);
    for(int32 Z=-2;Z<=2;++Z)for(int32 Y=-2;Y<=2;++Y)for(int32 X=-2;X<=2;++X)
        if(const auto* List=Buckets.Find(C+FIntVector(X,Y,Z)))for(const auto& Key:*List)Result.Add(Key);
    return Result;
}

bool FVoxelSupportGraph::Contact(const FVector& A,const FVector& B,FVoxelContact& R)
{
    for(int32 Axis=0;Axis<3;++Axis)
    {
        const double Delta=B[Axis]-A[Axis];
        if(FMath::Abs(FMath::Abs(Delta)-20)>.2)continue;
        const int32 U=(Axis+1)%3,V=(Axis+2)%3;
        const double LoU=FMath::Max(A[U],B[U]),LoV=FMath::Max(A[V],B[V]);
        const double W=FMath::Min(A[U],B[U])+20-LoU,H=FMath::Min(A[V],B[V])+20-LoV;
        if(W<=.2||H<=.2||W*H<4)continue;
        R.Normal=FVector::ZeroVector;R.Normal[Axis]=Delta>0?1:-1;
        R.Center=(A+B)*.5+FVector(10);R.Center[U]=LoU+W*.5;R.Center[V]=LoV+H*.5;
        R.Width=W*.01;R.Height=H*.01;R.Area=R.Width*R.Height;return true;
    }
    return false;
}

TArray<FVoxelBuildKey> FVoxelSupportGraph::Within(FVector Point,float Radius) const
{
    TArray<FVoxelBuildKey> Result;
    const FIntVector Lo=Bucket(Point-FVector(Radius+20)),Hi=Bucket(Point+FVector(Radius));
    const FVector Range(Hi-Lo+FIntVector(1));const double RadiusSq=FMath::Square(double(Radius));
    auto Add=[&](const FVoxelBuildKey& Key)
    {const FVector Min=Nodes.FindChecked(Key).Min;if(FVector::DistSquared(Point,FBox(Min,Min+FVector(20)).GetClosestPointTo(Point))<=RadiusSq)Result.Add(Key);};
    if(Range.X*Range.Y*Range.Z>Nodes.Num())for(const auto& E:Nodes)Add(E.Key);
    else for(int32 Z=Lo.Z;Z<=Hi.Z;++Z)for(int32 Y=Lo.Y;Y<=Hi.Y;++Y)for(int32 X=Lo.X;X<=Hi.X;++X)
        if(const auto* Entries=Buckets.Find(FIntVector(X,Y,Z)))for(const auto& Key:*Entries)Add(Key);
    return Result;
}

void FVoxelSupportGraph::Add(const FVoxelSupportNode& Node)
{
    if(Nodes.Contains(Node.Key))Remove(Node.Key);
    for(const auto& Other:Near(Node.Min))
    {
        FVoxelContact C;
        if(!Broken.Contains({Other,Node.Key})&&Contact(Nodes.FindChecked(Other).Min,Node.Min,C))
        {Edges.FindOrAdd(Other).Add(Node.Key);Edges.FindOrAdd(Node.Key).Add(Other);}
    }
    Nodes.Add(Node.Key,Node);Buckets.FindOrAdd(Bucket(Node.Min)).Add(Node.Key);
    if(Node.bAnchor)Supported.Add(Node.Key);
}

void FVoxelSupportGraph::Remove(FVoxelBuildKey Key)
{
    const auto* Node=Nodes.Find(Key);if(!Node)return;
    const FIntVector B=Bucket(Node->Min);
    if(auto* List=Buckets.Find(B)){List->Remove(Key);if(List->IsEmpty())Buckets.Remove(B);}
    if(const auto* List=Edges.Find(Key))for(const auto& Other:*List)if(auto* E=Edges.Find(Other))E->Remove(Key);
    Edges.Remove(Key);Nodes.Remove(Key);Supported.Remove(Key);
}

void FVoxelSupportGraph::Break(FVoxelBrokenBond Bond)
{
    Broken.Add(Bond);
    if(auto* E=Edges.Find(Bond.A))E->Remove(Bond.B);
    if(auto* E=Edges.Find(Bond.B))E->Remove(Bond.A);
}

void FVoxelSupportGraph::SolveConnectivity()
{
    Supported.Reset();TArray<FVoxelBuildKey> Queue;
    for(const auto& E:Nodes)if(E.Value.bAnchor){Queue.Add(E.Key);Supported.Add(E.Key);}
    for(int32 Read=0;Read<Queue.Num();++Read)
    {
        const auto Key=Queue[Read];if(!Nodes.FindChecked(Key).bBearing)continue;
        if(const auto* Next=Edges.Find(Key))for(const auto& Other:*Next)
            if(!Supported.Contains(Other)){Supported.Add(Other);Queue.Add(Other);}
    }
}

bool FVoxelSupportGraph::Overlaps(const FVector& Min) const
{
    const FBox Box(Min+FVector(.05),Min+FVector(19.95));
    for(const auto& Key:Near(Min))
        if(Box.Intersect(FBox(Nodes.FindChecked(Key).Min+FVector(.05),Nodes.FindChecked(Key).Min+FVector(19.95))))return true;
    return false;
}

FVoxelStressResult VoxelStress::Solve(FVoxelStressInput Input)
{
    FVoxelStressResult Result;Result.Revision=Input.Revision;Result.Iterations=Input.Iterations;
    FVoxelSupportGraph Graph;Graph.Broken=MoveTemp(Input.Broken);
    for(const auto& Node:Input.Nodes){Graph.Add(Node);Result.Evaluated.Add(Node.Key);}
    Graph.SolveConnectivity();Result.Supported=Graph.Supported;
    TSet<FVoxelBuildKey> Seen;
    for(const auto& Entry:Graph.Nodes)
    {
        if(Seen.Contains(Entry.Key))continue;
        TArray<FVoxelBuildKey> Component{Entry.Key};Seen.Add(Entry.Key);bool Anchored=false;
        for(int32 Read=0;Read<Component.Num();++Read)
        {
            const auto Key=Component[Read];Anchored|=Graph.Nodes.FindChecked(Key).bAnchor;
            if(const auto* Next=Graph.Edges.Find(Key))for(const auto& Other:*Next)
                if(!Seen.Contains(Other)){Seen.Add(Other);Component.Add(Other);}
        }
        if(!Anchored)
        {
            auto& Island=Result.Detached.AddDefaulted_GetRef();
            for(const auto& Key:Component)Island.Add(Graph.Nodes.FindChecked(Key));
            continue;
        }
        const FVector Reference=Graph.Nodes.FindChecked(Component[0]).Min;
        TMap<FVoxelBuildKey,int32> Indices;TArray<FPSBlastNode> Nodes;
        for(const auto& Key:Component)
        {
            const auto& N=Graph.Nodes.FindChecked(Key);const FVector P=(N.Min+FVector(10)-Reference)*.01;
            const float Mass=FMath::Max(.001f,N.Physics.DensityKgM3*.008f+N.AddedMassKg);
            Indices.Add(Key,Nodes.Num());
            Nodes.Add({{float(P.X),float(P.Y),float(P.Z)},Mass,Mass*.04f/6,{0,0,Input.GravityMS2}});
        }
        const int32 World=Nodes.Add({{0,0,0},0,0,{0,0,0}});
        struct FBond {FVoxelBuildKey A,B;FVoxelContact Contact;bool Ground=false;};
        TArray<FBond> Links;TArray<FPSBlastBond> Bonds;
        auto AddBond=[&](FVoxelBuildKey A,FVoxelBuildKey B,FVoxelContact C,bool Ground)
        {
            const FVector P=(C.Center-Reference)*.01;
            Links.Add({A,B,C,Ground});Bonds.Add({{uint32(Indices.FindChecked(A)),uint32(Ground?World:Indices.FindChecked(B))},{float(P.X),float(P.Y),float(P.Z)}});
        };
        for(const auto& Key:Component)
        {
            const auto& N=Graph.Nodes.FindChecked(Key);
            if(N.bAnchor)AddBond(Key,Key,{N.Min+FVector(10,10,0),FVector(0,0,-1),.04,.2,.2},true);
            if(const auto* Next=Graph.Edges.Find(Key))for(const auto& Other:*Next)
                if(Indices.FindChecked(Key)<Indices.FindChecked(Other))
                {FVoxelContact C;if(FVoxelSupportGraph::Contact(N.Min,Graph.Nodes.FindChecked(Other).Min,C))AddBond(Key,Other,C,false);}
        }
        TArray<FPSBlastForce> Forces;Forces.SetNumZeroed(Bonds.Num());
        const bool Converged=FPSBlastSolve(Nodes.GetData(),Nodes.Num(),Bonds.GetData(),Bonds.Num(),Input.Iterations,Forces.GetData());
        Result.bConverged&=Converged;
        for(int32 I=0;I<Links.Num();++I)
        {
            const auto& L=Links[I];const auto& A=Graph.Nodes.FindChecked(L.A);const auto& B=Graph.Nodes.FindChecked(L.B);
            const FVector F(Forces[I].linear[0],Forces[I].linear[1],Forces[I].linear[2]);
            const FVector M(Forces[I].angular[0],Forces[I].angular[1],Forces[I].angular[2]);
            if(F.ContainsNaN()||M.ContainsNaN()){Result.bConverged=false;continue;}
            const double Normal=FVector::DotProduct(F,L.Contact.Normal),Twist=FVector::DotProduct(M,L.Contact.Normal);
            const double Area=L.Contact.Area,Lever=FMath::Max(.002,FMath::Min(L.Contact.Width,L.Contact.Height));
            const double Bend=(M-L.Contact.Normal*Twist).Size()*6/(Area*Lever);
            const double Compression=FMath::Max(0.,-Normal/Area)+Bend,Tension=FMath::Max(0.,Normal/Area)+Bend;
            const double Shear=(F-L.Contact.Normal*Normal).Size()/Area+FMath::Abs(Twist)*3/(Area*Lever);
            const float Health=FMath::Max(.05f,FMath::Min(1-A.Damage/FMath::Max(1.f,A.Physics.Durability),1-B.Damage/FMath::Max(1.f,B.Physics.Durability)));
            const double C=Compression/(FMath::Max(1.f,FMath::Min(A.Physics.CompressionPa,B.Physics.CompressionPa))*Health);
            const double T=Tension/(FMath::Max(1.f,FMath::Min(A.Physics.TensionPa,B.Physics.TensionPa))*Health);
            const double S=Shear/(FMath::Max(1.f,FMath::Min(A.Physics.ShearPa,B.Physics.ShearPa))*Health);
            const float Ratio=float(FMath::Max3(C,T,S));
            Result.LoadRatios.FindOrAdd(L.A)=FMath::Max(Result.LoadRatios.FindRef(L.A),Ratio);
            Result.LoadRatios.FindOrAdd(L.B)=FMath::Max(Result.LoadRatios.FindRef(L.B),Ratio);
            // An unconverged estimate must not cause irreversible destruction.
            if(!Converged||Ratio<=1||Result.Broken.Num()+Result.Crushed.Num()>=64)continue;
            if(C>1||L.Ground)Result.Crushed.AddUnique(A.Physics.CompressionPa<=B.Physics.CompressionPa?L.A:L.B);
            else Result.Broken.Add({L.A,L.B});
        }
    }
    return Result;
}
