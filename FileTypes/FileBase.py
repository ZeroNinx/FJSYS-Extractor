import os
from ToolBox.ByteOperation import extract_bytes_to_file


class FileBase:
    source_filepath = ""  # 源文件路径
    filename_offset = 0  # 文件名在源文件中的偏移
    file_size = 0  # 文件大小
    file_offset = 0  # 文件数据在源文件中的偏移

    filename = ""  # 完整文件名（含扩展名）
    basename = ""  # 文件名主体部分
    filetype = ""  # 文件扩展名（不含点）

    def __init__(self, source_filepath, filename_offset, file_size, file_offset):
        self.source_filepath = source_filepath
        self.filename_offset = filename_offset
        self.file_size = file_size
        self.file_offset = file_offset

    def set_filename(self, filename):
        self.filename = filename
        self.basename, filetype = os.path.splitext(filename)
        self.filetype = filetype[1:]

    def extract_content(self, output_path, output_source_file=True):
        # 按原始扩展名输出数据，必要时创建整条目录结构
        os.makedirs(output_path, exist_ok=True)

        output_filename = os.path.join(output_path, self.filename)
        parent_dir = os.path.dirname(output_filename)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        extract_bytes_to_file(self.source_filepath, output_filename, self.file_offset, self.file_size)
        if self.filetype in {"MGD", "MSD"}:
            print(f"Source file output: {self.filename}")
