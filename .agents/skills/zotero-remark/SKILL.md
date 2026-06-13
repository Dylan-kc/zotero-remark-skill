---
name: zotero-remark
description: 从 Zotero 指定文件夹读取和筛选文献，根据摘要生成中文 remark，并可按用户明确要求添加英文摘要的中文 translate、依据指定研究话题用 1–5 个星号标签评价相关度、提取 2–5 个关键词并添加“#关键词”标签。用户提到“zotero 简记”“添加简记”“摘要翻译”“筛选文献”“给筛选好的文献评级，参考话题为……”“按研究方向相似度评级”“再加上标签”“提取关键词标签”或批量处理 Zotero 文献时使用。
---

# Zotero Remark - 批量生成文献简记

本技能从 Zotero 文献库的指定文件夹中批量提取文献，读取摘要并按请求执行文献筛选、中文简记、摘要翻译、相关度评级和关键词标签写入。

默认只写入 `remark: 内容`。只有当用户明确要求添加摘要翻译时，才对英文文献额外生成中文摘要翻译，并在 `remark:` 后另起一行写入 `translate: 内容`。

评级与关键词标签也是按需功能。用户未明确要求时，不添加星级或关键词标签。

## 前置条件

### 1. 环境要求

- 项目内 Python 环境已安装依赖：`.venv/bin/python -m pip install -r requirements.txt`
- Zotero API 凭证（存储在项目 `.env` 文件或环境变量中）：
  - `ZOTERO_LIBRARY_ID` — 用户 ID（数字）
  - `ZOTERO_API_KEY` — API Key
  - `ZOTERO_LIBRARY_TYPE` — `user` 或 `group`

### 2. Zotero Extra 字段中的 Remark 格式

Remark 存储在条目的 `extra` 字段中，默认格式为：
```
remark: 这里是一句话总结的内容
```

当用户明确要求摘要翻译，且文献摘要为英文时，格式为：
```
remark: 这里是一句话总结的内容
translate: 这里是英文摘要的中文翻译
```

## 工作流程

### Step 1: 连接 Zotero 并定位文件夹

```python
from pyzotero import Zotero
import os
from dotenv import load_dotenv

load_dotenv()  # 加载 .env 文件

zot = Zotero(
    library_id=os.getenv('ZOTERO_LIBRARY_ID'),
    library_type=os.getenv('ZOTERO_LIBRARY_TYPE', 'user'),
    api_key=os.getenv('ZOTERO_API_KEY')
)

# 获取所有收藏夹（处理分页，API 每页返回 100 条）
def get_all_collections(zot):
    """Zotero API 默认每页 100 条，需要手动分页获取全部"""
    all_collections = []
    offset = 0
    while True:
        cols = zot.collections(start=offset)
        if not cols:
            break
        all_collections.extend(cols)
        if len(cols) < 100:
            break
        offset += 100
    return all_collections

# 遍历所有收藏夹，找到名称匹配的那个
# 用户提供的路径如 "Readability/文本分析/中 经济C"，取最后一个文件夹名作为目标名称
# 文件夹名可能包含空格（如"中 经济C"），必须精确匹配
def find_collection(zot, folder_path):
    """根据路径找到收藏夹，路径中的最后一个文件夹名作为目标名称"""
    # 取路径中最后一个文件夹名
    parts = folder_path.split('/')
    target_name = parts[-1].strip()

    collections = get_all_collections(zot)
    # 精确匹配（大小写敏感，包含空格的名称）
    for col in collections:
        if col['data']['name'] == target_name:
            return col
    # 大小写不敏感的精确匹配
    for col in collections:
        if col['data']['name'].lower() == target_name.lower():
            return col
    return None
```

### Step 2: 获取文件夹中的文献（过滤附件，处理分页）

