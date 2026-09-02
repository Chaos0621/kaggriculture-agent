# Kaggriculture 起步指南

## 1. 先理解题目

这不是常见的 `train.csv -> 模型 -> submission.csv` 题，而是双人策略代理竞赛：

- 每局默认 30 天，每天 24 回合，共 720 回合。
- 每回合 `agent(obs)` 读取公开农场、私有仓库、市场和城镇状态，返回农夫、雇工和市场动作。
- 最终银行余额更高者获胜；本地验证因此应使用多随机种子的胜率、平均收益和最差表现，而不是单局结果。
- 提交入口必须是压缩包根目录下的 `main.py`，其中暴露 `agent(obs)`。

## 2. 当前框架

```text
.
├── main.py                       # 可直接提交的、自包含的保守基线
├── analyze_economy.py            # README 参数收益与市场锚点分析
├── run_local.py                  # 多局本地对战
├── scripts/package_submission.py # 生成 submission.tar.gz
├── tests/test_agent.py           # 不依赖模拟器的快速单元测试
├── requirements.txt
└── START_HERE_CN.md
```

当前策略只经营一个靠近仓库的地块，但已把 README 中的五种作物成本、产量、成熟期和九种商品市场曲线结构化。它会按当前价格与剩余天数选择预计日收益最高的可成熟作物，然后自动买种子、播种、每日浇水、收割、入库并出售。这个策略分数不会高，但流程完整，适合先验证环境、数据计算和提交链路。

## 3. 安装与运行

建议使用 Python 3.12 和独立虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python analyze_economy.py --day 0
python run_local.py --episodes 10 --opponent starter --replay replays/latest.json
python scripts/package_submission.py
```

提交前先在 Kaggle 网页点击 **Join Competition** 并接受规则。配置 Kaggle CLI 后：

```powershell
kaggle competitions submit kaggriculture -f submission.tar.gz -m "safe wheat baseline v1"
kaggle competitions submissions kaggriculture
```

也可以直接提交单文件：

```powershell
kaggle competitions submit kaggriculture -f main.py -m "safe wheat baseline v1"
```

## 4. 接下来怎么做

按下面顺序迭代，每次只改一个主要因素，并至少跑 30～100 个随机种子。

### 阶段 A：建立可靠评测

1. 记录每局最终余额、胜负、状态和运行异常。
2. 两个座位都测：候选策略既当 player 0，也当 player 1。
3. 固定一组随机种子，避免新版本因“运气好”而看似提升。
4. 保存失败局 replay，优先修复非法动作、漏浇水、仓库溢出和终局未清仓。

### 阶段 B：从单地块扩成生产调度器

1. 写 BFS/曼哈顿路径规划，管理多个地块和多名雇工。
2. 每回合给任务排序：保命浇水/喂食 > 即将衰减的收割 > 入库 > 播种 > 普通移动。
3. 先扩到 4～8 块小麦或胡萝卜，确认不会漏照料，再扩大农场。
4. 加入剩余天数约束：来不及成熟的作物不再播种。

### 阶段 C：经济与市场

1. 以“预计净利润 / 占地天数 / 所需动作数”比较作物与动物。
2. 根据已解锁商店、市场库存和价格选择品种。
3. 高价产品避免一次性倾销造成价格崩塌；测试分批出售和延迟出售。
4. 最后几回合强制清仓，不再买种子、动物或土地。

### 阶段 D：对手感知与搜索

1. 从对手公开农场估计未来产量和可能抛售量。
2. 做规则策略参数搜索：地块数、雇工数、收割日、出售阈值、土地购买时机。
3. 建立策略池做循环赛，防止只对 `starter` 过拟合。
4. 稳定后再考虑 rollout、MCTS 或轻量策略学习；本题先把模拟器、调度与经济启发式做好，通常比直接上深度强化学习更划算。

## 5. 每次提交前检查

- `python -m unittest discover -s tests -v` 全部通过。
- 至少 30 局本地对战无 `ERROR` / `INVALID` 状态。
- 动作计算时间稳定，任何异常都会返回合法 `PASS`。
- 压缩包根目录直接包含 `main.py`，不多套一层文件夹。
- 代码不依赖网络、私有路径、凭据或未打包的本地模块。
- 修改版本号/提交说明，并保存本地评测结果。
