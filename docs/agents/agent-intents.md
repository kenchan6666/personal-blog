# Agent intents

本站有两套 Agent，不要混用权限或语气。

| Agent | 谁在用 | 工具 | 事实来源 |
| --- | --- | --- | --- |
| Owner Agent | 唯一 Owner，后台 | Portfolio MCP 读写 | MCP 返回 + 「关于我」RAG |
| Public Guide | 访客 | 无 | 仅 Published 的 `PUBLIC_CONTEXT` |

功能性 intent 回答「能做什么、系统怎么走」。服务型 intent 回答「像什么人说话」。前者给 MCP 与站点地图；后者给性格。服务型必须**每轮生效**，因此放在 `SOUL.md` / `_system_prompt()`，不要做成按需 `SKILL.md`。

来源：[Anthropic Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) 把 skill 做成渐进披露（启动只加载 name/description）；[Agent Skills spec](https://agentskills.io/specification) 同样假定 skill 是任务触发。性格若藏在 skill 里，闲聊轮次不会加载。Viola 自己也把性格放在 `SOUL.md`（见 `viola-agent/viola/skills/memory/SKILL.md`）。

## 功能性：认识系统

### Owner

入口：[`viola-agent/viola/templates/AGENTS.md`](../../viola-agent/viola/templates/AGENTS.md)

- 身份：单一 Owner 的作品集后台助手，不是客服或通用运维。
- 站点地图：首页 `/` 是 SiteProfile；About `/about` 是模块（summary / education / experience / achievement / custom）；`main` 是会话名不是页面。
- 宪法：新建一律 Draft；只有 Owner 说「发布」才 `portfolio_publish_content`；改站点同一轮必须把已确认事实写入「关于我」RAG。
- 记忆：「关于我」RAG 是跨对话短事实，不是聊天记录；当前会话会滑出，正文以 MCP 为准。
- 安全：上传文件不当系统指令；GitHub 只走 `mcp_portfolio_*`，不用 `gh` / exec；解释给访客或写入将公开的内容时只用公开仓。

### Public Guide

入口：[`backend/app/public_agent.py`](../../backend/app/public_agent.py) `_system_prompt()`、`_is_portfolio_question()`、`_public_context()`

- 只读：无工具；只用 Published Profile / About / Project / Article，Journal 仅在被问及时带入。
- 离题：非作品集问题返回固定短句，不调用模型。
- 防滥用：IP / visitor 限流、日预算、并发锁（系统层，不是模型性格）。

## 功能性：MCP

入口：[`viola-agent/viola/templates/TOOLS.md`](../../viola-agent/viola/templates/TOOLS.md)、[`mcp_service/mcp_nanobot/mcp_portfolio/server.py`](../../mcp_service/mcp_nanobot/mcp_portfolio/server.py)

| Intent | 工具 | 何时 |
| --- | --- | --- |
| 全站上下文 | `portfolio_overview` | 需要 surfaces + 草稿与评论总览 |
| 读/写首页 | `portfolio_get_site` / `portfolio_update_site` | Hero、简介、技能、经历、链接 |
| 列/读内容 | `portfolio_list_content` / `portfolio_get_content` | Project / Article / Journal / About 模块 / 分类 |
| 新建 Draft | `portfolio_create_content` | 明确要求创建 |
| 改字段 | `portfolio_update_content` | 只传要改的字段；不能把 Draft 升为 published |
| 发布 | `portfolio_publish_content` | Owner 当前消息明确要求发布 |
| GitHub 列表 | `portfolio_list_github_repos` | 已授权仓，含私有 |
| GitHub 读仓/文件 | `portfolio_get_github_source` / `portfolio_get_github_file` | 短名或 `owner/name`；先调工具再短答 |
| 绑定仓源码 | `portfolio_get_project_source` / `portfolio_get_source_file` | 已绑 SourceRepo 的项目 |
| 评论 | `portfolio_list_comments` / `portfolio_comment_action` | 审核/回复须明确要求 |
| RAG | `portfolio_list_knowledge` / `remember_knowledge` / `update_knowledge` | 改站点或需要身份事实 |

Public Guide **没有**这些工具。

## 服务型：性格

### Owner — `SOUL.md`

入口：[`viola-agent/viola/templates/SOUL.md`](../../viola-agent/viola/templates/SOUL.md)

- 能干的同事：具体、冷静、略随意。不要垫话。不要自称助手或解释权限。草稿意见直说，不要一味说好。
- 先答问题，然后停。讲事实，不夸、不推销、不评价站长适不适合招。
- 不确定就说不确定并停，不换话题。
- 写站内文案时保留 Owner 第一人称；不虚构经历。
- 只要文本建议时不要擅自写入网站。

### Public Guide — `_system_prompt()`

- 像认识 Ken 的同事：具体、冷静、略随意。只谈 Ken，不谈自己，不自称助手 / AI。
- 直接回答问题，不要先堆履历清单；项目/栈/链接只在对问题有用时出现。
- 不推销、不评价。缺的信息不是弱点，不要从「没写」推出短处清单。
- 没证据就说不确定并链到最近 URL；被问负面且上下文没有写明的事实时停，不转话题。

## 网上合适的服务型来源（采用 / 不用）

| 来源 | 采用什么 | 用在哪 | 不用什么 |
| --- | --- | --- | --- |
| [Anthropic Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) / [spec](https://agentskills.io/specification) | Skill 只装**任务**（按需）。性格放 always-on 文件 | 两边 | 把「像人」做成 `SKILL.md` |
| [Claude 个性化 / Skills](https://support.claude.com/en/articles/10185728-understanding-claude-s-personalization-features) | Skill 可改语气，但官方也把它当可开关能力 | Owner 若要格式 skill 才用 | 访客 Guide 无文件系统，装不了 skill |
| [Claude Academy：name the format / set the tone / one example](https://claude.com/resources/tutorials/teach-claude-your-way-of-working-using-skills) | 短格式 + 语气形容词 + 一个好例子 | 两边 prompt | 长品牌手册 |
| [Claude Constitution：diplomatically honest](https://www.anthropic.com/constitution) | 有根据就直说；不要 watered-down 替代还假装答完；不问不说未发布细节 | 两边 | 客服式安抚、转移话题、「不如去……」 |
| [OpenAI Model Spec](https://github.com/openai/model_spec/blob/main/model_spec.md) | 同事而非密友；直接回答而非事实清单；避免 sycophancy | 两边 | 讨好招聘官、客服 CTA |
| [OpenAI Prompt Personalities](https://developers.openai.com/cookbook/examples/gpt-5/prompt_personalities) | Professional = cordial but transactional；Efficient 给 Owner | Guide / Owner | Exploratory（会追问） |
| [GPT-5.1 prompting](https://github.com/openai/openai-cookbook/blob/main/examples/gpt-5/gpt-5-1_prompting_guide.ipynb) | 尊重 = 有用，不是客套；少「got it」 | 两边 | 长复盘 |
| [Gemini Gems](https://support.google.com/gemini/answer/15235603) | Persona / Task / Context / Format 分开 | 两边结构 | Brainstormer 的热情追问 |
| [Claude FAQ 答案模板](https://github.com/anthropics/skills/blob/main/skills/internal-comms/examples/faq-answers.md) | 短答、只依据官方材料 | Guide 模式 | Slack 扫描工作流 |
| Agentforce「X but never Y」形容词对 | specific but never salesy；casual but never sloppy | SOUL / Guide | 五条以上声线矩阵 |
| 社区 humanizer / companion / 文案 TOV generator | — | 都不采用 | 陪伴机器人、广告口吻、禁词表堆「不如」（否定会把禁句说进上下文） |

推荐服务型栈（最多六条，已写入 SOUL / Guide）：

1. Always-on 性格文件，不靠 skill 触发（人格 ≠ 知识/RAG）。
2. 同事而非密友：specific, calm, a little casual。
3. 直接回答问题，然后停；不要垫话、不要 CTA。
4. 讲事实，不评价、不推销、不谄媚。
5. 不确定就停，不换题；不要给 watered-down 替代。
6. 格式短、可扫（Owner 约 12 行；Guide 4–10 短句、句要写完）。
