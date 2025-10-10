import os
import sys
import argparse
from ToolBox.ByteOperation import *
from FileTypes.FileBase import FileBase
from FileTypes.MGDFile import MGDFile

FILELIST_OFFSET = 84
MGD_HEADER_SIZE = 96
MGD_TAIL_SIZE = 24

file_list = [] #储存遍历出的文件信息

def get_args():
    parser = argparse.ArgumentParser(description="FJSYS Extractor")
    parser.add_argument("filename", help="Path to the FJSYS filename")
    parser.add_argument("--source", help="Output source file instead of decrypted file", action="store_true")
    parser.add_argument("--debug", help="With debug output", action="store_true")
    parser.add_argument("-o", "--output", help="Output directory", default="Output")
    return parser.parse_args()

def parse_file(args = None):
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
        file_list.append(FileBase(args.filename, filename_offset, file_size, file_offset))

        item_index = item_index + 1
        item_offset = FILELIST_OFFSET + item_index * (4*4)
        item_tail = item_offset + 3*4 #4字节一组，以0结尾 
    
    print(f"Found {len(file_list)} files.")

    # 文件列表结束，开始读取文件名
    filename_list_offset = item_offset
    for index, file in enumerate(file_list):

        # 解析文件名
        char_offset = filename_list_offset + file.filename_offset
        filename = read_string_until_null(args.filename, char_offset)
        file.set_filename(filename)

        # 输出文件信息
        if args.debug:
            print(f"File {index}: {filename}, size: {file.file_size}, offset: {file.file_offset}")

        # 构造输出路径
        output_path = args.output
        if not output_path:
            exec_path = sys.path[0]
            output_path = os.path.join(exec_path, args.output)
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        if file.filetype == "MGD":
            file = MGDFile(file)
        file.extract_content(output_path, output_source_file=args.source)

if __name__ == "__main__":
    args = get_args()
    if args.filename is None or not os.path.isfile(args.filename):
        print("Please provide a valid FJSYS filename.")
        sys.exit(1)
    parse_file(args)
