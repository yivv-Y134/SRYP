import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 漫画数据根目录（直接放在项目根目录下的 comics 文件夹）
COMICS_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'comics')


def load_comic_meta(comic_id):
    """读取漫画的 head.json"""
    path = os.path.join(COMICS_ROOT, comic_id, 'head.json')
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_image_url(comic_id, filename):
    """生成图片的访问 URL（通过 API 代理）"""
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
    if not os.path.exists(COMICS_ROOT):
        return jsonify({"page": page, "has_more": False, "results": []})
    
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
    # 自用不翻页，直接返回全部
    return jsonify({
        "page": page,
        "has_more": False,
        "results": results
    })


@app.route('/photo/<comic_id>/<int:chapter>', methods=['GET'])
def photo(comic_id, chapter):
    """获取某章节的所有图片 URL"""
    urls = get_chapter_images(comic_id, chapter)
    if urls is None:
        return jsonify({"code": 404, "message": "章节不存在"}), 404
    meta = load_comic_meta(comic_id)
    chapter_name = meta['chapters'][chapter]['name'] if meta else f"第{chapter+1}话"
    return jsonify({
        "title": chapter_name,
        "images": [{"url": url} for url in urls]
    })


# ------------------- 图片代理路由（Vercel 无静态托管） -------------------
@app.route('/comics/<comic_id>/<filename>')
def serve_comic_image(comic_id, filename):
    """通过 API 返回漫画图片文件"""
    safe_dir = os.path.join(COMICS_ROOT, comic_id)
    if not os.path.exists(safe_dir):
        return jsonify({"code": 404, "message": "漫画不存在"}), 404
    return send_from_directory(safe_dir, filename)


# ------------------- 本地调试入口 -------------------
if __name__ == '__main__':
    app.run(debug=True, port=5000)