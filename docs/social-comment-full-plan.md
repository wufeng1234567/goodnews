# 社媒完整评论采集：技术方案与实验计划

> 目标：尽可能拿到 Bilibili、抖音、小红书的完整评论树，并给出可执行、可复现、可验收的路线。
>
> 本文所有结论都区分“平台公开面”“浏览器会话”“第三方/官方商业接口”，不把 DOM 解析当作数据方案。DOM 只用于让页面滚动/点击，不用于解析评论内容。

## 0. 结论摘要

1. **Bilibili 是唯一能用公开 Web API 稳定拿全主评论的平台**。登录 Cookie 下 `/x/v2/reply` 可分页；楼中楼 `/x/v2/reply/reply` 可分页。实测 `max_comments=1000` 能返回 1000 条主评论（旧代码错误地在第 3 页 19 条时提前停止，已修复）。
2. **抖音没有可用的公开 Web 评论 API**。`iesdouyin` 旧接口只固定返回 11 条并忽略 cursor；Web 页面 XHR `comment/list` 使用 `cursor + count=5 + a_bogus`，一旦脱离页面上下文（即使原 URL 原样重放）也返回 0 条。可稳定执行的是真实浏览器会话 + 页面滚动，实测 `max=100` 花 23.1 秒得到 108 条，平台显示总量 247,848。
3. **小红书登录后可以用浏览器 XHR 抓到评论页**。带真实登录态的可见 Edge 能返回 `code=0` 的 `/api/sns/web/v2/comment/page`，首屏 10 条、`cursor + has_more` 正常；但直接改 cursor 的请求返回 406，自行用页面 `window._webmsxyw` 签名后请求也返回 461，说明平台服务端会校验浏览器上下文/风控。当前登录态不是小红书真实账号态时，页面会显示“登录查看全部评论”，只能拿到首屏 10 条。
4. **要接近“竞品级完整评论”，现实路线是：B 站公开 API + 抖音/小红书登录浏览器 XHR 工作流 + 任务化限速 + 断点续采 + 导出**。要承诺绝对全量/稳定 SLA，只能接官方企业接口或第三方数据供应商；这不是空话，下面给出对比和采购/验证步骤。

## 1. 可行性分级与成本口径

| 等级 | 含义 | 交付判断 |
|---|---|---|
| A | 已验证、可产品化 | 可直接进入主链路 |
| B | 已验证，但受登录/风控/速率影响 | 可做主链路，必须限速、重试、告警 |
| C | 技术可行但维护成本高，易失效 | 只做备选/实验，不承诺 SLA |
| D | 不满足“完整评论”目标 | 不投入 |

成本单位：**人日（1 人日 ≈ 6 小时工程时间）**，不含平台账号、代理 IP、第三方 API 费用。

## 2. 方案总表（每个结论都有依据、等级、成本、风险、下一步）

