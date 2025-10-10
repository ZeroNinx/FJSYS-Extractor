import os
from ToolBox.ByteOperation import *

class FileBase:
    
    source_filepath = "" #源文件路径
    filename_offset = 0 #文件名在源文件中的偏移
    file_size = 0 #文件大小
    file_offset = 0 #文件在原文件中的偏移
    
    filename = "" #完整文件名，含扩展名
    basename = "" #不含扩展名的文件名
    filetype = "" #扩展名

    def __init__(self, source_filepath, filename_offset, file_size, file_offset):
        self.source_filepath = source_filepath
        self.filename_offset = filename_offset
        self.file_size = file_size
        self.file_offset = file_offset

    def set_filename(self, filename):
        self.filename = filename
        self.basename, filetype = os.path.splitext(filename)
        self.filetype = filetype[1:]

    def extract_content(self, output_path, output_source_file = True):
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        
        output_filename = os.path.join(output_path, self.filename)
        extract_bytes_to_file(self.source_filepath, output_filename, self.file_offset, self.file_size)
        if self.filetype == "MGD" \
        or self.filetype == "MSD":
            print(f"Source file output: {self.filename}")

