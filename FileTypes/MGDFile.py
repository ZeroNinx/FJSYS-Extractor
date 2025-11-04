import io
import os
from typing import Optional

try:
    from PIL import Image, UnidentifiedImageError
except ImportError as exc:  # pragma: no cover
    raise ImportError("MGD image export requires the 'pillow' package. Install it via 'pip install pillow'.") from exc

from FileTypes.FileBase import FileBase
from ToolBox.ByteOperation import read_byte, read_int16, read_int32, read_string, extract_bytes_to_file

MGD_HEADER_SIZE = 96  # 文件头大小
MGD_RESOLUTION_X_OFFSET = 12  # 分辨率 X 偏移
MGD_RESOLUTION_Y_OFFSET = 14  # 分辨率 Y 偏移
MGD_BUFFER_SIZE_OFFSET = 16  # 缓冲区大小偏移
MGD_ASSET_MODE_OFFSET = 24  # 资产模式偏移
MGD_CONTENT_SIZE_OFFSET = 92  # 内容区域大小偏移
MGD_CONTENT_OFFSET = 96  # 内容区域起始偏移
MGD_TAIL_SIZE = 24  # 文件尾大小

SPRITE_INFO_OFFSET = 8  # 内容结束后第 9 个字节（基于 0 下标）
SPRITE_COUNT_SIZE = 2  # 精灵数量字段长度
SPRITE_ENTRY_OFFSET = 4  # 精灵表数据起始（从第 5 个字节算起）
SPRITE_ENTRY_SIZE = 8  # 每个精灵条目 4*int16