```python
def get_papers_from_collection(zot, collection_key, batch_size=50):
    """获取收藏夹中所有实际论文（排除附件），每次返回一批

    注意：collection_items 也分页，每页 100 条，需要循环获取全部
    """
    all_items = []
    offset = 0
    while True:
        items = zot.collection_items(collection_key, start=offset, limit=100)
        if not items:
            break
        all_items.extend(items)
        if len(items) < 100:
            break
        offset += 100

    papers = []
    for item in all_items:
        item_type = item['data'].get('itemType', '')
        title = item['data'].get('title', '')

        # 跳过附件类型的条目（attachment, note, annotation等）
        if item_type in ('attachment', 'note', 'annotation'):
            continue
        # 跳过 PDF/全文附件（标题中含 PDF、Full Text、SAGE、ScienceDirect、Snapshot 等）
        skip_titles = ['Full Text PDF', 'PDF', 'SAGE', 'ScienceDirect', 'Snapshot']
        if any(t in title for t in skip_titles):
            continue
        # 跳过无标题的条目
        if not title:
            continue
        # 只保留主要文献类型。Zotero 的 preprint 与 workingPaper 是两个独立类型，必须同时纳入。
        valid_types = (
            'journalArticle', 'book', 'bookSection', 'conferencePaper',
            'report', 'thesis', 'workingPaper', 'preprint'
        )
        if item_type not in valid_types:
            continue

        papers.append({'key': item['key'], 'title': title})

    # 分批返回
    for i in range(0, len(papers), batch_size):
        yield papers[i:i + batch_size]
```

### Step 3: 检查是否已有 Remark

```python
def get_remark(item_key, zot):
    """获取单篇文献的 remark"""
    full_item = zot.item(item_key)
    extra = full_item['data'].get('extra', '')
    for line in extra.split('\n'):
        if line.strip().startswith('remark:'):
            return line.replace('remark:', '').strip()
    return ''

def has_remark(item_key, zot):
    """检查文献是否已有 remark"""
    return bool(get_remark(item_key, zot))

def get_translate(item_key, zot):
    """获取单篇文献的 translate（英文摘要中文翻译）"""
    full_item = zot.item(item_key)
    extra = full_item['data'].get('extra', '')
    for line in extra.split('\n'):
        if line.strip().startswith('translate:'):
            return line.replace('translate:', '').strip()
    return ''

def has_translate(item_key, zot):
    """检查文献是否已有 translate"""
    return bool(get_translate(item_key, zot))
```

### Step 4: 判断是否需要摘要翻译

只有用户的提示词明确要求摘要翻译时，才启用摘要翻译功能。可识别的表达包括但不限于：

- "加上摘要翻译"
- "翻译摘要"
- "英文摘要翻译成中文"
- "translate"
- "translation"
- "把摘要中文翻译加到 remark 后面"

如果用户没有明确提出以上需求，默认只生成并写入 `remark:`。

```python
def should_add_translation(user_prompt):
    """根据用户提示词判断是否需要给英文文献追加摘要中文翻译"""
    prompt = user_prompt.lower()
    keywords = [
        '摘要翻译',
        '翻译摘要',
        '摘要中文',
        '中文摘要',
        '英文摘要翻译',
        'translate',
        'translation',
    ]
    return any(keyword in prompt for keyword in keywords)
```

### Step 5: 生成一句话总结

根据摘要内容，用简洁准确的语言概括研究的核心发现或方法。

**规则：**
- 一句话只描述一个核心观点
- 优先描述研究结论，其次是研究方法
- **无论中英文文献，一律用中文生成一句话总结**
- 长度控制在 50-150 字
- 不要添加"本文发现"、"本文研究"等废话，直接陈述结论
- 包含关键数据或方法术语（如"DID"、"双重差分"、"NLP"等）
- 英文摘要需准确翻译核心发现，不可遗漏关键信息

**示例：**

| 文献标题 | 生成的一句话总结 |
|---------|---------------|
| 实质性创新还是策略性创新?——宏观产业政策对微观企业创新的影响 | 受产业政策激励的公司追求"数量"而忽略"质量"，专利申请增加但仅非发明专利显著 |
| 文本可读性与IPO审核问询的信息效果检验 | 问询回复函可读性通过影响投资者情绪显著降低IPO抑价率 |
| CEO decision horizon and corporate R&D investments | CEO决策视野越短越倾向于减少研发投入，风险厌恶加剧短视行为对创新的负面效应 |

