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

class Operations(llfuse.Operations):
    '''
    fhとinodeは同じ値を使いまわす
    '''
    
    def __init__(self):
        super(Operations, self).__init__()
        self.contents = {}
        self.stats = {}
        self.inode_count = defaultdict(int)
        self.nextino = llfuse.ROOT_INODE

        # make root content
        mode = S_IFDIR|S_IRUSR|S_IRGRP|S_IROTH \
               |S_IWUSR|S_IXUSR|S_IXGRP|S_IXOTH
        ctx = llfuse.RequestContext();
        ctx.uid = os.getuid()
        ctx.gid = os.getgid()
        ctx.pid = os.getpid()
        inode, s = self._create_entry(mode, ctx)
        self.stats[inode] = s
        self.contents[inode] = Content(inode, s)
        self.contents[inode].add_child(".", inode)

    def open(self, inode, flags):
        logging.debug("Called open function")
        self.inode_count[inode] += 1
        return inode

    def opendir(self, inode):
        logging.debug("Called opendir function")
        return inode
        
    def create(self, inode_p, name, mode, flags, ctx):
        logging.debug("Called create function")
        inode, s = self._create_entry(mode, ctx)
        self.stats[inode] = s
        self.contents[inode] = Content(inode, s)
        self.contents[inode_p].add_child(name, inode)
        return (inode, s)
        
    def getattr(self, inode):
        logging.debug("Called getattr function(inode=%s)"%inode)
        return self.stats[inode]

    def read(self, fh, off, size):
        logging.debug("Called read function")
        return self.contents[fh].data[off:off+size+1]

    def lookup(self, inode_p, name):
        logging.debug("Called lookup function(inode_p=%s,name=%s)"%(inode_p,name))
        try:
            inode = self.contents[inode_p].children[name]
            return self.getattr(inode)
        except KeyError:
            raise llfuse.FUSEError(errno.ENOENT)

    def readdir(self, inode, off):
        logging.debug("Called readdir function")
        logging.info("Read directory, %s(off: %s)"%(inode, off))
        c = ((name, self.getattr(ino), len(self.contents[inode].children)) for name, ino in self.contents[inode].children.items())
        for i in xrange(off):
            try:
                c.next()
            except StopIteration:
                break
        return c

    def access(self, inode, mode, ctx):
        logging.debug("Called access function")
        return True
        
    def write(self, fh, offset, buf):
        logging.debug("Called write function")
        self.contents[fh].write(offset, buf)
        self.stats[fh].st_size = len(self.contents[fh].data)
        return len(buf)

    def release(self, fh):
        logging.debug("Called release function")
        self.inode_count[fh] -= 1

    def mkdir(self, inode_p, name, mode, ctx):
        logging.debug("Called mkdir function")
        inode, s = self._create_entry(mode, ctx)
        self.stats[inode] = s
        self.contents[inode] = Content(inode, s)
        self.contents[inode].add_child(".", inode)
        self.stats[inode].st_nlink += 1
        self.contents[inode].add_child("..", inode_p)
        self.stats[inode_p].st_nlink += 1
        self.contents[inode_p].add_child(name, inode)
        logging.info("Created directory %s(%s)"%(name, inode))
        return s

    def forget(self, inode_list):
        logging.debug("Called forget function")
        pass
    def fsync(self, fh, datasync):
        logging.debug("Called fsync function")
        pass
    def fsyncdir(self, fh, datasync):
        logging.debug("Called fsyncdir function")
        pass
    def getxattr(self, inode, name):
        logging.debug("Called getxattr function")
        raise llfuse.FUSEError(llfuse.ENOATTR)
#    def link(self, inode, new_parent_inode, new_name):
#    def linkxattr(self, inode):
    def flush(self, fh):
        pass
#    def readlink(self, inode):
    def unlink(self, inode_p, name):
        logging.debug("Called unlink function")
        s = self.lookup(inode_p, name)
        s.st_nlink -= 1
        self.contents[inode_p].del_child(name)
    def rmdir(self, inode_p, name):
        logging.debug("Called rmdir function")
        s = self.lookup(inode_p, name)
        if len(self.contents[s.st_ino].children) != 2:
            raise llfuse.FUSEError(errno.ENOTEMPTY)
        s.st_nlink -= 1
        self.contents[inode_p].del_child(name)
#    def symlink(self, inode_p, name, target, ctx):
#    def rename(self, inode_p_old, name_old, inode_p_new, name_new):     
#    def link(self, inode, new_inode_p, new_name):
    def setattr(self, inode, attr):
        logging.debug("Called setattr function")
        s = self.stats[inode]
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
    def releasedir(self, fh):
        logging.debug("Called releasedir function")
#    def removexattr(self, inode, name):
#    def setxattr(self, name, value):

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
        logging.info("Created entry %s"%inode)
        return (s.st_ino, s)

class Content(object):
    def __init__(self, inode, stat):
        self.inode = inode
        self.stat = stat
        self.children = {}
        self.data=b""
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