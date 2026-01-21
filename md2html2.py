import os
import base64
import mimetypes
import re
import markdown
import tkinter as tk
from tkinter import filedialog

# 手动：pip install markdown python-markdown-math
# 打包建议：pyinstaller --onefile --windowed --hidden-import=mdx_math md2html2.py

def md_to_single_html_reader(md_path: str, html_path: str):
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. 去除 YAML 题头（front matter）
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) == 3:
            content = parts[2].lstrip()

    # 2. Markdown -> HTML 转换
    # 保持原有扩展，新增 'mdx_math' 以支持 LaTeX 公式
    html_body = markdown.markdown(content, extensions=["extra", "toc", "fenced_code", "mdx_math"])

    # 3. 给 h1–h4 添加唯一 id (用于目录跳转)
    counter = {"h1": 0, "h2": 0, "h3": 0, "h4": 0}

    def add_ids(m):
        tag, text = m.group(1), m.group(2)
        counter[tag] += 1
        anchor = f"{tag}-{counter[tag]}"
        return f'<{tag} id="{anchor}">{text}</{tag}>'

    html_body = re.sub(r'<(h[1-4])>(.*?)</h[1-4]>', add_ids, html_body)

    # 4. 构建目录（嵌套 ul）
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

    # 5. 图片处理（转 Base64 且支持懒加载）
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
        mime_type = mime_type or "image/png"
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f'<img data-src="data:{mime_type};base64,{b64}" alt="" loading="lazy">'

    html_body = re.sub(r'<img[^>]*src="([^"]+)"[^>]*>', img_repl, html_body)

    # 6. MathJax 配置脚本 (专门针对 $...$ 格式优化)
    mathjax_config = """
    <script>
    window.MathJax = {
      tex: {
        inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
        displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
        processEscapes: true
      },
      options: {
        // 避开代码块等标签，防止误渲染
        skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code']
      }
    };
    </script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    """

    # 7. CSS 样式 (严格遵循你要求的布局逻辑)
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
      position: fixed; top: 10px; left: 10px; z-index: 3000;
      font-size: 14px; padding: 6px 12px;
      background: #007acc; color: #fff;
      border: none; border-radius: 6px;
      cursor: pointer; box-shadow: 0 2px 6px rgba(0,0,0,.15);
    }

    nav {
        position: fixed; top: 0; left: 0; bottom: 0;
        width: var(--toc-width);
        box-sizing: border-box; 
        overflow-y: auto;
        padding: 48px 1rem 1rem 1rem;
        border-right: 1px solid #ddd;
        background: #f9f9f9;
        z-index: 2000;
        transform: translateX(0);
        transition: transform .25s ease;
    }
    body.toc-collapsed nav { transform: translateX(-100%); }

    /* 恢复你的正文间距计算逻辑：padding-left 永远比目录宽 1em */
    main {
        min-height: 100%;
        box-sizing: border-box;
        padding: 2rem 1em;
        padding-left: calc(var(--toc-width) + 1em); 
        transition: padding-left .25s ease;
    }
    body.toc-collapsed main { padding-left: 1em; }

    /* 目录树样式 */
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
    code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }

    /* LaTeX 公式溢出处理 */
    .MathJax { overflow-x: auto; overflow-y: hidden; }

    /* 表格样式 */
    table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
    th, td { border: 1px solid #ccc; padding: 0.5em; text-align: left; }
    th { background-color: #f0f0f0; font-weight: bold; }

    /* 暗色模式 */
    @media (prefers-color-scheme: dark) {
        body { background: #121212; color: #e0e0e0; }
        nav { background: #1e1e1e; border-right: 1px solid #444; }
        pre { background: #1e1e1e; color: #e0e0e0; }
        code { color: #ffcc66; }
        #toggle-toc { background: #444; }
        th, td { border-color: #555; }
        th { background-color: #222; color: #eee; }
    }

    /* 小屏适配 */
    @media (max-width: 768px) {
        main { padding-left: 1em; }
        nav { box-shadow: 0 0 12px rgba(0,0,0,.25); padding-top: 48px; }
    }
    """

    # 8. JavaScript (保留原始的宽度同步和懒加载逻辑)
    js = """
    <script>
    document.addEventListener("DOMContentLoaded", function() {
        const body = document.body;
        const btn = document.getElementById("toggle-toc");
        const nav = document.querySelector("nav");
        const root = document.documentElement;

        function syncTocWidth() {
            const w = nav.offsetWidth;
            const width = Math.max(w, 240);
            root.style.setProperty('--toc-width', width + 'px');
        }

        body.classList.add("toc-expanded");
        requestAnimationFrame(syncTocWidth);
        setTimeout(syncTocWidth, 200);
        window.addEventListener('resize', syncTocWidth);

        btn.addEventListener("click", function() {
            body.classList.toggle("toc-collapsed");
            body.classList.toggle("toc-expanded");
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

        // 目录折叠
        document.querySelectorAll(".toc li").forEach(li => {
            const childUl = li.querySelector(":scope > ul");
            if (childUl) {
                li.classList.add("has-children");
                li.addEventListener("click", function(e) {
                    if (e.target.tagName.toLowerCase() === "a") return;
                    li.classList.toggle("open");
                });
            }
        });
    });
    </script>
    """

    # 9. 组合 HTML
    full_html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{os.path.basename(md_path)}</title>
<style>{css}</style>
{mathjax_config}
</head>
<body>
<button id="toggle-toc">☰ 目录</button>
<nav>{toc_html}</nav>
<main>{html_body}</main>
{js}
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"✅ 成功生成支持公式的 HTML: {html_path}")


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    md_file = filedialog.askopenfilename(title="选择 Markdown 文件", filetypes=[("Markdown", "*.md")])
    if md_file:
        save_path = os.path.splitext(md_file)[0] + "_reader.html"
        md_to_single_html_reader(md_file, save_path)
    else:
        print("❌ 未选择文件")