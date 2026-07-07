import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 漫画数据根目录（相对于项目根目录）
COMICS_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'comics')

def load_comic_meta(comic_id):
    """读取漫画的 head.json"""
    path = os.path.join(COMICS_ROOT, comic_id, 'head.json')
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_image_url(comic_id, filename):
    """生成图片的绝对访问 URL（Vercel 静态托管）"""
    # 注意：Vercel 会将 /comics 目录映射到静态路由，后面配置
    return f"/comics/{comic_id}/{filename}"

def get_chapter_images(comic_id, chapter_index):
    """根据章节索引（0开始）返回该章节所有图片 URL 列表"""
    meta = load_comic_meta(comic_id)
    if not meta:
        return None
    chapters = meta.get('chapters', [])
    if chapter_index < 0 or chapter_index >= len(chapters):
        return None
    # 计算起始页码（1-based）
    start_page = 1
    for i in range(chapter_index):
        start_page += chapters[i]['page_count']
    end_page = start_page + chapters[chapter_index]['page_count'] - 1
    # 生成文件名列表
    urls = []
    for p in range(start_page, end_page + 1):
        fname = f"{p:05d}.jpeg"
        urls.append(get_image_url(comic_id, fname))
    return urls

# ------------------- 官方必须实现的接口 -------------------

@app.route('/config', methods=['GET'])
def config():
    """返回漫画源配置"""
    return jsonify({
        "sourceKey": "SRYP",               # 唯一标识
        "name": "我的自用源",
        "apiUrl": "https://sryp.vercel.app",  # 部署后替换
        "detailPath": "/detail/{{id}}",
        "photoPath": "/photo/{{id}}/{{chapter}}",
        "searchPath": "/search/{{keyword}}/{{page}}"
    })

@app.route('/detail/<comic_id>', methods=['GET'])
def detail(comic_id):
    """获取漫画详情"""
    meta = load_comic_meta(comic_id)
    if not meta:
        return jsonify({"code": 404, "message": "漫画不存在"}), 404

    # 构造详情返回（字段名必须与官方一致）
    return jsonify({
        "item_id": comic_id,
        "name": meta['name'],
        "cover": get_image_url(comic_id, meta['cover']),
        "page_count": meta['page_count'],
        "total_chapters": len(meta.get('chapters', [])),
        "tags": meta.get('tags', [])
    })

@app.route('/search/<keyword>/<int:page>', methods=['GET'])
def search(keyword, page):
    """搜索漫画（支持分页）"""
    results = []
    # 遍历所有漫画文件夹
    for comic_id in os.listdir(COMICS_ROOT):
        meta_path = os.path.join(COMICS_ROOT, comic_id, 'head.json')
        if not os.path.isfile(meta_path):
            continue
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        # 匹配搜索名（不区分大小写）
        if keyword.lower() in meta.get('searchName', '').lower():
            results.append({
                "comic_id": comic_id,
                "title": meta['name'],
                "cover_url": get_image_url(comic_id, meta['cover'])
            })
    # 简单分页（每页20条，这里自用只返回全部）
    # 若需要分页，根据 page 切片，并返回 has_more
    return jsonify({
        "page": page,
        "has_more": False,   # 自用不翻页
        "results": results
    })

@app.route('/photo/<comic_id>/<int:chapter>', methods=['GET'])
def photo(comic_id, chapter):
    """获取某章节的所有图片 URL"""
    urls = get_chapter_images(comic_id, chapter)
    if urls is None:
        return jsonify({"code": 404, "message": "章节不存在"}), 404
    # 获取章节名称（可选）
    meta = load_comic_meta(comic_id)
    chapter_name = meta['chapters'][chapter]['name'] if meta else f"第{chapter+1}话"
    return jsonify({
        "title": chapter_name,
        "images": [{"url": url} for url in urls]
    })

# ------------------- 静态文件托管（Vercel 推荐用路由，这里仅用于本地测试） -------------------
@app.route('/comics/<path:filename>')
def serve_comics(filename):
    """在本地开发时提供漫画图片访问（Vercel 会通过配置直接托管，此路由可省略）"""
    return send_from_directory(COMICS_ROOT, filename)

# 本地调试入口
if __name__ == '__main__':
    app.run(debug=True, port=5000)