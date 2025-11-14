import os
import pickle
import hashlib
from pathlib import Path
from typing import Tuple, Optional, List
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.prepared import prep
from shapely import ops
import shapefile
from rtree import index

# 황해(Yellow Sea) 주요 항로 구역 - 고정 바운딩 박스
YELLOW_SEA_BBOX = {
    "name": "Yellow Sea Maritime Routes",
    "description": "중국 동부 해안과 한국 서해안 사이의 주요 항로 구역",
    "bbox": (19.40, 106.90, 41.68, 129.00),  # (min_lat, min_lon, max_lat, max_lon)
    "major_routes": [
        "홍콩 - 인천 (Hong Kong - Incheon)",
        "인천 - 청도 (Incheon - Qingdao)",
        "인천 - 상하이 (Incheon - Shanghai)",
        "평택 - 연운항 (Pyeongtaek - Lianyungang)",
        "목포 - 상하이 (Mokpo - Shanghai)",
        "부산 - 칭다오 (Busan - Qingdao)"
    ]
}

class LandPolygonChecker:
    """
    OpenStreetMap Land Polygons 데이터를 사용하여 육지/바다를 판별하는 클래스.
    황해 구역에 최적화된 캐싱 시스템 포함.
    """
    
    def __init__(self, data_path: Optional[str] = None, bbox: Optional[Tuple[float, float, float, float]] = None, use_yellow_sea_cache: bool = False):
        """
        :param data_path: Land polygons shapefile 경로 (.shp 파일)
        :param bbox: 바운딩 박스 (min_lat, min_lon, max_lat, max_lon)
        :param use_yellow_sea_cache: 황해 최적화 캐시 사용 여부
        """
        self.data_path = data_path or self._get_default_data_path()
        self.use_yellow_sea_cache = use_yellow_sea_cache
        
        # 황해 최적화 캐시 사용 시 고정 bbox 적용
        if use_yellow_sea_cache and bbox is None:
            self.bbox = YELLOW_SEA_BBOX["bbox"]
            print(f"🌊 Using Yellow Sea optimized cache")
            print(f"   Region: {YELLOW_SEA_BBOX['name']}")
            print(f"   Coverage: {YELLOW_SEA_BBOX['description']}")
            print(f"   Major routes:")
            for route in YELLOW_SEA_BBOX["major_routes"]:
                print(f"     - {route}")
        else:
            self.bbox = bbox
        
        self.land_polygons = []
        self.prepared_geometry = None
        self.spatial_index = None  # R-tree 공간 인덱스
        
        if os.path.exists(self.data_path):
            self._load_data()
        else:
            print(f"Warning: Land polygons data not found at {self.data_path}")
            print("Please download from: https://osmdata.openstreetmap.de/data/land-polygons.html")
            print("Download 'land-polygons-split-4326' and extract to land-sea-checker/land-polygons/")
    
    def _get_default_data_path(self) -> str:
        """기본 데이터 경로 반환"""
        current_dir = Path(__file__).parent
        data_dir = current_dir / "land-polygons-split"
        return str(data_dir / "land_polygons.shp")
    
    def _get_cache_path(self, bbox: Tuple[float, float, float, float]) -> Path:
        """bbox에 대한 캐시 파일 경로 생성"""
        cache_dir = Path(__file__).parent / "cache"
        cache_dir.mkdir(exist_ok=True)
        
        # 황해 최적화 캐시는 고정 이름 사용
        if self.use_yellow_sea_cache and bbox == YELLOW_SEA_BBOX["bbox"]:
            return cache_dir / "yellow_sea_optimized.pkl"
        
        # 일반 bbox 캐시는 해시 기반
        bbox_str = f"{bbox[0]:.4f}_{bbox[1]:.4f}_{bbox[2]:.4f}_{bbox[3]:.4f}"
        bbox_hash = hashlib.md5(bbox_str.encode()).hexdigest()[:12]
        return cache_dir / f"polygons_{bbox_hash}.pkl"
    
    def _load_from_cache(self, bbox: Tuple[float, float, float, float]) -> bool:
        """캐시에서 데이터 로드 시도"""
        cache_path = self._get_cache_path(bbox)
        
        if not cache_path.exists():
            return False
        
        try:
            print(f"Loading from cache: {cache_path.name}...")
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)
            
            # 캐시 버전 확인
            if cache_data.get('version') != '1.0':
                print("Cache version mismatch, rebuilding...")
                return False
            
            # 황해 최적화 캐시 확인
            if self.use_yellow_sea_cache:
                if cache_data.get('region') != 'yellow_sea':
                    print("Not a Yellow Sea cache, rebuilding...")
                    return False
            
            # bbox 확인
            if cache_data.get('bbox') != bbox:
                print("Cache bbox mismatch, rebuilding...")
                return False
            
            self.land_polygons = cache_data['polygons']
            self.spatial_index = cache_data['spatial_index']
            
            # prepared_geometry는 캐시하지 않고 다시 생성
            print("Preparing unified geometry...")
            unified_geometry = ops.unary_union(self.land_polygons)
            self.prepared_geometry = prep(unified_geometry)
            
            print(f"✓ Loaded {len(self.land_polygons)} polygons from cache")
            return True
            
        except Exception as e:
            print(f"Cache load failed: {e}, rebuilding...")
            return False
    
    def _save_to_cache(self, bbox: Tuple[float, float, float, float]):
        """현재 데이터를 캐시에 저장"""
        cache_path = self._get_cache_path(bbox)
        
        try:
            print(f"Saving to cache: {cache_path.name}...")
            cache_data = {
                'version': '1.0',
                'bbox': bbox,
                'polygons': self.land_polygons,
                'spatial_index': self.spatial_index
                # prepared_geometry는 pickle 불가능하므로 제외
            }
            
            # 황해 최적화 캐시 메타데이터 추가
            if self.use_yellow_sea_cache and bbox == YELLOW_SEA_BBOX["bbox"]:
                cache_data['region'] = 'yellow_sea'
                cache_data['region_info'] = YELLOW_SEA_BBOX
            
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            file_size_mb = cache_path.stat().st_size / (1024 * 1024)
            print(f"✓ Cache saved: {file_size_mb:.1f} MB")
            
        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")
    
    def _load_data(self):
        """Land polygons 데이터 로드 (지정된 영역만 필터링)"""
        print(f"Loading land polygons from {self.data_path}...")
        
        # 바운딩 박스 설정 (사용자 지정 또는 기본값)
        if self.bbox:
            min_lat, min_lon, max_lat, max_lon = self.bbox
            print(f"Using custom bounding box: {min_lat}°N-{max_lat}°N, {min_lon}°E-{max_lon}°E")
        else:
            # 기본: 한국과 중국 연안을 포함하는 바운딩 박스
            # 위도: 20°N ~ 45°N (중국 남부 ~ 한국 북부)
            # 경도: 110°E ~ 135°E (중국 동부 ~ 일본 서부)
            min_lat, max_lat = 20.0, 45.0
            min_lon, max_lon = 110.0, 135.0
            print(f"Using default region: {min_lat}°N-{max_lat}°N, {min_lon}°E-{max_lon}°E")
        
        # 캐시된 bbox 형식
        cache_bbox = (min_lat, min_lon, max_lat, max_lon)
        
        # 캐시에서 로드 시도
        if self._load_from_cache(cache_bbox):
            return
        
        print("Cache not found or invalid, building from shapefile...")
        
        try:
            # pyshp를 사용하여 shapefile 읽기
            sf = shapefile.Reader(self.data_path)
            
            print("Building R-tree spatial index...")
            
            # R-tree 인덱스 생성
            idx = index.Index()
            polygons = []
            polygon_id = 0
            
            # 모든 shape를 순회하며 bbox 필터링 및 인덱스 구축
            total_shapes = len(sf.shapes())
            print(f"Scanning {total_shapes} shapes...")
            
            for i, shape_obj in enumerate(sf.iterShapes()):
                if i % 5000 == 0 and i > 0:
                    print(f"  Indexed {i}/{total_shapes} shapes, kept {len(polygons)} in region...")
                
                # shape의 바운딩 박스 확인
                shape_bbox = shape_obj.bbox  # pyright: ignore[reportOptionalMemberAccess] # [minx, miny, maxx, maxy]
                
                # 관심 영역과 겹치는지 확인
                if not (shape_bbox[0] <= max_lon and shape_bbox[2] >= min_lon and
                        shape_bbox[1] <= max_lat and shape_bbox[3] >= min_lat):
                    continue  # 관심 영역 밖
                
                # Shapefile의 points를 Shapely Polygon으로 변환
                if shape_obj.shapeType == 5:  # pyright: ignore[reportOptionalMemberAccess] # Polygon
                    coords = list(shape_obj.points) # pyright: ignore[reportOptionalMemberAccess]
                    if len(coords) >= 3:
                        try:
                            polygon = Polygon(coords) # pyright: ignore[reportArgumentType]
                            if polygon.is_valid:
                                # R-tree에 폴리곤의 바운딩 박스 추가
                                # 형식: (minx, miny, maxx, maxy)
                                bounds = polygon.bounds
                                idx.insert(polygon_id, bounds)
                                polygons.append(polygon)
                                polygon_id += 1
                        except Exception:
                            continue  # 잘못된 폴리곤 무시
            
            self.land_polygons = polygons
            self.spatial_index = idx
            print(f"✓ Built R-tree index with {len(polygons)} land polygons")
            
            if len(polygons) == 0:
                print("Warning: No polygons found in the specified region!")
                self.prepared_geometry = None
                return
            
            # 모든 폴리곤을 하나로 합침 (성능 향상)
            print("Preparing unified geometry for fast lookup...")
            unified_geometry = ops.unary_union(polygons)
            self.prepared_geometry = prep(unified_geometry)
            print("✓ Geometry preparation complete!")
            
            # 캐시에 저장
            self._save_to_cache(cache_bbox)
            
        except Exception as e:
            print(f"Error loading land polygons: {e}")
            import traceback
            traceback.print_exc()
            self.land_polygons = []
            self.prepared_geometry = None
    
    def is_land(self, lat: float, lon: float) -> bool:
        """
        좌표가 육지인지 확인합니다.
        
        :param lat: 위도
        :param lon: 경도
        :return: 육지이면 True, 바다이면 False
        """
        if self.prepared_geometry is None:
            raise RuntimeError("Land polygons data not loaded. Cannot check coordinates.")
        
        point = Point(lon, lat)  # Shapely는 (경도, 위도) 순서 사용
        return self.prepared_geometry.contains(point)
    
    def get_distance_to_land(self, lat: float, lon: float) -> float:
        """
        좌표에서 가장 가까운 육지까지의 거리를 계산합니다 (근사값, 도 단위).
        
        :param lat: 위도
        :param lon: 경도
        :return: 육지까지의 거리 (도 단위, 대략 111km = 1도)
        """
        if not self.land_polygons or self.spatial_index is None:
            raise RuntimeError("Land polygons data not loaded.")
        
        point = Point(lon, lat)
        
        if self.prepared_geometry and self.prepared_geometry.contains(point):
            return 0.0  # 육지 위에 있음
        
        # R-tree를 사용하여 근처 폴리곤 찾기 (1도 반경)
        search_radius = 1.0
        search_bbox = (lon - search_radius, lat - search_radius, 
                      lon + search_radius, lat + search_radius)
        
        # R-tree에서 후보 폴리곤 ID 가져오기
        candidate_ids = list(self.spatial_index.intersection(search_bbox))
        
        if not candidate_ids:
            return float('inf')  # 근처에 육지 없음
        
        # 가장 가까운 육지까지의 거리 계산
        min_distance = float('inf')
        for poly_id in candidate_ids:
            polygon = self.land_polygons[poly_id]
            distance = point.distance(polygon)
            min_distance = min(min_distance, distance)
        
        return min_distance
    
    def is_safe_water(self, lat: float, lon: float, min_clearance_km: float = 10.0) -> bool:
        """
        좌표가 안전한 거리만큼 육지에서 떨어진 바다인지 확인합니다.
        
        :param lat: 위도
        :param lon: 경도
        :param min_clearance_km: 최소 이격 거리 (킬로미터)
        :return: 안전한 바다이면 True
        """
        if self.is_land(lat, lon):
            return False
        
        # 킬로미터를 도 단위로 변환 (대략 111km = 1도)
        min_clearance_degrees = min_clearance_km / 111.0
        
        distance = self.get_distance_to_land(lat, lon)
        return distance >= min_clearance_degrees

