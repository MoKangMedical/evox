"""
EvoAgentX 集成层 — 将EvoAgentX的进化能力接入任意项目

三层进化架构:
  Layer 1: Darwin (Skill文档) — 8维度评分 + 棘轮
  Layer 2: EvoPrompt (Prompt) — 遗传算法优化Prompt
  Layer 3: SEW (工作流) — 工作流结构进化

集成方式:
  1. 安装EvoAgentX: pip install evoagentx (或 ~/EvoAgentX/venv)
  2. 配置LLM API Key
  3. 调用evolve()

回退策略: 如果EvoAgentX不可用，使用内置简化版进化引擎
"""

import os
import json
import subprocess
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional


# ============================================
# 尝试导入EvoAgentX (可选依赖)
# ============================================

EVOAGENTX_AVAILABLE = False
try:
    import sys
    evox_path = os.path.expanduser("~/EvoAgentX")
    venv_path = os.path.join(evox_path, "venv", "lib")
    # 尝试导入
    sys.path.insert(0, evox_path)
    from evoagentx.core.module import BaseModule
    from evoagentx.models import OpenAILLMConfig
    EVOAGENTX_AVAILABLE = True
except Exception:
    pass


# ============================================
# 集成配置
# ============================================

@dataclass
class EvoXConfig:
    """进化引擎配置"""
    project_path: str = ""
    
    # Layer 1: Darwin
    darwin_enabled: bool = True
    darwin_rounds: int = 3
    darwin_checkpoint: bool = True  # Human in the loop
    
    # Layer 2: EvoPrompt
    evoprompt_enabled: bool = False  # 需要EvoAgentX + API Key
    evoprompt_population: int = 6
    evoprompt_iterations: int = 5
    evoprompt_model: str = "gpt-4o"
    
    # Layer 3: SEW
    sew_enabled: bool = False  # 需要EvoAgentX + API Key
    sew_max_steps: int = 5
    
    # LLM配置
    openai_api_key: str = ""
    openai_base_url: str = ""
    
    def to_dict(self):
        return asdict(self)


# ============================================
# 进化结果
# ============================================

@dataclass
class EvoResult:
    layer: str = ""  # "darwin" | "evoprompt" | "sew"
    target: str = ""
    before_score: float = 0
    after_score: float = 0
    improved: bool = False
    description: str = ""
    timestamp: str = ""


# ============================================
# 三层进化引擎
# ============================================

