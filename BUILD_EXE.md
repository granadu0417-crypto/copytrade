# EXE 빌드 가이드

바이낸스 카피트레이딩 시스템을 Windows 실행 파일(.exe)로 빌드하는 방법입니다.

## 빌드 방법

### 1. 자동 빌드 (권장)

```cmd
build_exe.bat
```

이 스크립트는 자동으로:
- PyInstaller 설치
- 이전 빌드 정리
- .exe 파일 생성
- 배포 패키지 생성 (release 폴더)

빌드에는 **5-10분** 정도 소요됩니다.

### 2. 수동 빌드

```cmd
# 1. PyInstaller 설치
pip install pyinstaller

# 2. 빌드 실행
pyinstaller --clean copytrade.spec

# 3. 결과 확인
dir dist\BinanceCopyTrading.exe
```

## 빌드 결과

빌드가 완료되면 다음 파일들이 생성됩니다:

```
release/
├── BinanceCopyTrading.exe    # 실행 파일 (약 200-400MB)
├── config.yaml                # 설정 파일
├── .env                       # 환경 변수 (API 키 입력 필요)
├── frontend/                  # 웹 대시보드
└── README.txt                 # 사용 설명서
```

## 배포 방법

### 최종 사용자에게 전달할 파일

1. **release 폴더 전체**를 압축하여 전달
2. 사용자는 압축을 풀고 다음 단계를 실행:

```cmd
# 1. Playwright 브라우저 설치 (최초 1회만)
playwright install chromium

# 2. .env 파일에 API 키 입력
notepad .env

# 3. 실행 파일 더블클릭
BinanceCopyTrading.exe
```

## 실행 파일 사용법

### 방법 1: 더블클릭으로 실행

1. `BinanceCopyTrading.exe`를 더블클릭
2. 콘솔 창이 열리면서 시스템 시작
3. 모드 선택:
   - **1**: API 서버 (웹 대시보드)
   - **2**: 자동 거래

### 방법 2: 바로가기 만들기

웹 서버 모드로 바로 시작하는 바로가기:

```cmd
BinanceCopyTrading.exe --mode=1
```

자동 거래 모드로 바로 시작하는 바로가기:

```cmd
BinanceCopyTrading.exe --mode=2
```

## 주의사항

### ✅ 장점

- Python 설치 불필요
- 가상환경 설정 불필요
- 더블클릭 한 번으로 실행
- 간편한 배포

### ⚠️ 제약사항

1. **Playwright 브라우저 필수**
   - 최초 1회 `playwright install chromium` 실행 필요
   - 약 300MB 다운로드

2. **파일 크기**
   - 실행 파일이 200-400MB로 큼
   - 모든 의존성이 포함되기 때문

3. **설정 파일 외부 유지**
   - config.yaml과 .env는 exe와 같은 폴더에 있어야 함
   - 설정 변경 시 파일 수정으로 가능

4. **바이러스 백신 오탐**
   - PyInstaller로 만든 exe는 일부 백신에서 오탐 가능
   - Windows Defender 예외 추가 필요할 수 있음

## 커스터마이징

### 아이콘 변경

1. `.ico` 파일 준비 (256x256 권장)
2. `copytrade.spec` 파일 수정:

```python
exe = EXE(
    ...
    icon='icon.ico',  # 아이콘 파일 경로
)
```

### 콘솔 창 숨기기

웹 서버만 사용하는 경우 콘솔 창을 숨길 수 있습니다:

`copytrade.spec` 파일 수정:

```python
exe = EXE(
    ...
    console=False,  # True -> False로 변경
)
```

### 단일 파일 vs 폴더 형태

**현재 설정**: 단일 파일 (onefile)
- 장점: 배포 간편
- 단점: 실행 시 임시 압축 해제로 초기 로딩 느림

**폴더 형태**로 변경하려면 `copytrade.spec`에서:

```python
exe = EXE(
    pyz,
    a.scripts,
    # 아래 4줄 제거
    # a.binaries,
    # a.zipfiles,
    # a.datas,
    # [],
    ...
)

# 추가
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BinanceCopyTrading'
)
```

## 트러블슈팅

### 빌드 실패: ModuleNotFoundError

```cmd
# 모든 의존성 재설치
pip install -r requirements.txt --force-reinstall
```

### 실행 실패: DLL 오류

Windows용 Visual C++ 재배포 패키지 설치:
https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist

### 바이러스 백신 오탐

1. Windows Defender 예외 추가:
   - 설정 → 업데이트 및 보안 → Windows 보안 → 바이러스 및 위협 방지
   - 설정 관리 → 제외 추가
   - BinanceCopyTrading.exe 파일 추가

2. 디지털 서명 추가 (고급):
   - 코드 서명 인증서 구매
   - signtool.exe로 서명

### 실행 파일 크기 줄이기

불필요한 라이브러리 제외:

```python
# copytrade.spec
a = Analysis(
    ...
    excludes=['matplotlib', 'numpy', 'scipy'],  # 사용하지 않는 큰 라이브러리
)
```

UPX 압축 활성화 (이미 활성화됨):

```python
exe = EXE(
    ...
    upx=True,  # 실행 파일 압축
)
```

## 대안: 간편 설치 프로그램

PyInstaller 대신 **Inno Setup**으로 설치 프로그램 생성:

1. https://jrsoftware.org/isinfo.php 에서 다운로드
2. 설치 스크립트 작성 (setup.iss)
3. Python, 의존성, Playwright까지 자동 설치
4. 바탕화면 바로가기 자동 생성

## 배포 체크리스트

실행 파일을 배포하기 전에 확인:

- [ ] .env 파일에 **실제 API 키가 없는지** 확인 (보안!)
- [ ] config.yaml의 testnet 모드 확인
- [ ] release 폴더에 모든 필요 파일 포함
- [ ] README.txt에 명확한 설명
- [ ] 다른 PC에서 테스트 실행
- [ ] Windows Defender 스캔 통과 확인

## 다음 단계

EXE 빌드 후:

1. **테스트 배포**: 다른 PC에서 실행 테스트
2. **문서화**: 사용자 매뉴얼 작성
3. **자동 업데이트**: 버전 체크 기능 추가 고려
4. **모니터링**: 원격 모니터링 설정

---

**참고 문서**:
- [PyInstaller 공식 문서](https://pyinstaller.org/)
- [Spec 파일 상세 설정](https://pyinstaller.org/en/stable/spec-files.html)
