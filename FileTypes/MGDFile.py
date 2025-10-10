import os
from FileTypes.FileBase import FileBase
from ToolBox.ByteOperation import *

MGD_HEADER_SIZE = 96 #文件头大小
MGD_CONTENT_SIZE_OFFSET = 92 #内容大小偏移
MGD_CONTENT_OFFSET = 96 #内容偏移
MGD_TAIL_SIZE = 24 #文件尾大小

class MGDFile(FileBase):

    content_size = 0
    content_filetype = "MGD"

    def __init__(self, file_base:FileBase):
        super().__init__(file_base.source_filepath, file_base.filename_offset, file_base.file_size, file_base.file_offset)
        self.set_filename(file_base.filename)
        self.content_size = read_int32(self.source_filepath, self.file_offset + MGD_CONTENT_SIZE_OFFSET)
        self.detect_content_filetype()
    
    def detect_content_filetype(self):
        # 读取内容的前8字节，判断文件类型
        header = read_string(self.source_filepath, self.file_offset + MGD_CONTENT_OFFSET, 8)
        if header.startswith("\x89PNG\r\n\x1a\n"):
            self.content_filetype = "png"

    def extract_content(self, output_path, output_source_file = False):
        if self.content_filetype == "MGD" or output_source_file:
            super().extract_content(output_path)
            return

        if not os.path.exists(output_path):
            os.makedirs(output_path)
        
        output_filename = os.path.join(output_path, self.basename + "." +self.content_filetype)
        extract_bytes_to_file(self.source_filepath, output_filename, self.file_offset + MGD_CONTENT_OFFSET, self.content_size)

