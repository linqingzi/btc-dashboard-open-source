# 演示截图来源 / Screenshot provenance

以下 JPG 均于 2026-10-21 从 Chrome 中实际运行的本机页面直接截取，没有生成、拼接或重绘界面：

- `dashboard-demo-en.jpg`：明确标注 English 模式的概览，1265 × 889；中文 README 同时展示此图及中文图。
- `dashboard-demo-en-full.jpg`：English 模式的完整页面，1265 × 3452；包含 20 个指标、全部解读及 51 张资料卡，英文 README 优先展示此图。
- `dashboard-demo-zh.jpg`：中文默认模式的同一页面，1265 × 889。
- `dashboard-demo.jpg`：前次英文概览的兼容地址，1265 × 889；两个 README 现在使用上面明确标注语言的文件。
- `social-preview.jpg`：英文模式页面顶部的原始截图裁切，1280 × 640，用于 GitHub 分享预览。

所有图片都保留清晰的中英文合成演示说明。英文图内实际选中 **English**；指标、解读、层级、状态及资料卡均为英文，只有合成说明和语言按钮保留双语。新截图的界面代码与合成输入对应公开提交 `dd9084f6a7ccd6a68e9a0683240db63c97054ec6`，本次未更改程序或数据。截图不含账户、个人路径或真实行情。

重现画面：在仓库根目录运行 `python3 scripts/generate_demo.py --check`，然后运行 `python3 -m http.server 8080 --bind 127.0.0.1`，在 Chrome 打开 `http://127.0.0.1:8080`，使用 1280 × 900 浏览器视窗。默认显示中文；点击右上角 **English** 切到英文。保持页面顶部双语合成提示可见，使用浏览器截图工具捕捉内容区域。字体、滚动条、浏览器缩放及本地时区可能影响截图尺寸与日期显示；固定输入及评分不变。

These JPEGs were captured directly from the running local Chrome UI on 2026-10-21. No AI generation, compositing, or UI redrawing was used. `dashboard-demo-en-full.jpg` shows the complete English interface: 20 indicator rows, their interpretations, and 51 data cards. The `-en` overview is also English, `-zh` is Chinese, and the social image is a direct crop of English mode. The old `dashboard-demo.jpg` URL remains available for compatibility. Only the synthetic notice and language buttons remain bilingual. The new captures use the unchanged application and fixtures from commit `dd9084f6a7ccd6a68e9a0683240db63c97054ec6`. Run the local server as described above, then use **中文 / English** to reproduce either mode. Browser fonts, scrollbars, zoom, and timezone can affect appearance; inputs and scoring remain fixed.

这些项目截图与本仓库自有文档一同以 MIT 授权。 These project screenshots are MIT licensed with the original documentation.
