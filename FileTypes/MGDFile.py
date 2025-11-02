import os
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


class MGDFile(FileBase):
    # MGD 资产解析器：负责读取头部公共字段并根据模式委托处理

    resolution_x = 0
    resolution_y = 0
    buffer_size = 0
    asset_mode = 0
    content_size = 0

    mode_handler = None

    def __init__(self, file_base: FileBase):
        super().__init__(file_base.source_filepath, file_base.filename_offset, file_base.file_size, file_base.file_offset)
        self.set_filename(file_base.filename)
        self._content_type = "MGD"
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


class Mode02PNGHandler(BaseMGDModeHandler):
    # 模式 02：内容固定为 PNG
    def parse(self):
        self.mgd_file.set_content_type("png")

MODE_HANDLER_MAP = {
    0x01: Mode01GenericHandler,
    0x02: Mode02PNGHandler,
}
