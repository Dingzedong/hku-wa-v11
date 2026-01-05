import json, math, csv
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"

TILE = 32
MAX_SHEET_WIDTH_PX = 3072  # 3072x? 通常能把高度控制在 4096 内

SRC_TSJ = PUBLIC / "tilesets" / "hku_objects.tsj"   # 你现在的 image-collection tileset
OBJ_DIR = PUBLIC / "objects"

OUT_PNG = PUBLIC / "tilesets" / "hku_objects_sheet.png"
OUT_TSJ = PUBLIC / "tilesets" / "hku_objects_sheet.tsj"
OUT_CSV = PUBLIC / "tilesets" / "hku_objects_sheet_index.csv"
OUT_CATALOG = PUBLIC / "maps" / "hku_objects_catalog.tmj"

def ceil_to_tile(n: int) -> int:
    return int(math.ceil(n / TILE) * TILE)

def main():
    if not SRC_TSJ.exists():
        raise SystemExit(f"Missing: {SRC_TSJ}")

    ts = json.loads(SRC_TSJ.read_text(encoding="utf-8"))

    # 只打包 tileset 里真正引用到的那些 png（避免 objects 文件夹里杂图干扰）
    image_files = []
    for t in ts.get("tiles", []):
        img_rel = t.get("image")
        if not img_rel:
            continue
        img_path = (SRC_TSJ.parent / img_rel).resolve()
        if not img_path.exists():
            raise SystemExit(f"Missing object image referenced by tsj: {img_path}")
        image_files.append(img_path)

    if not image_files:
        raise SystemExit("No images found in hku_objects.tsj")

    # 打包到一张大图（每张图先 padding 到 32 的倍数）
    max_w = (MAX_SHEET_WIDTH_PX // TILE) * TILE
    x = y = 0
    row_h = 0
    placements = []

    for img_path in image_files:
        im = Image.open(img_path).convert("RGBA")
        w, h = im.size
        wp, hp = ceil_to_tile(w), ceil_to_tile(h)

        if x + wp > max_w:
            x = 0
            y += row_h
            row_h = 0

        placements.append({
            "name": img_path.name,
            "path": img_path,
            "x_px": x,
            "y_px": y,
            "w_px": wp,
            "h_px": hp,
            "orig_w": w,
            "orig_h": h,
        })

        x += wp
        row_h = max(row_h, hp)

    sheet_w = max_w
    sheet_h = ceil_to_tile(y + row_h)

    sheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))
    for p in placements:
        im = Image.open(p["path"]).convert("RGBA")
        sheet.paste(im, (p["x_px"], p["y_px"]))

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT_PNG)

    # 生成 tileset（标准 spritesheet tileset，WA 可读）
    columns = sheet_w // TILE
    rows = sheet_h // TILE
    tilecount = columns * rows

    tsj = {
        "type": "tileset",
        "name": "hku_objects_sheet",
        "tilewidth": TILE,
        "tileheight": TILE,
        "spacing": 0,
        "margin": 0,
        "columns": columns,
        "tilecount": tilecount,
        "image": "hku_objects_sheet.png",
        "imagewidth": sheet_w,
        "imageheight": sheet_h,
    }
    OUT_TSJ.write_text(json.dumps(tsj, ensure_ascii=False, indent=2), encoding="utf-8")

    # 输出索引，方便你知道每个对象在 catalog / sheet 哪一块
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "x_tile", "y_tile", "w_tiles", "h_tiles", "orig_w", "orig_h"])
        for p in placements:
            w.writerow([
                p["name"],
                p["x_px"] // TILE,
                p["y_px"] // TILE,
                p["w_px"] // TILE,
                p["h_px"] // TILE,
                p["orig_w"],
                p["orig_h"],
            ])

    # 生成 catalog 地图：把每个对象“整块”铺出来（方便你在 Tiled 里框选复制）
    # catalog 采用固定宽度（tile）
    cat_w = 120  # tiles
    cat_x = 0
    cat_y = 0
    cat_row_h = 0

    # 初始化空图层
    data = [0] * (cat_w * 2000)  # 先给大一点，最后再裁剪

    def set_gid(tx, ty, gid):
        idx = ty * cat_w + tx
        data[idx] = gid

    # tileset 里 tileIndex = (y*columns + x), gid = firstgid(1)+tileIndex
    for p in placements:
        w_tiles = p["w_px"] // TILE
        h_tiles = p["h_px"] // TILE

        if cat_x + w_tiles > cat_w:
            cat_x = 0
            cat_y += cat_row_h + 1
            cat_row_h = 0

        src_x0 = p["x_px"] // TILE
        src_y0 = p["y_px"] // TILE

        for dy in range(h_tiles):
            for dx in range(w_tiles):
                tile_index = (src_y0 + dy) * columns + (src_x0 + dx)
                gid = 1 + tile_index
                set_gid(cat_x + dx, cat_y + dy, gid)

        cat_x += w_tiles + 1
        cat_row_h = max(cat_row_h, h_tiles)

    used_h = ceil_to_tile((cat_y + cat_row_h + 2) * TILE) // TILE
    used_h = max(used_h, 1)

    data = data[:cat_w * used_h]

    catalog = {
        "type": "map",
        "version": "1.10",
        "tiledversion": "1.10.2",
        "orientation": "orthogonal",
        "renderorder": "right-down",
        "infinite": False,
        "tilewidth": TILE,
        "tileheight": TILE,
        "width": cat_w,
        "height": used_h,
        "layers": [
            {
                "type": "tilelayer",
                "name": "catalog",
                "width": cat_w,
                "height": used_h,
                "opacity": 1,
                "visible": True,
                "data": data,
            }
        ],
        "tilesets": [
            {"firstgid": 1, "source": "../tilesets/hku_objects_sheet.tsj"}
        ]
    }

    OUT_CATALOG.parent.mkdir(parents=True, exist_ok=True)
    OUT_CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    print("✅ Generated:")
    print(" -", OUT_PNG)
    print(" -", OUT_TSJ)
    print(" -", OUT_CSV)
    print(" -", OUT_CATALOG)

if __name__ == "__main__":
    main()