# 전역 인스턴스 (싱글톤 패턴)
_checker_instance = None

def get_checker(bbox: Optional[Tuple[float, float, float, float]] = None, use_yellow_sea: bool = False) -> LandPolygonChecker:
    """
    전역 LandPolygonChecker 인스턴스 반환
    
    :param bbox: 커스텀 바운딩 박스 (지정 시 황해 최적화 무시)
    :param use_yellow_sea: 황해 최적화 캐시 사용 여부
    """
    global _checker_instance
    
    # bbox가 명시적으로 지정되면 황해 최적화 비활성화
    if bbox is not None:
        use_yellow_sea = False
    
    if _checker_instance is None:
        _checker_instance = LandPolygonChecker(bbox=bbox, use_yellow_sea_cache=use_yellow_sea)
    elif bbox and _checker_instance.bbox != bbox:
        # bbox가 변경되면 새 인스턴스 생성
        _checker_instance = LandPolygonChecker(bbox=bbox, use_yellow_sea_cache=False)
    
    return _checker_instance

def initialize_yellow_sea_checker() -> LandPolygonChecker:
    """
    황해 구역 최적화 체커 초기화 (권장 방법)
    
    중국 동부 해안과 한국 서해안 사이의 주요 항로에 최적화된 체커를 생성합니다.
    """
    global _checker_instance
    print(f"\n=== Initializing Yellow Sea optimized checker ===")
    _checker_instance = LandPolygonChecker(use_yellow_sea_cache=True)
    return _checker_instance

