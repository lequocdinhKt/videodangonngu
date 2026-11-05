"""Generate four original, programmatic demo clips and multilingual SRT files."""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "demo_assets"
SIZE = (960, 540)
FPS = 12
DURATION_SECONDS = 10

DEMOS = [
    {
        "slug": "hoi-an",
        "accent": "#f59e0b",
        "translations": {
            "vi-VN": {"title": "Đèn lồng Hội An", "description": "Một lát cắt ngắn về phố cổ và sắc đèn bên sông Hoài."},
            "en-US": {"title": "Lanterns of Hoi An", "description": "A short glimpse of the ancient town and lanterns by the Hoai River."},
            "ru-RU": {"title": "Фонари Хойана", "description": "Короткий рассказ о древнем городе и фонарях у реки Хоай."},
            "zh-CN": {"title": "会安灯笼", "description": "一段关于古城与怀河畔灯笼的短片。"},
        },
        "subtitles": {
            "vi-VN": ["Hội An lưu giữ nhịp sống chậm giữa lòng phố cổ.", "Những mái nhà vàng soi bóng xuống dòng sông Hoài.", "Khi chiều buông, hàng nghìn chiếc đèn lồng cùng tỏa sáng.", "Đây là dữ liệu minh họa do dự án tự tạo."],
            "en-US": ["Hoi An preserves a slower rhythm in its ancient streets.", "Yellow houses are reflected in the Hoai River.", "At dusk, thousands of lanterns begin to glow.", "This is original demonstration content created for the project."],
            "ru-RU": ["Хойан хранит неспешный ритм древних улиц.", "Жёлтые дома отражаются в реке Хоай.", "С наступлением сумерек зажигаются тысячи фонарей.", "Это оригинальный демонстрационный материал проекта."],
            "zh-CN": ["会安古街保留着舒缓的生活节奏。", "黄色的老屋倒映在怀河水面。", "黄昏时，成千上万盏灯笼渐次亮起。", "这是本项目自行创作的演示内容。"],
        },
    },
    {
        "slug": "ha-long",
        "accent": "#0891b2",
        "translations": {
            "vi-VN": {"title": "Sớm mai trên vịnh Hạ Long", "description": "Mặt nước xanh và những đảo đá vôi trong buổi sớm yên tĩnh."},
            "en-US": {"title": "Morning on Ha Long Bay", "description": "Blue water and limestone islands in a quiet morning."},
            "ru-RU": {"title": "Утро в бухте Халонг", "description": "Голубая вода и известняковые острова тихим утром."},
            "zh-CN": {"title": "下龙湾的清晨", "description": "宁静清晨里的碧水与石灰岩岛屿。"},
        },
        "subtitles": {
            "vi-VN": ["Vịnh Hạ Long mở ra với hàng nghìn đảo đá vôi.", "Mỗi khối đá mang một hình dáng riêng qua thời gian.", "Thuyền nhỏ lướt chậm trên mặt nước xanh yên ả.", "Đây là dữ liệu minh họa do dự án tự tạo."],
            "en-US": ["Ha Long Bay opens onto thousands of limestone islands.", "Time has shaped every rock into a distinct form.", "Small boats glide slowly across the calm blue water.", "This is original demonstration content created for the project."],
            "ru-RU": ["Бухта Халонг насчитывает тысячи известняковых островов.", "Время придало каждой скале неповторимую форму.", "Лодки медленно скользят по спокойной голубой воде.", "Это оригинальный демонстрационный материал проекта."],
            "zh-CN": ["下龙湾分布着数千座石灰岩岛屿。", "岁月赋予每块岩石独特的形态。", "小船缓缓划过宁静的碧蓝水面。", "这是本项目自行创作的演示内容。"],
        },
    },
    {
        "slug": "ca-phe",
        "accent": "#92400e",
        "translations": {
            "vi-VN": {"title": "Một ly cà phê Việt", "description": "Câu chuyện nhỏ về phin cà phê và khoảng lặng buổi sáng."},
            "en-US": {"title": "A Cup of Vietnamese Coffee", "description": "A small story about the coffee filter and a quiet morning pause."},
            "ru-RU": {"title": "Чашка вьетнамского кофе", "description": "Небольшая история о кофейном фильтре и тихой утренней паузе."},
            "zh-CN": {"title": "一杯越南咖啡", "description": "关于滴漏咖啡与清晨片刻宁静的小故事。"},
        },
        "subtitles": {
            "vi-VN": ["Cà phê phin cần một chút thời gian để nhỏ xuống.", "Hương thơm đậm mở đầu cho nhiều buổi sáng ở Việt Nam.", "Một chiếc ghế nhỏ cũng đủ tạo nên góc chuyện trò thân quen.", "Đây là dữ liệu minh họa do dự án tự tạo."],
            "en-US": ["Filter coffee needs a little time to drip.", "Its rich aroma begins many mornings in Vietnam.", "A small chair is enough to create a familiar place for conversation.", "This is original demonstration content created for the project."],
            "ru-RU": ["Кофе через фин медленно капает в чашку.", "Его насыщенный аромат начинает многие утра во Вьетнаме.", "Небольшого стула достаточно для привычной беседы.", "Это оригинальный демонстрационный материал проекта."],
            "zh-CN": ["滴漏咖啡需要一点时间慢慢落入杯中。", "浓郁的香气开启许多越南人的早晨。", "一张小椅子就能成为熟悉的聊天角落。", "这是本项目自行创作的演示内容。"],
        },
    },
    {
        "slug": "cho-noi",
        "accent": "#ea580c",
        "translations": {
            "vi-VN": {"title": "Nhịp chợ nổi miền Tây", "description": "Thuyền hàng, trái cây và ánh bình minh trên miền sông nước."},
            "en-US": {"title": "Rhythm of the Floating Market", "description": "Trading boats, fruit and sunrise across the Mekong waterways."},
            "ru-RU": {"title": "Ритм плавучего рынка", "description": "Торговые лодки, фрукты и рассвет в дельте Меконга."},
            "zh-CN": {"title": "水上市场的节奏", "description": "湄公河水乡的商船、水果与日出。"},
        },
        "subtitles": {
            "vi-VN": ["Chợ nổi bắt đầu khi mặt trời vừa lên trên sông.", "Nông sản được chuyển từ thuyền này sang thuyền khác.", "Cây bẹo giúp người mua nhận ra món hàng từ xa.", "Đây là dữ liệu minh họa do dự án tự tạo."],
            "en-US": ["The floating market begins as the sun rises over the river.", "Produce moves from one boat to another.", "Tall display poles help buyers recognize goods from afar.", "This is original demonstration content created for the project."],
            "ru-RU": ["Плавучий рынок оживает с восходом солнца над рекой.", "Продукты переходят с одной лодки на другую.", "Высокие шесты помогают издалека увидеть товар.", "Это оригинальный демонстрационный материал проекта."],
            "zh-CN": ["太阳升起时，水上市场开始热闹起来。", "农产品从一艘船转运到另一艘船。", "高高的货杆让买家从远处就能看见商品。", "这是本项目自行创作的演示内容。"],
        },
    },
]