class TripleEvolver:
    """
    三层进化引擎
    
    自动检测环境:
    - 有EvoAgentX → 启用全三层
    - 无EvoAgentX → 仅用Layer 1 (达尔文)
    
    用法:
        config = EvoXConfig(project_path="~/Desktop/metaforge", openai_api_key="sk-...")
        evolver = TripleEvolver(config)
        results = evolver.evolve_all()
    """
    
    def __init__(self, config: EvoXConfig):
        self.config = config
        self.results = []
        self._darwin = None
        self._evoprompt = None
        self._sew = None
        
        # 初始化可用的进化器
        self._init_darwin()
        if EVOAGENTX_AVAILABLE and config.openai_api_key:
            self._init_evoprompt()
            self._init_sew()
    
    def _init_darwin(self):
        """初始化达尔文评分器 (Layer 1)"""
        import sys
        sys.path.insert(0, os.path.expanduser("~/Desktop/evox"))
        from evox import UniversalEvolver
        self._darwin = UniversalEvolver(self.config.project_path)
    
    def _init_evoprompt(self):
        """初始化EvoPrompt优化器 (Layer 2)"""
        if not EVOAGENTX_AVAILABLE:
            return
        try:
            from evoagentx.models import OpenAILLMConfig
            self._llm_config = OpenAILLMConfig(
                model=self.config.evoprompt_model,
                api_key=self.config.openai_api_key,
                base_url=self.config.openai_base_url or None,
            )
            self._evoprompt = True  # 标记可用
        except Exception as e:
            print(f"⚠️ EvoPrompt初始化失败: {e}")
    
    def _init_sew(self):
        """初始化SEW优化器 (Layer 3)"""
        if not EVOAGENTX_AVAILABLE:
            return
        try:
            self._sew = True  # 标记可用
        except Exception as e:
            print(f"⚠️ SEW初始化失败: {e}")
    
    def evolve_layer1(self) -> list:
        """
        Layer 1: 达尔文进化 (Skill文档)
        
        始终可用，不需要EvoAgentX
        """
        if not self.config.darwin_enabled or not self._darwin:
            return []
        
        print(f"\n🧬 Layer 1: 达尔文进化 ({self.config.darwin_rounds}轮)")
        
        report = self._darwin.evolve(rounds=self.config.darwin_rounds)
        
        results = []
        for r in self._darwin.rounds:
            results.append(EvoResult(
                layer="darwin",
                target=r.target,
                before_score=r.before,
                after_score=r.after,
                improved=r.improved,
                description=r.description,
                timestamp=datetime.now().isoformat(),
            ))
        
        print(f"  ✅ 成功: {report.successful} | ⏪ 回滚: {report.reverted}")
        print(f"  📈 平均分: {report.avg_score_before:.1f} → {report.avg_score_after:.1f}")
        
        return results
    
    def evolve_layer2(self) -> list:
        """
        Layer 2: EvoPrompt进化 (Agent Prompt)
        
        需要EvoAgentX + API Key
        """
        if not self.config.evoprompt_enabled or not self._evoprompt:
            return []
        
        print(f"\n🧬 Layer 2: EvoPrompt进化 (种群={self.config.evoprompt_population}, 迭代={self.config.evoprompt_iterations})")
        
        # 这里集成EvoAgentX的GA/DE优化器
        # 由于需要完整的Benchmark定义，这里提供框架
        # 实际使用时需要为每个项目定义evaluate函数
        
        results = []
        
        # 扫描prompt文件
        import sys
        sys.path.insert(0, os.path.expanduser("~/Desktop/evox"))
        from evox import scan_assets
        
        assets = scan_assets(self.config.project_path)
        prompt_assets = [a for a in assets if a["type"] in ("prompt", "prompt_embedded")]
        
        for asset in prompt_assets:
            full_path = os.path.join(self.config.project_path, asset["path"])
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                original_prompt = f.read()
            
            # TODO: 用EvoAgentX的GA优化器进化prompt
            # ga = GAOptimizer(registry=registry, program=program, ...)
            # best_config, best_score, history = await ga.optimize(benchmark)
            
            results.append(EvoResult(
                layer="evoprompt",
                target=asset["path"],
                description="EvoPrompt进化 (需要完整Benchmark定义)",
                timestamp=datetime.now().isoformat(),
            ))
        
        print(f"  📋 发现 {len(prompt_assets)} 个Prompt资产待进化")
        return results
    
    def evolve_layer3(self) -> list:
        """
        Layer 3: SEW进化 (工作流结构)
        
        需要EvoAgentX + API Key
        """
        if not self.config.sew_enabled or not self._sew:
            return []
        
        print(f"\n🧬 Layer 3: SEW工作流进化 (最大{self.config.sew_max_steps}步)")
        
        results = []
        
        # 扫描workflow文件
        import sys
        sys.path.insert(0, os.path.expanduser("~/Desktop/evox"))
        from evox import scan_assets
        
        assets = scan_assets(self.config.project_path)
        workflow_assets = [a for a in assets if a["type"] in ("skill", "workflow")]
        
        for asset in workflow_assets:
            full_path = os.path.join(self.config.project_path, asset["path"])
            
            # TODO: 用EvoAgentX的SEW优化器进化工作流
            # sew = SEWWorkFlowOptimizer(graph=workflow, evaluator=evaluator, ...)
            # sew.optimize(dataset=benchmark)
            
            results.append(EvoResult(
                layer="sew",
                target=asset["path"],
                description="SEW工作流进化 (需要完整Benchmark定义)",
                timestamp=datetime.now().isoformat(),
            ))
        
        print(f"  📋 发现 {len(workflow_assets)} 个工作流资产待进化")
        return results
    
    def evolve_all(self) -> list:
        """执行三层进化"""
        print(f"\n{'='*60}")
        print(f"🧬 三层进化引擎启动")
        print(f"  项目: {self.config.project_path}")
        print(f"  EvoAgentX: {'✅ 可用' if EVOAGENTX_AVAILABLE else '❌ 不可用 (使用内置引擎)'}")
        print(f"{'='*60}")
        
        # Layer 1: 始终执行
        r1 = self.evolve_layer1()
        self.results.extend(r1)
        
        # Layer 2: 需要EvoAgentX
        if self.config.evoprompt_enabled:
            r2 = self.evolve_layer2()
            self.results.extend(r2)
        
        # Layer 3: 需要EvoAgentX
        if self.config.sew_enabled:
            r3 = self.evolve_layer3()
            self.results.extend(r3)
        
        # 保存结果
        self._save_results()
        
        print(f"\n{'='*60}")
        print(f"🧬 进化完成 — 共 {len(self.results)} 条记录")
        improved = sum(1 for r in self.results if r.improved)
        print(f"  ✅ 改进: {improved} | ⏭️ 无变化: {len(self.results)-improved}")
        print(f"{'='*60}")
        
        return self.results
    
    def _save_results(self):
        """保存进化结果"""
        report_dir = os.path.join(self.config.project_path, ".evox")
        os.makedirs(report_dir, exist_ok=True)
        
        report = {
            "project": self.config.project_path,
            "timestamp": datetime.now().isoformat(),
            "evoagentx_available": EVOAGENTX_AVAILABLE,
            "config": self.config.to_dict(),
            "results": [asdict(r) for r in self.results],
        }
        
        report_path = os.path.join(report_dir, "triple_evolution.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)


# ============================================
# 快捷函数: 对所有项目进化
# ============================================

def evolve_all_projects(api_key: str = "", projects: list = None):
    """对所有项目执行三层进化"""
    
    if projects is None:
        projects = [
            "~/Desktop/metaforge",
            "~/Desktop/PharmaSim",
            "~/Desktop/KnowHealth",
            "~/Desktop/global-app-starter",
        ]
    
    all_results = {}
    
    for proj in projects:
        expanded = os.path.expanduser(proj)
        if not os.path.exists(expanded):
            continue
        
        config = EvoXConfig(
            project_path=proj,
            darwin_enabled=True,
            darwin_rounds=2,
            evoprompt_enabled=bool(api_key),
            openai_api_key=api_key,
        )
        
        evolver = TripleEvolver(config)
        results = evolver.evolve_all()
        all_results[proj] = results
    
    return all_results


# ============================================
# CLI
# ============================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("用法: python evox_integration.py <command> <project_path> [api_key]")
        print()
        print("命令:")
        print("  evolve <path> [api_key]    执行三层进化")
        print("  status <path>              查看进化状态")
        print("  all [api_key]              对所有项目进化")
        print()
        print(f"EvoAgentX状态: {'✅ 已安装' if EVOAGENTX_AVAILABLE else '❌ 未安装 (使用内置引擎)'}")
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "evolve":
        path = sys.argv[2]
        api_key = sys.argv[3] if len(sys.argv) > 3 else ""
        config = EvoXConfig(project_path=path, openai_api_key=api_key, evoprompt_enabled=bool(api_key))
        evolver = TripleEvolver(config)
        evolver.evolve_all()
    
    elif cmd == "all":
        api_key = sys.argv[2] if len(sys.argv) > 2 else ""
        evolve_all_projects(api_key)
    
    elif cmd == "status":
        path = sys.argv[2]
        report_path = os.path.join(os.path.expanduser(path), ".evox", "triple_evolution.json")
        if os.path.exists(report_path):
            with open(report_path) as f:
                data = json.load(f)
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print("未找到进化报告")
