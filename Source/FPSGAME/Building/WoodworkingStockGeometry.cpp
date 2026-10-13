#include "WoodworkingStockGeometry.h"
#include <algorithm>

namespace WoodworkingStockGeometry
{
FPlan Plan(const uint8_t* Cells,int Count,int Width,int Height)
{
    FPlan Result;
    if(!Cells||Width<1||Height<1||Width>768||Height>512||Count!=Width*Height||Count>MaximumCells)return Result;
    auto Solid=[&](int X,int Y){return X>=0&&Y>=0&&X<Width&&Y<Height&&Cells[Y*Width+X]!=0;};
    std::vector<int> Previous(Width,-1),Current(Width,-1);
    for(int Y=0;Y<Height;++Y)
    {
        std::fill(Current.begin(),Current.end(),-1);
        for(int X=0;X<Width;)
        {
            if(!Solid(X,Y)){++X;continue;}
            const int Start=X;while(X<Width&&Solid(X,Y))++X;
            Result.Area+=X-Start;
            int Index=Previous[Start];
            if(Index>=0&&Result.Faces[Index].X1==X)Result.Faces[Index].Y1=Y+1;
            else
            {
                Index=int(Result.Faces.size());Result.Faces.push_back({Start,Y,X,Y+1});
                if(Result.Faces.size()*2>MaximumQuads)return FPlan();
            }
            Current[Start]=Index;
        }
        Previous.swap(Current);
    }
    auto AddEdge=[&](FEdge E,int Length)
    {
        Result.Edges.push_back(E);Result.Perimeter+=Length;
        return Result.Faces.size()*2+Result.Edges.size()<=MaximumQuads;
    };
    for(int Y=0;Y<=Height;++Y)for(int X=0;X<Width;)
    {
        const int Sign=int(Solid(X,Y-1))-int(Solid(X,Y));
        if(!Sign){++X;continue;}
        const int Start=X;
        while(X<Width&&int(Solid(X,Y-1))-int(Solid(X,Y))==Sign)++X;
        if(!AddEdge({Start,Y,X,Y,0,Sign},X-Start))return FPlan();
    }
    for(int X=0;X<=Width;++X)for(int Y=0;Y<Height;)
    {
        const int Sign=int(Solid(X-1,Y))-int(Solid(X,Y));
        if(!Sign){++Y;continue;}
        const int Start=Y;
        while(Y<Height&&int(Solid(X-1,Y))-int(Solid(X,Y))==Sign)++Y;
        if(!AddEdge({X,Start,X,Y,Sign,0},Y-Start))return FPlan();
    }
    Result.Valid=true;return Result;
}
}
