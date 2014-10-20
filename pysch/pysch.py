#!/usr/bin/python2
# -*- coding:utf-8 -*-

import argparse
import os
import sys

class Process(Object):
    def __init__(self, path):
        self.path = path
        self.line_num = 0

# pyschで走らせることのできるファイルかどうかを検査
def is_valid(path):
    os.path.isfile(path)

def main(pathes):
    for p in pathes:
        if not is_valid(p):
            sys.exit("{} is invalid file.".format(p))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='pysch -- PYthon SCHeduler')
    parser.add_argument('path', nargs='+', help='path to python script')
    args = parser.parse_args()
    main(args.path)