"""
Main entry point for chapter splitting tools.

This script provides a command-line interface for the chapter splitting tools,
allowing users to split novels, separate EPUB chapters, and combine output files.
"""

import argparse
import sys
from typing import Optional

from .epub_separator import EpubSeparator
from .novel_splitter import NovelSplitter
from .output_combiner import OutputCombiner
from .folder_manager import FolderManager

def main(args: Optional[list[str]] = None) -> None:
    """
    Main entry point for the chapter splitting tools.
    
    Args:
        args: Optional command line arguments. If None, sys.argv[1:] is used.
    """
    parser = argparse.ArgumentParser(description="Chapter splitting tools for novel processing")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # EPUB separator command
    epub_parser = subparsers.add_parser("epub", help="Separate EPUB into chapters")
    epub_parser.add_argument("epub_file", help="Path to the EPUB file")
    epub_parser.add_argument("output_dir", help="Directory to save separated chapters")

    # Novel splitter command
    novel_parser = subparsers.add_parser("split", help="Split a novel into chapters")
    novel_parser.add_argument("input_file", help="Path to the input text file")
    novel_parser.add_argument("output_dir", help="Directory to save split chapters")

    # Output combiner command
    combine_parser = subparsers.add_parser("combine", help="Combine output files")
    combine_parser.add_argument("input_dir", help="Directory containing files to combine")
    combine_parser.add_argument("output_file", help="Path to save combined output")
    combine_parser.add_argument("--format", choices=["txt", "epub"], default="txt", help="Output format (default: txt)")
    combine_parser.add_argument("--reference_epub", help="Path to a reference EPUB for ordering chapters", default=None)

    # Clear folders command
    clear_parser = subparsers.add_parser("clear", help="Clear input and output folders")
    clear_parser.add_argument("--input", action="store_true", help="Clear input folder")
    clear_parser.add_argument("--output", action="store_true", help="Clear output folder")

    args = parser.parse_args(args)

    try:
        if args.command == "epub":
            separator = EpubSeparator()
            separator.separate(args.epub_file, args.output_dir)
            print(f"EPUB separated successfully. Output in: {args.output_dir}")

        elif args.command == "split":
            splitter = NovelSplitter()
            splitter.split(args.input_file, args.output_dir)
            print(f"Novel split successfully. Output in: {args.output_dir}")

        elif args.command == "combine":
            combiner = OutputCombiner()
            combiner.combine(args.input_dir, args.output_file, args.format, args.reference_epub)
            print(f"Files combined successfully. Output saved to: {args.output_file}")

        elif args.command == "clear":
            manager = FolderManager()
            if args.input:
                manager.clear_input()
                print("Input folder cleared successfully")
            if args.output:
                manager.clear_output()
                print("Output folder cleared successfully")
            if not args.input and not args.output:
                print("Please specify --input and/or --output")

        else:
            parser.print_help()

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 