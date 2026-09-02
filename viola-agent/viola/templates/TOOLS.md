# Tool Usage Notes

- `mcp_portfolio_portfolio_overview`：需要全站上下文时使用。
- `mcp_portfolio_portfolio_list_content` / `get_content`：写作前读取相关内容。
- `mcp_portfolio_portfolio_create_content`：创建 Draft 项目、文章、日志或 About 模块。
- `mcp_portfolio_portfolio_update_content` / `update_site`：只传用户要求改变的字段。
- `mcp_portfolio_portfolio_get_project_source` / `get_source_file`：读取已公开项目的 GitHub 源码。
- `mcp_portfolio_portfolio_list_comments`：可读取待审核及历史评论。
- `mcp_portfolio_portfolio_comment_action`：仅在用户明确要求时审核、拒绝或回复。
- `mcp_portfolio_portfolio_list_knowledge`：查看“关于我”RAG 资料。
- `mcp_portfolio_portfolio_remember_knowledge`：仅当用户明确说“记住、记录、加入关于我”等意图时，把聊天中确认的个人事实或经历写入知识库。
- `mcp_portfolio_portfolio_update_knowledge`：用户要求修正既有个人资料时使用；先读取列表并确认目标记录。

不要使用 exec、notebook 或工作区文件来代替上述业务工具。
