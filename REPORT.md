# 验证报告

## A 游戏工程 -list
```
Command line invocation:
    /Applications/Xcode_16.4.app/Contents/Developer/usr/bin/xcodebuild -project NarutoSenki.xcodeproj -list

Information about project "NarutoSenki":
    Targets:
        NarutoSenki

    Build Configurations:
        Debug
        Release

    If no build configuration is specified and -scheme is not passed then "Debug" is used.

    Schemes:
        cocos2dx
        NarutoSenki

```

## B 子工程 -list
```
Command line invocation:
    /Applications/Xcode_16.4.app/Contents/Developer/usr/bin/xcodebuild -project ../../../cocos2dx/proj.ios/cocos2dx.xcodeproj -list

Information about project "cocos2dx":
    Targets:
        cocos2dx

    Build Configurations:
        Debug
        Release

    If no build configuration is specified and -scheme is not passed then "Release" is used.

    Schemes:
        cocos2dx

```
