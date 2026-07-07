@app.route('/detail/<comic_id>', methods=['GET'])
def detail(comic_id):
    meta = load_comic_meta(comic_id)
    if not meta:
        return jsonify({"code": 404, "message": "漫画不存在"}), 404
    # 构建绝对封面 URL
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
    urls = get_chapter_images(comic_id, chapter)  # 这个函数内部生成相对路径，需要改
    if urls is None:
        return jsonify({"code": 404, "message": "章节不存在"}), 404
    # 将相对路径转换为绝对路径
    abs_urls = [request.url_root + url.lstrip('/') for url in urls]
    meta = load_comic_meta(comic_id)
    chapter_name = meta['chapters'][chapter]['name'] if meta else f"第{chapter+1}话"
    return jsonify({
        "title": chapter_name,
        "images": [{"url": url} for url in abs_urls]
    })