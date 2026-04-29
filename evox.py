"""
Universal Evolution Engine — 通用三层进化引擎
适配所有项目：MetaForge / PharmaSim / KnowHealth / MediChat-RD / GlobalApp

三层架构:
  Layer 1: Darwin (Skill文档层) — 8维度评分 + 棘轮
  Layer 2: EvoPrompt (Prompt层) — 遗传算法优化Prompt
  Layer 3: SEW (工作流层) — 工作流结构进化

使用方式:
  from evox import UniversalEvolver
  evolver = UniversalEvolver(project_path="~/Desktop/my-project")
  evolver.scan()          # 扫描所有可进化资产
  evolver.evolve(rounds=3) # 运行3轮进化
  evolver.report()         # 生成进化报告
"""

import os
import sys
import json
import time
import random
import hashlib
import subprocess
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path


# ============================================
# 8维度评分系统 (来自达尔文框架)
# ============================================

DARWIN_DIMENSIONS = {
    "frontmatter":       {"name": "Frontmatter规范",   "max": 8,  "category": "structure"},
    "workflow_clarity":  {"name": "工作流清晰度",       "max": 15, "category": "structure"},
    "error_handling":    {"name": "异常处理",           "max": 10, "category": "structure"},
    "checkpoints":       {"name": "确认检查点",         "max": 7,  "category": "structure"},
    "specificity":       {"name": "指令具体性",         "max": 15, "category": "structure"},
    "path_integrity":    {"name": "路径完整性",         "max": 5,  "category": "structure"},
    "architecture":      {"name": "架构合理性",         "max": 15, "category": "effectiveness"},
    "real_world_output": {"name": "实测输出质量",       "max": 25, "category": "effectiveness"},
}


@dataclass
class AssetScore:
    path: str = ""
    asset_type: str = ""  # skill, prompt, config, workflow
    total: int = 0
    dimensions: dict = field(default_factory=dict)
    weakest: str = ""
    weakest_score: int = 0
    weakest_max: int = 0


@dataclass
class EvolutionRound:
    round_num: int = 0
    target: str = ""
    dimension: str = ""
    before: int = 0
    after: int = 0
    improved: bool = False
    description: str = ""
    commit_hash: str = ""
    reverted: bool = False


@dataclass
class EvolutionReport:
    project: str = ""
    timestamp: str = ""
    total_assets: int = 0
    avg_score_before: float = 0
    avg_score_after: float = 0
    rounds: list = field(default_factory=list)
    successful: int = 0
    reverted: int = 0


# ============================================
# 扫描器: 发现所有可进化资产
# ============================================

EVOLVABLE_PATTERNS = {
    "skill":   ["SKILL.md", "*.skill.md"],
    "prompt":  ["*.prompt.md", "PROMPT.md", "system_prompt.txt", "system_prompt.md"],
    "config":  ["agent_config.yaml", "agent_config.json", "agent_config.yml"],
    "workflow": ["workflow.yaml", "workflow.json", "workflow.yml", "WORKFLOW.md"],
}

