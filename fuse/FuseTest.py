#!/usr/bin/env python2
# -*- coding:utf-8 -*-

import llfuse
import errno
from collections import defaultdict
from time import time
import os
import sys
import logging
from stat import *
import struct

def logger(func):
    def _logger(*args, **kargs):
        logging.debug("Called %s%s."%(func.__name__, args[1:]))
        return func(*args, **kargs)
    return _logger

class Operations(llfuse.Operations):
    '''
    fhとinodeは同じ値を使いまわす
    '''

    def __init__(self, path):
        super(Operations, self).__init__()
        self.contents = ContentBuffer(path)
        self.inode_count = defaultdict(int)
        self.nextino = self.contents.next_ino()
        try:
            self.contents[llfuse.ROOT_INODE]
        except:
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
            inode = self.contents[inode_p].get_children()[name]
            return self.getattr(inode)
        except KeyError:
            raise llfuse.FUSEError(errno.ENOENT)

    @logger
    def readdir(self, inode, off):
        c = self.contents[inode].get_children()
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
        c.stat.st_blocks = (c.stat.st_size-1)/512 + 1
        self.contents.flush()
        return len(buf)

    @logger
    def release(self, fh):
        self.inode_count[fh] -= 1

    @logger
    def releasedir(self, fh):
        self.inode_count[fh] -= 1

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
        for inode, _ in inode_list:
            del self.contents[inode]

    @logger
    def link(self, inode, new_parent_inode, new_name):
        s = self.contents[inode].stat
        s.st_nlink += 1
        self.contents[new_parent_inode].add_child(new_name, inode)
        return s

    @logger
    def rename(self, inode_p_old, name_old, inode_p_new, name_new):
        inode = self.lookup(inode_p_old, name_old).st_ino
        self.contents[inode_p_old].del_child(name_old)
        self.contents[inode_p_new].add_child(name_new, inode)

    @logger
    def symlink(self, inode_p, name, target, ctx):
        mode = S_IFLNK|S_IRUSR|S_IRGRP|S_IROTH \
               |S_IWUSR|S_IWGRP|S_IWOTH|S_IXUSR|S_IXGRP|S_IXOTH
        inode, s = self.create(inode_p, name, mode, None, ctx)
        self.contents[inode].setlink(target)
        return s

    @logger
    def readlink(self, inode):
        return self.contents[inode].getlink()

    @logger
    def unlink(self, inode_p, name):
        s = self.lookup(inode_p, name)
        s.st_nlink -= 1
        self.contents[inode_p].del_child(name)

    @logger
    def rmdir(self, inode_p, name):
        s = self.lookup(inode_p, name)
        if len(self.contents[s.st_ino].get_children()) != 2:
            raise llfuse.FUSEError(errno.ENOTEMPTY)
        s.st_nlink -= 1
        self.contents[inode_p].del_child(name)

#    def mknod(self, inode_p, name, mode, rdev, ctx):
#    def fsync(self, fh, datasync):
#    def fsyncdir(self, fh, datasync):
#    def flush(self, fh):
#    def statfs(self):
#    def setxattr(self, name, value):
#    def getxattr(self, inode, name):
#    def linkxattr(self, inode):
#    def removexattr(self, inode, name):

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
        s.st_size = 0
        s.st_blksize = 512
        s.st_blocks = 1
        s.st_mtime = int(time())
        s.st_atime = int(time())
        s.st_ctime = int(time())
        self.contents[inode] = Content(s)
        logging.info("Created entry %s"%inode)
        return inode

