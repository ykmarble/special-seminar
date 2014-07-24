# TestFS

## Abstract
* 簡単なファイルシステムの実装を通して理解を深める
* FUSEを使うことで実装を簡単に
* 使い慣れているというだけで言語はPythonを選択

## Requirements
* Python 2.7
* llfuse (FUSEのPythonラッパー)

## Usage
`./FuseTest <mountpoint>`

## Classes
* Operations -- FUSE(llfuse)から実際に呼ばれる関数群
* Content -- inode構造体とBlocksクラスのインスタンスを保持、1ファイルを表す
* Blocks -- ファイルの実データを管理、ディスク上にいい感じにマップしてくれたりする
* ContentBuffer -- Contentのコンテナ、Operationsからはこれを通してContentを操作する
* TestFSHeader -- inode番号とブロックの使用状況やエントリ数を管理、ブロックサイズとかも変えられるようにする(予定)

## Structures on disk
| 名前                      | サイズ                    |
| ------------------------- | ------------------------  |
| inodeエントリ数           | unsigned int              |
| block数                   | unsigned int              |
| inode番号使用状況のbitmap | inodeエントリ数/8         |
| block使用状況のbitmap     | block数/8                 |
| Content構造体             | 64 byte * inodeエントリ数 |
| 実データ領域              |                           |
| Block                     | 512byte * block数         |

### Content構造体
| 名前       | サイズ        |
| ---------- | ------------- |
| st_ino     | unsigned int  |
| generation | unsigned int  |
| st_mode    | unsigned int  |
| st_nlink   | unsigned int  |
| st_uid     | unsigned int  |
| st_gid     | unsigned int  |
| st_size    | unsigned int  |
| st_atime   | unsigned long |
| st_mtime   | unsigned long |
| st_ctime   | unsigned long |
| datap      | unsigned long |
