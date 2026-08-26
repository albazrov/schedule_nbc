import argparse
import datetime
import json
import os
import openpyxl
from PIL import Image, ImageDraw, ImageFont

# t1

def load_config(script_dir):
    config_path = os.path.join(script_dir, "config.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Файл конфигурации не найден по пути: {config_path}"
        )
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Генератор расписаний с синхронным масштабированием холста и текста."
    )
    parser.add_argument(
        "-t", "--template", type=str, help="Имя файла изображения-шаблона"
    )
    parser.add_argument(
        "-d",
        "--data",
        type=str,
        help="Имя файла данных (.xlsx или .txt)",
    )
    parser.add_argument(
        "-o", "--output", type=str, help="Имя итогового изображения"
    )
    parser.add_argument(
        "-s",
        "--scale",
        type=float,
        help="Коэффициент изменения размера итогового файла (например, 0.5 для FullHD из 4K шаблона)",
    )

    return parser.parse_args()


def read_data_file(data_path, months_ru):
    rows_data = []
    _, ext = os.path.splitext(data_path.lower())

    if ext == ".xlsx":
        wb = openpyxl.load_workbook(data_path, data_only=True)
        sheet = wb.active
        for row in sheet.iter_rows(min_row=2, max_row=7, values_only=True):
            date_val, event_val = row
            if date_val is None and event_val is None:
                continue

            date_str = ""
            if date_val is not None:
                if isinstance(date_val, (datetime.datetime, datetime.date)):
                    day = date_val.day
                    month_num = date_val.month
                    month_name = months_ru.get(month_num, "")
                    date_str = f"{day:02d} {month_name}"
                else:
                    date_str = str(date_val).strip()

            event_str = (
                str(event_val).strip() if event_val is not None else None
            )
            rows_data.append({"date_str": date_str, "event_val": event_str})

    elif ext == ".txt":
        with open(data_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or "|" not in line:
                    continue

                parts = line.split("|", 1)
                date_val = parts[0].strip()
                event_val = parts[1].strip()

                if not date_val and not event_val:
                    continue

                date_str = date_val if date_val else ""
                event_str = event_val if event_val else None
                rows_data.append({"date_str": date_str, "event_val": event_str})
    else:
        raise ValueError(f"Неподдерживаемый формат файла: {ext}")

    return rows_data


def generate_exact_schedule_fixed():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    config = load_config(script_dir)
    args = parse_arguments()

    template_name = args.template or config["files"]["template_name"]
    data_name = (
        args.data
        or config["files"].get("data_name")
        or config["files"]["excel_name"]
    )
    output_name = args.output or config["files"]["output_name"]

    template_path = os.path.join(script_dir, template_name)
    data_path = os.path.join(script_dir, data_name)
    output_path = os.path.join(script_dir, output_name)

    if not os.path.exists(template_path):
        raise FileNotFoundError(f"\n[!] Шаблон не найден: {template_path}\n")

    # 1. Открываем оригинальный качественный шаблон
    base_image = Image.open(template_path).convert("RGBA")

    # 2. ИСПРАВЛЕНИЕ АРТЕФАКТА: Родной масштаб картинки равен 2.0 (так как выгружен @2x относительно 1920 CSS)
    native_scale = base_image.width / config["figma_css"]["base_width"]

    # 3. Применяем пользовательский масштаб (из ключа -s или force_scale), если он задан
    user_scale = args.scale
    if user_scale is None and config["settings"]["force_scale"] is not None:
        user_scale = float(config["settings"]["force_scale"])

    if user_scale is not None:
        # Рассчитываем новые размеры для картинки на основе пользовательского масштаба
        new_width = int(config["figma_css"]["base_width"] * user_scale)
        new_height = int(
            (base_image.height / base_image.width) * new_width
        )  # сохраняем пропорции

        # Синхронно изменяем размер самой фоновой картинки сглаживающим фильтром Lanczos
        image = base_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        scale = user_scale
        print(f"Картинка и текст синхронно масштабированы к: x{scale} ({new_width}x{new_height}px)")
    else:
        # Если ключ -s не задан, картинка остается в оригинальном 4K качестве, масштаб = native_scale (2.0)
        image = base_image
        scale = native_scale
        print(f"Картинка сохранена в оригинальном качестве. Масштаб текста: x{scale}")

    draw = ImageDraw.Draw(image)

    months_ru = {
        1: "января", 2: "февраля", 3: "марта", 4: "апреля",
        5: "мая", 6: "июня", 7: "июля", 8: "августа",
        9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
    }

    # === НАСТРОЙКА ШРИФТОВ ===
    font_file_regular = os.path.join(script_dir, config["files"]["font_regular"])
    font_file_italic = os.path.join(script_dir, config["files"]["font_italic"])

    target_date_size = int(config["figma_css"]["font_date_size"] * scale)
    target_event_size = int(config["figma_css"]["font_event_size"] * scale)

    try:
        font_date = ImageFont.truetype(font_file_regular, target_date_size)
        font_event = ImageFont.truetype(font_file_italic, target_event_size)
    except IOError:
        print("ВНИМАНИЕ: Файлы шрифтов не найдены! Включена защита.")
        font_date = ImageFont.load_default(size=target_date_size)
        font_event = ImageFont.load_default(size=target_event_size)

    color_date = (0, 0, 0, 204)
    color_event = (0, 0, 0, 255)

    css = config["figma_css"]
    start_x_date = int(css["container_left"] * scale)
    start_y = int(css["container_top"] * scale)
    row_height = int(css["row_height"] * scale)
    dynamic_gap = int(50 * scale)

    if not os.path.exists(data_path):
        raise FileNotFoundError(f"\n[!] Файл данных не найден: {data_path}\n")

    rows_data = read_data_file(data_path, months_ru)

    # === ПЕРВЫЙ ПРОХОД — СБОР МАКСИМАЛЬНОЙ ШИРИНЫ ДАТЫ ===
    max_date_width = 0
    for data in rows_data:
        if data["date_str"]:
            current_width = draw.textlength(data["date_str"], font=font_date)
            if current_width > max_date_width:
                max_date_width = current_width

    if max_date_width == 0:
        exact_x_event = start_x_date + int(css["event_column_offset"] * scale)
    else:
        exact_x_event = start_x_date + int(max_date_width) + dynamic_gap

    # === ВТОРОЙ ПРОХОД — НАЛОЖЕНИЕ СТРОК ===
    for i, data in enumerate(rows_data):
        current_y = start_y + (i * row_height)

        if data["date_str"]:
            draw.text((start_x_date, current_y), data["date_str"], fill=color_date, font=font_date)

        if data["event_val"] is not None:
            draw.text((exact_x_event, current_y), str(data["event_val"]), fill=color_event, font=font_event)

    # Сохраняем итоговый результат
    final_image = Image.alpha_composite(Image.new("RGBA", image.size, (0, 0, 0, 0)), image).convert("RGB")
    final_image.save(output_path, "PNG")
    print(f"Результат успешно сохранен: {output_path}")


if __name__ == "__main__":
    generate_exact_schedule_fixed()
# Final CI/CD verify