def initialize_checker_for_route(start_lat: float, start_lon: float, 
                                 end_lat: float, end_lon: float,
                                 margin_km: float = 200.0) -> LandPolygonChecker:
    """
    특정 경로에 최적화된 체커 초기화 (커스텀 경로용)
    
    :param start_lat: 출발지 위도
    :param start_lon: 출발지 경도
    :param end_lat: 목적지 위도
    :param end_lon: 목적지 경도
    :param margin_km: 경로 주변 마진 (킬로미터)
    :return: 초기화된 LandPolygonChecker
    """
    global _checker_instance
    
    # 경로를 포함하는 바운딩 박스 계산 (마진 포함)
    margin_degrees = margin_km / 111.0  # 대략 111km = 1도
    
    min_lat = min(start_lat, end_lat) - margin_degrees
    max_lat = max(start_lat, end_lat) + margin_degrees
    min_lon = min(start_lon, end_lon) - margin_degrees
    max_lon = max(start_lon, end_lon) + margin_degrees
    
    bbox = (min_lat, min_lon, max_lat, max_lon)
    
    print(f"\n=== Initializing polygon checker for custom route ===")
    print(f"Route: ({start_lat:.4f}, {start_lon:.4f}) → ({end_lat:.4f}, {end_lon:.4f})")
    print(f"Margin: {margin_km} km ({margin_degrees:.2f}°)")
    
    _checker_instance = LandPolygonChecker(bbox=bbox, use_yellow_sea_cache=False)
    return _checker_instance

def is_land(lat: float, lon: float) -> bool:
    """
    좌표가 육지인지 확인합니다 (편의 함수).
    """
    checker = get_checker()
    return checker.is_land(lat, lon)

def is_safe_water(lat: float, lon: float, min_clearance_km: float = 10.0) -> bool:
    """
    좌표가 안전한 바다인지 확인합니다 (편의 함수).
    """
    checker = get_checker()
    return checker.is_safe_water(lat, lon, min_clearance_km)
