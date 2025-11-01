import argparse
import os
import sys

from ToolBox.ByteOperation import read_int32, read_string_until_null
from FileTypes.FileBase import FileBase
from FileTypes.MGDFile import MGDFile

FILELIST_OFFSET = 84
TABLE_ENTRY_SIZE = 16


def get_args():
    parser = argparse.ArgumentParser(description="FJSYS Extractor")
    parser.add_argument("filename", help="Path to the FJSYS filename")
    parser.add_argument("--source", help="Output source file instead of decrypted file", action="store_true")
    parser.add_argument("--debug", help="With debug output", action="store_true")
    parser.add_argument("-o", "--output", help="Output directory", default="Output")
    return parser.parse_args()


def parse_file(args=None):
    if args is None:
        raise ValueError("parse_file requires a valid argparse.Namespace instance.")

    def debug_log(message):
        # 调试输出统一入口，避免重复判断
        if args.debug:
            print(message)

    # 计算输出目录并确保存在，避免后续写文件失败
    total_size = os.path.getsize(args.filename)
    output_root = args.output or "Output"
    if not os.path.isabs(output_root):
        output_root = os.path.abspath(output_root)
    os.makedirs(output_root, exist_ok=True)

    files = []
    try:
        with open(args.filename, 'rb') as source_file:
            # 顺序扫描文件表：每条记录 16 字节，遇到非零终止值或越界即停止
            while True:
                item_offset = FILELIST_OFFSET + len(files) * TABLE_ENTRY_SIZE
                item_tail = item_offset + 12

                if item_tail + 4 > total_size:
                    debug_log("Warning: stopped parsing because the file table terminator exceeds the archive size.")
                    break

                tail_marker = read_int32(args.filename, item_tail, file_obj=source_file)
                if tail_marker != 0:
                    debug_log(f"Detected file table terminator value: {tail_marker}")
                    break

                filename_offset = read_int32(args.filename, item_offset, file_obj=source_file)
                file_size = read_int32(args.filename, item_offset + 4, file_obj=source_file)
                file_offset = read_int32(args.filename, item_offset + 8, file_obj=source_file)

                # 立即校验边界，防止损坏记录导致越界读取
                if file_offset + file_size > total_size:
                    raise ValueError(f"Entry {len(files)} exceeds archive bounds.")

                files.append(FileBase(args.filename, filename_offset, file_size, file_offset))

            filename_list_offset = FILELIST_OFFSET + len(files) * TABLE_ENTRY_SIZE
            print(f"Found {len(files)} files.")

            for index, file in enumerate(files):
                char_offset = filename_list_offset + file.filename_offset
                filename = read_string_until_null(args.filename, char_offset, file_obj=source_file)
                if not filename:
                    raise ValueError(f"Entry {index} contains an empty filename.")
                file.set_filename(filename)

                debug_log(f"File {index}: {filename}, size: {file.file_size}, offset: {file.file_offset}")

                # 对 MGD 做特殊处理，其余文件保持原样抽取
                if file.filetype.upper() == "MGD":
                    file = MGDFile(file)
                file.extract_content(output_root, output_source_file=args.source)
    except (OSError, ValueError) as exc:
        print(f"Failed to parse archive: {exc}")


if __name__ == "__main__":
    cli_args = get_args()
    if cli_args.filename is None or not os.path.isfile(cli_args.filename):
        print("Please provide a valid FJSYS filename.")
        sys.exit(1)

    parse_file(cli_args)
