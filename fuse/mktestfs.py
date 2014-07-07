#!/usr/bin/env python2

import argparse
import struct
import os.path

DEFAULT_INODE=1024

def calk_blksize():
    return 2**20

def main():
    parser = argparse.ArgumentParser(description='Initialize testfs data file.')
    parser.add_argument('file', help='Path to testfs data file.')
    parser.add_argument('-b', '--blocks', type=int, help='Specify number of blocks.')
    parser.add_argument('-i', '--inodes', type=int, default=DEFAULT_INODE,
                        help='Specify number of inode entries.(default {})'.format(DEFAULT_INODE))
    args = parser.parse_args()
    if not os.path.isfile(args.file):
        parser.print_usage()
        print "mktestfs.py: eroor: {} is not file".format(args.file)
        return
    blocks = (args.blocks or calk_blksize())
    d = struct.pack("2I", args.inodes, blocks)
    with open(args.file, 'wb') as f:
        f.write(d)
        f.write(b"\x00"*args.inodes)
        f.write(b"\x00"*blocks)

if __name__ == '__main__':
    main()