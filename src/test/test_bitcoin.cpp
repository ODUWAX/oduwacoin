// Copyright (c) 2011-2015 The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#define BOOST_TEST_MODULE Bitcoin Test Suite

#include "test_bitcoin.h"

#include "chainparams.h"
#include "consensus/consensus.h"
#include "consensus/merkle.h"
#include "consensus/validation.h"
#include "key.h"
#include "main.h"
#include "miner.h"
#include "pubkey.h"
#include "pow.h"
#include "random.h"
#include "txdb.h"
#include "txmempool.h"
#include "ui_interface.h"
#include "util.h"
#include "rpc/server.h"
#include "rpc/register.h"

#include "test/testutil.h"

#include <boost/filesystem.hpp>
#include <boost/test/unit_test.hpp>
#include <boost/thread.hpp>

extern bool fPrintToConsole;
extern void noui_connect();

BasicTestingSetup::BasicTestingSetup(const std::string& chainName)
{
        ECC_Start();
        SetupEnvironment();
        SetupNetworking();
        fPrintToDebugLog = false; // don't want to write to debug.log file
        fCheckBlockIndex = true;
        SelectParams(chainName);
        noui_connect();
}

BasicTestingSetup::~BasicTestingSetup()
{
        ECC_Stop();
}

TestingSetup::TestingSetup(const std::string& chainName) : BasicTestingSetup(chainName)
{
    // The legacy production regtest genesis does not satisfy its configured
    // proof-of-work target. Keep production chain parameters untouched, but
    // use the known-valid nonce inside the unit-test process so fixtures can
    // initialize an active regtest chain deterministically.
    if (chainName == CBaseChainParams::REGTEST) {
        CChainParams& regtest = Params(chainName);
        CBlock& genesis = const_cast<CBlock&>(regtest.GenesisBlock());
        Consensus::Params& consensus = const_cast<Consensus::Params&>(regtest.GetConsensus());
        genesis.nNonce = 10638;
        consensus.hashGenesisBlock = genesis.GetHash();
    }

    const CChainParams& chainparams = Params();
        // Ideally we'd move all the RPC tests to the functional testing framework
        // instead of unit tests, but for now we need these here.
        RegisterAllCoreRPCCommands(tableRPC);
        ClearDatadirCache();
        pathTemp = GetTempPath() / strprintf("test_bitcoin_%lu_%i", (unsigned long)GetTime(), (int)(GetRand(100000)));
        boost::filesystem::create_directories(pathTemp);
        mapArgs["-datadir"] = pathTemp.string();
        mempool.setSanityCheck(1.0);
        pblocktree = new CBlockTreeDB(1 << 20, true);
        pcoinsdbview = new CCoinsViewDB(1 << 23, true);
        pcoinsTip = new CCoinsViewCache(pcoinsdbview);
        InitBlockIndex(chainparams);
        {
            CValidationState state;
            bool ok = ActivateBestChain(state, chainparams);
            BOOST_CHECK(ok);
        }
        nScriptCheckThreads = 3;
        for (int i=0; i < nScriptCheckThreads-1; i++)
            threadGroup.create_thread(&ThreadScriptCheck);
        RegisterNodeSignals(GetNodeSignals());
}

TestingSetup::~TestingSetup()
{
        UnregisterNodeSignals(GetNodeSignals());
        threadGroup.interrupt_all();
        threadGroup.join_all();
        UnloadBlockIndex();
        delete pcoinsTip;
        delete pcoinsdbview;
        delete pblocktree;
        boost::filesystem::remove_all(pathTemp);
}

