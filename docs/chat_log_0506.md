# Zotero Remark Skill 开发日志

**日期**: 2026-05-06
**项目**: zotero-remark
**功能**: 从 Zotero 文件夹批量提取文献，根据摘要生成一句话总结，写入条目的 extra 字段中的 remark

---

## 一、对话背景与目标

用户希望创建一个 Claude Code Skill，能够：
1. 从 Zotero 文献库中指定文件夹提取文献
2. 读取每篇文献的 abstractNote（摘要）
3. 根据摘要用中文生成一句话总结
4. 将总结写入条目的 "简记"（remark）字段
5. 支持分批处理（20 或 50 条），因为后续处理文献数量可能很大

---

## 二、核心实现逻辑

### 2.1 Zotero API 连接

```python
from pyzotero import Zotero
import os
from dotenv import load_dotenv

load_dotenv()

zot = Zotero(
    library_id=os.getenv('ZOTERO_LIBRARY_ID'),
    library_type='user',
    api_key=os.getenv('ZOTERO_API_KEY')
)
```

### 2.2 定位目标文件夹

Zotero 收藏夹有层级结构，需要：
1. 获取用户所有收藏夹（**注意分页**）
2. 按名称精确匹配或模糊匹配目标文件夹
3. 显示文件夹路径和文献数量

### 2.3 获取文件夹中的文献

```python
def get_papers_from_collection(zot, collection_key, batch_size=20):
    # 关键：collection_items 也分页，每页100条
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

    # 过滤：跳过 attachment 类型、跳过 PDF 附件、跳过无标题条目
    papers = []
    for item in all_items:
        item_type = item['data'].get('itemType', '')
        title = item['data'].get('title', '')
        if item_type == 'attachment':
            continue
        skip_titles = ['Full Text PDF', 'PDF', 'SAGE', 'ScienceDirect', 'Snapshot']
        if any(t in title for t in skip_titles):
            continue
        if not title:
            continue
        papers.append({'key': item['key'], 'title': title})
    return papers
```

### 2.4 Remark 的读写

**存储位置**: `item['data']['extra']`
**格式**: `remark: 这里是一句话总结的内容`

```python
# 读取
def get_remark(item_key, zot):
    full_item = zot.item(item_key)
    extra = full_item['data'].get('extra', '')
    for line in extra.split('\n'):
        if line.strip().startswith('remark:'):
            return line.replace('remark:', '').strip()
    return ''

# 写入
def add_remark(item_key, zot, remark):
    item = zot.item(item_key)
    extra = item['data'].get('extra', '')
    if any('remark:' in line for line in extra.split('\n')):
        return False  # 已有 remark，跳过
    new_extra = (extra + f"\nremark: {remark}").strip()
    item['data']['extra'] = new_extra
    zot.update_item(item)
    return True
```

### 2.5 一句话总结生成规则

- 一句话只描述一个核心观点
- 优先描述研究结论，其次是研究方法
- **无论中英文，一律用中文总结**
- 长度 50-150 字
- 直接陈述结论，不添加"本文发现"等废话
- 包含关键方法术语（如 DID、双重差分、NLP 等）

---

## 三、发现的 Bug 及修复

### Bug 1: collections() 分页问题

**问题**: Zotero API 每页返回 100 条收藏夹，`zot.collections()` 默认只返回第一页

**发现经过**: 用户说"相生相克"文件夹找不到，但实际存在。排查发现用户有 149 个收藏夹，但 API 只返回了 100 个

**修复**:
```python
def get_all_collections(zot):
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
```

### Bug 2: collection_items() 分页问题

**问题**: `zot.collection_items()` 也分页，每页 100 条。"相生相克-关系"文件夹实际有 62 篇论文，但第一页只返回了 53 篇

**发现经过**: 用户确认文件夹应有 57 条（实际 62 篇过滤附件后），但处理结果显示只有 53 篇。进一步检查发现 API 返回 100 条，但还有第二页 30 条

**修复**: 同 Bug 1 的分页逻辑，应用到 `collection_items` 调用

### Bug 3: 漏处理无标题的笔记条目

**问题**: 文件夹中有 5 个 `itemType=note` 且标题为空的条目，被当作"无摘要"处理

**修复**: 过滤时跳过 `not title` 的条目

---

## 四、处理记录

### 4.1 readability 文件夹（L4XWH5DI）

- 20 篇论文
- 2 篇已有 remark（跳过）
- 18 篇新添加 remark

### 4.2 相生相克-关系 文件夹（8PLDEHRT）

- 62 篇论文（从 130 条总条目中过滤附件和无标题笔记）
- 0 篇已有 remark
- 62 篇新添加 remark
- 5 篇无标题笔记已跳过

---

## 五、Skill 文件结构

```
.claude/skills/zotero-remark/
└── SKILL.md    # 主技能文件，包含完整工作流程和代码示例
```

---

## 六、关键配置信息

- **Python 路径**: `/opt/anaconda3/bin/python`（系统 Python 未安装 pyzotero）
- **Zotero API**: 用户 ID `13675226`，Library Type `user`
- **凭证存储**: 项目 `.env` 文件
- **配置文件路径**: `/Users/dylan_kc/Documents/AIproject/project1/.env`
