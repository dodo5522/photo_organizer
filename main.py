from collections import defaultdict
from datetime import datetime
from subprocess import run, PIPE
import glob
import json
import re
import shutil
import string
import sys
import os
from configparser import ConfigParser


PATH_TO_EXIF_TOOL = '/usr/local/bin/exiftool'
DEFAULT_OUTPUT_BASE_PATH = os.path.join(os.environ.get('HOME'), 'OutBox')
DEFAULT_FILENAME_FORMAT = (
    '{y}{m}{d}/{Model}/{y}{m}{d}{H}{M}{S}-{bn}.{FileTypeExtension}')


def parse_datetime(createdate: str) -> dict:
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


def branch_no(output_base_path: str, filename_format: str, photo_info) -> int:
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


def load_configure(source_dir: str) -> tuple:
    """入力フォルダにあるsetting.iniファイルより出力設定を読み込む"""
    config_file = os.path.join(source_dir, 'setting.ini')
    config = ConfigParser({
        'output_photo_base': DEFAULT_OUTPUT_BASE_PATH,
        'output_video_base': DEFAULT_OUTPUT_BASE_PATH,
        'filename_format': DEFAULT_FILENAME_FORMAT,
    })
    config.read([config_file])
    filename_format = config.get('DEFAULT', 'filename_format')
    output_photo_base = config.get('DEFAULT', 'output_photo_base')
    output_video_base = config.get('DEFAULT', 'output_video_base')
    return filename_format, output_photo_base, output_video_base


def manipulate_file(exif: dict, output_base_path: str, filename_format: str, is_move: bool):
    """写真のexif属性により適切なフォルダへファイルをコピーする"""
    photo_info = defaultdict(lambda: 'Unknown')
    photo_info.update({
        k: v.replace(' ', '_') if isinstance(v, str) else v
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

    src_path = exif.get('SourceFile')
    print(f'{"Move" if is_move else "Copy"} {src_path} to {new_path}')

    # manipulate file
    manipulate = shutil.move if is_move else shutil.copyfile
    manipulate(src_path, new_path)


def is_movie(exif: dict) -> bool:
    n = len(list(filter(lambda k: 'FrameRate' in k, exif.keys())))
    return n > 0


def make_exif_json(source_dir: str, path_to_exif_tool: str) -> str:
    """exiftoolを実行し、出力されたjsonファイルへのパスを返す"""
    if not os.path.isfile(path_to_exif_tool):
        raise ValueError(f'{path_to_exif_tool} not found')

    log_root_dir = '/tmp/photo_organizer'
    log_file_base = f'{log_root_dir}/{datetime.now().strftime("%Y%m%d-%H%M%S")}'
    json_out = f'{log_file_base}.json'

    os.makedirs(log_root_dir, exist_ok=True)

    command = f'{path_to_exif_tool} -api largefilesupport=1 -r -j {source_dir} > {json_out}'
    with open(f'{log_file_base}_cmd.log', mode='w') as f:
        f.write(command)

    res = run(command, shell=True, stderr=PIPE)
    if res.returncode != 0:
        #raise RuntimeError(res.stderr.decode('utf-8'))
        pass

    return json_out


def main(source_dir: str, input_json: str, is_move: bool) -> None:
    """exiftoolが出力するJSONファイルの属性から写真を整理する"""
    if not input_json:
        return

    exifs: list = sorted(json.loads(input_json), key=lambda x: x['FileName'])
    configurations = load_configure(source_dir)
    filename_format, output_photo_base, output_video_base = configurations
    for exif in exifs:
        if 'Error' in exif:
            continue
        if is_movie(exif):
            output_base_path = output_video_base
        else:
            output_base_path = output_photo_base
        manipulate_file(exif, output_base_path, filename_format, is_move)


if __name__ == '__main__':
    from argparse import ArgumentParser, Namespace

    parser = ArgumentParser()
    parser.add_argument(
        '-s', '--source-dir',
        type=str,
    )
    parser.add_argument(
        '-e', '--path-to-exif-tool',
        type=str,
        default=PATH_TO_EXIF_TOOL,
    )
    parser.add_argument(
        '-m', '--move',
        action='store_true',
    )

    args: Namespace = parser.parse_args()

    is_move = False
    if args.source_dir:
        is_move = args.move
        source_dir = args.source_dir
        input_json = make_exif_json(source_dir, args.path_to_exif_tool)
    else:
        source_dir, input_json = sys.stdin.read().strip().split(',')

    main(source_dir, open(input_json, 'r').read(), is_move)