class MGDFile(FileBase):
    # MGD 资产解析器：负责读取头部公共字段并根据模式委托处理

    resolution_x = 0
    resolution_y = 0
    buffer_size = 0
    asset_mode = 0
    content_size = 0

    mode_handler = None

    def __init__(self, file_base: FileBase, *, debug_enabled=False):
        super().__init__(file_base.source_filepath, file_base.filename_offset, file_base.file_size, file_base.file_offset)
        self.set_filename(file_base.filename)
        self._content_type = "MGD"
        self.debug_enabled = debug_enabled
        self.sprite_count = 0
        self.sprites = []
        self.inner_header_size = 0
        self.inner_header = b""
        self.pixel_data_length = 0
        self.pixel_data_offset: Optional[int] = None
        self.parse_header()

    def parse_header(self):
        # 解析文件头，读取内容大小、分辨率、缓冲区和模式信息
        with open(self.source_filepath, 'rb') as source_file:
            self.content_size = read_int32(self.source_filepath, self.file_offset + MGD_CONTENT_SIZE_OFFSET, file_obj=source_file)
            self.read_resolution(source_file)
            self.read_buffer_size(source_file)
            self.read_asset_mode(source_file)
            self.mode_handler = self.create_mode_handler(source_file)
            self.mode_handler.parse()
            self._parse_mode_specific_content(source_file)
            self._parse_sprite_sheet(source_file)

    def read_resolution(self, source_file):
        # 读取分辨率信息，字段缺失时保持默认值
        try:
            self.resolution_x = read_int16(self.source_filepath, self.file_offset + MGD_RESOLUTION_X_OFFSET, file_obj=source_file)
            self.resolution_y = read_int16(self.source_filepath, self.file_offset + MGD_RESOLUTION_Y_OFFSET, file_obj=source_file)
        except ValueError:
            self.resolution_x = 0
            self.resolution_y = 0

    def read_buffer_size(self, source_file):
        # 读取缓冲区大小，字段缺失时保持默认值
        try:
            self.buffer_size = read_int32(self.source_filepath, self.file_offset + MGD_BUFFER_SIZE_OFFSET, file_obj=source_file)
        except ValueError:
            self.buffer_size = 0

    def read_asset_mode(self, source_file):
        # 读取资产模式信息，未定义时保持默认值
        try:
            mode_byte = read_byte(self.source_filepath, self.file_offset + MGD_ASSET_MODE_OFFSET, file_obj=source_file)
            self.asset_mode = mode_byte[0]
        except ValueError:
            self.asset_mode = 0

    def create_mode_handler(self, source_file):
        # 根据资产模式创建处理器
        handler_cls = MODE_HANDLER_MAP.get(self.asset_mode, Mode01GenericHandler)
        return handler_cls(self, source_file)

    @property
    def content_type(self):
        # 当前资产内容类型
        return self._content_type

    def set_content_type(self, value):
        # 设置资产内容类型
        self._content_type = value

    def extract_content(self, output_path, output_source_file=False):
        if output_source_file:
            self._extract_raw(output_path)
            return

        if self.asset_mode == 0x01:
            self._export_mode1_bitmap(output_path)
            return

        self.mode_handler.extract_content(output_path, output_source_file)

    def _extract_raw(self, output_path):
        # 提取原始 MGD 内容
        super().extract_content(output_path)

    def _extract_payload(self, output_path):
        # 提取嵌入的真实内容
        if not os.path.exists(output_path):
            os.makedirs(output_path, exist_ok=True)
        output_filename = os.path.join(output_path, f"{self.basename}.{self.content_type}")
        extract_bytes_to_file(self.source_filepath, output_filename, self.file_offset + MGD_CONTENT_OFFSET, self.content_size)

    def _parse_sprite_sheet(self, source_file):
        # 解析内容尾部附带的精灵表
        content_end = self.file_offset + MGD_CONTENT_OFFSET + self.content_size
        sprite_info_start = content_end + SPRITE_INFO_OFFSET
        file_end = self.file_offset + self.file_size

        self.sprite_count = 0
        self.sprites = []

        if sprite_info_start + SPRITE_COUNT_SIZE > file_end:
            return

        try:
            sprite_total = read_int16(self.source_filepath, sprite_info_start, file_obj=source_file)
        except ValueError:
            return

        entries_start = sprite_info_start + SPRITE_ENTRY_OFFSET
        available_bytes = max(0, file_end - entries_start)
        max_entries = available_bytes // SPRITE_ENTRY_SIZE
        parsed_entries = min(sprite_total, max_entries)

        sprites = []
        for index in range(parsed_entries):
            entry_offset = entries_start + index * SPRITE_ENTRY_SIZE
            try:
                origin_x = read_int16(self.source_filepath, entry_offset, signed=True, file_obj=source_file)
                origin_y = read_int16(self.source_filepath, entry_offset + 2, signed=True, file_obj=source_file)
                size_x = read_int16(self.source_filepath, entry_offset + 4, file_obj=source_file)
                size_y = read_int16(self.source_filepath, entry_offset + 6, file_obj=source_file)
            except ValueError:
                break

            sprites.append({
                "origin_x": origin_x,
                "origin_y": origin_y,
                "width": size_x,
                "height": size_y,
            })

            if self.debug_enabled:
                print(f"Sprite {index}: offset=({origin_x}, {origin_y}), size=({size_x}, {size_y})")

        self.sprite_count = len(sprites)
        self.sprites = sprites

    def _parse_mode_specific_content(self, source_file):
        if self.asset_mode == 0x01:
            self._parse_mode1_content(source_file)

    def _parse_mode1_content(self, source_file):
        content_start = self.file_offset + MGD_CONTENT_OFFSET
        content_end = content_start + self.content_size
        read_offset = content_start

        self.inner_header_size = 0
        self.inner_header = b""
        self.pixel_data_length = 0

        if read_offset + 4 > content_end:
            return

        try:
            header_size = read_int32(self.source_filepath, read_offset, file_obj=source_file)
        except ValueError:
            return

        if header_size < 0:
            return

        read_offset += 4
        header_end = read_offset + header_size
        if header_end > content_end:
            return

        source_file.seek(read_offset)
        header_bytes = source_file.read(header_size)
        if len(header_bytes) != header_size:
            return

        read_offset = header_end
        if read_offset + 4 > content_end:
            return

        try:
            pixel_length = read_int32(self.source_filepath, read_offset, file_obj=source_file)
        except ValueError:
            return

        pixel_length = max(0, pixel_length)
        pixel_data_start = read_offset + 4
        pixel_data_end = pixel_data_start + pixel_length
        if pixel_data_end > content_end:
            return

        self.inner_header_size = header_size
        self.inner_header = header_bytes
        self.pixel_data_length = pixel_length
        self.pixel_data_offset = pixel_data_start

        if self.debug_enabled:
            print(f"Mode01 header size: {header_size}, pixel data length: {self.pixel_data_length}")

    def _load_mode1_image(self) -> Optional[Image.Image]:
        if self.pixel_data_offset is None or self.pixel_data_length <= 0:
            return None

        width = int(self.resolution_x) if self.resolution_x else 0
        height = int(self.resolution_y) if self.resolution_y else 0

        if width <= 0 or height <= 0:
            return None

        expected_size = width * height * 4
        with open(self.source_filepath, "rb") as source_file:
            source_file.seek(self.pixel_data_offset)
            raw_pixels = source_file.read(self.pixel_data_length)

        if not raw_pixels:
            return None

        if len(raw_pixels) == 4 and expected_size > 4:
            raw_pixels = raw_pixels * (width * height)
        elif len(raw_pixels) < expected_size:
            if self.debug_enabled:
                print("Mode01 pixel data insufficient, aborting image export.")
            return None
        elif len(raw_pixels) > expected_size:
            raw_pixels = raw_pixels[:expected_size]

        try:
            return Image.frombytes("RGBA", (width, height), raw_pixels, "raw", "ARGB")
        except ValueError:
            if self.debug_enabled:
                print("Failed to decode Mode01 ARGB payload.")
            return None

    def _export_mode1_bitmap(self, output_path):
        image = self._load_mode1_image()
        if image is None:
            self._extract_raw(output_path)
            return

        self._export_sprite_images(image, output_path, "bmp", "BMP")

    def _load_mode2_image(self) -> Optional[Image.Image]:
        if self.content_size <= 0:
            return None

        payload_offset = self.file_offset + MGD_CONTENT_OFFSET
        with open(self.source_filepath, "rb") as source_file:
            source_file.seek(payload_offset)
            payload = source_file.read(self.content_size)

        if not payload:
            return None

        try:
            image = Image.open(io.BytesIO(payload))
            image.load()
            return image.convert("RGBA")
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            if self.debug_enabled:
                print(f"Failed to decode Mode02 PNG: {exc}")
            return None

    def _export_mode2_sprites(self, output_path):
        image = self._load_mode2_image()
        if image is None:
            self._extract_payload(output_path)
            return

        self._export_sprite_images(image, output_path, "png", "PNG")

    def _export_sprite_images(self, image: Image.Image, output_path: str, extension: str, format_name: str):
        full_sheet = (
            self.sprite_count == 1
            and self.sprites
            and self.sprites[0]["origin_x"] == 0
            and self.sprites[0]["origin_y"] == 0
            and self.sprites[0]["width"] == image.width
            and self.sprites[0]["height"] == image.height
        )

        if full_sheet or self.sprite_count == 0:
            os.makedirs(output_path, exist_ok=True)
            output_filename = os.path.join(output_path, f"{self.basename}.{extension}")
            image.save(output_filename, format=format_name)
            if self.debug_enabled:
                print(f"Saved sprite sheet to {output_filename}")
            return

        sprite_dir = os.path.join(output_path, self.basename)
        os.makedirs(sprite_dir, exist_ok=True)

        for index, sprite in enumerate(self.sprites, start=1):
            width = sprite["width"]
            height = sprite["height"]
            if width <= 0 or height <= 0:
                if self.debug_enabled:
                    print(f"Sprite {index} has non-positive dimensions, skipped.")
                continue

            left = sprite["origin_x"]
            top = sprite["origin_y"]
            right = left + width
            bottom = top + height

            if left < 0 or top < 0 or right > image.width or bottom > image.height:
                if self.debug_enabled:
                    print(f"Sprite {index} out of bounds, skipped.")
                continue

            cropped = image.crop((left, top, right, bottom))
            sprite_filename = os.path.join(sprite_dir, f"{self.basename}_{index}.{extension}")
            cropped.save(sprite_filename, format=format_name)
            if self.debug_enabled:
                print(f"Saved sprite {index} to {sprite_filename}")


