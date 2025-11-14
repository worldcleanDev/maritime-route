# OpenStreetMap Land Polygons 데이터 다운로드 안내

이 프로그램을 사용하려면 OpenStreetMap Land Polygons 데이터가 필요합니다.

## 다운로드 방법

1. 다음 웹사이트를 방문하세요:
   https://osmdata.openstreetmap.de/data/land-polygons.html

2. **land-polygons-split-4326** 파일을 다운로드하세요.
   - Shapefile 형식 (.shp.zip)
   - 파일 크기: 약 600MB (압축), 1.5GB (압축 해제)

3. 다운로드한 파일을 이 폴더(`data/`)에 압축 해제하세요.

## 예상 디렉토리 구조

```
land-sea-checker/
├── data/
│   └── land-polygons-split-4326/
│       ├── land_polygons.shp
│       ├── land_polygons.shx
│       ├── land_polygons.dbf
│       ├── land_polygons.prj
│       └── land_polygons.cpg
```

## 대안

전 세계 데이터가 너무 큰 경우, 특정 지역만 다운로드할 수 있습니다:
- https://download.geofabrik.de/
- 예: 아시아만 필요한 경우 "Asia" 데이터셋 다운로드

## 라이선스

OpenStreetMap 데이터는 ODbL (Open Database License)을 따릅니다.
출처: © OpenStreetMap contributors
https://www.openstreetmap.org/copyright

## 문제 해결

데이터가 제대로 로드되지 않으면:
1. 파일 경로가 올바른지 확인
2. 모든 shapefile 구성 요소(.shp, .shx, .dbf 등)가 함께 있는지 확인
3. 필요한 Python 패키지(geopandas, shapely)가 설치되었는지 확인
