# 演示截图来源 / Screenshot provenance

三张 JPG 均于 2026-10-21 从 Chrome 中实际运行的本机页面直接截取，没有生成、拼接或重绘界面：

- `dashboard-demo.jpg`：英文模式的看板与评分明细，1265 × 889。
- `dashboard-demo-zh.jpg`：中文默认模式的同一页面，1265 × 889。
- `social-preview.jpg`：英文模式页面顶部的原始截图裁切，1280 × 640，用于 GitHub 分享预览。

所有图片都保留清晰的中英文合成演示说明。界面对应与截图一同提交的 `index.html`、`app.js` 和 `i18n.js`；输入为本仓库固定合成示例。截图不含账户、个人路径或真实行情。

重现画面：在仓库根目录运行 `python3 scripts/generate_demo.py --check`，然后运行 `python3 -m http.server 8080 --bind 127.0.0.1`，在 Chrome 打开 `http://127.0.0.1:8080`，使用 1280 × 900 浏览器视窗。默认显示中文；点击右上角 **English** 切到英文。保持页面顶部双语合成提示可见，使用浏览器截图工具捕捉内容区域。字体、滚动条、浏览器缩放及本地时区可能影响截图尺寸与日期显示；固定输入及评分不变。

These three JPEGs were captured directly from the running local Chrome UI on 2026-10-21. No AI generation, compositing, or UI redrawing was used. The main image shows English mode, the `-zh` image shows Chinese mode, and the social image is a direct crop of the English page. Every image retains the bilingual synthetic-demo notice and contains only this repository's fictional fixtures. Run the local server as described above, then use **中文 / English** to reproduce either mode. Browser fonts, scrollbars, zoom, and timezone can affect appearance; inputs and scoring remain fixed.

这些项目截图与本仓库自有文档一同以 MIT 授权。 These project screenshots are MIT licensed with the original documentation.