**注意**：第三行是英文论文，但 remark 仍用中文总结。

### Step 6: 可选生成英文摘要的中文翻译

仅当 `should_add_translation(user_prompt)` 返回 `True`，并且该文献摘要为英文时，才生成摘要中文翻译。

**规则：**
- 只翻译英文摘要；中文摘要不需要生成 `translate`
- 翻译应完整覆盖原摘要的研究问题、方法、核心发现和机制，不要只概括
- 保留必要术语和缩写（如 CEO、CFO、IPO、DID、CAPM、SEO、NLP、13F 等）
- 译文使用中文自然表达，不要添加"以下是翻译"等说明性废话
- 写入时字段名固定为 `translate:`，不要使用"摘要翻译:"、"translation:"或其他开头
- `translate:` 必须紧跟在该条目的 `remark:` 下一行

```python
def is_english_abstract(abstract):
    """粗略判断摘要是否为英文：英文字符占比较高且中文字符很少"""
    if not abstract:
        return False
    chinese_chars = sum('\u4e00' <= ch <= '\u9fff' for ch in abstract)
    latin_chars = sum(('a' <= ch.lower() <= 'z') for ch in abstract)
    return latin_chars > 50 and chinese_chars < 10
```

### Step 7: 按研究话题进行 1–5 星评级

仅当用户明确提出“给筛选好的文献评级”“按研究方向相似度评级”等要求时执行。

1. 从用户提示中提取完整的参考话题，例如“参考话题为：企业创新战略如何影响分析师预测”。
2. 只评价用户指定或前序步骤已经筛选出的文献，不要扩大到收藏夹中的其他条目。
3. 综合题名、摘要、已有 remark 和 translate 判断相关性，不要只按关键词命中评级。
4. 使用以下统一标准，不要求各星级数量均衡：
   - `⭐⭐⭐⭐⭐`：直接研究参考话题的核心自变量、因变量或两者关系，可直接支撑研究设计或核心假设。
   - `⭐⭐⭐⭐`：研究关键机制、测量方法、识别策略或紧密相邻的理论关系，对核心话题有重要支撑。
   - `⭐⭐⭐`：研究同一理论领域或重要背景变量，可提供机制、边界条件或辅助证据，但不直接回答核心问题。
   - `⭐⭐`：仅部分概念、情境或方法相关，能提供有限背景材料。
   - `⭐`：联系较弱，仅有宽泛主题重合；如果用户此前要求筛选，通常不应把明显不相关文献纳入评级集合。
5. 将星级写入 Zotero 的 `tags` 字段，单独作为一个标签，例如 `{"tag": "⭐⭐⭐⭐"}`。
6. 每篇文献只保留一个星级标签。更新评级时删除旧的 `⭐` 至 `⭐⭐⭐⭐⭐` 标签，再添加新评级；保留所有非星级原标签。
7. 若用户没有提供参考话题，且当前上下文也没有明确唯一的话题，先询问参考话题，不要自行猜测。

### Step 8: 添加关键词标签

仅当用户明确提出“加上标签”“提取关键词标签”等要求时执行。

- 为每篇指定文献提取 2–5 个最能代表研究对象、核心变量、理论机制或方法的关键词。
- 默认使用简洁中文关键词；必要的通用缩写可保留，如 `#DID`、`#NLP`。
- 每个关键词作为独立 Zotero 标签，固定使用 `#关键词` 格式，例如 `#专利战略`，不要把多个关键词合并为一个标签。
- 优先使用具有区分度的学术概念，避免 `#研究`、`#企业`、`#实证分析` 等过宽标签。
- 保留条目所有原有标签；只追加尚不存在的关键词标签，不重复添加。
- “再加上标签”默认沿用当前对话中刚刚筛选或评级的同一批文献，不处理未入选文献。

评级和关键词标签写入优先使用技能脚本：

