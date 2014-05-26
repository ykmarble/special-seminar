#!/usr/bin/env python
# -*- coding:utf-8 -*-

import llfuse
import errno
from collections import defaultdict
from time import time
import os
import sys
from stat import *

class Operations(llfuse.Operations):
    '''
    fhとinodeは同じ値を使いまわす
    '''
    
    def __init__(self):
        super(Operations, self).__init__()
        self.contents = {}
        self.stats = {}
        self.inode_count = defaultdict(int)

        # make root content
        self.contents[llfuse.ROOT_INODE] = \
            Content(llfuse.ROOT_INODE, llfuse.ROOT_INODE, b"..")
        s = llfuse.EntryAttributes()
        s.generation = 0
        s.entry_timeout = 300
        s.attr_timeout = 300
        s.st_ino = llfuse.ROOT_INODE
        s.st_mode = S_IFDIR|S_IRUSR|S_IRGRP|S_IROTH \
                    |S_IWUSR|S_IXUSR|S_IXGRP|S_IXOTH
        s.st_nlink = 1
        s.st_uid = os.getuid()
        s.st_gid = os.getgid()
        s.st_rdev = 0
        s.st_size = 1
        s.st_blksize = 512
        s.st_blocks = 1
        s.st_mtime = time()
        s.st_atime = time()
        s.st_ctime = time()
        self.stats[llfuse.ROOT_INODE] = s

    def open(self, inode, flags):
        self.inode_count[inode] += 1
        return inode

    def opendir(self, inode):
        return inode
        
    def create(self, inode_p, name, mode, flags, ctx):
        inode = len(self.inode_count) + llfuse.ROOT_INODE + 1
        c = Content(inode, inode_p, name)
        self.contents[inode] = c
        s = llfuse.EntryAttributes()
        s.generation = 0
        s.entry_timeout = 300
        s.attr_timeout = 300
        s.st_ino = inode
        s.st_mode = mode
        s.st_nlink = 1
        s.st_uid = ctx.uid
        s.st_gid = ctx.gid
        s.st_rdev = 0
        s.st_size = 1
        s.st_blksize = 512
        s.st_blocks = 1
        s.st_mtime = time()
        s.st_atime = time()
        s.st_ctime = time()
        self.stats[inode] = s
        return (s.st_ino, s)

    def getattr(self, inode):
        return self.stats[inode]

    def read(self, fh, off, size):
        return self.contents[fh].data[off:off+size+1]

    def lookup(self, inode_p, name):
        if name == '.':
            return(self.getattr(inode_p))
        elif name == '..':
            return(self.getattr(self.contents[inode_p].parent))
        else:
            for c in self.contents.values():
                if c.parent ==inode_p and c.name ==name:
                    return(self.getattr(c.inode))
            raise llfuse.FUSEError(errno.ENOENT)

    def readdir(self, inode, off):
        return ((c.name, self.getattr(c.inode), c.inode)
                for c in self.contents.values()
                if c.parent == inode and c.inode > off)

    def access(self, inode, mode, ctx):
        return True
        
    def write(self, fh, offset, buf):
        d = self.contents[fh].data
        self.contents[fh].data = d[:offset] + buf + d[offset+len(buf):]
        self.stats[fh].st_size = len(self.contents[fh].data)
        return len(buf)

    def release(self, fh):
        self.inode_count[fh] -= 1

    def mkdir(self, inode_p, name, mode, ctx):
        inode = llfuse.ROOT_INODE + len(self.inode_count) + 1
        self.contents[inode] = \
            Content(inode, inode_p, name)
        s = llfuse.EntryAttributes()
        s.generation = 0
        s.entry_timeout = 300
        s.attr_timeout = 300
        s.st_ino = inode
        s.st_mode = S_IFDIR|S_IRUSR|S_IRGRP|S_IROTH \
                    |S_IWUSR|S_IXUSR|S_IXGRP|S_IXOTH
        s.st_nlink = 1
        s.st_uid = os.getuid()
        s.st_gid = os.getgid()
        s.st_rdev = 0
        s.st_size = 1
        s.st_blksize = 512
        s.st_blocks = 1
        s.st_mtime = time()
        s.st_atime = time()
        s.st_ctime = time()
        self.stats[inode] = s
        
#    def forget(self, inode_list):
#    def fsync(self, fh):
#    def fsyncdir(self, fh):
#    def getxattr(self, inode, name):
#    def link(self, inode, new_parent_inode, new_name):
#    def linkxattr(self, inode):
#    def flush(self, fh):
#    def readlink(self, inode):
#    def unlink(self, inode_p, name):
#    def rmdir(self, inode_p, name):
#    def symlink(self, inode_p, name, target, ctx):
#    def rename(self, inode_p_old, name_old, inode_p_new, name_new):     
#    def link(self, inode, new_inode_p, new_name):
#    def setattr(self, inode, attr):
#    def mknod(self, inode_p, name, mode, rdev, ctx):
#    def statfs(self):
#    def releasedir(self, fh):
#    def removexattr(self, inode, name):
#    def rmdir(self, inode_parent, name):
#    def setxattr(self, name, value):

class Content(object):
    def __init__(self, inode, inode_p, name, data=b''):
        self.inode = inode
        self.parent =inode_p
        self.name = name
        self.data = data


    
if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: %s <mountpoint>' % sys.argv[0])
    mountpoint = sys.argv[1]
    operations = Operations()
    llfuse.init(operations, mountpoint, ['fsname=testfs', 'nonempty'])
    try:
        llfuse.main(single=True)
    except:
        llfuse.close(unmount=False)
        raise
    llfuse.close()