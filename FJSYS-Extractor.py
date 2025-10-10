import os
import sys
import argparse
from ByteOperation import *

FILELIST_OFFSET = 84
MGD_HEADER_SIZE = 96

class file_item:
    def __init__(self, filename_offset, file_size, file_offset):
        self.filename_offset = filename_offset
        self.file_size = file_size
        self.file_offset = file_offset

file_list = [] #储存遍历出的文件信息

def get_args():
    parser = argparse.ArgumentParser(description="FJSYS Extractor")
    parser.add_argument("filename", help="Path to the FJSYS filename")
    parser.add_argument("--list", help="List files in the archive", action="store_true")
    parser.add_argument("--image", help="Extract images", action="store_true")
    parser.add_argument("-o", "--output", help="Output directory", default="Output")
    return parser.parse_args()

def parse_header(args = None):
    item_index = 0
    item_offset = FILELIST_OFFSET + item_index * (4*4)
    item_tail = item_offset + 3*4 #4字节一组，以0结尾 
    while read_int32(args.filename, item_tail) == 0:
        filename_offset = read_int32(args.filename, item_offset)
        file_size = read_int32(args.filename, item_offset + 4)
        file_offset = read_int32(args.filename, item_offset + 2*4)

        # print(f"Item = {item_index}")
        # print(f"filename_offset = {filename_offset}")
        # print(f"file_size = {file_size}")
        # print(f"file_offset = {file_offset}")
        # print("---")
        file_list.append(file_item(filename_offset, file_size, file_offset))

        item_index = item_index + 1
        item_offset = FILELIST_OFFSET + item_index * (4*4)
        item_tail = item_offset + 3*4 #4字节一组，以0结尾 
    
    # 文件列表结束，开始读取文件名
    filename_list_offset = item_offset
    for index, item in enumerate(file_list):
        filename = ""
        char_offset = filename_list_offset + item.filename_offset
        filename = read_string_until_null(args.filename, char_offset)

        # 输出文件信息
        if args.list:
            print(f"File {index}: {filename}, size: {item.file_size}, offset: {item.file_offset}")

        # 构造输出路径
        output_path = args.output
        if not output_path:
            exec_path = sys.path[0]
            output_path = os.path.join(exec_path, args.output)
            
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        if args.image:

            # 判定是否为PNG图片
            png_header = read_string(args.filename, item.file_offset + MGD_HEADER_SIZE, 8)
            if png_header == "\x89PNG\r\n\x1a\n":
                print("Detected PNG image, extracting...")

                output_filename = os.path.join(output_path, filename + ".png")
                print(output_filename)
                extract_bytes_to_file(args.filename, output_filename, item.file_offset + MGD_HEADER_SIZE, item.file_size - MGD_HEADER_SIZE)
            else:
                print("Not a PNG image, skipping...")
        else:
            output_filename = os.path.join(output_path, filename)
            extract_bytes_to_file(args.filename, filename, item.file_offset, item.file_size)

if __name__ == "__main__":
    args = get_args()
    if args.filename is None or not os.path.isfile(args.filename):
        print("Please provide a valid FJSYS filename.")
        sys.exit(1)
    parse_header(args)
