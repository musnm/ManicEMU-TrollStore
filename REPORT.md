# 验证报告

## A 游戏工程 -list
```
Command line invocation:
    /Applications/Xcode_16.4.app/Contents/Developer/usr/bin/xcodebuild -project NarutoSenki.xcodeproj -list

2026-11-12 01:27:26.760 xcodebuild[1363:6584] Error Domain=NSCocoaErrorDomain Code=3840 "JSON text did not start with array or object and option to allow fragments not set. around line 1, column 0." UserInfo={NSDebugDescription=JSON text did not start with array or object and option to allow fragments not set. around line 1, column 0., NSJSONSerializationErrorIndex=0}
2026-11-12 01:27:26.821 xcodebuild[1363:6584] Writing error result bundle to /var/folders/2s/vty41l455yv698g4xkgfv7z00000gn/T/ResultBundle_2026-12-11_01-27-0026.xcresult
xcodebuild: error: Unable to read project 'NarutoSenki.xcodeproj'.
	Reason: The project ‘NarutoSenki’ is damaged and cannot be opened due to a parse error. Examine the project file for invalid edits or unresolved source control conflicts.

Path: /Users/runner/work/ManicEMU-TrollStore/ManicEMU-TrollStore/src/out/projects/NarutoSenki/proj.ios/NarutoSenki.xcodeproj


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
