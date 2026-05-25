# Zotero Remark

Claude Code Skill — 批量为 Zotero 文献添加简记

根据文献摘要自动生成一句话总结，写入 Zotero 条目的 extra 字段中的 remark。

默认只添加 `remark:`；当提示词明确要求摘要翻译时，会为英文文献额外生成中文摘要翻译，并紧跟在 remark 后写入 `translate:`。

## 功能

- 从指定文件夹批量提取 Zotero 文献
- 读取每篇文献的摘要（abstractNote）
- 根据摘要内容生成一句话总结
- 写入条目的"简记"（remark 字段）
- 可选：当用户明确要求摘要翻译时，为英文摘要追加中文 `translate` 字段
- 支持分批处理（20 或 50 条），避免 API 频率限制

## 适用场景

当你需要对大量 Zotero 文献进行整理、归类、生成阅读笔记时使用。例如：
- "帮我处理 xxx 文件夹中的文献"
- "为这个文件夹的文献添加简记"
- "批量处理 zotero 文献"
- "根据摘要生成一句话总结"
- "帮我处理 xxx 文件夹中的文献，并给英文文章加上摘要翻译"
- "为这个文件夹添加 remark，同时 translate 英文摘要"

## 前置条件

### 1. 安装 pyzotero

```bash
/opt/anaconda3/bin/python -m pip install pyzotero
```

### 2. 配置 Zotero API 凭证

在项目根目录创建 `.env` 文件：

```
ZOTERO_LIBRARY_ID=你的用户ID
ZOTERO_API_KEY=你的API密钥
ZOTERO_LIBRARY_TYPE=user  # 或 group
```

获取方式：
- **User ID**: Zotero → 编辑 → 偏好设置 → 同步（页面顶部显示）
- **API Key**: https://www.zotero.org/settings/keys/new 创建

### 3. 安装 Skill

将 `zotero-remark` 文件夹放到项目的 `.claude/skills/` 目录下：

```
项目/
├── .claude/
│   └── skills/
│       └── zotero-remark/
│           └── SKILL.md
└── .env
```

## 使用方式

在 Claude Code 中直接描述需求，例如：

> "帮我处理『无形资产/readability』文件夹中的文献，每次处理 30 条"

Claude 会自动：
1. 连接到你的 Zotero 账户
2. 定位目标文件夹
3. 逐条读取文献摘要
4. 判断用户是否明确要求摘要翻译
5. 生成一句话总结
6. 写入 remark 字段；如用户要求翻译，则对英文文献追加 translate 字段

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

- **Python 路径**: `/opt/anaconda3/bin/python`
- **API**: Zotero Web API v3
- **Remark 位置**: `item['data']['extra']`
- **中英文处理**: 无论原文是中文还是英文，remark 均用中文生成
- **可选摘要翻译**: 仅当用户明确要求时，对英文摘要生成中文翻译并以 `translate:` 写入 remark 后一行

## License

MIT
