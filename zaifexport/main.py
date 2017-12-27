import os
import sys

from docopt import docopt

from .exporter import Exporter


def main():
    args = docopt("""
    Usage:
      {f} [options] KEY SECRET EXPORT_TYPE [FILE]
    
    Arguments:
      KEY  APIキー
      SECRET  APIシークレット
      EXPORT_TYPE  spot(現物), margin(信用), future(先物) のいずれかを指定
      FILE  出力先ファイル名の指定、省略時は標準出力

    Options:
      --wait-interval SECONDS  API呼び出し制限時の待ち時間 [default: 30.0]

    Example:
      {f} eefd3b06-2d6b-4c47-9453-26bf3c0461a8 0c0bae5c-a601-42a0-93ec-f1c4ae285422 spot spot.csv
      
    """.format(f=os.path.basename(sys.argv[0])))

    key = args['KEY']
    secret = args['SECRET']
    export_type = args['EXPORT_TYPE']
    file_name = args['FILE']
    wait_interval = float(args['--wait-interval'])

    exporter = Exporter(api_key=key, api_secret=secret, wait_interval=wait_interval)
    file = open(file_name, 'w') if file_name else sys.stdout
    try:
        method = 'export_{}'.format(export_type)
        assert method in dir(exporter), 'unknown EXPORT_TYPE: {}'.format(export_type)
        gen = getattr(exporter, method)()
        exporter.write_csv(gen, file)
    finally:
        file.close()


if __name__ == '__main__':
    main()
