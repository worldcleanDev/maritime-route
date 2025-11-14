# Land-Sea Checker & Maritime Route Planner

OpenStreetMap Land Polygons 데이터를 사용하여 좌표가 육지인지 바다인지 판별하고, 해상 경로를 계산하는 CLI 도구입니다.

## 필수 요구사항

- Python 3.8 이상
- OpenStreetMap Land Polygons 데이터

## 설치

### 1. 필요한 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. Land Polygons 데이터 다운로드

1. https://osmdata.openstreetmap.de/data/land-polygons.html 방문
2. **land-polygons-split-4326** (Shapefile 형식) 다운로드
3. `land-sea-checker/land-polygons/` 폴더에 압축 해제

데이터 구조 예시:
```
land-sea-checker/
├── land-polygons/
│   ├── land_polygons.shp
│   ├── land_polygons.shx
│   ├── land_polygons.dbf
│   ├── land_polygons.prj
│   └── land_polygons.cpg
├── main.py
├── polygon_checker.py
├── navigation.py
└── requirements.txt
```

## 사용법

### 1. 좌표 확인 (육지/바다 판별)

```bash
python main.py check [위도] [경도]
```

**예시:**
```bash
python main.py check 37.5665 126.9780  # 서울 (육지)
python main.py check 35.0 129.0        # 동해 (바다)
python main.py check 32.01159 120.75667 # 양쯔강 (수면)
```

### 2. 해상 경로 계산

```bash
python main.py route [출발_위도] [출발_경도] [도착_위도] [도착_경도]
```

**예시:**
```bash
# 기본 사용
python main.py route 35.1 129.0 33.5 126.5

# 상세 옵션 지정
python main.py route 35.1 129.0 33.5 126.5 --step 5 --clearance 15 --max-iter 2000
```

**옵션:**
- `--step`: 각 단계의 이동 거리 (km, 기본값: 10)
- `--clearance`: 해안선으로부터 최소 유지 거리 (km, 기본값: 10)
- `--max-iter`: 최대 반복 횟수 (기본값: 1000)

## 특징

✅ **API 호출 없음** - 완전히 오프라인으로 작동
✅ **빠른 판별** - Shapely prepared geometry로 최적화
✅ **해안선 회피** - 설정 가능한 안전 거리 유지
✅ **양방향 탐색** - 좌/우 두 경로를 동시에 탐색
✅ **직선 경로 최적화** - 가능하면 최단 거리로 이동
✅ **경로 병합** - 두 경로가 만나면 더 짧은 것 선택

## 알고리즘 설명

이 도구는 다음과 같은 방식으로 해상 경로를 계산합니다:

1. **Haversine 공식**으로 직선 거리와 초기 방향 계산
2. 해안선으로부터 **최소 안전 거리 유지**
3. 장애물을 만나면 **좌/우 두 경로로 분기**
4. 주기적으로 **직선 경로 가능 여부 확인** (최적화)
5. 두 경로가 가까워지면 **더 짧은 경로만 유지**
6. 막다른 길에 도달한 경로는 **자동으로 포기**

## 성능 최적화

- **Prepared Geometry**: Shapely의 최적화된 공간 인덱스 사용
- **Bounding Box**: 거리 계산 시 근처 폴리곤만 검색
- **싱글톤 패턴**: Land polygons 데이터를 한 번만 로드

## 주의사항

⚠️ **이 도구는 교육 및 프로토타입 목적으로 제작되었습니다.**

실제 항해에는 사용하지 마세요. 다음 요소들이 고려되지 않았습니다:
- 수심 (Draft/Depth)
- 조류 및 해류
- 날씨 및 파고
- 항로 표지 및 등대
- 국제 해상 교통 규칙
- 항만 접근 규정

전문적인 해상 내비게이션은 공인된 시스템을 사용하세요.

## 라이선스

- 이 프로젝트: MIT License
- OpenStreetMap 데이터: ODbL (Open Database License)
