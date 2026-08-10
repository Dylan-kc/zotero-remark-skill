# 贡献指南

感谢你改进 Zotero Remark。欢迎提交错误报告、兼容性问题、文档改进和小而明确的功能建议。

## 报告问题

提交 Issue 前，请先搜索是否已有相同问题，并说明：

- 使用的操作系统、Python 版本和代理工具（Codex 或 Claude Code）
- 可复现问题的最小步骤
- 预期行为与实际行为
- 已隐藏凭证和私人文献内容的错误信息

请勿在 Issue、日志或截图中包含 Zotero API Key、私人文献库内容或其他敏感信息。安全问题请按 [SECURITY.md](SECURITY.md) 私下报告。

## 本地开发

```bash
git clone https://github.com/Dylan-kc/zotero-remark-skill.git
cd zotero-remark-skill
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

如需连接自己的 Zotero 文献库：

```bash
cp .env.example .env
```

只在本地 `.env` 中填写凭证，绝不要提交该文件。

## 修改要求

- 保持 `.agents/skills/zotero-remark/` 与 `.claude/skills/zotero-remark/` 中的同名文件同步。
- 不要在测试、示例或日志中加入真实的 Zotero 凭证和私人文献数据。
- 保持变更范围明确；功能变更应同时更新相关说明。
- 提交前运行基本语法检查：

```bash
python -m compileall \
  .agents/skills/zotero-remark/scripts \
  .claude/skills/zotero-remark/scripts
```

## Pull Request

PR 描述应说明变更目的、用户影响和验证方法。若修改技能规则或辅助脚本，请确认 Codex 与 Claude Code 两份文件内容一致。
