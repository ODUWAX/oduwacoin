// Copyright (c) 2015 The Bitcoin Core developers
// Distributed under the MIT/X11 software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#include "arith_uint256.h"
#include "chain.h"
#include "chainparams.h"
#include "pow.h"
#include "random.h"
#include "test/test_bitcoin.h"
#include "util.h"

#include <boost/test/unit_test.hpp>

using namespace std;

BOOST_FIXTURE_TEST_SUITE(pow_tests, BasicTestingSetup)

static void LinkBlock(CBlockIndex& block, CBlockIndex* prev, int height, int64_t time, unsigned int bits)
{
    block.pprev = prev;
    block.nHeight = height;
    block.nTime = time;
    block.nBits = bits;
}

BOOST_AUTO_TEST_CASE(initial_pow_blocks_use_pow_limit)
{
    SelectParams(CBaseChainParams::MAIN);
    const Consensus::Params& params = Params().GetConsensus();

    CBlockIndex first;
    LinkBlock(first, NULL, 0, 1500000000, UintToArith256(params.powLimit).GetCompact());

    BOOST_CHECK_EQUAL(
        GetNextTargetRequired(&first, NULL, params, false),
        UintToArith256(params.powLimit).GetCompact());

    CBlockIndex second;
    LinkBlock(second, &first, 1, first.nTime + params.nTargetSpacingV1,
              UintToArith256(params.powLimit).GetCompact());

    BOOST_CHECK_EQUAL(
        GetNextTargetRequired(&second, NULL, params, false),
        UintToArith256(params.powLimit).GetCompact());
}

BOOST_AUTO_TEST_CASE(target_spacing_keeps_target_stable)
{
    SelectParams(CBaseChainParams::MAIN);
    const Consensus::Params& params = Params().GetConsensus();

    const int height = 1300000;
    const int64_t spacing = params.nTargetSpacing;
    const arith_uint256 baseTarget = UintToArith256(params.powLimit) >> 4;
    const unsigned int bits = baseTarget.GetCompact();

    CBlockIndex first;
    CBlockIndex second;
    CBlockIndex third;

    LinkBlock(first, NULL, height - 2, 1500000000, bits);
    LinkBlock(second, &first, height - 1, first.nTime + spacing, bits);
    LinkBlock(third, &second, height, second.nTime + spacing, bits);

    BOOST_CHECK_EQUAL(GetNextTargetRequired(&third, NULL, params, false), bits);
}

BOOST_AUTO_TEST_CASE(shorter_spacing_increases_difficulty)
{
    SelectParams(CBaseChainParams::MAIN);
    const Consensus::Params& params = Params().GetConsensus();

    const int height = 1300000;
    const int64_t spacing = params.nTargetSpacing;
    const arith_uint256 baseTarget = UintToArith256(params.powLimit) >> 4;
    const unsigned int bits = baseTarget.GetCompact();

    CBlockIndex first;
    CBlockIndex second;
    CBlockIndex third;

    LinkBlock(first, NULL, height - 2, 1500000000, bits);
    LinkBlock(second, &first, height - 1, first.nTime + spacing, bits);
    LinkBlock(third, &second, height, second.nTime + spacing / 2, bits);

    arith_uint256 result;
    result.SetCompact(GetNextTargetRequired(&third, NULL, params, false));

    arith_uint256 decodedBase;
    decodedBase.SetCompact(bits);

    BOOST_CHECK(result < decodedBase);
}

BOOST_AUTO_TEST_CASE(longer_spacing_decreases_difficulty)
{
    SelectParams(CBaseChainParams::MAIN);
    const Consensus::Params& params = Params().GetConsensus();

    const int height = 1300000;
    const int64_t spacing = params.nTargetSpacing;
    const arith_uint256 baseTarget = UintToArith256(params.powLimit) >> 4;
    const unsigned int bits = baseTarget.GetCompact();

    CBlockIndex first;
    CBlockIndex second;
    CBlockIndex third;

    LinkBlock(first, NULL, height - 2, 1500000000, bits);
    LinkBlock(second, &first, height - 1, first.nTime + spacing, bits);
    LinkBlock(third, &second, height, second.nTime + spacing * 2, bits);

    arith_uint256 result;
    result.SetCompact(GetNextTargetRequired(&third, NULL, params, false));

    arith_uint256 decodedBase;
    decodedBase.SetCompact(bits);

    BOOST_CHECK(result > decodedBase);
    BOOST_CHECK(result <= UintToArith256(params.powLimit));
}

BOOST_AUTO_TEST_CASE(negative_spacing_after_height_10000_is_normalized)
{
    SelectParams(CBaseChainParams::MAIN);
    const Consensus::Params& params = Params().GetConsensus();

    const int height = 1300000;
    const int64_t spacing = params.nTargetSpacing;
    const arith_uint256 baseTarget = UintToArith256(params.powLimit) >> 4;
    const unsigned int bits = baseTarget.GetCompact();

    CBlockIndex first;
    CBlockIndex second;
    CBlockIndex third;

    LinkBlock(first, NULL, height - 2, 1500000000, bits);
    LinkBlock(second, &first, height - 1, first.nTime + spacing, bits);
    LinkBlock(third, &second, height, second.nTime - spacing, bits);

    BOOST_CHECK_EQUAL(GetNextTargetRequired(&third, NULL, params, false), bits);
}

BOOST_AUTO_TEST_CASE(GetBlockProofEquivalentTime_test)
{
    SelectParams(CBaseChainParams::MAIN);
    const Consensus::Params& params = Params().GetConsensus();

    std::vector<CBlockIndex> blocks(10000);
    for (int i = 0; i < 10000; i++) {
        blocks[i].pprev = i ? &blocks[i - 1] : NULL;
        blocks[i].nHeight = i;
        blocks[i].nTime = 1269211443 + i * params.nTargetSpacing;
        blocks[i].nBits = 0x207fffff;
        blocks[i].nChainWork = i ? blocks[i - 1].nChainWork + GetBlockProof(blocks[i - 1]) : arith_uint256(0);
    }

    for (int j = 0; j < 1000; j++) {
        CBlockIndex *p1 = &blocks[GetRand(10000)];
        CBlockIndex *p2 = &blocks[GetRand(10000)];
        CBlockIndex *p3 = &blocks[GetRand(10000)];

        int64_t tdiff = GetBlockProofEquivalentTime(*p1, *p2, *p3, params);
        BOOST_CHECK_EQUAL(tdiff, p1->GetBlockTime() - p2->GetBlockTime());
    }
}

BOOST_AUTO_TEST_SUITE_END()
