# zaifexport

https://zaif.jp 非公式エクスポートツールです。  
現物・信用・先物の取引履歴をcsvで取得することができます。  

※ Linux以外での動作は未確認です。

# 準備

python(version3.5以上)が必要です。  
https://www.python.org/

ZaifのAPIキーとAPIシークレットが必要です。  
https://zaif.jp/api_keys で発行してください。  
**APIキー、APIシークレットは公開しないよう注意してください。**

# インストール

```
  pip3 install git+https://github.com/gokoro/zaifexport
```
もしくは
```
  pip install git+https://github.com/gokoro/zaifexport
```

# 使用例

- ヘルプ
```
 # zaifexport -h
    Usage:
      zaifexport [options] KEY SECRET EXPORT_TYPE [FILE]
    
    Arguments:
      KEY  APIキー
      SECRET  APIシークレット
      EXPORT_TYPE  spot(現物), margin(信用), future(先物) のいずれかを指定
      FILE  出力先ファイル名の指定、省略時は標準出力

    Options:
      --wait-interval SECONDS  API呼び出し制限時の待ち時間 [default: 30.0]

    Example:
      zaifexport 11111111-2222-3333-4444-555555555555 aaaaaaaa-bbbb-cccc-eeee-eeeeeeeeeeee spot spot.csv
```

- 現物の取引履歴
```
  zaifexport 11111111-2222-3333-4444-555555555555 aaaaaaaa-bbbb-cccc-eeee-eeeeeeeeeeee spot spot.csv
```

- 信用の取引履歴
```
  zaifexport 11111111-2222-3333-4444-555555555555 aaaaaaaa-bbbb-cccc-eeee-eeeeeeeeeeee margin margin.csv
```

- 先物の取引履歴
```
  zaifexport 11111111-2222-3333-4444-555555555555 aaaaaaaa-bbbb-cccc-eeee-eeeeeeeeeeee future future.csv
```

# ライセンス

MIT