def scan_assets(project_path: str) -> list:
    """扫描项目中所有可进化资产"""
    project_path = os.path.expanduser(project_path)
    assets = []
    
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in 
                   ("node_modules", "__pycache__", "venv", ".git", ".next", "dist", "build")]
        
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, project_path)
            
            for atype, patterns in EVOLVABLE_PATTERNS.items():
                for pat in patterns:
                    if pat.startswith("*"):
                        if f.endswith(pat[1:]):
                            assets.append({"path": rel, "type": atype, "size": os.path.getsize(full)})
                    elif f == pat:
                        assets.append({"path": rel, "type": atype, "size": os.path.getsize(full)})
            
            # 也扫描 .py 文件中的 prompt 字符串
            if f.endswith(".py") and os.path.getsize(full) < 50000:
                try:
                    with open(full, "r", encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                    if "system_prompt" in content.lower() or "SYSTEM_PROMPT" in content:
                        assets.append({"path": rel, "type": "prompt_embedded", "size": os.path.getsize(full)})
                except:
                    pass
    
    # 去重
    seen = set()
    unique = []
    for a in assets:
        if a["path"] not in seen:
            seen.add(a["path"])
            unique.append(a)
    
    return unique


# ============================================
# Layer 1: 达尔文评分引擎
# ============================================

class DarwinScorer:
    """8维度评分"""
    
    @staticmethod
    def score_file(filepath: str) -> AssetScore:
        full = os.path.expanduser(filepath)
        if not os.path.exists(full):
            return AssetScore(path=filepath, total=0)
        
        with open(full, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        dims = {}
        total = 0
        
        # 1. Frontmatter (8分)
        fm = 0
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                fm_text = content[3:end]
                if "name:" in fm_text: fm += 2
                if "description:" in fm_text and len(fm_text.split("description:")[1].split("\n")[0]) > 10: fm += 2
                if "triggers:" in fm_text or "trigger:" in fm_text: fm += 2
                if "version:" in fm_text or "category:" in fm_text: fm += 2
        dims["frontmatter"] = {"score": fm, "max": 8}
        total += fm
        
        # 2. 工作流清晰度 (15分)
        wf = 0
        lines = content.split("\n")
        steps = [l for l in lines if l.strip().startswith(("##", "###", "Step", "步骤"))]
        if len(steps) >= 3: wf += 5
        if len(steps) >= 5: wf += 5
        numbered = [l for l in lines if l.strip() and l.strip()[0].isdigit() and "." in l[:4]]
        if len(numbered) >= 3: wf += 5
        dims["workflow_clarity"] = {"score": min(wf, 15), "max": 15}
        total += min(wf, 15)
        
        # 3. 异常处理 (10分)
        err = 0
        for kw in ["error", "异常", "失败", "fallback", "兜底", "边界", "exception", "catch", "retry", "超时"]:
            if kw.lower() in content.lower():
                err += 2
                if err >= 10: break
        dims["error_handling"] = {"score": err, "max": 10}
        total += err
        
        # 4. 检查点 (7分)
        cp = 0
        for kw in ["确认", "confirm", "检查点", "checkpoint", "暂停", "wait", "⚠️"]:
            if kw in content:
                cp += 1
                if cp >= 7: break
        dims["checkpoints"] = {"score": cp, "max": 7}
        total += cp
        
        # 5. 指令具体性 (15分)
        sp = 0
        if "```" in content: sp += 5
        if "示例" in content or "example" in content.lower(): sp += 5
        if "格式" in content or "format" in content.lower(): sp += 3
        if len(content) > 1000: sp += 2
        dims["specificity"] = {"score": min(sp, 15), "max": 15}
        total += min(sp, 15)
        
        # 6. 路径完整性 (5分)
        pi = 5
        import re
        paths = re.findall(r'[~/][\w/\-._]+', content)
        for p in paths[:5]:
            expanded = os.path.expanduser(p.split(":")[0])
            if not os.path.exists(expanded):
                pi = max(0, pi - 2)
        dims["path_integrity"] = {"score": pi, "max": 5}
        total += pi
        
        # 7. 架构合理性 (15分)
        ar = 0
        if len(steps) > 0: ar += 5
        if "---" in content: ar += 3
        if len(content.split("\n\n")) >= 4: ar += 4
        if len(content) < 8000: ar += 3
        dims["architecture"] = {"score": min(ar, 15), "max": 15}
        total += min(ar, 15)
        
        # 8. 实测 (25分) — 需要实际测试，默认0
        dims["real_world_output"] = {"score": 0, "max": 25}
        
        # 找最弱维度
        weakest = ""
        lowest_rate = 1.0
        for name, data in dims.items():
            rate = data["score"] / data["max"] if data["max"] > 0 else 1
            if rate < lowest_rate:
                lowest_rate = rate
                weakest = name
        
        return AssetScore(
            path=filepath, total=total, dimensions=dims,
            weakest=weakest,
            weakest_score=dims.get(weakest, {}).get("score", 0),
            weakest_max=DARWIN_DIMENSIONS.get(weakest, {}).get("max", 0),
        )


# ============================================
# Layer 2: EvoPrompt 进化引擎 (简化版)
# ============================================

class EvoPromptEngine:
    """
    Prompt进化引擎
    
    核心逻辑:
    1. 读取现有Prompt
    2. 生成N个变体 (变异+交叉)
    3. 评估每个变体 (用规则评分)
    4. 保留最好的
    """
    
    MUTATION_STRATEGIES = [
        ("add_example", "添加具体示例"),
        ("add_constraint", "添加约束条件"),
        ("add_error_handling", "添加错误处理"),
        ("simplify", "简化冗余表述"),
        ("add_format", "明确输出格式"),
        ("add_context", "补充上下文"),
        ("strengthen", "强化关键指令"),
    ]
    
    @staticmethod
    def mutate_prompt(content: str, strategy: str) -> str:
        """对Prompt进行单一变异"""
        
        if strategy == "add_example":
            if "```" not in content and "示例" not in content:
                # 在第一个##标题后插入示例
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if line.startswith("## ") and i > 0:
                        lines.insert(i + 1, "\n### 示例\n```\n输入: ...\n输出: ...\n```\n")
                        break
                return "\n".join(lines)
        
        elif strategy == "add_error_handling":
            if "异常" not in content and "error" not in content.lower():
                return content + "\n\n## 异常处理\n- 输入为空时返回友好提示\n- 处理超时时自动重试\n"
        
        elif strategy == "add_format":
            if "格式" not in content and "format" not in content.lower():
                return content + "\n\n## 输出格式\n请以JSON格式返回结果。\n"
        
        elif strategy == "add_constraint":
            if "⚠️" not in content and "确认" not in content:
                return content.replace("## 工作流程", "⚠️ **确认检查点**: 关键步骤前需用户确认。\n\n## 工作流程")
        
        return content  # 无法变异时返回原内容
    
    @staticmethod
    def evaluate_prompt(content: str) -> int:
        """快速评分 (0-100)"""
        score = DarwinScorer.score_file.__func__(None, content) if hasattr(DarwinScorer.score_file, '__func__') else 0
        return score


# ============================================
# Layer 3: SEW 工作流进化引擎 (简化版)
# ============================================

class SEWEngine:
    """
    工作流结构进化
    
    核心操作:
    1. 节点变异: 增删改工作流步骤
    2. 顺序变异: 重排步骤顺序
    3. 合并变异: 合并相关步骤
    """
    
    @staticmethod
    def analyze_workflow(content: str) -> dict:
        """分析工作流结构"""
        lines = content.split("\n")
        steps = []
        for i, line in enumerate(lines):
            if line.strip().startswith(("## ", "### ", "Step ", "步骤")):
                steps.append({"line": i, "text": line.strip(), "type": "header"})
        
        return {
            "total_steps": len(steps),
            "steps": steps,
            "has_error_handling": any("异常" in l or "error" in l.lower() for l in lines),
            "has_checkpoints": any("⚠️" in l or "确认" in l for l in lines),
            "has_examples": any("```" in l for l in lines),
            "structure_score": min(len(steps) * 3, 30),
        }
    
    @staticmethod
    def suggest_improvements(content: str) -> list:
        """基于结构分析，建议改进方向"""
        analysis = SEWEngine.analyze_workflow(content)
        suggestions = []
        
        if analysis["total_steps"] < 3:
            suggestions.append(("add_steps", "工作流步骤太少，建议拆分为3-5个步骤"))
        
        if not analysis["has_error_handling"]:
            suggestions.append(("add_error", "缺少异常处理，建议添加错误恢复路径"))
        
        if not analysis["has_checkpoints"]:
            suggestions.append(("add_checkpoint", "缺少确认检查点，关键步骤前应暂停"))
        
        if not analysis["has_examples"]:
            suggestions.append(("add_example", "缺少示例，建议添加代码/输入输出示例"))
        
        return suggestions


# ============================================
# Git操作
# ============================================

class GitOps:
    @staticmethod
    def init(project_path: str):
        try:
            subprocess.run(["git", "init"], cwd=project_path, capture_output=True, timeout=5)
            subprocess.run(["git", "add", "-A"], cwd=project_path, capture_output=True, timeout=10)
            subprocess.run(["git", "commit", "-m", "evox: initial commit"], cwd=project_path, capture_output=True, timeout=10)
        except:
            pass
    
    @staticmethod
    def commit(project_path: str, message: str) -> str:
        try:
            subprocess.run(["git", "add", "-A"], cwd=project_path, capture_output=True, timeout=10)
            r = subprocess.run(["git", "commit", "-m", message], cwd=project_path, capture_output=True, text=True, timeout=10)
            h = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project_path, capture_output=True, text=True, timeout=5)
            return h.stdout.strip()[:8]
        except:
            return ""
    
    @staticmethod
    def revert(project_path: str):
        try:
            subprocess.run(["git", "reset", "--hard", "HEAD~1"], cwd=project_path, capture_output=True, timeout=10)
        except:
            pass


# ============================================
# 通用进化引擎
# ============================================

class UniversalEvolver:
    """
    三层进化引擎 — 适配所有项目
    
    用法:
        evolver = UniversalEvolver("~/Desktop/metaforge")
        evolver.scan()           # 扫描资产
        evolver.evolve(rounds=3) # 进化3轮
        evolver.report()         # 输出报告
    """
    
    def __init__(self, project_path: str):
        self.project_path = os.path.expanduser(project_path)
        self.assets = []
        self.scores = []
        self.rounds = []
        self.report = EvolutionReport(project=project_path)
    
    def scan(self) -> list:
        """扫描所有可进化资产"""
        self.assets = scan_assets(self.project_path)
        
        for asset in self.assets:
            full_path = os.path.join(self.project_path, asset["path"])
            score = DarwinScorer.score_file(full_path)
            score.asset_type = asset["type"]
            self.scores.append(score)
        
        self.scores.sort(key=lambda s: s.total)
        return self.scores
    
    def evolve_one(self, asset: AssetScore, round_num: int) -> EvolutionRound:
        """对单个资产执行一轮进化"""
        
        full_path = os.path.join(self.project_path, asset.path)
        
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            original = f.read()
        
        before_score = asset.total
        dim = asset.weakest
        dim_info = DARWIN_DIMENSIONS.get(dim, {})
        
        # 根据最弱维度选择改进策略
        improved_content = original
        
        if dim == "specificity":
            improved_content = EvoPromptEngine.mutate_prompt(original, "add_example")
            improved_content = EvoPromptEngine.mutate_prompt(improved_content, "add_format")
        
        elif dim == "error_handling":
            improved_content = EvoPromptEngine.mutate_prompt(original, "add_error_handling")
        
        elif dim == "checkpoints":
            improved_content = EvoPromptEngine.mutate_prompt(original, "add_constraint")
        
        elif dim == "path_integrity":
            import re
            # 补充实际存在的路径引用
            improved_content = original
        
        elif dim == "workflow_clarity":
            suggestions = SEWEngine.suggest_improvements(original)
            if suggestions:
                improved_content = original + f"\n\n<!-- EvoX改进: {suggestions[0][1]} -->\n"
        
        else:
            # 通用改进: 添加示例
            improved_content = EvoPromptEngine.mutate_prompt(original, "add_example")
        
        # 写入改进
        if improved_content != original:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(improved_content)
            
            # 重新评分
            new_score = DarwinScorer.score_file(full_path)
            
            if new_score.total > before_score:
                # 改进了，commit
                commit = GitOps.commit(self.project_path, f"evox: improve {asset.path} ({dim}: {before_score}→{new_score.total})")
                
                return EvolutionRound(
                    round_num=round_num, target=asset.path, dimension=dim,
                    before=before_score, after=new_score.total, improved=True,
                    description=f"改进「{dim_info.get('name', dim)}」维度: {asset.weakest_score}/{asset.weakest_max}",
                    commit_hash=commit,
                )
            else:
                # 没改进，revert
                GitOps.revert(self.project_path)
                
                return EvolutionRound(
                    round_num=round_num, target=asset.path, dimension=dim,
                    before=before_score, after=new_score.total, improved=False,
                    description=f"改进无效，已回滚",
                    reverted=True,
                )
        
        return EvolutionRound(
            round_num=round_num, target=asset.path, dimension=dim,
            before=before_score, after=before_score, improved=False,
            description="无法生成有效改进",
        )
    
    def evolve(self, rounds: int = 3) -> EvolutionReport:
        """执行多轮进化"""
        
        # 确保有git仓库
        GitOps.init(self.project_path)
        
        if not self.scores:
            self.scan()
        
        avg_before = sum(s.total for s in self.scores) / len(self.scores) if self.scores else 0
        self.report.avg_score_before = avg_before
        
        for r in range(rounds):
            # 每轮对最差的资产进化
            for asset in self.scores[:3]:  # 每轮改进最差的3个
                result = self.evolve_one(asset, r + 1)
                self.rounds.append(result)
                self.report.rounds.append(asdict(result))
        
        # 重新扫描所有资产
        self.scan()
        avg_after = sum(s.total for s in self.scores) / len(self.scores) if self.scores else 0
        self.report.avg_score_after = avg_after
        self.report.total_assets = len(self.assets)
        self.report.successful = sum(1 for r in self.rounds if r.improved)
        self.report.reverted = sum(1 for r in self.rounds if r.reverted)
        self.report.timestamp = datetime.now().isoformat()
        
        # 保存报告
        report_path = os.path.join(self.project_path, ".evox", "evolution_report.json")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self.report), f, ensure_ascii=False, indent=2)
        
        return self.report
    
    def report_text(self) -> str:
        """生成文本报告"""
        lines = [f"🧬 进化报告: {self.project_path}", "=" * 60]
        lines.append(f"资产数: {self.report.total_assets}")
        lines.append(f"平均分: {self.report.avg_score_before:.1f} → {self.report.avg_score_after:.1f} (+{self.report.avg_score_after - self.report.avg_score_before:.1f})")
        lines.append(f"成功轮: {self.report.successful} | 回滚轮: {self.report.reverted}")
        lines.append("")
        
        for r in self.rounds:
            emoji = "✅" if r.improved else ("⏪" if r.reverted else "⏭️")
            lines.append(f"  {emoji} R{r.round_num} {r.target} [{r.dimension}] {r.before}→{r.after} {r.description}")
        
        lines.append("")
        lines.append("当前评分排名:")
        for s in self.scores:
            emoji = "🟢" if s.total >= 70 else "🟡" if s.total >= 50 else "🔴"
            lines.append(f"  {emoji} {s.total:3d} {s.path}")
        
        return "\n".join(lines)


