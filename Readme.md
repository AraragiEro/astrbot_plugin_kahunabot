
# 项目处于开发起步阶段，暂不接受pr

# 依赖
Playwright依赖：
1. 安装Playwright
```bash
pip install playwright
```

2. 安装浏览器依赖
```bash
python -m playwright install
```

3. 如果在Linux环境下，可能需要安装额外的系统依赖
```bash
python -m playwright install-deps
```


# 常用匹配器与黑名单分类
## 建筑
### markget_group

- Reaction Materials - 所有反应
  - Advanced Moon Materials_ - 高反 T2 旗舰
  - Processed Moon Materials - 低反 T2 旗舰
  - Molecular-Forged Materials - 分子熔铸 旗舰
  - Polymer Materials - 聚合物 T3， 旗舰
  - Booster Materials - 增效剂
- Components 组件
  - Advanced Components 高级组件 T2 旗舰 势力
  - Standard Capital Ship Components 标准旗舰组件旗舰
  - Advanced Capital Components 高级旗舰组件 T2旗舰
- R.A.M.

### meta

- Tech II
- Tech I
- Faction

### group

- Fuel Blocks 燃料块