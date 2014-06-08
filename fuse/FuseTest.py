#!/usr/bin/env python
# -*- coding:utf-8 -*-

import llfuse
import errno
from collections import defaultdict
from time import time
import os
import sys
import logging
from stat import *

def logger(func):
    def _logger(*args, **kargs):
        logging.debug("Called %s%s."%(func.__name__, args[1:]))
        return func(*args, **kargs)
    return _logger

class Operations(llfuse.Operations):
    '''
    fhとinodeは同じ値を使いまわす
    '''
    
    def __init__(self):
        super(Operations, self).__init__()
        self.contents = {}
        self.inode_count = defaultdict(int)
        self.nextino = llfuse.ROOT_INODE

        # make root content
        mode = S_IFDIR|S_IRUSR|S_IRGRP|S_IROTH \
               |S_IWUSR|S_IXUSR|S_IXGRP|S_IXOTH
        ctx = llfuse.RequestContext();
        ctx.uid = os.getuid()
        ctx.gid = os.getgid()
        ctx.pid = os.getpid()
        inode = self._create_entry(mode, ctx)
        self.contents[inode].add_child(".", inode)

    @logger
    def open(self, inode, flags):
        self.inode_count[inode] += 1
        return inode

    @logger
    def opendir(self, inode):
        self.inode_count[inode] += 1
        return inode

    @logger
    def create(self, inode_p, name, mode, flags, ctx):
        inode = self._create_entry(mode, ctx)
        self.contents[inode_p].add_child(name, inode)
        return (inode, self.contents[inode].stat)

    @logger
    def getattr(self, inode):
        return self.contents[inode].stat

    @logger
    def read(self, fh, off, size):
        return self.contents[fh].read(off, size)

    @logger
    def lookup(self, inode_p, name):
        try:
            inode = self.contents[inode_p].children[name]
            return self.getattr(inode)
        except KeyError:
            raise llfuse.FUSEError(errno.ENOENT)

    @logger
    def readdir(self, inode, off):
        c = self.contents[inode].children
        children = ((name, self.getattr(c[name]), len(c)) for name in c)
        for i in xrange(off):
            try:
                children.next()
            except StopIteration:
                break
        return children

    @logger
    def access(self, inode, mode, ctx):
        return True
        
    @logger
    def write(self, fh, offset, buf):
        c = self.contents[fh]
        c.write(offset, buf)
        c.stat.st_size = len(c.data)
        return len(buf)

    @logger
    def release(self, fh):
        self.inode_count[fh] -= 1

    @logger
    def releasedir(self, fh):
        self.inode_count[inode] -= 1

    @logger
    def mkdir(self, inode_p, name, mode, ctx):
        inode = self._create_entry(mode, ctx)
        self.contents[inode_p].add_child(name, inode)
        c = self.contents[inode]
        c.add_child(".", inode)
        c.stat.st_nlink += 1
        c.add_child("..", inode_p)
        self.contents[inode_p].stat.st_nlink += 1
        return c.stat

    @logger
    def forget(self, inode_list):
        pass

    @logger
    def fsync(self, fh, datasync):
        pass

    @logger
    def fsyncdir(self, fh, datasync):
        pass

#    def getxattr(self, inode, name):

#    def link(self, inode, new_parent_inode, new_name):

#    def linkxattr(self, inode):

#    def flush(self, fh):

#    def readlink(self, inode):

    @logger
    def unlink(self, inode_p, name):
        s = self.lookup(inode_p, name)
        s.st_nlink -= 1
        self.contents[inode_p].del_child(name)

    @logger
    def rmdir(self, inode_p, name):
        s = self.lookup(inode_p, name)
        if len(self.contents[s.st_ino].children) != 2:
            raise llfuse.FUSEError(errno.ENOTEMPTY)
        s.st_nlink -= 1
        self.contents[inode_p].del_child(name)

#    def symlink(self, inode_p, name, target, ctx):

#    def rename(self, inode_p_old, name_old, inode_p_new, name_new):     

#    def link(self, inode, new_inode_p, new_name):

    @logger
    def setattr(self, inode, attr):
        s = self.contents[inode].stat
        changed = ""
        if attr.st_size is not None:
            d = self.contents[inode].data
            if attr.st_size < len(d):
                self.contents[inode].data = d[:attr.st_size]
            else:
                self.contents[inode].data = d + b'\0' * (attr.st_size - len(d))
            s.st_size = attr.st_size
            changed = "st_size"
        elif attr.st_mode is not None:
            s.st_mode = attr.st_mode
            changed = "st_mode"
        elif attr.st_uid is not None:
            s.st_uid = attr.st_uid
            changed = "st_uid"
        elif attr.st_gid is not None:
            s.st_gid = attr.st_gid
            changed = "st_gid"
        elif attr.st_rdev is not None:
            s.st_rdev = attr.st_rdev
            changed = "st_rdev"
        elif attr.st_atime is not None:
            s.st_atime = attr.st_atime
            changed = "st_atime"
        elif attr.st_mtime is not None:
            s.st_mtime = attr.st_mtime
            changed = "st_mtime"
        elif attr.st_ctime is not None:
            s.st_mtime = attr.st_ctime
            changed = "st_ctime"
        else:
            logging.warning("Failed in setattr. Unknown attribute.")
            raise llfuse.FUSEError(errno.ENOSYS)
        logging.info("Set attribute of %s"%changed)
        return s

#    def mknod(self, inode_p, name, mode, rdev, ctx):
#    def statfs(self):
#    def removexattr(self, inode, name):
#    def setxattr(self, name, value):

    @logger
    def _create_entry(self, mode, ctx):
        inode = self.nextino
        self.nextino = inode + 1
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
        self.contents[inode] = Content(s)
        logging.info("Created entry %s"%inode)
        return inode

class Content(object):
    def __init__(self, stat):
        self.stat = stat
        self.children = {}
        self.data=b""
    def read(self, off, size):
        return self.data[off:off+size]
    def write(self, offset, buf):
        assert self.is_reg(), "Called write function on the file which is not regular file."
        d = self.data
        self.data = d[:offset] + buf + d[offset+len(buf):]
    def add_child(self, name, inode):
        assert self.is_dir(), "Called write function on the file which is not directory"
        self.children[name] = inode
    def del_child(self, name):
        assert self.is_dir(), "Called write function on the file which is not directory"
        del self.children[name]
    def is_reg(self):
        return S_ISREG(self.stat.st_mode) != 0
    def is_dir(self):
        return S_ISDIR(self.stat.st_mode) != 0

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: %s <mountpoint>' % sys.argv[0])
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] %(message)s')
    mountpoint = sys.argv[1]
    operations = Operations()
    llfuse.init(operations, mountpoint, ['fsname=testfs', 'nonempty'])
    logging.info('Mounted on %s'%mountpoint)
    try:
        llfuse.main(single=True)
    except:
        llfuse.close(unmount=False)
        raise
    llfuse.close()