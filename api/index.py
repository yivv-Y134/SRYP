import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

COMICS_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'comics')


def load_comic_meta(comic_id):
    path = os.path.join(COMICS_ROOT, comic_id, 'head.json')
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_chapter_images(comic_id, chapter_index):
    """
    根据章节索引（0-based）返回该章节所有图片的【相对路径】列表
    使用 start/end 起止页码
    """
    meta = load_comic_meta(comic_id)
    if not meta:
        return None
    chapters = meta.get('chapters', [])
    if chapter_index < 0 or chapter_index >= len(chapters):
        return None
    chapter = chapters[chapter_index]
    start = chapter.get('start')
    end = chapter.get('end')
    if start is None or end is None:
        return None
    urls = []
    for p in range(start, end + 1):
        fname = f"{p:05d}.jpeg"
        urls.append(f"/comics/{comic_id}/{fname}")
    return urls


@app.route('/config', methods=['GET'])
def config():
    api_url = request.host_url.rstrip('/')
    return jsonify({
        "SRYP": {
            "name": "我的自用源",
            "apiUrl": api_url,
            "detailPath": "/album/<id>",
            "photoPath": "/photo/<id>/chapter/<chapter>",
            "searchPath": "/search/<text>/<page>"
        }
    })


@app.route('/album/<item_id>', methods=['GET'])
def album(item_id):
    meta = load_comic_meta(item_id)
    if not meta:
        return jsonify({"code": 404, "message": "漫画不存在"}), 404
    api_url = request.host_url.rstrip('/')
    cover_url = f"{api_url}/comics/{item_id}/{meta['cover']}"

    chapters = meta.get('chapters', [])
    # 计算总页数（基于所有章节的起止）
    total_pages = sum(ch.get('end', 0) - ch.get('start', 0) + 1 for ch in chapters if 'start' in ch and 'end' in ch)

    return jsonify({
        "item_id": item_id,
        "name": meta['name'],
        "cover": cover_url,
        "page_count": total_pages,
        "total_chapters": len(chapters),
        "tags": meta.get('tags', [])
    })


@app.route('/search/<text>/<int:page>', methods=['GET'])
def search(text, page):
    results = []
    if not os.path.exists(COMICS_ROOT):
        return jsonify({"page": page, "has_more": False, "results": []})
    api_url = request.host_url.rstrip('/')
    for comic_id in os.listdir(COMICS_ROOT):
        meta_path = os.path.join(COMICS_ROOT, comic_id, 'head.json')
        if not os.path.isfile(meta_path):
            continue
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        if text.lower() in meta.get('searchName', '').lower():
            cover_url = f"{api_url}/comics/{comic_id}/{meta['cover']}"
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


@app.route('/photo/<item_id>/chapter/<int:chapter>', methods=['GET'])
def photo_list(item_id, chapter):
    """
    手表传递的 chapter 是从 1 开始计数的（即第1话、第2话...）
    后端数组索引从 0 开始，所以需要 chapter - 1
    """
    chapter_index = chapter - 1
    if chapter_index < 0:
        return jsonify({"code": 404, "message": "章节索引无效"}), 404

    meta = load_comic_meta(item_id)
    if not meta:
        return jsonify({"code": 404, "message": "漫画不存在"}), 404
    total_chapters = len(meta.get('chapters', []))
    if chapter_index >= total_chapters:
        return jsonify({"code": 404, "message": "章节不存在"}), 404

    relative_urls = get_chapter_images(item_id, chapter_index)
    if relative_urls is None:
        return jsonify({"code": 404, "message": "章节数据错误"}), 404

    api_url = request.host_url.rstrip('/')
    absolute_urls = [f"{api_url}{url}" for url in relative_urls]
    chapters = meta.get('chapters', [])
    chapter_name = chapters[chapter_index]['name'] if chapter_index < len(chapters) else f"第{chapter}话"
    return jsonify({
        "title": chapter_name,
        "images": [{"url": url} for url in absolute_urls]
    })


@app.route('/comics/<comic_id>/<filename>')
def serve_comic_image(comic_id, filename):
    safe_dir = os.path.join(COMICS_ROOT, comic_id)
    if not os.path.exists(safe_dir):
        return jsonify({"code": 404, "message": "漫画不存在"}), 404
    return send_from_directory(safe_dir, filename)


if __name__ == '__main__':
    app.run(debug=True, port=5000)