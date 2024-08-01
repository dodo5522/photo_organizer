# 写真整理ツール「photo_organizer」

EXIF情報を取得し、
撮影日とカメラの機種名を元に写真を整理するmac用のワークフローです。

applicationとして実行します。

## インストール

1. ExifToolをインストールする
    - sudo apt install libimage-exiftool-perl
2. 整理したいSDカードのルートディレクトリに、環境に合わせて設定したsetting.iniを置きます。
3. SDカード等をマウントしたドライブをapplicationアイコンにD&Dすると整理開始します。
4. 整理が完了したらAutomatorが通知します。