class BaseMGDModeHandler:
    # 模式处理基类
    def __init__(self, mgd_file: MGDFile, source_file):
        self.mgd_file = mgd_file
        self.source_file = source_file

    def parse(self):
        # 默认设置为 MGD 类型
        self.mgd_file.set_content_type("MGD")

    def extract_content(self, output_path, output_source_file):
        # 默认按照内容类型输出
        if self.mgd_file.content_type == "MGD" or output_source_file:
            self.mgd_file._extract_raw(output_path)
        else:
            self.mgd_file._extract_payload(output_path)


class Mode01GenericHandler(BaseMGDModeHandler):
    # 模式 01：根据内容签名判断类型
    def parse(self):
        self.mgd_file.set_content_type("MGD")

    def extract_content(self, output_path, output_source_file):
        self.mgd_file._export_mode1_bitmap(output_path)


class Mode02PNGHandler(BaseMGDModeHandler):
    # 模式 02：内容固定为 PNG
    def parse(self):
        self.mgd_file.set_content_type("png")

    def extract_content(self, output_path, output_source_file):
        if output_source_file:
            self.mgd_file._extract_raw(output_path)
            return

        self.mgd_file._export_mode2_sprites(output_path)


MODE_HANDLER_MAP = {
    0x01: Mode01GenericHandler,
    0x02: Mode02PNGHandler,
}
