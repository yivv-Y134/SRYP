import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
# 保持默认 JSON_AS_ASCII=True，确保所有非 ASCII 字符转义为 \uXXXX，兼容手环解析器
CORS(app)

COMICS_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'comics')


def load_comic_meta(comic_id):
    """读取漫画的 head.json"""
    path = os.path.join(COMICS_ROOT, comic_id, 'head.json')
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


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
        urls.append(f"/comics/{comic_id}/{fname}")
    return urls


@app.route('/config', methods=['GET'])
def config():
    """返回漫画源配置（使用中文，Flask 自动转为 \u 转义，手环可安全解析）"""
    return jsonify({
        "sourceKey": "SRYP",
        "name": "我的自用源",
        "apiUrl": "https://sryp.vercel.app",
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
    """搜索漫画（支持分页）"""
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

    absolute_urls = [request.url_root + url.lstrip('/') for url in relative_urls]
    meta = load_comic_meta(comic_id)
    chapter_name = meta['chapters'][chapter]['name'] if meta else f"第{chapter+1}话"
    return jsonify({
        "title": chapter_name,
        "images": [{"url": url} for url in absolute_urls]
    })


@app.route('/comics/<comic_id>/<filename>')
def serve_comic_image(comic_id, filename):
    """通过 API 返回漫画图片（代理路由）"""
    safe_dir = os.path.join(COMICS_ROOT, comic_id)
    if not os.path.exists(safe_dir):
        return jsonify({"code": 404, "message": "漫画不存在"}), 404
    return send_from_directory(safe_dir, filename)


if __name__ == '__main__':
    app.run(debug=True, port=5000)