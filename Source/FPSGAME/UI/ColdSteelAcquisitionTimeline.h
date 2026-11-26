#pragma once
#include "ColdSteelAcquisitionNotice.h"

/** The feed's real admission/animation state, independent of Slate and transport. */
struct FColdSteelAcquisitionTimeline
{
    static constexpr float Pitch=28.f,Drop=.3f,Life=12.f,Fade=.65f,Interval=.34f;
    struct FLine
    {
        FColdSteelAcquisitionNotice Notice;
        FString DisplayName,Quantity;
        float Age=0,MotionAge=0,Y=-24,StartY=-24,NameX=0,QuantityX=0;
        bool bTextChanged=true;
    };
    TArray<FLine> Lines;
    float AdmissionAge=Interval;
    void Reset(){Lines.Reset();AdmissionAge=Interval;}

    bool Advance(float Delta,int32 Capacity,TFunctionRef<bool(FColdSteelAcquisitionNotice&,const FString&)> Take)
    {
        if(Capacity<=0)return false;
        const bool HadLines=!Lines.IsEmpty();
        // If a window shrinks, retain the obscured rows until there is space again.
        for(int32 I=0;I<FMath::Min(Capacity,Lines.Num());++I){Lines[I].Age+=Delta;Lines[I].MotionAge+=Delta;}
        Lines.RemoveAll([](const auto& L){return L.Age>=Life;});
        AdmissionAge+=Delta;
        if(AdmissionAge>=Interval)
        {
            bool Taken=false;FColdSteelAcquisitionNotice Notice;
            for(auto& Line:Lines)if(Take(Notice,Line.Notice.Key))
            {
                Line.Notice.Count+=Notice.Count;Line.Age=FMath::Min(Line.Age,.16f);
                Line.MotionAge=0;Line.StartY=Line.Y-8;Line.bTextChanged=true;Taken=true;break;
            }
            // Existing rows get their readable lifetime. Pending gains wait instead
            // of being popped and immediately evicting the last visible row.
            if(!Taken&&Lines.Num()<Capacity&&Take(Notice,FString()))
            {
                FLine Line;Line.Notice=MoveTemp(Notice);
                Line.Y=Line.StartY=-Lines.Num()*Pitch-24.f;
                Lines.Insert(MoveTemp(Line),0);Taken=true;
            }
            if(Taken||Lines.Num()>=Capacity)AdmissionAge=0;
        }
        const int32 VisibleCount=FMath::Min(Capacity,Lines.Num());
        for(int32 I=0;I<Lines.Num();++I)
        {
            // The last visible row stays above the soul HUD. New rows drop into
            // free space above the stack without reserving empty rows below it.
            auto& Line=Lines[I];const float Target=(I-VisibleCount+1)*Pitch;
            const float T=FMath::Clamp(Line.MotionAge/Drop,0.f,1.f);
            Line.Y=Line.MotionAge<Drop?FMath::Lerp(Line.StartY,Target,T*T*(3.f-2.f*T))
                :FMath::FInterpTo(Line.Y,Target,Delta,16.f);
        }
        return HadLines||!Lines.IsEmpty();
    }
};
