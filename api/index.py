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
    """对应 detailPath: /album/<id>"""
    meta = load_comic_meta(item_id)
    if not meta:
        return jsonify({"code": 404, "message": "漫画不存在"}), 404
    api_url = request.host_url.rstrip('/')
    cover_url = f"{api_url}/comics/{item_id}/{meta['cover']}"
    return jsonify({
        "item_id": item_id,
        "name": meta['name'],
        "cover": cover_url,
        "page_count": meta['page_count'],
        "total_chapters": len(meta.get('chapters', [])),
        "tags": meta.get('tags', [])
    })


@app.route('/search/<text>/<int:page>', methods=['GET'])
def search(text, page):
    """对应 searchPath: /search/<text>/<page>"""
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
    """对应 photoPath: /photo/<id>/chapter/<chapter>"""
    relative_urls = get_chapter_images(item_id, chapter)
    if relative_urls is None:
        return jsonify({"code": 404, "message": "章节不存在"}), 404
    api_url = request.host_url.rstrip('/')
    absolute_urls = [f"{api_url}{url}" for url in relative_urls]  # relative_urls 以 / 开头
    meta = load_comic_meta(item_id)
    chapter_name = meta['chapters'][chapter]['name'] if meta else f"第{chapter+1}话"
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