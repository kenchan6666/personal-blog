# Tool Usage Notes

- `mcp_portfolio_portfolio_overview`：需要全站上下文时使用；返回里的 `surfaces` 标明首页与 About。
- 改首页 / Hero / 简介 / 技能 / 经历条：`portfolio_get_site` 再 `portfolio_update_site`。不要找名叫 main 的 About 页。同一轮把已确认事实写入 RAG。
- 查看或改 About 页：同一轮 `portfolio_list_content` kind=`about`，用返回的 id 或 slug（模块 kind 为 summary / education / experience / achievement / custom）。同一轮同步 RAG。
- `mcp_portfolio_portfolio_list_content` / `get_content`：写作前读取相关 Project / Article / Journal / About 模块。
- `mcp_portfolio_portfolio_create_content`：创建 Draft 项目、文章、日志或 About 模块。写完后同步 RAG。不要在创建时发布。
- `mcp_portfolio_portfolio_update_content`：只传用户要求改变的字段；About 用 kind=`about`。不能把 Draft 升为 published。已发布记录普通更新会保持 published。写完后同步 RAG。
- `mcp_portfolio_portfolio_publish_content`：仅在 Owner 明确要求发布时调用。kind 为 project / article / journal / about，identifier 为 id 或 slug。首页 SiteProfile 与分类不用此工具。发布后同步 RAG。
- `mcp_portfolio_portfolio_list_github_repos`：列出 Owner 已授权的全部 GitHub 仓库（含私有）。未连接时先请用户到后台 GitHub 页授权。
- `mcp_portfolio_portfolio_get_github_source` / `get_github_file`：用 `owner/name` 或唯一仓库短名（如 `fabric_demo`）读取已授权仓库。README 文件名大小写不敏感。第一动作就是调用工具，禁止只预告。读完只摘要，不要把整份文件贴回对话。
- `mcp_portfolio_portfolio_get_project_source` / `get_source_file`：读取已绑定 SourceRepo 的项目源码。
- 私有仓只在后台对话中使用，不要把私有细节写进会公开发布的内容。
- `mcp_portfolio_portfolio_list_comments`：可读取待审核及历史评论。
- `mcp_portfolio_portfolio_comment_action`：仅在用户明确要求时审核、拒绝或回复。
- `mcp_portfolio_portfolio_list_knowledge`：查看“关于我”RAG（跨对话的私有记忆，不是首页，也不是完整聊天记录）。改站点或需要身份事实时先读，避免重复条目。
- `mcp_portfolio_portfolio_remember_knowledge`：把已确认事实写入知识库。改站点内容的同一轮必须调用；闲聊不调用。
- `mcp_portfolio_portfolio_update_knowledge`：修正既有 RAG 条目；先 `list_knowledge` 确认目标记录。只写事实。

不要使用 exec、notebook、`gh` CLI 或工作区文件来代替上述业务工具。
