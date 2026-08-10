# Zotero Remark

Codex / Claude Code Skill — 批量为 Zotero 文献添加简记

根据文献摘要自动生成一句话总结，并可为筛选后的文献添加摘要翻译、研究话题相关度评级和关键词标签。

默认只添加 `remark:`；当提示词明确要求摘要翻译时，会为英文文献额外生成中文摘要翻译，并紧跟在 remark 后写入 `translate:`。

## 功能

- 从指定文件夹批量提取 Zotero 文献
- 读取每篇文献的摘要（abstractNote）
- 根据摘要内容生成一句话总结
- 写入条目的"简记"（remark 字段）
- 可选：当用户明确要求摘要翻译时，为英文摘要追加中文 `translate` 字段
- 可选：根据用户给出的参考话题，用 `⭐` 至 `⭐⭐⭐⭐⭐` 评价筛选文献的相关度
- 可选：为每篇指定文献提取 2–5 个关键词，并添加独立的 `#关键词` 标签
- 更新评级时只替换旧星级，添加关键词时保留并去重所有原标签
- 支持分批处理（20 或 50 条），避免 API 频率限制

## 适用场景

当你需要对大量 Zotero 文献进行整理、归类、生成阅读笔记时使用。例如：
- "帮我处理 xxx 文件夹中的文献"
- "为这个文件夹的文献添加简记"
- "批量处理 zotero 文献"
- "根据摘要生成一句话总结"
- "帮我处理 xxx 文件夹中的文献，并给英文文章加上摘要翻译"
- "为这个文件夹添加 remark，同时 translate 英文摘要"
- "把筛选好的文献进行评级，参考话题为：企业创新战略如何影响分析师预测"
- "再给这些文献加上标签，每篇提取 2–5 个关键词"

## 前置条件

### 1. 创建环境并安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 2. 配置 Zotero API 凭证

复制示例文件并填写自己的 Zotero 凭证：

```bash
cp .env.example .env
```

```dotenv
ZOTERO_LIBRARY_ID=你的用户或群组ID
ZOTERO_API_KEY=你的API密钥
ZOTERO_LIBRARY_TYPE=user
```

`.env` 已加入 `.gitignore`。不要将 API Key、私人文献数据或包含真实凭证的测试文件提交到仓库。

获取方式：
- **User ID**: Zotero → 编辑 → 偏好设置 → 同步（页面顶部显示）
- **API Key**: https://www.zotero.org/settings/keys/new 创建

### 3. 安装 Skill

本仓库同时提供 Codex 和 Claude Code 目录。将相应的 `zotero-remark` 文件夹复制到目标项目：

```
Codex:       .agents/skills/zotero-remark/
Claude Code: .claude/skills/zotero-remark/
```

两个目录中的技能内容应保持一致。

## 使用方式

在 Codex 或 Claude Code 中直接描述需求，例如：

> "帮我处理『无形资产/readability』文件夹中的文献，每次处理 30 条"

代理会自动：
1. 连接到你的 Zotero 账户
2. 定位目标文件夹
3. 逐条读取文献摘要
4. 判断用户是否明确要求摘要翻译
5. 生成一句话总结
6. 写入 remark 字段；如用户要求翻译，则对英文文献追加 translate 字段
7. 如用户给出参考话题并要求评级，只对指定或已筛选文献添加 1–5 星标签
8. 如用户要求关键词标签，为同一批文献各添加 2–5 个 `#关键词` 标签

## Remark 格式

Remark 存储在 Zotero 条目的 extra 字段中，格式为：

```
remark: 这里是一句话总结的内容
```

如果用户明确要求摘要翻译，英文文献会写成：

```
remark: 这里是一句话总结的内容
translate: 这里是英文摘要的中文翻译
```

未明确要求摘要翻译时，默认不会添加 `translate:`。

## 处理记录

| 文件夹 | 文献数 | 状态 |
|--------|--------|------|
| readability（L4XWH5DI） | 20 篇 | ✓ 已完成 |
| 相生相克-关系（8PLDEHRT） | 62 篇 | ✓ 已完成 |

## 已知问题

- Zotero API 每页返回 100 条，`zot.collections()` 和 `zot.collection_items()` 默认只返回第一页，需要循环分页获取全部数据
- 部分文献可能没有摘要（abstractNote），这些文献会跳过处理

## 技术细节

- **Python**: Python 3，推荐使用项目内的 `.venv`
- **API**: Zotero Web API v3
- **Remark 位置**: `item['data']['extra']`
- **中英文处理**: 无论原文是中文还是英文，remark 均用中文生成
- **可选摘要翻译**: 仅当用户明确要求时，对英文摘要生成中文翻译并以 `translate:` 写入 remark 后一行
- **相关度评级**: 星级作为 Zotero `tags` 中的独立标签；每篇仅保留一个星级
- **关键词标签**: 每个关键词以独立 `#关键词` 写入 Zotero `tags`，保留其他原标签

## 贡献与安全

- 欢迎通过 Issue 或 Pull Request 提交问题、改进和兼容性修复，具体流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。
- 若发现可能泄露凭证、越权修改 Zotero 数据或其他安全问题，请不要公开披露，按 [SECURITY.md](SECURITY.md) 私下报告。

## License

本项目采用 [MIT License](LICENSE)。
