import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# ========== 创建 Flask 应用 ==========
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False   # 保证中文日文正常显示
CORS(app)

# ========== 配置漫画根目录 ==========
# 漫画文件夹放在项目根目录下的 comics/ 中，与 api/ 同级
COMICS_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'comics')


def load_comic_meta(comic_id):
    """读取漫画的 head.json"""
    path = os.path.join(COMICS_ROOT, comic_id, 'head.json')
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_absolute_url(relative_path):
    """将相对路径转换为完整的 HTTPS URL"""
    # Vercel 环境下 request.url_root 会包含协议和域名
    # 但为了让 /config 等无请求上下文的地方也能用，我们在路由中直接使用 request.url_root
    # 这里保留为辅助函数，但实际在路由中拼接更安全
    return relative_path


def get_chapter_images(comic_id, chapter_index):
    """根据章节索引返回该章节所有图片的【相对路径】列表"""
    meta = load_comic_meta(comic_id)
    if not meta:
        return None
    chapters = meta.get('chapters', [])
    if chapter_index < 0 or chapter_index >= len(chapters):
        return None
    start_page = 1
    for i in range(chapter_index):
        start_page += chapters[i]['page_count']
    end_page = start_page + chapters[chapter_index]['page_count'] - 1
    urls = []
    for p in range(start_page, end_page + 1):
        fname = f"{p:05d}.jpeg"
        # 使用 /comics/{id}/{filename} 相对路径
        urls.append(f"/comics/{comic_id}/{fname}")
    return urls


# ==================== 必须实现的官方接口 ====================

@app.route('/config', methods=['GET'])
def config():
    """返回漫画源配置"""
    return jsonify({
        "sourceKey": "SRYP",
        "name": "我的自用源",
        "apiUrl": "https://sryp.vercel.app",   # 固定你的域名
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

    # 封面使用绝对路径
    cover_url = request.url_root + f"comics/{comic_id}/{meta['cover']}"
    return jsonify({
        "item_id": comic_id,
        "name": meta['name'],
        "cover": cover_url,
        "page_count": meta['page_count'],
        "total_chapters": len(meta.get('chapters', [])),
        "tags": meta.get('tags', [])
    })


@app.route('/search/<keyword>/<int:page>', methods=['GET'])
def search(keyword, page):
    """搜索漫画"""
    results = []
    if not os.path.exists(COMICS_ROOT):
        return jsonify({"page": page, "has_more": False, "results": []})

    for comic_id in os.listdir(COMICS_ROOT):
        meta_path = os.path.join(COMICS_ROOT, comic_id, 'head.json')
        if not os.path.isfile(meta_path):
            continue
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        if keyword.lower() in meta.get('searchName', '').lower():
            cover_url = request.url_root + f"comics/{comic_id}/{meta['cover']}"
            results.append({
                "comic_id": comic_id,
                "title": meta['name'],
                "cover_url": cover_url
            })
    return jsonify({
        "page": page,
        "has_more": False,
        "results": results
    })


@app.route('/photo/<comic_id>/<int:chapter>', methods=['GET'])
def photo(comic_id, chapter):
    """获取某章节的所有图片 URL（绝对路径）"""
    relative_urls = get_chapter_images(comic_id, chapter)
    if relative_urls is None:
        return jsonify({"code": 404, "message": "章节不存在"}), 404

    # 转换为绝对路径
    absolute_urls = [request.url_root + url.lstrip('/') for url in relative_urls]

    meta = load_comic_meta(comic_id)
    chapter_name = meta['chapters'][chapter]['name'] if meta else f"第{chapter+1}话"
    return jsonify({
        "title": chapter_name,
        "images": [{"url": url} for url in absolute_urls]
    })


# ==================== 图片代理路由（当静态托管不可用时备用） ====================
@app.route('/comics/<comic_id>/<filename>')
def serve_comic_image(comic_id, filename):
    """直接返回漫画图片（用于绝对路径的请求）"""
    safe_dir = os.path.join(COMICS_ROOT, comic_id)
    if not os.path.exists(safe_dir):
        return jsonify({"code": 404, "message": "漫画不存在"}), 404
    return send_from_directory(safe_dir, filename)


# ==================== 本地调试入口 ====================
if __name__ == '__main__':
    app.run(debug=True, port=5000)