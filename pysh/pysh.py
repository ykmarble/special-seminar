#!/Usr/bin/python2
#-*- coding: utf-8 -*-

import os
import sys
import subprocess
import shlex
import cStringIO

class Parser(object):
    st_normal = 0
    st_squote = 1
    st_dquote = 2
    st_escape = 3
    st_variable = 4
    alnum_char = \
      [chr(c) for c in xrange(ord("a"), ord("z")+1)] + \
      [chr(c) for c in xrange(ord("A"), ord("Z")+1)] + \
      [chr(c) for c in xrange(ord("0"), ord("9")+1)] + ["_"]
    brank_string = ["\t", " ", "\n"]
    quote_string = ["'", '"']
    comment_string = ["#"]
    escape_string = ["\\"]
    variable_string = ["$"]
    token_string = [";", "(", ")"]
    token_part_string = [">", "<", "|", "&"]  # 後ろに続く文字に依存するもの
    token_full_string = [">>", "<<", "||", "&&", ">&", "<&", "|&"]
    def __init__(self):
        self.state = self.st_normal
        self.stream = cStringIO.StringIO()
        self.tokens = []
        self.buffer = ''

    def feed(self, s):
        self.stream = cStringIO.StringIO(self.stream.read()+s)

    def parse(self):
        while True:
            n = self.stream.read(1)
            if n == "":  # EOF
                break
            if self.state is self.st_normal:
                if n in self.brank_string:
                    self.tokens.append(self.buffer)
                    self.buffer = ''
                elif n == "'":
                    self.state = self.st_squote
                elif n == '"':
                    self.state = self.st_dquote
                elif n in self.comment_string:
                    self.tokens.append(self.buffer)
                    self.buffer = ''
                    self.stream.readline()
                elif n in self.escape_string:
                    self.state = self.st_escape
                elif n in self.variable_string:
                    self.state = self.st_variable
                    self.tokens.append(self.buffer)
                    self.buffer = n
                elif n in self.token_string:
                    self.tokens.append(self.buffer)
                    self.buffer = ''
                    self.tokens.append(n)
                elif n in self.token_part_string:
                    self.tokens.append(self.buffer)
                    self.buffer = n
                    n = self.stream.read(1)
                    if self.buffer + n in self.token_full_string:
                        self.tokens.append(self.buffer + n)
                        self.buffer = ''
                    else:
                        self.tokens.append(self.buffer)
                        self.stream.seek(-1, os.SEEK_CUR)
                        self.buffer = ''
                else:
                    self.buffer += n
            elif self.state is self.st_squote:  # single quote
                if n == "'":
                    self.state = self.st_normal
                    self.tokens.append(self.buffer)
                    self.buffer = ''
                else:
                    self.buffer += n
            elif self.state is self.st_dquote:  # double quote
                if n == '"':
                    self.state = self.st_normal
                    self.tokens.append(self.buffer)
                    self.buffer = ''
                else:
                    self.buffer += n
            elif self.state is self.st_escape:  # escape char
                self.buffer += n
                self.state = self.st_normal
            elif self.state is self.st_variable:  # variable($hoge)
                if n in self.alnum_char:
                    self.buffer += n
                else:
                    self.tokens.append(self.buffer)
                    self.buffer = ''
                    self.state = self.st_normal
                    self.stream.seek(-1, os.SEEK_CUR)
        if self.state == self.st_normal:
            self.tokens.append(self.buffer)
            self.buffer = ''
            self.tokens = [t for t in self.tokens if bool(t)]
            self.tokens.append(";")
            return True
        else:
            print "Encountered EOF during parsing.[state={}]".format(self.state)
            return False

    def pop_tokens(self):
        t = self.tokens
        self.tokens = []
        return t

# eval order: () -> && -> || -> | -> ;
def eval_tokens(tokens, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
    cmdline = []
    exit_status = 0
    token_iter = tokens.__iter__()
    for t in token_iter:
        if t == "(":
            pass
        elif t == "&&":
            p = subprocess.Popen(cmdline, stdin=stdin, stdout=stdout, stderr=stderr)
            exit_status = p.wait()
            if exit_status == 0:
                exit_status = eval_tokens(list(token_iter))
            break
        elif t == "||":
            p = subprocess.Popen(cmdline, stdin=stdin, stdout=stdout, stderr=stderr)
            exit_status = p.wait()
            if exit_status != 0:
                exit_status = eval_tokens(list(token_iter))
            break
        elif t == "|":
            p = subprocess.Popen(cmdline, stdin=stdin, stdout=subprocess.PIPE, stderr=stderr)
            exit_status = eval_tokens(list(token_iter), stdin=p.stdout, stdout=stdout, stderr=stderr)
        elif t == ";":
            p = subprocess.Popen(cmdline, stdin=stdin, stdout=stdout, stderr=stderr)
            p.wait()
            exit_status = eval_tokens(list(token_iter))
            break
        elif t == ">":
            path = token_iter.next()
            stdout = open(path, 'w')
        elif t == ">>":
            path = token_iter.next()
            stdout = open(path, 'a')
        elif t == "<":
            path = token_iter.next()
            stdin = open(path, 'r')
        elif t == "<<":
            # TODO: raw input
            pass
        elif t == "&":
            p = subprocess.Popen(cmdline, stdin=stdin, stdout=stdout, stderr=stderr)
            exit_status = 0
            break
        elif t == "!":
            pass
        else:
            cmdline.append(t)
    return exit_status


def main():
    parser = Parser()
    while True:
        parser.feed(raw_input("$ "))
        while not parser.parse():
            parser.feed("\n")
            parser.feed(raw_input("> "))
        tokens = parser.pop_tokens()
        print tokens
        eval_tokens(tokens)



if __name__ == '__main__':
    main()