def font(size: int, bold: bool = False):
    names = ["arialbd.ttf" if bold else "arial.ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for name in names:
        for base in (Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu")):
            path = base / name
            if path.exists():
                return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def background(draw: ImageDraw.ImageDraw, top: tuple[int, int, int], bottom: tuple[int, int, int]):
    for y in range(SIZE[1]):
        ratio = y / SIZE[1]
        color = tuple(round(a * (1 - ratio) + b * ratio) for a, b in zip(top, bottom))
        draw.line((0, y, SIZE[0], y), fill=color)


def draw_scene(index: int, frame: int) -> Image.Image:
    image = Image.new("RGB", SIZE)
    draw = ImageDraw.Draw(image)
    t = frame / FPS
    drift = math.sin(t * 1.1)
    if index == 0:
        background(draw, (255, 236, 188), (242, 168, 86))
        draw.rectangle((0, 315, 960, 540), fill=(23, 94, 111))
        for x in range(-60, 1020, 130):
            draw.rectangle((x, 210, x + 115, 360), fill=(247, 190, 67), outline=(122, 72, 37), width=4)
            draw.polygon((x - 8, 210, x + 57, 155, x + 123, 210), fill=(111, 54, 35))
        for n in range(8):
            x = 80 + n * 116
            y = 70 + 12 * math.sin(t + n)
            draw.line((x, 0, x, y - 23), fill=(79, 42, 29), width=3)
            draw.ellipse((x - 22, y - 22, x + 22, y + 25), fill=(238, 74 + n * 8, 52), outline=(255, 237, 172), width=4)
    elif index == 1:
        background(draw, (188, 232, 244), (111, 191, 211))
        draw.ellipse((730, 65, 830, 165), fill=(255, 240, 172))
        draw.rectangle((0, 295, 960, 540), fill=(49, 153, 177))
        for x, height in ((80, 220), (245, 165), (530, 240), (760, 185)):
            draw.polygon((x - 95, 320, x - 55, 220, x, 320 - height, x + 50, 235, x + 100, 320), fill=(41, 105, 91))
        boat_x = 260 + t * 34
        draw.polygon((boat_x, 405, boat_x + 150, 405, boat_x + 120, 438, boat_x + 25, 438), fill=(107, 57, 38))
        draw.polygon((boat_x + 72, 400, boat_x + 72, 305, boat_x + 130, 390), fill=(248, 244, 224))
    elif index == 2:
        background(draw, (251, 235, 204), (208, 158, 102))
        draw.rectangle((0, 370, 960, 540), fill=(113, 71, 46))
        draw.ellipse((320, 285, 640, 415), fill=(238, 221, 188), outline=(103, 62, 39), width=8)
        draw.rectangle((405, 220, 555, 360), fill=(121, 72, 42), outline=(67, 39, 28), width=7)
        draw.rectangle((425, 150, 535, 250), fill=(177, 171, 151), outline=(78, 72, 63), width=7)
        for n in range(7):
            y = 240 + n * 14 + (frame % 14)
            draw.ellipse((475 + 8 * math.sin(t + n), y, 483 + 8 * math.sin(t + n), y + 10), fill=(77, 45, 27))
        for n in range(3):
            x = 450 + n * 30 + drift * 7
            draw.arc((x, 90 - n * 8, x + 55, 195), 190, 330, fill=(255, 255, 255), width=5)
    else:
        background(draw, (255, 211, 143), (244, 136, 89))
        draw.ellipse((690, 68, 820, 198), fill=(255, 236, 166))
        draw.rectangle((0, 285, 960, 540), fill=(45, 132, 154))
        for n, x in enumerate((120, 380, 650)):
            offset = 18 * math.sin(t * .8 + n)
            draw.polygon((x + offset, 370, x + 210 + offset, 370, x + 170 + offset, 435, x + 35 + offset, 435), fill=(104, 55, 34))
            for fruit in range(12):
                fx = x + 45 + (fruit % 6) * 25 + offset
                fy = 350 - (fruit // 6) * 24
                draw.ellipse((fx, fy, fx + 23, fy + 23), fill=(246, 155 + (fruit % 2) * 50, 42))
            draw.line((x + 150 + offset, 365, x + 150 + offset, 170), fill=(77, 47, 30), width=6)
    return image


def overlay_title(image: Image.Image, title: str, frame: int):
    draw = ImageDraw.Draw(image, "RGBA")
    alpha = min(210, frame * 12)
    draw.rounded_rectangle((48, 390, 720, 500), radius=22, fill=(15, 32, 60, alpha))
    draw.text((78, 414), title, font=font(38, True), fill=(255, 255, 255, alpha))
    draw.text((80, 463), "VIDEO GUIDE · DEMO TỰ TẠO", font=font(16, True), fill=(202, 223, 255, alpha))


def write_srt(path: Path, lines: list[str]):
    windows = ((0, 2200), (2300, 4700), (4800, 7200), (7300, 9700))
    def stamp(ms: int):
        return f"00:00:{ms // 1000:02d},{ms % 1000:03d}"
    blocks = [f"{i}\n{stamp(start)} --> {stamp(end)}\n{text}" for i, ((start, end), text) in enumerate(zip(windows, lines), 1)]
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def write_vtt(path: Path, lines: list[str]):
    windows = ((0, 2200), (2300, 4700), (4800, 7200), (7300, 9700))
    def stamp(ms: int):
        return f"00:00:{ms // 1000:02d}.{ms % 1000:03d}"
    blocks = [f"{i}\n{stamp(start)} --> {stamp(end)}\n{text}" for i, ((start, end), text) in enumerate(zip(windows, lines), 1)]
    path.write_text("WEBVTT\n\n" + "\n\n".join(blocks) + "\n", encoding="utf-8")


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for index, demo in enumerate(DEMOS):
        folder = OUTPUT / demo["slug"]
        folder.mkdir(parents=True, exist_ok=True)
        video_path = folder / "original.mp4"
        preview_video_path = folder / "preview.webm"
        writer = imageio_ffmpeg.write_frames(
            video_path,
            SIZE,
            fps=FPS,
            codec="libx264",
            quality=7,
            macro_block_size=2,
            output_params=["-movflags", "+faststart"],
        )
        writer.send(None)
        preview_writer = imageio_ffmpeg.write_frames(
            preview_video_path,
            SIZE,
            fps=FPS,
            codec="libvpx-vp9",
            quality=8,
            macro_block_size=2,
        )
        preview_writer.send(None)
        thumbnail = None
        for frame_number in range(FPS * DURATION_SECONDS):
            frame = draw_scene(index, frame_number)
            overlay_title(frame, demo["translations"]["vi-VN"]["title"], frame_number)
            if frame_number == FPS * 3:
                thumbnail = frame.copy()
            writer.send(frame.tobytes())
            preview_writer.send(frame.tobytes())
        writer.close()
        preview_writer.close()
        (thumbnail or draw_scene(index, 0)).save(folder / "thumbnail.webp", "WEBP", quality=88)
        for code, lines in demo["subtitles"].items():
            write_srt(folder / f"{code.split('-')[0]}.srt", lines)
            write_vtt(folder / f"{code.split('-')[0]}.vtt", lines)
        manifest.append({
            "slug": demo["slug"],
            "video": str(video_path.relative_to(OUTPUT)).replace("\\", "/"),
            "preview_video": str(preview_video_path.relative_to(OUTPUT)).replace("\\", "/"),
            "thumbnail": f"{demo['slug']}/thumbnail.webp",
            "subtitles": {code: f"{demo['slug']}/{code.split('-')[0]}.vtt" for code in demo["subtitles"]},
            "srt_subtitles": {code: f"{demo['slug']}/{code.split('-')[0]}.srt" for code in demo["subtitles"]},
            "translations": [{"language_code": code, **copy} for code, copy in demo["translations"].items()],
        })
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    public_demo = ROOT / "frontend" / "public" / "demo"
    if public_demo.exists():
        shutil.rmtree(public_demo)
    shutil.copytree(OUTPUT, public_demo)
    print(f"Generated {len(manifest)} original demo videos in {OUTPUT}")


if __name__ == "__main__":
    main()
