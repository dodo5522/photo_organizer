from __future__ import unicode_literals

from collections import defaultdict
import ConfigParser
from datetime import datetime
import glob
import json
import re
import shutil
import string
import sys
import os


DEFAULT_OUTPUT_BASE_PATH = os.path.join(os.environ.get('HOME'), 'OutBox')
DEFAULT_FILENAME_FORMAT = (
    '{y}{m}{d}/{Model}/{y}{m}{d}{H}{M}{S}-{bn}.{FileTypeExtension}')


def parse_datetime(createdate):
    """CreatedDateを扱いやすい形に分解する."""
    try:
        cdt = datetime.strptime(createdate[:19], '%Y:%m:%d %H:%M:%S')
        return dict(
            y=cdt.strftime('%Y'),
            m=cdt.strftime('%m'),
            d=cdt.strftime('%d'),
            H=cdt.strftime('%H'),
            M=cdt.strftime('%M'),
            S=cdt.strftime('%S'),
        )
    except Exception:
        # 不正な日付は0に置き換えする
        return dict(
            y='0000',
            m='00',
            d='00',
            H='00',
            M='00',
            S='00',
        )


def branch_no(output_base_path, filename_format, photo_info):
    """枝番を求める.

    同一ファイル名のファイルがある場合枝番をカウントアップする.
    枝番は0から始まる

    """
    photo_info['bn'] = '[0-9]*'
    new_name = string.Formatter().vformat(filename_format, (), photo_info)
    new_path = os.path.join(output_base_path, new_name)
    files = glob.glob(new_path)
    if not files:
        return 0

    bn = 0
    photo_info['bn'] = '([0-9]*)'
    bn_search = string.Formatter().vformat(filename_format, (), photo_info)
    for fn in files:
        m = re.search(bn_search, fn)
        bn = max(bn, int(m.group(1)))
    return bn + 1


def load_configure(source_dir):
    """入力フォルダにあるsetting.iniファイルより出力設定を読み込む"""
    config_file = os.path.join(source_dir, 'setting.ini')
    config = ConfigParser.SafeConfigParser({
        'output_photo_base': DEFAULT_OUTPUT_BASE_PATH,
        'output_video_base': DEFAULT_OUTPUT_BASE_PATH,
        'filename_format': DEFAULT_FILENAME_FORMAT,
    })
    config.read([config_file])
    filename_format = config.get('DEFAULT', 'filename_format')
    output_photo_base = config.get('DEFAULT', 'output_photo_base')
    output_video_base = config.get('DEFAULT', 'output_video_base')
    return filename_format, output_photo_base, output_video_base


def copy_outbox(exif, output_base_path, filename_format):
    """写真のexif属性により適切なフォルダへファイルをコピーする"""
    photo_info = defaultdict(lambda: 'Unknown')
    photo_info.update({
        k: v.replace(' ', '_') if isinstance(v, basestring) else v
        for k, v in exif.items()
    })
    photo_info.update(parse_datetime(
        exif.get('CreateDate') or
        exif.get('DateCreated') or
        exif.get('DateTimeOriginal') or
        exif.get('FileModifyDate')
    ))

    photo_info['bn'] = branch_no(
        output_base_path, filename_format, photo_info)

    new_name = string.Formatter().vformat(filename_format, (), photo_info)
    new_path = os.path.join(output_base_path, new_name)

    # make dirs
    if not os.path.exists(os.path.dirname(new_path)):
        os.makedirs(os.path.dirname(new_path))

    # copy file
    shutil.copyfile(exif.get('SourceFile'), new_path)


def is_movie(exif):
    n = len(list(filter(lambda k: 'FrameRate' in k, exif.keys())))
    return n &gt; 0


def main(source_dir, input_json):
    """exiftoolが出力するJSONファイルの属性から写真を整理する"""
    exifs = json.loads(input_json)
    configurations = load_configure(source_dir)
    filename_format, output_photo_base, output_video_base = configurations
    for exif in exifs:
        if 'Error' in exif:
            continue
        if is_movie(exif):
            output_base_path = output_video_base
        else:
            output_base_path = output_photo_base
        copy_outbox(exif, output_base_path, filename_format)


if __name__ == '__main__':
    source_dir, input_json = sys.stdin.read().strip().split(',')
    main(source_dir, open(input_json, 'r').read())

