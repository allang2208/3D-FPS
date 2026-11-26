#pragma once
#include "CoreMinimal.h"
namespace TemperateHills
{
uint32 Mix(uint32 V);
uint32 Key(int32 X,int32 Y,uint32 Seed,uint32 Salt);
uint64 CellId(int32 X,int32 Y);
inline constexpr double EditBucketCm=3200.0;
double Unit(uint32 V);
double Smooth(double T);
double ValleyY(double X,int32 Seed);
}
