#pragma once

#include "../UI/FPSPerformanceMetrics.h"
#include <type_traits>

// The dungeon also ships against the published metrics API, before the optional
// event recorder. Keep that recorder's in-progress UI changes out of this module.
class FPSGAME_API FFPSPerformanceScope;

namespace DungeonPerformance
{
template<typename T, typename = void>
class TScope
{
public:
    TScope(const UObject*, FName, const FString& = FString()) {}
    void Finish() {}
};

template<typename T>
class TScope<T, std::void_t<decltype(sizeof(T))>>
{
public:
    TScope(const UObject* Context, FName Stage, const FString& Key = FString())
        : Scope(Context, Stage, Key) {}
    void Finish() { Scope.Finish(); }
private:
    T Scope;
};

template<typename T, typename = void>
struct TMarker
{
    static void Record(const UObject*, FName, const FString&) {}
};

template<typename T>
struct TMarker<T, std::void_t<decltype(&T::RecordMarker)>>
{
    static void Record(const UObject* Context, FName Stage, const FString& Detail)
    { T::RecordMarker(Context, Stage, Detail); }
};

using FScope = TScope<FFPSPerformanceScope>;
using FMarker = TMarker<UFPSPerformanceMetricsSubsystem>;
}
