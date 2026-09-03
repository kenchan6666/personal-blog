# Portfolio MCP

供 `viola-agent` 使用的 Owner-only MCP 服务。它不直接访问 MongoDB，而是通过
博客 FastAPI 的 Owner API 读取和修改数据，因此沿用同一套校验和数据模型。

## 环境变量

- `BACKEND_API_BASE_URL`：容器内为 `http://api:8000`
- `PORTFOLIO_SERVICE_TOKEN`：须与后端 `AGENT_SERVICE_TOKEN` 相同
- `PORTFOLIO_WRITE_ENABLED`：生产编排中显式设为 `true`

## 工具

- `portfolio_overview` / `portfolio_get_site` / `portfolio_update_site`（首页 SiteProfile；不是 About）
- `portfolio_list_content` / `portfolio_get_content`
- `portfolio_create_content` / `portfolio_update_content` / `portfolio_publish_content`
- `portfolio_list_github_repos` / `portfolio_get_github_source` / `portfolio_get_github_file`
- `portfolio_get_project_source` / `portfolio_get_source_file`
- `portfolio_list_comments` / `portfolio_comment_action`
- `portfolio_list_knowledge` / `portfolio_remember_knowledge` / `portfolio_update_knowledge`

创建项目、文章、日志和 About 模块时固定为 Draft。只有 Owner 明确说发布 / publish
时才调用 `portfolio_publish_content`；普通更新不得把已上线内容改回 Draft。没有删除
工具。评论审核、拒绝和站长回复必须由 Agent 根据 Owner 的明确指令调用。个人资料只在
Owner 明确要求记住或修改时写入“关于我”知识库。

## 本地运行

```bash
pip install -e ./mcp_service/mcp_nanobot
python -m mcp_portfolio.server
```