| # | 方案 | 平台 | 依据 | 可行性 | 落地成本 | 风险与合规 | 下一步验证实验 |
|---|---|---|---|---|---|---|---|
| 1 | 公开 Web API 层级分页 + 楼中楼分页 | Bilibili | 实测 `x/v2/reply` 第 1–10 页均有数据；修复前 max=1000 只到 59 条，修复后 max=1000 返回 1000 条 | **A** | 1–2 人日（已基本完成） | 平台 ToS/频率限制；Cookie 失效；不做验证码绕过 | 以 68,898 条视频为目标跑 100k 上限，记录页数、耗时、失败页；连续 3 次重跑确认不重复 |
| 2 | `/x/v2/reply/main` 的 `pagination_reply.next_offset` | Bilibili | 原始响应 `cursor.pagination_reply.next_offset` 存在；`mode=3` 返回 20 条；旧接口页大小 20 | **B+** | 1 人日 | 参数/接口可能变更；需与层级分页合并去重 | 用 `reply/main` 连续取 10 页，与 `x/v2/reply` 前 10 页的 comment id 集合做差异比较 |
| 3 | 楼中楼 `/x/v2/reply/reply` 分页 | Bilibili | 单 root 实测 151 条；主评论 150/607/2970 等回复数存在 | **A** | 已完成 | 大 root 会放大请求数和耗时 | root 级并发限 4；测量 1,000/5,000 条楼中楼的 P95 耗时和错误率 |
| 4 | 抖音 Web XHR `comment/list` + 页面滚动 | 抖音 | 页面真实请求 `cursor=0,count=5,a_bogus=...`；首响应 `total=247,845`；`max=100` 实测 23.1 秒 108 条 | **B-** | 5–8 人日（已有基础） | 登录态/账号/IP 风控；页面结构变化；不能承诺绝对全量 | 用真实登录账号跑 1,000 条目标，记录每页 cursor、滚动次数、请求失败码；目标 ≥ 1,000 条/10 分钟 |
| 5 | 抖音 `comment/list` 原请求/改 cursor 重放 | 抖音 | 页面原生 URL 原样 `page.request` 重放 200 但 `comments=[]`；改 count/cursor 同样为空 | **D** | 0.5 人日即可判死 | 触发风控；签名与浏览器上下文绑定 | 不再投入；保留为反例，禁止在生产代码中重放 |
| 6 | 抖音 `iesdouyin` 旧 API | 抖音 | `iesdouyin.com/web/api/v2/comment/list/` 返回 11 条；`cursor=0/20/40,count=5/20/50` 均约 11 条且无 cursor/has_more | **D** | 0.5 人日 | 旧接口已不完整；可能随时下线 | 不再作为全量方案；只可做“快速预览候选”并标注非完整 |
| 7 | 抖音 `a_bogus` 本地签名生成 | 抖音 | 公开项目 `douyin-abogus` 提供 a_bogus 构造；但 Web 端参数/版本频繁变化 | **C** | 4–8 人日 + 持续维护 | 逆向/绕过风控合规风险；账号封禁；高维护 | 在隔离测试账号上生成 `count=20,cursor=N`，与页面请求响应字段对比；必须只做内部 PoC，不进生产 |
| 8 | 抖音官方开放平台评论接口 | 抖音 | 官方文档存在“评论列表”接口，但需要开放平台 App/Token；当前项目无企业资质/凭证 | **A（有资质时）** | 申请 1–4 周 + 2–4 人日接入 | 资质、权限、数据用途限制；合规成本 | 读官方文档申请测试应用；用 1 个测试视频验证返回条数、分页、评论层级 |
| 9 | 小红书登录态浏览器 XHR | 小红书 | 可见 Edge + 登录态首屏 `/api/sns/web/v2/comment/page` 返回 `code=0`、10 条、`has_more=true`；原请求重放 200，改 cursor 406；`_webmsxyw` 重签 cursor 461 | **B-/C** | 7–12 人日 | 登录态强绑定浏览器/IP；安全风控/验证码；账号风险 | 用真实账号登录后关闭登录遮罩，测 100/500 条滚动；记录每次评论请求的 cursor、has_more、状态码 |
| 10 | 小红书第三方评论 API/数据服务 | 小红书 | 公开文章展示评论 API 契约：Token、cursor、`page_size` 最大 50、`need_sub_comment`；Apify 也有 RedNote Comments Scraper | **A-/B** | 2–5 人日接入 + 按量费用 | 非官方、数据合规与稳定性依赖供应商；成本不可控 | 申请试用 1 个供应商，用示例笔记核对主评论/楼中楼/总数三项 |
| 11 | MediaCrawler 等开源采集器 | 三平台 | 公开项目覆盖小红书/抖音/B站评论，采用浏览器自动化+平台接口；可作为实现参考 | **B** | 3–7 人日集成/改造 | 开源许可证、上游变更、平台合规；仍需账号和风控策略 | 在隔离环境跑一个视频/笔记，对比评论数与我们的现有适配器 |
| 12 | DOM 解析 | 三平台 | 不稳定、慢、字段缺失；用户明确排除 | **D** | 不投入 | 页面改版即失效；不可审计 | 不安排实验 |

## 2.1 可复现实验入口

在 `backend/` 下运行：

```bat
.venv\Scripts\python.exe -m scripts.social_probe --platform bilibili --url "https://www.bilibili.com/video/BV1MN4y177PB/" --max 1000 --no-replies
.venv\Scripts\python.exe -m scripts.social_probe --platform douyin --url "https://www.douyin.com/video/7690992782325240232" --max 100
.venv\Scripts\python.exe -m scripts.social_probe --platform xiaohongshu --url "https://www.xiaohongshu.com/explore/6a81d8ce0000000005030e80?xsec_token=..." --max 100 --headful
```

输出字段：`declared_comments`（平台声明）、`fetched_comments`（实际）、`top_level_comments`、`has_more`、`collection_method`、`auth_mode`、`elapsed_seconds`、`warnings`。

## 3. 已执行的实验与证据

### 3.1 Bilibili

**实验 B1：匿名 vs 登录态、分页停止条件**

- 视频：`BV1MN4y177PB`，平台显示 `comment_count=68,898`。
- 原始代码：`max_comments=1000` 只返回 59 条；原因是第 3 页返回 19 条，旧逻辑 `len(replies) < 20` 直接 `break`。
- 逐页探测：第 1–10 页分别约 20/20/19/19/20/20/19/20/20/20 条，rpid 无重复；第 4 页仍有新数据。
- 修复后：`max=300 -> 300 条`、`max=1000 -> 1000 条`（1000 条约 18.7 秒）。
- 结论：B 站主评论可连续分页，不能再以“一页不足 20 条”判结束。

