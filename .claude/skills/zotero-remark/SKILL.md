---
name: zotero-remark
description: 从 Zotero 文献库的指定文件夹中提取文献，根据摘要自动生成一句话总结，写入条目的简记（extra 字段中的 remark）。当且仅当用户在提示词中明确要求"摘要翻译"、"翻译摘要"、"translate"、"translation"或类似需求时，对英文文献额外生成中文摘要翻译，并在 remark 后另起一行写入 translate。用户未明确要求翻译时，默认只添加 remark。当用户提到"zotero 简记"、"添加简记"、"根据摘要生成简记"、"为 zotero 文献添加一句话总结"、"批量处理 zotero 文献"或需要从 Zotero 文件夹批量读取并处理文献时触发本技能。
allowed-tools: Read Write Edit Bash
license: MIT License
metadata:
    skill-author: Claude
    compatibility: pyzotero >= 1.0, python >= 3.8
---

# Zotero Remark - 批量生成文献简记

本技能从 Zotero 文献库的指定文件夹中批量提取文献，读取每篇文献的摘要（abstractNote），生成一句话总结，写入条目的 **简记（remark）** 字段（存储在 extra 字段中，格式为 `remark: 内容`）。

默认只写入 `remark: 内容`。只有当用户明确要求添加摘要翻译时，才对英文文献额外生成中文摘要翻译，并在 `remark:` 后另起一行写入 `translate: 内容`。

## 前置条件

### 1. 环境要求

- Python 已安装 pyzotero：`/opt/anaconda3/bin/python -m pip install pyzotero`
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
        # 只保留主要文献类型（journalArticle, book, bookSection, conferencePaper, report, thesis等）
        valid_types = ('journalArticle', 'book', 'bookSection', 'conferencePaper', 'report', 'thesis', 'workingPaper')
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

### Step 7: 写入 Remark 和可选 Translate 到 Extra 字段

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

### Step 8: 批量处理主流程

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
6. **逐条确认**：每条文献显示标题、摘要和生成的 remark；如启用翻译，也显示 translate，用户确认后写入
7. **处理完成**：汇总报告，显示成功添加的条数、跳过的条数（含已有 remark、已有 translate 和无摘要的）

## 重要提示

- **Remark 字段位置**：在 Zotero API 中，remark 存储在 `item['data']['extra']` 中，读取时用 `full_item['data'].get('extra', '')`，写入时设置 `item['data']['extra']`
- **Remark 格式**：`remark: 内容`，remark 前没有缩进，是 extra 中的一个独立行
- **Translate 格式**：只有用户明确要求摘要翻译时才添加，格式必须是 `translate: 内容`，紧跟在 `remark:` 下一行；不要使用"摘要翻译:"作为字段名
- **默认行为**：如果用户只要求"添加简记"、"生成 remark"、"总结文献"等，但没有明确要求翻译摘要，则只写入 `remark:`，不写入 `translate:`
- **英文文献翻译**：启用翻译时，只对英文摘要生成中文 `translate:`；中文摘要不需要重复翻译
- **检查已有 remark**：写入前必须检查是否已存在 remark，避免重复写入
- **检查已有 translate**：追加摘要翻译前必须检查是否已存在 `translate:`，避免重复写入
- **Python 路径**：使用 `/opt/anaconda3/bin/python` 运行 pyzotero（系统 Python 可能没有安装该库）
- **API 分页问题**：Zotero API 每页返回 100 条，**`zot.collections()` 和 `zot.collection_items()` 都会截断**，必须使用循环获取全部数据！
- **确认目标文件夹**：处理前先显示文件夹名称、key、文献数量，避免处理错误文件夹
- **中英文统一处理**：所有文献都用中文生成 remark，不论原文是中文还是英文
- **无摘要处理**：如果文献没有摘要（abstractNote 为空），跳过并记录，但这种情况很少
- **路径解析**：用户指定文件夹时，如果包含路径如"Readability/文本分析/中 经济C"，只取最后一个文件夹名"中 经济C"作为匹配目标。文件夹名可能包含空格，必须精确匹配（大小写敏感）。
- **条目过滤**：只处理主要文献类型（journalArticle、book、conferencePaper等），跳过 attachment、note、annotation、PDF 附件等
