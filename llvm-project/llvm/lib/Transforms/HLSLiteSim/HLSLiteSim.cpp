#include "llvm/Pass.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/Analysis/LoopInfo.h"
#include "llvm/Analysis/LoopPass.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/IRBuilder.h"

using namespace llvm;
using namespace std;

namespace {
    struct BBTracePass : public FunctionPass {
        static char ID;
        FunctionCallee trace_func;

        BBTracePass() : FunctionPass(ID) {}

        bool doInitialization(Module &M) override {
            trace_func = M.getOrInsertFunction(
                "__hlslitesim_trace_bb",
                FunctionType::get(
                    Type::getVoidTy(M.getContext()),
                    {
                        Type::getInt8PtrTy(M.getContext()),
                        Type::getInt32Ty(M.getContext())
                    },
                    false
                )
            );
            return true;
        }

        bool runOnFunction(Function &F) override {
            if (!isTraceable(F)) {
                return false;
            }

            IRBuilder<> builder(&F.getEntryBlock());
            Value* func_name = builder.CreateGlobalStringPtr(F.getName());

            uint32_t bb_id = 0;
            for (BasicBlock& BB : F) {
                IRBuilder<> builder(&BB, BB.getFirstInsertionPt());
                builder.CreateCall(trace_func, array<Value*, 2>({
                    func_name,
                    ConstantInt::get(Type::getInt32Ty(F.getContext()), bb_id)
                }));
                bb_id++;
            }

            return true;
        }

        StringRef getPassName() const override {
            return "HLSLiteSim Basic Block Trace Pass";
        }

    private:
        bool isTraceable(Function &F) {
            if (F.isDeclaration()) {
                return false;
            }
            if (F.getName().startswith("_ssdm_op_")) {
                return false;
            }
            return true;
        }
    };

    struct FixLoopMDPass : public LoopPass {
        static char ID;

        FixLoopMDPass() : LoopPass(ID) {}

        bool runOnLoop(Loop *L, LPPassManager &LPM) override {
            MDNode *LoopID = L->getLoopID();
            if (!LoopID || LoopID->getNumOperands() < 1) {
                return false;
            }

            bool modified = false;
            TempMDTuple Temp = MDNode::getTemporary(LoopID->getContext(), None);
            SmallVector<Metadata*> Args({ Temp.get() });
            for (unsigned i = 1, e = LoopID->getNumOperands(); i < e; ++i) {
                Metadata *operand = LoopID->getOperand(i);
                MDNode *MD = dyn_cast<MDNode>(operand);
                if (!MD || MD->getNumOperands() >= 1) {
                    Args.push_back(operand);
                } else {
                    modified = true;
                }
            }
            if (!modified) {
                return false;
            }

            LoopID = MDNode::get(LoopID->getContext(), Args);
            LoopID->replaceOperandWith(0, LoopID);
            L->setLoopID(LoopID);
            return true;
        }

        StringRef getPassName() const override {
            return "HLSLiteSim Fix Loop Metadata Pass";
        }
    };

    struct HLSLiteSimPassManager : public ModulePass {
        static char ID;

        HLSLiteSimPassManager() : ModulePass(ID) {}

        bool runOnModule(Module &M) override {
            legacy::PassManager PM;
            PM.add(new BBTracePass());
            PM.add(new FixLoopMDPass());
            return PM.run(M);
        }
    };
}

char BBTracePass::ID = 0;
char FixLoopMDPass::ID = 0;
char HLSLiteSimPassManager::ID = 0;
static RegisterPass<HLSLiteSimPassManager> X("hlslitesim", "HLSLiteSim Pass");