**实验 B2：楼中楼**

- 对 root `122383501920` 调用 `/x/v2/reply/reply?type=1&oid=898762590&root=122383501920&pn=1&ps=20`，实测 151 条回复。
- 现有前端已支持单 root 按需加载，不再只显示预览的 5 条。

### 3.2 抖音

**实验 D1：页面原生评论请求**

- 直接视频：`https://www.douyin.com/video/7690992782325240232`
- 首请求：`/aweme/v1/web/comment/list/?...&cursor=0&count=5...&a_bogus=...`
- 响应：`comments` 5 条，`cursor=5`，`has_more=1`，`total=247,845`。
- 当前浏览器适配器 `max=100`：23.1 秒，108 条，仍 `has_more=true`。

**实验 D2：脱离页面重放**

- `page.request.get(原始完整 URL)`：HTTP 200、`status_code=0`、`comments=[]`。
- 将 `count` 改 20/50、`cursor` 改 5/10：同样 200/0 条。
- 结论：评论请求与页面执行上下文/签名强绑定，不能靠复制 URL + 改 cursor 做服务端直连。

**实验 D3：IES 旧接口**

- `https://www.iesdouyin.com/web/api/v2/comment/list/?aweme_id=...&cursor=0&count=20`
- 返回 11 条，`cursor`/`has_more` 缺失；换 cursor/count 不变。
- 结论：只能做快速预览，不满足全量。

### 3.3 小红书

**实验 X1：headful + 登录态**

- Chrome/Edge 使用 `headless=False` + `storage_state`，页面标题正常，首屏评论接口 `/api/sns/web/v2/comment/page` 返回 `code=0`、10 条、`has_more=true`、`cursor=6a85fb9e...`。
- `headless=True` 时同一 URL 会进入安全限制页；因此 XHS 采集必须使用可见浏览器/真实会话。

**实验 X2：请求重放**

- 原请求头（含 `x-s`、`x-t`、`x-s-common`）重放原 URL：200。
- 修改 `cursor` 后重放：406。
- 页面暴露 `window._webmsxyw(path, null)`，能为新 cursor 生成 `X-s/X-t`；用重新签名后的请求：461（平台风控/验证码）。
- 结论：XHS 的评论游标不是简单签名问题，平台还校验浏览器上下文；必须走页面滚动或真实登录后的 UI 请求。

**实验 X3：DOM 策略**

- 已从 XHS 适配器删除 `_extract_dom_note` 和 `parse_xhs_dom_*`；代码不再回退 DOM。数据只接受页面 XHR 捕获。
- 这也避免“页面上有但接口没返回”的假完整。

## 4. 推荐的可执行架构

### 4.1 数据模型

现有 `social_fetch_jobs` + `social_fetch_records` 适合 MVP，但为了 68k+ 级别评论，建议再加：

```text
social_comment_pages
  job_id, page_no, cursor, platform, request_url_hash,
  fetched_count, has_more, raw_payload_ref, created_at
  unique(job_id, page_no)

social_comments
  job_id, platform, comment_id, root_id, parent_id, depth,
  author_id, author_name, text, like_count, reply_count,
  created_at, raw_fields JSONB
  unique(job_id, platform, comment_id)
```

- 每页完成后立即提交 checkpoint，进程崩溃可 `resume from cursor`.
- 评论明细不要继续放在单个 JSONB `result` 中；JSONB 只存摘要/导出元数据。
- 导出从 `social_comments` 分页生成，Excel 用 write-only 流式写。

### 4.2 适配器接口

```python
class FullCommentAdapter(Protocol):
    async def collect(
        self,
        request: SocialFetchRequest,
        checkpoint: Callable[[CursorPage], Awaitable[None]],
    ) -> CollectionSummary: ...
```

- Bilibili：HTTP `x/v2/reply` + `x/v2/reply/reply`，支持 page/cursor；请求限速 2–4 QPS。
- 抖音：Playwright `page.on("response")` 捕获 `comment/list`；只做页面滚动/点击，不解析 DOM 文本；每次记录 `cursor/has_more`。
- 小红书：`headless=False` + `storage_state`；只接受 `comment/page` XHR；登录态失效/风控返回 `platform_access_blocked`。

### 4.3 作业调度

- 1 个平台账号同一时刻 1 个浏览器任务；全局并发上限 2。
- 每页最多重试 3 次，指数退避；401/403/406/461 区分：
  - 登录失效：要求重新登录
  - 风控/验证码：暂停账号，换 IP/稍后重试
  - 参数/页面变化：熔断并告警