# ============================================
# CLI入口
# ============================================

def main():
    import sys
    
    if len(sys.argv) < 3:
        print("用法: python evox.py <command> <project_path> [rounds]")
        print()
        print("命令:")
        print("  scan   <path>       扫描可进化资产并评分")
        print("  evolve <path> [N]   运行N轮进化 (默认3)")
        print("  report <path>       显示进化报告")
        return
    
    cmd = sys.argv[1]
    path = sys.argv[2]
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    
    evolver = UniversalEvolver(path)
    
    if cmd == "scan":
        scores = evolver.scan()
        print(f"\n🔍 扫描 {path}")
        print(f"找到 {len(scores)} 个可进化资产\n")
        for s in scores:
            emoji = "🟢" if s.total >= 70 else "🟡" if s.total >= 50 else "🔴"
            print(f"  {emoji} {s.total:3d} [{s.asset_type:8}] {s.path}")
            print(f"       最弱: {DARWIN_DIMENSIONS.get(s.weakest,{}).get('name','?')} ({s.weakest_score}/{s.weakest_max})")
    
    elif cmd == "evolve":
        print(f"\n🧬 进化 {path} ({rounds}轮)")
        report = evolver.evolve(rounds)
        print(evolver.report_text())
    
    elif cmd == "report":
        report_path = os.path.join(os.path.expanduser(path), ".evox", "evolution_report.json")
        if os.path.exists(report_path):
            with open(report_path) as f:
                data = json.load(f)
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print("未找到进化报告，请先运行 evolve")


if __name__ == "__main__":
    main()
