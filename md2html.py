import os
import base64
import mimetypes
import re
import markdown
import tkinter as tk
from tkinter import filedialog

# 打包：pip install pyinstaller
# 终端：pyinstaller --onefile --windowed md2html.py
def md_to_single_html_reader(md_path: str, html_path: str):
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 去除 YAML 题头（front matter）
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) == 3:
            content = parts[2].lstrip()

    # Markdown -> HTML
    html_body = markdown.markdown(content, extensions=["extra", "toc", "fenced_code"])

    # 给 h1–h4 添加唯一 id
    counter = {"h1": 0, "h2": 0, "h3": 0, "h4": 0}

    def add_ids(m):
        tag, text = m.group(1), m.group(2)
        counter[tag] += 1
        anchor = f"{tag}-{counter[tag]}"
        return f'<{tag} id="{anchor}">{text}</{tag}>'

    html_body = re.sub(r'<(h[1-4])>(.*?)</h[1-4]>', add_ids, html_body)

    # 构建目录（嵌套 ul）
    headings = re.findall(r'<(h[1-4]) id="(.*?)">(.*?)</h[1-4]>', html_body)
    toc_html = "<ul class='toc'>"
    last_level = 1
    for tag, anchor, text in headings:
        level = int(tag[1])
        if level > last_level:
            toc_html += "<ul>" * (level - last_level)
        elif level < last_level:
            toc_html += "</ul>" * (last_level - level)
        toc_html += f"<li><a href='#{anchor}'>{text}</a></li>"
        last_level = level
    toc_html += "</ul>" * (last_level - 1)
    toc_html += "</ul>"

    # 图片懒加载（整标签替换，避免原标签尾部残留）
    md_dir = os.path.dirname(os.path.abspath(md_path))

    def img_repl(m):
        src = m.group(1)
        if src.startswith(("http://", "https://", "data:")):
            return m.group(0)
        img_path = os.path.join(md_dir, src)
        if not os.path.exists(img_path):
            print(f"⚠️ 图片不存在：{img_path}")
            return m.group(0)
        mime_type, _ = mimetypes.guess_type(img_path)
        if not mime_type:
            mime_type = "image/png"
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f'<img data-src="data:{mime_type};base64,{b64}" alt="" loading="lazy">'

    html_body = re.sub(r'<img[^>]*src="([^"]+)"[^>]*>', img_repl, html_body)

    css = """
    :root { color-scheme: light dark; --toc-width: 300px; }
    html, body { height: 100%; }
    body {
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans", "Microsoft YaHei", Arial, sans-serif;
        line-height: 1.6;
        background: #fff; color: #000;
    }

    #toggle-toc {
      position: fixed;
      top: 10px;       /* 固定像素位置 */
      left: 10px;      /* 固定像素位置 */
      z-index: 3000;
      font-size: 14px;     /* 固定像素大小 */
      padding: 6px 12px;   /* 固定像素内边距 */
      background: #007acc;
      color: #fff;
      border: none;
      border-radius: 6px;   /* 固定像素圆角 */
      cursor: pointer;
      box-shadow: 0 2px 6px rgba(0,0,0,.15);
    }


    /* 固定目录：实际宽度以 offsetWidth 为准（JS 同步到 --toc-width） */
    nav {
        position: fixed; top: 0; left: 0; bottom: 0;
        width: var(--toc-width);
        box-sizing: border-box; /* 包含边框与滚动条 */
        overflow-y: auto;
        padding: 48px 1rem 1rem 1rem; /* 顶部留出按钮空间 */
        border-right: 1px solid #ddd;
        background: #f9f9f9;
        z-index: 2000;
        transform: translateX(0);
        transition: transform .25s ease;
    }
    body.toc-collapsed nav { transform: translateX(-100%); }

    /* 正文：以 padding-left 避开目录，永不被覆盖；左右各留 1em */
    main {
        min-height: 100%;
        box-sizing: border-box;
        padding: 2rem 1em;
        padding-left: calc(var(--toc-width) + 1em); /* 让出目录宽度 + 1em */

        transition: padding-left .25s ease;
    }
    body.toc-collapsed main { padding-left: 1em; } /* 收起目录时全屏 */

    /* 目录树样式与折叠箭头 */
    .toc { list-style: none; padding-left: 0; margin: 0; }
    .toc ul { list-style: none; padding-left: 1rem; margin: 0; }
    .toc li.has-children > a::before {
        content: '▸'; display: inline-block; margin-right: 6px;
        transform: rotate(0deg); transition: transform .2s ease;
    }
    .toc li.open > a::before { transform: rotate(90deg); }
    .toc a {
        display: inline-block; padding: 4px 0;
        color: inherit; text-decoration: none;
        word-break: break-word;
    }

    /* 内容样式 */
    img { max-width: 100%; height: auto; display: block; margin: 1rem auto; }
    pre { background: #f4f4f4; padding: 1rem; border-radius: 8px; overflow-x: auto; }
    code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }

    /* 表格样式 */
    table {
      border-collapse: collapse;
      width: 100%;
      margin: 1rem 0;
    }
    th, td {
      border: 1px solid #ccc;
      padding: 0.5em;
      text-align: left;
    }
    th {
      background-color: #f0f0f0;
      font-weight: bold;
    }

    /* 暗色模式下的表格样式 */
    @media (prefers-color-scheme: dark) {
      th, td { border-color: #555; }
      th { background-color: #222; color: #eee; }
    }

    /* 暗色模式 */
    @media (prefers-color-scheme: dark) {
        body { background: #121212; color: #e0e0e0; }
        nav { background: #1e1e1e; border-right: 1px solid #444; }
        pre { background: #1e1e1e; color: #e0e0e0; }
        code { color: #ffcc66; }
        #toggle-toc { background: #444; }
    }

    /* 小屏：目录抽屉覆盖，正文不缩进；按钮仍固定 */
    @media (max-width: 768px) {
        main { padding-left: 1em; }
        nav { box-shadow: 0 0 12px rgba(0,0,0,.25); padding-top: 48px; }
    }
    """

    js = """
    <script>
    document.addEventListener("DOMContentLoaded", function() {
        const body = document.body;
        const btn = document.getElementById("toggle-toc");
        const nav = document.querySelector("nav");
        const root = document.documentElement;

        // 根据目录实际宽度同步 CSS 变量，确保正文让出空间足够
        function syncTocWidth() {
            // 使用 offsetWidth 包括边框与滚动条宽度
            const w = nav.offsetWidth;
            // 最小宽度保护，防止字体尚未加载时值为 0
            const width = Math.max(w, 240);
            root.style.setProperty('--toc-width', width + 'px');
        }

        // 初始展开并同步宽度
        body.classList.add("toc-expanded");
        // 多次触发，覆盖字体加载与渲染抖动
        requestAnimationFrame(syncTocWidth);
        setTimeout(syncTocWidth, 0);
        setTimeout(syncTocWidth, 200);
        window.addEventListener('resize', syncTocWidth);

        // 折叠/展开切换，同时再次同步宽度
        btn.addEventListener("click", function() {
            body.classList.toggle("toc-collapsed");
            body.classList.toggle("toc-expanded");
            // 展开时才需要让出空间；收起后 main 已用 1em
            syncTocWidth();
        });

        // 懒加载图片
        const imgs = document.querySelectorAll("img[data-src]");
        const observer = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    observer.unobserve(img);
                }
            });
        }, { rootMargin: "200px" });
        imgs.forEach(img => observer.observe(img));

        // 目录折叠：仅有子项的 li 可折叠
        document.querySelectorAll(".toc li").forEach(li => {
            const childUl = li.querySelector(":scope > ul");
            if (childUl) {
                li.classList.add("has-children");
                const a = li.querySelector(":scope > a");
                li.addEventListener("click", function(e) {
                    if (e.target.tagName.toLowerCase() === "a") return;
                    li.classList.toggle("open");
                });
                if (a) a.addEventListener("click", function() { li.classList.toggle("open"); });
            }
        });
    });
    </script>
    """

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{os.path.basename(md_path)}</title>
<style>{css}</style>
</head>
<body class="toc-expanded">
<button id="toggle-toc">☰ 目录</button>
<nav>{toc_html}</nav>
<main>{html_body}</main>
{js}
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 已生成最终修复版 HTML 阅读器: {html_path}")


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    md_file = filedialog.askopenfilename(title="选择 Markdown 文件", filetypes=[("Markdown 文件", "*.md")])
    if md_file:
        html_file = os.path.splitext(md_file)[0] + "_reader.html"
        md_to_single_html_reader(md_file, html_file)
    else:
        print("❌ 没有选择文件")