TestChain100Setup::TestChain100Setup() : TestingSetup(CBaseChainParams::REGTEST)
{
    // Generate a 100-block chain:
    coinbaseKey.MakeNewKey(true);
    CScript scriptPubKey = CScript() <<  ToByteVector(coinbaseKey.GetPubKey()) << OP_CHECKSIG;
    for (int i = 0; i < Params().GetConsensus().nCoinbaseMaturity; i++)
    {
        std::vector<CMutableTransaction> noTxns;
        CBlock b = CreateAndProcessBlock(noTxns, scriptPubKey);
        // Setup blocks must connect; callers of CreateAndProcessBlock() may
        // intentionally submit invalid blocks, so the strict check lives here.
        BOOST_REQUIRE_MESSAGE(chainActive.Tip()->GetBlockHash() == b.GetHash(),
                              "TestChain100Setup block failed to connect");
        coinbaseTxns.push_back(b.vtx[0]);
    }
}

//
// Create a new block with just given transactions, coinbase paying to
// scriptPubKey, and try to add it to the current chain.
//
CBlock
TestChain100Setup::CreateAndProcessBlock(const std::vector<CMutableTransaction>& txns, const CScript& scriptPubKey)
{
    const CChainParams& chainparams = Params();
    CBlockIndex* pindexPrev = chainActive.Tip();
    BOOST_REQUIRE(pindexPrev != NULL);

    // Build fixture blocks directly instead of calling CreateNewBlock().
    // The legacy production TestBlockValidity() path creates a temporary
    // CBlockIndex without phashBlock; this test fixture must not depend on it.
    // ProcessNewBlock() below still applies the real consensus validation.
    CBlock block;
    block.nVersion = 6;
    block.hashPrevBlock = pindexPrev->GetBlockHash();
    block.nTime = pindexPrev->GetPastTimeLimit() + 1;
    BOOST_FOREACH(const CMutableTransaction& tx, txns) {
        if (block.nTime < tx.nTime)
            block.nTime = tx.nTime;
    }
    block.nBits = GetNextTargetRequired(pindexPrev, &block, chainparams.GetConsensus(), false);
    block.nNonce = 0;

    CMutableTransaction coinbaseTx;
    coinbaseTx.nTime = block.nTime;
    coinbaseTx.vin.resize(1);
    coinbaseTx.vin[0].prevout.SetNull();
    coinbaseTx.vin[0].scriptSig = CScript() << (pindexPrev->nHeight + 1) << OP_0;
    coinbaseTx.vout.resize(1);
    coinbaseTx.vout[0].scriptPubKey = scriptPubKey;
    coinbaseTx.vout[0].nValue = GetProofOfWorkSubsidy(pindexPrev->nHeight + 1, 0);
    block.vtx.push_back(CTransaction(coinbaseTx));

    BOOST_FOREACH(const CMutableTransaction& tx, txns)
        block.vtx.push_back(CTransaction(tx));

    block.hashMerkleRoot = BlockMerkleRoot(block);
    while (!CheckProofOfWork(block.GetPoWHash(), block.nBits, chainparams.GetConsensus()))
        ++block.nNonce;

    // Do not require acceptance here: some tests (e.g. tx_validationcache_tests)
    // deliberately submit invalid blocks and assert on the resulting chain tip.
    CValidationState state;
    ProcessNewBlock(state, chainparams, NULL, &block, true, NULL, false);

    return block;
}

TestChain100Setup::~TestChain100Setup()
{
}


CTxMemPoolEntry TestMemPoolEntryHelper::FromTx(CMutableTransaction &tx, CTxMemPool *pool) {
    CTransaction txn(tx);
    return FromTx(txn, pool);
}

CTxMemPoolEntry TestMemPoolEntryHelper::FromTx(CTransaction &txn, CTxMemPool *pool) {
    bool hasNoDependencies = pool ? pool->HasNoInputsOf(txn) : hadNoDependencies;
    // Hack to assume either its completely dependent on other mempool txs or not at all
    CAmount inChainValue = hasNoDependencies ? txn.GetValueOut() : 0;

    return CTxMemPoolEntry(txn, nFee, nTime, dPriority, nHeight,
                           hasNoDependencies, inChainValue, spendsCoinbase, sigOpCost, lp);
}

void Shutdown(void* parg)
{
  exit(0);
}

void StartShutdown()
{
  exit(0);
}

bool ShutdownRequested()
{
  return false;
}