```bash
.venv/bin/python .codex/skills/zotero-remark/scripts/update_ratings_tags.py \
  --input ratings_tags.json \
  --dry-run
```

输入 JSON 格式：

```json
{
  "reference_topic": "用户给出的研究话题",
  "records": [
    {
      "key": "ZOTERO_ITEM_KEY",
      "rating": 5,
      "keyword_tags": ["#专利战略", "#技术竞争", "#专利围栏"]
    }
  ]
}
```

只评级时可省略 `keyword_tags`，只加关键词时可省略 `rating`。正式写入前必须先运行 `--dry-run`；写入后再次运行 `--dry-run`，结果应全部为 `[same]`。

### Step 9: 写入 Remark 和可选 Translate 到 Extra 字段

```python
def add_remark(item_key, zot, remark, translate=None):
    """将 remark 写入条目的 extra 字段；如提供 translate，则紧跟 remark 下一行写入"""
    item = zot.item(item_key)
    extra = item['data'].get('extra', '')

    # 如果已有 remark，跳过
    if any('remark:' in line for line in extra.split('\n')):
        return False

    # 追加 remark；如果用户明确要求摘要翻译且英文摘要已翻译，则追加 translate
    block = f"remark: {remark}"
    if translate:
        block += f"\ntranslate: {translate}"
    new_extra = (extra + f"\n{block}").strip()
    item['data']['extra'] = new_extra
    zot.update_item(item)
    return True
```

### Step 10: 批量处理主流程

```python
def process_folder(folder_path, batch_size=50, limit=None, user_prompt=''):
    """主流程：处理整个文件夹，folder_path支持路径格式如'自由阅读/补充学习'

    Args:
        batch_size: 每批处理数量，默认 50。不足 50 条则一次性处理完所有文献。
        user_prompt: 用户原始提示词，用于判断是否明确要求摘要翻译。
    """
    zot = get_zotero_client()
    add_translation = should_add_translation(user_prompt)
    col = find_collection(zot, folder_path)
    if not col:
        print(f"未找到文件夹: {folder_path}")
        return

    col_key = col['key']
    print(f"找到文件夹: {col['data']['name']} (key: {col_key})")

    # 分批处理
    batch_num = 0
    total_processed = 0
    total_added = 0
    total_skipped = 0

    for batch in get_papers_from_collection(zot, col_key, batch_size):
        batch_num += 1
        print(f"\n=== 第 {batch_num} 批 (共 {len(batch)} 篇) ===")

        for paper in batch:
            if limit and total_processed >= limit:
                break

            item_key = paper['key']
            title = paper['title']

            # 检查是否有 remark
            remark = get_remark(item_key, zot)
            if remark:
                print(f"[跳过-已有] {title[:40]}...")
                total_skipped += 1
            else:
                # 获取摘要
                full_item = zot.item(item_key)
                abstract = full_item['data'].get('abstractNote', '')

                if not abstract:
                    print(f"[跳过-无摘要] {title[:40]}...")
                    total_skipped += 1
                else:
                    # 生成总结（人工根据摘要生成）
                    summary = generate_summary_from_abstract(abstract, title)
                    if summary:
                        translation = None
                        if add_translation and is_english_abstract(abstract):
                            translation = translate_english_abstract_to_chinese(abstract, title)
                        add_remark(item_key, zot, summary, translation)
                        print(f"[添加] {title[:40]}...")
                        print(f"       remark: {summary[:50]}...")
                        if translation:
                            print(f"       translate: {translation[:50]}...")
                        total_added += 1
                    else:
                        print(f"[跳过-生成失败] {title[:40]}...")

            total_processed += 1

        if limit and total_processed >= limit:
            break

    print(f"\n完成！处理 {total_processed} 篇，新增 {total_added} 条 remark，跳过 {total_skipped} 篇")
```

## 交互方式

用户告诉你要处理的文件夹路径后，按照以下步骤操作：