- 任务进度按 `page_no / total_pages` 和 `comments_fetched` 双指标展示。

## 5. 分阶段实验计划（可执行）

### Phase 0：基线（已完成）

- Bilibili：68,898 条视频，登录态；max=1000 实测 1000 条；单 root 151 条。
- 抖音：页面 XHR 首屏 5 条；max=100 23.1 秒 108 条；IES 11 条；重放 0 条。
- 小红书：headful 首屏 10 条；headless 安全页；改 cursor 406/461。

### Phase 1：Bilibili 全量（1–2 天）

- 目标：68,898 条主评论 + 可配置楼中楼深度。
- 实验：`max_comments=100000` 跑 3 次，统计页数、耗时、重复 ID 数、失败页；目标重复率为 0，失败页可重试补回。
- 验收：导出的 `social_comments` 与平台 `comment_count` 差值可解释（平台折叠/删除/审核）。

### Phase 2：抖音登录账号 + 滚动驱动（3–5 天）

- 用真实登录账号，打开目标视频，滚动 `.comment-mainContent` 对应的真实评论区（不解析 DOM 文本）。
- 记录每个请求的 `cursor/has_more`；目标 1,000 条/10 分钟。
- 若页面只返回 108/100，检查登录遮罩/滚动容器；若仍被限，转 Phase 2b。
- Phase 2b：申请抖音开放平台测试应用，验证官方评论接口；或试用 `douyin-abogus` PoC（隔离环境，不进生产）。

### Phase 3：小红书真实账号 + 评论面板（3–5 天）

- 用 App 内登录的 storage_state，headful 打开笔记；确认 `comment/page` 返回 `code=0` 且页面无“登录查看全部评论”。
- 控制 `.note-scroller`/评论面板滚动；目标 100 条/2 分钟，记录 cursor 与 `has_more`。
- 若仍只有 10 条：切换第三方评论 API/POC（见 Phase 4），不再耗 DOM。

### Phase 4：第三方/官方通道对比（1 周）

- 申请 1 家小红书评论 API 试用 + 抖音开放平台测试应用；
- 用同一视频/笔记做字段完整性、总数、楼中楼、延迟、单价对比；
- 只有在“必须承诺全量 SLA”的产品需求下才接入生产。

## 6. 成本、风险与合规判断

| 风险 | 影响 | 控制 |
|---|---|---|
| 平台 ToS/robots | 可能被限流/封号 | 只采集公开页面；遵循站点条款；不绕过验证码；提供删除/停止机制 |
| 账号安全 | 登录态泄露/封禁 | 本地 storage_state 加密、gitignore、最小权限、单账号隔离 |
| 个人信息 | 评论含昵称/头像等 | 只采集业务必要字段；提供保留期限和删除；导出权限控制 |
| 平台反爬升级 | 适配器失效 | 版本化适配器、熔断、健康检查、第三方兜底 |
| 绝对全量承诺 | 无法兑现 | 产品文案明确“平台实际返回范围”；SLA 需求走官方/商业 API |

## 7. 最终建议

- **近期主链路**：Bilibili 用 API 做完整主评论+楼中楼；抖音/小红书用登录态浏览器 XHR 做“最佳努力”全量，并保留 `platform_access_blocked`、`has_more`、`fetched_count` 等诚实状态。
- **要追平竞品“完整评论”体验**：优先采购/接入小红书、抖音的第三方数据 API 或官方企业接口；自建只适合做 B 站和垂直深挖。
- **不做**：DOM 解析、脱离页面的抖音/小红书签名重放、伪造全量。
- **立即验收指标**：B 站 1,000 条/18.7 秒可复现；抖音 108 条/23.1 秒可复现；XHS headful 首屏 10 条可复现。下一步按 Phase 1–4 把“可复现”提升到“可 SLA”。

## 8. 参考与公开资料

- [Bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect)
- [MediaCrawler 开源采集器](https://github.com/dongsheng2025/MediaCrawler-)
- [抖音评论抓取 Skill（照抄页面真实请求）](https://github.com/Pluviobyte/douyin-comments)
- [抖音开放平台评论列表文档](https://developer.open-douyin.com/docs/resource/zh-CN/mini-app/develop/server/basic-abilities/video-id-convert/video-review-data/comment-list)
- [douyin-abogus 公开实现](https://github.com/idinging/douyin-abogus)
- [小红书笔记评论 API 文档（第三方）](https://developer.aliyun.com/article/1740796)
- [Apify RedNote Comments Scraper](https://apify.com/memo23/rednote-comments-scraper)

> 注：第三方文章/项目只作为方案证据，不构成平台官方承诺；平台接口可能随时变化。
