// Offline tests of the same admission function called by the runtime module.
// No Unreal process, D3D device, gameplay simulation, or copied policy implementation.
#include "../../Plugins/FPSDeformationResidency/Source/FPSDeformationResidency/Private/DeformationResidencyBudget.h"
#include <array>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <set>
#include <vector>

using FPSDeformationResidency::EBufferClass;
using FPSDeformationResidency::SelectHeapBudget;
struct FCandidate
{
    uintptr_t Key;
    uint64_t Bytes;
    EBufferClass Class;
    bool bProtected = false;
    bool bReservedElsewhere = false;
    bool bSelected = false;
};
static void Require(bool Condition, const char* Message)
{
    if (!Condition) { std::fprintf(stderr, "FAIL: %s\n", Message); std::exit(1); }
}
static std::set<uintptr_t> Selected(const std::vector<FCandidate>& Values)
{
    std::set<uintptr_t> Result;
    for (const auto& Value : Values) if (Value.bSelected) Result.insert(Value.Key);
    return Result;
}

int main()
{
    constexpr uint64_t MiB = 1024ull * 1024;
    std::mt19937 Random(20261029);
    Require(SelectHeapBudget<FCandidate>(nullptr, 0, 512 * MiB, 0) == 0, "empty request");

    std::vector<FCandidate> Full;
    for (uintptr_t Id = 1; Id <= 16; ++Id) Full.push_back({Id, 32 * MiB, EBufferClass::Hair, true});
    Full.push_back({17, 32 * MiB, EBufferClass::Morph});
    Require(SelectHeapBudget(Full.data(), Full.size(), 512 * MiB, 0) == 1, "17 heaps exceed 512 MiB by one heap");
    const auto Expected = Selected(Full);
    Require(Expected.size() == 16 && Expected.contains(17) && !Expected.contains(16), "late Morph replaces lower-class protected heap");
    for (int Run = 0; Run < 100; ++Run)
    {
        std::shuffle(Full.begin(), Full.end(), Random);
        SelectHeapBudget(Full.data(), Full.size(), 512 * MiB, 0);
        Require(Selected(Full) == Expected, "actor enumeration order must not churn the selected set");
    }

    std::array<FCandidate, 2> Shared{{
        {1, 32 * MiB, EBufferClass::Hair, true, true},
        {2, 32 * MiB, EBufferClass::Morph}
    }};
    Require(SelectHeapBudget(Shared.data(), Shared.size(), 512 * MiB, 512 * MiB) == 1, "other worlds exhaust budget");
    for (const auto& Value : Shared)
        Require(Value.bSelected == (Value.Key == 1), "another world's shared heap is retained without double charging");
    Require(SelectHeapBudget(Shared.data(), Shared.size(), 512 * MiB, 480 * MiB) == 0, "shared reservation plus exact remaining slot");
    Require(SelectHeapBudget(Shared.data(), Shared.size(), 32 * MiB, 64 * MiB) == 1, "reserved bytes above cap cannot underflow");

    std::array<FCandidate, 2> Mixed{{
        {1, 64 * MiB, EBufferClass::Morph},
        {2, 32 * MiB, EBufferClass::Skin}
    }};
    Require(SelectHeapBudget(Mixed.data(), Mixed.size(), 32 * MiB, 0) == 1, "oversized heap does not block a fitting heap");
    Require(!Mixed[0].bSelected && Mixed[1].bSelected, "heap admission remains within cap");
    Require(SelectHeapBudget(Mixed.data(), Mixed.size(), 0, 0) == 2, "zero available budget");

    // Property checks: bounded bytes, protected shared ownership, accurate skips,
    // and input-order independence across varying category/heap-size combinations.
    for (int Run = 0; Run < 10000; ++Run)
    {
        std::vector<FCandidate> Values;
        uint64_t Reserved = (Random() % 8) * MiB;
        const uint64_t Budget = (Random() % 65) * MiB;
        const uint32_t Count = Random() % 40;
        for (uintptr_t Id = 1; Id <= Count; ++Id)
        {
            const uint64_t Bytes = (1 + Random() % 8) * MiB;
            const bool IsShared = Random() % 5 == 0;
            if (IsShared) Reserved += Bytes;
            Values.push_back({Id, Bytes, EBufferClass(Random() % 3), IsShared || Random() % 2 == 0, IsShared});
        }
        const auto Skipped = SelectHeapBudget(Values.data(), Values.size(), Budget, Reserved);
        uint64_t AddedBytes = 0;
        uint32_t Rejected = 0;
        for (const auto& Value : Values)
        {
            Require(!Value.bReservedElsewhere || Value.bSelected, "shared owner must survive selection");
            if (Value.bSelected && !Value.bReservedElsewhere) AddedBytes += Value.Bytes;
            if (!Value.bSelected) ++Rejected;
        }
        Require(AddedBytes <= (Budget > Reserved ? Budget - Reserved : 0), "admission exceeds remaining process budget");
        Require(Skipped == Rejected, "skipped diagnostic mismatch");
        const auto First = Selected(Values);
        std::shuffle(Values.begin(), Values.end(), Random);
        SelectHeapBudget(Values.data(), Values.size(), Budget, Reserved);
        Require(Selected(Values) == First, "unstable tie breaking");
    }
    std::puts("PASS: late-Morph replacement, 512 MiB cap, stable selection, shared-world ownership, boundary cases, 10000 randomized cases.");
}