1. **路径解析**：用户说"Readability/文本分析/中 经济C"时，取最后一个文件夹名"中 经济C"作为目标名称（注意空格，精确匹配）
2. **确认文件夹**：查询 Zotero 中所有收藏夹，找到目标文件夹，显示名称和包含的文献数量
3. **过滤条目**：只处理主要文献条目（journalArticle、book、conferencePaper等），跳过attachment、note、annotation、PDF等
4. **分批处理**：固定每批处理 50 条（不足 50 条则一次性处理），处理前先显示该批次的文献列表
5. **识别翻译需求**：只有用户明确要求摘要翻译时，才为英文文献生成 `translate:`；否则默认只生成 `remark:`
6. **识别评级需求**：用户提供参考话题并要求评级时，只对指定或已筛选文献按统一标准添加 1–5 星标签
7. **识别标签需求**：用户要求加标签时，为同一批文献各提取 2–5 个 `#关键词` 标签
8. **写入前检查**：展示标题、拟写入内容及标签，先 dry-run，确认不覆盖 remark、translate 和非目标标签
9. **处理完成**：回读验证并汇总新增、更新、已有、无摘要和未入选数量

## 重要提示

- **Remark 字段位置**：在 Zotero API 中，remark 存储在 `item['data']['extra']` 中，读取时用 `full_item['data'].get('extra', '')`，写入时设置 `item['data']['extra']`
- **Remark 格式**：`remark: 内容`，remark 前没有缩进，是 extra 中的一个独立行
- **Translate 格式**：只有用户明确要求摘要翻译时才添加，格式必须是 `translate: 内容`，紧跟在 `remark:` 下一行；不要使用"摘要翻译:"作为字段名
- **默认行为**：如果用户只要求"添加简记"、"生成 remark"、"总结文献"等，但没有明确要求翻译摘要，则只写入 `remark:`，不写入 `translate:`
- **英文文献翻译**：启用翻译时，只对英文摘要生成中文 `translate:`；中文摘要不需要重复翻译
- **检查已有 remark**：写入前必须检查是否已存在 remark，避免重复写入
- **检查已有 translate**：追加摘要翻译前必须检查是否已存在 `translate:`，避免重复写入
- **评级存储位置**：星级存储在 `item['data']['tags']`，值必须是连续 1–5 个 `⭐`；同一条目只能有一个星级标签
- **关键词存储位置**：关键词同样存储在 `item['data']['tags']`，每个标签使用独立的 `#关键词` 字符串
- **保留原标签**：评级只替换旧星级，关键词只追加并去重，任何其他原有标签都不得删除或改写
- **限定处理集合**：“筛选好的文献”“再加上标签”指当前对话中已筛选的条目 key，不得顺带处理收藏夹其他文献
- **评级依据**：相关度必须相对于用户给出的参考话题，而不是相对于收藏夹名称或宽泛学科；无需强制形成正态分布或覆盖全部星级
- **Python 路径**：使用项目内 `.venv/bin/python` 运行 pyzotero（系统 Python 可能没有安装该库）
- **API 分页问题**：Zotero API 每页返回 100 条，**`zot.collections()` 和 `zot.collection_items()` 都会截断**，必须使用循环获取全部数据！
- **确认目标文件夹**：处理前先显示文件夹名称、key、文献数量，避免处理错误文件夹
- **中英文统一处理**：所有文献都用中文生成 remark，不论原文是中文还是英文
- **无摘要处理**：如果文献没有摘要（abstractNote 为空），跳过并记录，但这种情况很少
- **路径解析**：用户指定文件夹时，如果包含路径如"Readability/文本分析/中 经济C"，只取最后一个文件夹名"中 经济C"作为匹配目标。文件夹名可能包含空格，必须精确匹配（大小写敏感）。
- **条目过滤**：只处理主要文献类型（journalArticle、book、conferencePaper、workingPaper、preprint 等），跳过 attachment、note、annotation、PDF 附件等。注意 Zotero 的 `preprint` 与 `workingPaper` 是两个独立的 `itemType`，预印本不能仅靠 `workingPaper` 覆盖。
