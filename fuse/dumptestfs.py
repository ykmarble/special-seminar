#!/usr/bin/env python2

import struct
import os.path
import argparse

def count_bits(n):
    s = 0
    while n != 0:
        if (n & 1 == 1):
            s += 1
        n >> 1
    return s

def main():
    parser = argparse.ArgumentParser(description='Dump testfs infomation.')
    parser.add_argument('file', help='Path to testfs data file.')
    args = parser.parse_args()
    if not os.path.isfile(args.file):
        parser.print_usage()
        print "dumptestfs.py: eroor: {} is not file".format(args.file)
        return
    s = struct.Struct('2I')
    with open(args.file, 'rb') as f:
        inodes, blocks = s.unpack(f.read(s.size))
        inode_bytes = (inodes-1)/8+1
        blk_bytes = (blocks-1)/8+1
        inode_entries = struct.unpack("{}B".format(inode_bytes), f.read(inode_bytes))
        blk_entries = struct.unpack("{}B".format(blk_bytes), f.read(blk_bytes))
    inode_used =sum([count_bits(i) for i in inode_entries])
    blk_used = sum([count_bits(i) for i in blk_entries])
    print "inode entries: {} total, {} used, {} free".format(inodes, inode_used, inodes - inode_used)
    print "blocks: {} total, {} used, {} free".format(blocks, blk_used, blocks - blk_used)

if __name__ == '__main__':
    main()