class ContentBuffer(object):
    """
    unsigned int ino_length  // inodeエントリ数
    unsigned int block_length  // block数
    inode_status ino_length bit  // 該当するinode番号が使用中であれば1
    block_status block_length bit  //該当ブロックが使用中であれば1
    --------------------------------------
    content 構造体 64 byte * 1024 entry = 65536 byte
    unsigned int st_ino
    unsigned int generation
    unsigned int st_mode
    unsigned int st_nlink
    unsigned int st_uid
    unsigned int st_gid
    unsigned int st_size
    unsigned long st_atime
    unsigned long st_mtime
    unsigned long st_ctime
    unsigned long datap
    --------------------------------------
    以降、データ用領域
    """
    byte_size = 8
    block_size = 512
    format_content = "7I4L"
    struct_content = struct.Struct(format_content)
    def __init__(self, path):
        self.buffer = {}  # メモリ上にのってる
        self.dirty = defaultdict(bool)
        self.path = path
        s = struct.Struct('2I')
        with open(path, 'rb') as f:
            self.max_ino, self.max_blk = s.unpack(f.read(s.size))
            self.inode_bytes = (self.max_ino-1)/self.byte_size+1
            self.blk_bytes = (self.max_blk-1)/self.byte_size+1
            self.ino_status = struct.unpack("{}B".format(self.inode_bytes),
                                            f.read(self.inode_bytes))
            self.blk_status = struct.unpack("{}B".format(self.blk_bytes),
                                            f.read(self.blk_bytes))
            self.ino_status = list(self.ino_status)
            self.blk_status = list(self.blk_status)
        self.ino_status_head = s.size
        self.blk_status_head = self.ino_status_head + self.inode_bytes
        self.content_head = self.blk_status_head + self.blk_bytes
        self.data_head = self.content_head
        self.data_head += self.struct_content.size * self.max_ino

    def next_ino(self):
        for i in xrange(self.max_ino):
            if self._get_bit(self.ino_stpatus, i) == 0:
                return i + llfuse.ROOT_INODE

    def flush(self):
        update_list = [key for (key, value) in self.dirty.items() if value]
        with open(self.path, 'r+b') as f:
            f.seek(self.ino_status_head)
            f.write(struct.pack("{}B".format(self.inode_bytes), *self.ino_status))
            f.write(struct.pack("{}B".format(self.blk_bytes), *self.blk_status))
            for inode in update_list:
                self._set_bit(self.ino_status, inode)
                s = self.buffer[inode].stat
                datap = self._get_space(s.st_size)
                f.seek(self.content_head + self.struct_content.size * inode)
                f.write(self.struct_content.pack(s.st_ino, s.generation, s.st_mode,
                                                 s.st_nlink, s.st_uid, s.st_gid, s.st_size,
                                                 s.st_atime, s.st_mtime, s.st_ctime, datap))
                f.seek(self.data_head + datap * self.block_size)
                f.write(self.buffer[inode].data)
                ### TODO: dataとchildrenを書き出す(統合方法を考える) ###

    # datap用の連続領域を探してindex+offsetを返す
    def _get_space(self, size):
        blks = (size - 1)/self.block_size + 1
        count = 0
        for i in xrange(len(self.blk_status)):
            b = self.blk_status[i]
            for j in xrange(self.byte_size):
                if (b >> (7-j)) & 1 == 1:
                    count = 0
                    continue
                else:
                    count += 1
                if count >= blks:
                    add = 8*i + j
                    for k in xrange(blks):
                        self._set_bit(self.blk_status, add)
                        add -= 1
                    return add + 1
        raise IOError("No space is avilable.")

    def _get_bit(self, bitmap, address):
        index = address / self.byte_size
        offset = address % self.byte_size
        offset = self.byte_size - offset -1
        return bitmap[index]

    # bitmapと相対addressを受け取って該当ビットを立てる
    def _set_bit(self, bitmap, address, value=1):
        index = address / self.byte_size
        offset = address % self.byte_size
        offset = self.byte_size - offset -1
        bitmap[index] = bitmap[index] | (value << offset)

    def _del_bit(self, bitmap, address):
        self._set_bit(bitmap, address, 0)

    def __getitem__(self, inode):
        if not inode in self.buffer:
            index = inode - llfuse.ROOT_INODE
            offset = index % self.byte_size
            index = index / self.byte_size
            s = self.ino_status[index]
            if ((s >> offset) & 1) == 0:   # no entry
                raise KeyError(inode)
            with open(self.path, 'r+b') as f:
                stat = llfuse.EntryAttributes()
                f.seek(self.content_head + struct_format.size * (inode - llfuse.ROOT_INODE))
                (st_ino, generation, st_mode,
                 st_nlink, st_uid, st_gid, st_size,
                 st_atime, st_mtime, st_ctime, datap) \
                    = struct_format.unpack(f.read(struct_format.size))
                stat.st_ino = st_ino
                stat.generation = generation
                stat.entry_timeout = 300
                stat.attr_timeout = 300
                stat.st_mode = st_mode
                stat.st_nlink = st_nlink
                stat.st_uid = st_uid
                stat.st_gid = st_gid
                stat.st_rdev = 0
                stat.st_size = st_size
                stat.st_blksize = 512
                stat.st_blocks = (st_size-1)/512 + 1
                stat.st_atime = st_atime
                stat.st_mtime = st_mtime
                stat.st_ctime = st_ctime
                self.buffer[inode] = Content(stat)
                f.seek(self.data_head + datap * self.block_size)
                self.buffer[inode].write(0, f.read(stat.st_size))
        return self.buffer[inode]

    def __setitem__(self, inode, content):
        self.buffer[inode] = content
        self.dirty[inode] = True

    def __delitem__(self, key):
        pass


class Content(object):
    def __init__(self, stat):
        self.stat = stat
        self.children = {}
        self.data=""
    def read(self, off, size):
        return self.data[off:off+size]
    def write(self, offset, buf):
        assert self.is_reg(), "Called write function on the file which is not regular file."
        d = self.data
        self.data = d[:offset] + buf + d[offset+len(buf):]
    def add_child(self, name, inode):
        assert self.is_dir(), "Called add_child function on the file which is not directory"
        self.children[name] = inode
    def del_child(self, name):
        assert self.is_dir(), "Called del_child function on the file which is not directory"
        del self.children[name]
    def get_children(self):
        return self.children
    def setlink(self, target):
        assert self.is_link(), "Called setlink function on the file which is not regular file."
        self.data = target
    def getlink(self):
        assert self.is_link(), "Called getlink function on the file which is not regular file."
        return self.data
    def is_reg(self):
        return S_ISREG(self.stat.st_mode) != 0
    def is_dir(self):
        return S_ISDIR(self.stat.st_mode) != 0
    def is_link(self):
        return S_ISLNK(self.stat.st_mode) != 0

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: %s <mountpoint>' % sys.argv[0])
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] %(message)s')
    mountpoint = sys.argv[1]
    operations = Operations(mountpoint + ".tfs")
    llfuse.init(operations, mountpoint, ['fsname=testfs', 'nonempty'])
    logging.info('Mounted on %s'%mountpoint)
    try:
        llfuse.main(single=True)
    except:
        llfuse.close(unmount=False)
        raise
    llfuse.close()
