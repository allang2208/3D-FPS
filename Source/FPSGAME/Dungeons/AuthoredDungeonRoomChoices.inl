// Included in FPlan. Family probability is independent of how many variants it owns.
int32 FamilyUses(int32 Module,const FString* Route=nullptr)const
{
    int32 Count=0;
    for(const FPlaced& P:Pieces)
        if(Combat.Contains(P.Module)&&Modules[P.Module].Family==Modules[Module].Family&&(!Route||P.Route==*Route))++Count;
    return Count;
}
double RoomRepetitionCost(int32 Module,const FString& Route)const
{
    double Cost=100.*FamilyUses(Module)+220.*FamilyUses(Module,&Route);
    for(int32 I=Pieces.Num()-1;I>=0;--I)
        if(Pieces[I].Route==Route&&Combat.Contains(Pieces[I].Module))
        {if(Modules[Pieces[I].Module].Family==Modules[Module].Family)Cost+=450.;break;}
    return Cost;
}
TArray<TPair<int32,int32>> RoomChoices(const FString& Route)
{
    TArray<FString> Families;TArray<TArray<int32>> Variants;
    for(int32 M:Combat)
    {
        int32 F=Families.IndexOfByKey(Modules[M].Family);
        if(F==INDEX_NONE){F=Families.Add(Modules[M].Family);Variants.AddDefaulted();}
        Variants[F].Add(M);
    }
    struct FFamilyOrder {int32 Index;double Score;};TArray<FFamilyOrder> Order;
    int32 MaxVariants=0;
    for(int32 F=0;F<Families.Num();++F)
    {
        auto& V=Variants[F];MaxVariants=FMath::Max(MaxVariants,V.Num());
        for(int32 I=V.Num()-1;I>0;--I)V.Swap(I,Random.RandRange(0,I));
        Order.Add({F,RoomRepetitionCost(V[0],Route)+Random.FRand()*700.});
    }
    Order.StableSort([](const FFamilyOrder& A,const FFamilyOrder& B){return A.Score<B.Score;});
    TArray<TPair<int32,int32>> Result;
    // Each family gets a first candidate before another receives a second variant.
    for(int32 Round=0;Round<MaxVariants;++Round)for(const auto& F:Order)
        if(Variants[F.Index].IsValidIndex(Round))
        {
            const int32 M=Variants[F.Index][Round],First=Random.RandRange(0,1);
            Result.Emplace(M,First);Result.Emplace(M,1-First);
        }
    return Result;
}
bool CompleteSocketGraph(const FSocket& Start)
{
    TArray<FSocket> Sockets;Sockets.Add(Start);
    for(int32 I=0;I<Pieces.Num();++I)for(int32 J=0;J<PortCount(I);++J)Sockets.Add(Socket(I,J));
    TArray<TArray<int32>> Links;Links.SetNum(Pieces.Num()+1);
    for(int32 I=0;I<Sockets.Num();++I)
    {
        const auto& A=Sockets[I];int32 Mate=INDEX_NONE;
        for(int32 J=0;J<Sockets.Num();++J)
        {
            const auto& B=Sockets[J];
            if(A.Owner==B.Owner||!A.P.Equals(B.P,1.)||FVector::DotProduct(A.N,B.N)>-.999||
               FMath::Abs(A.Width-B.Width)>=1.||FMath::Abs(A.Height-B.Height)>=1.)continue;
            if(Mate!=INDEX_NONE){CompactFailure=TEXT("多个接口占用同一门口，放弃该布局");return false;}
            Mate=J;
        }
        if(Mate==INDEX_NONE){CompactFailure=TEXT("房间或通道存在未闭合接口，放弃该布局");return false;}
        Links[A.Owner+1].AddUnique(Sockets[Mate].Owner+1);
    }
    TArray<int32> Queue{0};TSet<int32> Seen{0};
    for(int32 Head=0;Head<Queue.Num();++Head)for(int32 Next:Links[Queue[Head]])
        if(!Seen.Contains(Next)){Seen.Add(Next);Queue.Add(Next);}
    if(Seen.Num()!=Links.Num()){CompactFailure=TEXT("存在与入口断开的房间，放弃该布局");return false;}
    return true;
}
