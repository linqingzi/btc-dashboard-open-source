# 数据与第三方声明

## 本仓库的数据

`data/latest.json` 和 `data/history.json` 完全由 `scripts/generate_demo.py` 中的固定常数生成。它们不包含从供应商下载或从原私有仓库复制的数值。所有记录均有 `meta.synthetic: true` 及生成器标识，可用 `--check` 逐字节验证。

本仓库没有实时行情采集器、环境密钥加载器、自动更新器、交易执行器或定时工作流。生成器及评分程序无需网络。静态页面只请求同目录下的固定 JSON，拒绝未标为合成的数据；此标识用于清楚说明来源，不是数据权利证明。

静态托管打包脚本 `scripts/build_static_demo.py` 先逐字节验证固定合成示例，再仅复制 `index.html`、`app.js`、`i18n.js`、`data/latest.json`、MIT `LICENSE` 及空的 `.nojekyll`。发布包不包含 Git 历史、采集器、Python 脚本、账户、凭证或第三方行情。网页没有输入上传、交易或数据采集功能，也不自动请求外部数据接口；说明链接由使用者点击后才跳转到 GitHub。

## 代码与名称

仓库中的自有源代码、文档与合成示例以 MIT 发布。未打包第三方 JavaScript/Python 程序库、字体、图像或供应商数据集；Python 使用标准库，前端使用浏览器内建功能和系统字体。

原评分配置和界面保留部分常见指标、交易场所、数据供应商及金融产品的名称。这些名称只用于说明指标背景及兼容字段，不表示关联、赞助、背书或取得数据授权。评分规则中的来源标签不表示合成数值来自该来源。

## 将来接入真实数据

MIT 不会覆盖第三方数据权利。使用者如自行接入真实数据，应在下载、缓存、展示或再分发之前核对适用计划、数据许可、署名要求及书面批准。公开端点或免费 API 不等于允许再分发。

以下官方材料是接入前的核对入口，核对日期为 2026-10-21；具体条款可能变更，且不能替代适用于使用者的合同：

| 来源 | 核对事项 | 官方入口 |
| --- | --- | --- |
| Finnhub | 行情及派生结果的再分发需要书面批准 | [Terms of Service](https://finnhub.io/terms-of-service) |
| Yahoo Finance | 行情数据再分发限制 | [Exchanges and data providers](https://help.yahoo.com/kb/SLN2310.html) |
| OKX | §9.4 对公开端点数据同样适用再分发限制 | [API Agreement](https://www.okx.com/help/okx-api-agreement) |
| CoinGecko | 计划范围、数据使用及署名要求 | [API Terms](https://www.coingecko.com/en/api_terms) |
| Coin Metrics Community | 数据适用 CC BY-NC 4.0 等社区条件，另于软件许可 | [Community Data](https://gitbook-docs.coinmetrics.io/packages/coin-metrics-community-data) |
| Alternative.me | 数据使用及紧邻展示处的署名要求 | [Fear & Greed API rules](https://alternative.me/crypto/fear-and-greed-index/) |
| FRED | 各数据系列拥有者的版权及限制仍然适用 | [API Terms](https://fred.stlouisfed.org/docs/api/terms_of_use.html) |
| ECB / Frankfurter | 来源署名及具体数据提供者的条款 | [ECB reuse policy](https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html)、[Frankfurter terms](https://frankfurter.dev/license/) |
| Blockchain.com | API 和数据内容的许可及再分发限制 | [API Terms](https://www.blockchain.com/legal/api-terms) |

其他交易场所或第三方资料同样需要独立核对。本项目不提供任何供应商账户、数据订阅或数据授权，也不自动联系供应商。
