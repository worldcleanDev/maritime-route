import math
from typing import List, Tuple, Dict, Optional, Set
from collections import deque
from polygon_checker import (
    is_land, is_safe_water, 
    initialize_yellow_sea_checker,
    initialize_checker_for_route,
    YELLOW_SEA_BBOX
)

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 좌표 간의 거리를 계산합니다 (킬로미터)."""
    R = 6371  # 지구 반지름 (km)
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

def quantize_coordinate(lat: float, lon: float, grid_size_km: float) -> Tuple[int, int]:
    """
    좌표를 그리드 셀로 변환합니다.
    
    :param lat: 위도
    :param lon: 경도
    :param grid_size_km: 그리드 셀 크기 (킬로미터)
    :return: (grid_lat, grid_lon) 그리드 좌표
    """
    # 1도 ≈ 111km
    grid_size_degrees = grid_size_km / 111.0
    grid_lat = int(round(lat / grid_size_degrees))
    grid_lon = int(round(lon / grid_size_degrees))
    return (grid_lat, grid_lon)

def dequantize_coordinate(grid_lat: int, grid_lon: int, grid_size_km: float) -> Tuple[float, float]:
    """
    그리드 셀을 실제 좌표로 변환합니다.
    
    :param grid_lat: 그리드 위도
    :param grid_lon: 그리드 경도
    :param grid_size_km: 그리드 셀 크기 (킬로미터)
    :return: (lat, lon) 실제 좌표
    """
    grid_size_degrees = grid_size_km / 111.0
    lat = grid_lat * grid_size_degrees
    lon = grid_lon * grid_size_degrees
    return (lat, lon)

def get_neighbors(grid_lat: int, grid_lon: int, diagonal: bool = True) -> List[Tuple[int, int]]:
    """
    그리드 셀의 이웃 셀들을 반환합니다.
    
    :param grid_lat: 그리드 위도
    :param grid_lon: 그리드 경도
    :param diagonal: 대각선 방향 포함 여부
    :return: 이웃 그리드 좌표 리스트
    """
    neighbors = [
        (grid_lat + 1, grid_lon),      # 북
        (grid_lat - 1, grid_lon),      # 남
        (grid_lat, grid_lon + 1),      # 동
        (grid_lat, grid_lon - 1),      # 서
    ]
    
    if diagonal:
        neighbors.extend([
            (grid_lat + 1, grid_lon + 1),  # 북동
            (grid_lat + 1, grid_lon - 1),  # 북서
            (grid_lat - 1, grid_lon + 1),  # 남동
            (grid_lat - 1, grid_lon - 1),  # 남서
        ])
    
    return neighbors

def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 점 사이의 방위각을 계산합니다 (0-360도)."""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)
    
    x = math.sin(delta_lon) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)
    
    bearing = math.atan2(x, y)
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360
    
    return bearing

def move_point(lat: float, lon: float, bearing: float, distance_km: float) -> Tuple[float, float]:
    """특정 방향과 거리만큼 이동한 새로운 좌표를 계산합니다."""
    R = 6371  # 지구 반지름 (km)
    
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    bearing_rad = math.radians(bearing)
    
    new_lat_rad = math.asin(
        math.sin(lat_rad) * math.cos(distance_km / R) +
        math.cos(lat_rad) * math.sin(distance_km / R) * math.cos(bearing_rad)
    )
    
    new_lon_rad = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(distance_km / R) * math.cos(lat_rad),
        math.cos(distance_km / R) - math.sin(lat_rad) * math.sin(new_lat_rad)
    )
    
    new_lat = math.degrees(new_lat_rad)
    new_lon = math.degrees(new_lon_rad)
    
    return (new_lat, new_lon)

def is_path_clear(lat1: float, lon1: float, lat2: float, lon2: float, 
                  step_km: float = 5.0, min_clearance_km: float = 10.0) -> bool:
    """
    두 점 사이의 직선 경로가 해안선으로부터 안전한 거리를 유지하는지 확인합니다.
    """
    total_distance = haversine_distance(lat1, lon1, lat2, lon2)
    bearing = calculate_bearing(lat1, lon1, lat2, lon2)
    
    steps = int(total_distance / step_km) + 1
    
    for i in range(steps + 1):
        progress = i / steps if steps > 0 else 1
        check_lat, check_lon = move_point(lat1, lon1, bearing, total_distance * progress)
        
        # polygon_checker의 is_safe_water 함수 사용
        if not is_safe_water(check_lat, check_lon, min_clearance_km):
            return False
    
    return True

def wave_propagation_search(start_lat: float, start_lon: float,
                           end_lat: float, end_lon: float,
                           grid_size_km: float,
                           min_clearance_km: float) -> Optional[Dict]:
    """
    파동 전파 방식으로 최적 경로를 탐색합니다.
    
    물을 목적지에서 붓듯이, 목적지에서 파동을 퍼뜨려 출발지까지 도달하는 경로를 찾습니다.
    
    :param start_lat: 출발지 위도
    :param start_lon: 출발지 경도
    :param end_lat: 목적지 위도
    :param end_lon: 목적지 경도
    :param grid_size_km: 그리드 셀 크기 (킬로미터)
    :param min_clearance_km: 해안선으로부터 최소 거리
    :return: 경로 정보 또는 None
    """
    print("=== Wave Propagation Search ===")
    print(f"Grid size: {grid_size_km} km")
    
    # 좌표를 그리드로 변환
    start_grid = quantize_coordinate(start_lat, start_lon, grid_size_km)
    end_grid = quantize_coordinate(end_lat, end_lon, grid_size_km)
    
    print(f"Start grid: {start_grid}")
    print(f"End grid: {end_grid}")
    
    # BFS를 위한 자료구조
    queue = deque([end_grid])
    visited: Set[Tuple[int, int]] = {end_grid}
    parent_map: Dict[Tuple[int, int], Tuple[int, int]] = {}
    distance_map: Dict[Tuple[int, int], int] = {end_grid: 0}
    
    iteration = 0
    max_iterations = 1000000  # 안전장치
    
    print("\nPropagating wave from destination...")
    
    while queue and iteration < max_iterations:
        iteration += 1
        
        if iteration % 1000 == 0:
            print(f"  Wave front size: {len(queue)}, Visited: {len(visited)}")
        
        current_grid = queue.popleft()
        current_distance = distance_map[current_grid]
        
        # 출발지에 도달했으면 종료
        if current_grid == start_grid:
            print(f"\n✓ Wave reached start point after {iteration} iterations!")
            print(f"Total cells visited: {len(visited)}")
            
            # 경로 재구성
            path_grids = []
            current = start_grid
            while current in parent_map:
                path_grids.append(current)
                current = parent_map[current]
            path_grids.append(end_grid)
            
            # 그리드를 실제 좌표로 변환
            waypoints = [dequantize_coordinate(g[0], g[1], grid_size_km) for g in path_grids]
            
            # 총 거리 계산
            total_distance = 0.0
            for i in range(len(waypoints) - 1):
                total_distance += haversine_distance(
                    waypoints[i][0], waypoints[i][1],
                    waypoints[i+1][0], waypoints[i+1][1]
                )
            
            return {
                "success": True,
                "waypoints": waypoints,
                "total_distance": total_distance,
                "grid_cells": len(path_grids),
                "iterations": iteration,
                "visited_cells": len(visited)
            }
        
        # 이웃 셀들로 파동 전파
        for neighbor_grid in get_neighbors(current_grid[0], current_grid[1]):
            if neighbor_grid in visited:
                continue
            
            # 실제 좌표로 변환하여 안전성 확인
            neighbor_lat, neighbor_lon = dequantize_coordinate(
                neighbor_grid[0], neighbor_grid[1], grid_size_km
            )
            
            # 안전한 바다인지 확인
            if is_safe_water(neighbor_lat, neighbor_lon, min_clearance_km):
                visited.add(neighbor_grid)
                parent_map[neighbor_grid] = current_grid
                distance_map[neighbor_grid] = current_distance + 1
                queue.append(neighbor_grid)
    
    print(f"\n✗ Wave did not reach start point after {iteration} iterations")
    print(f"Total cells visited: {len(visited)}")
    return None

def find_sea_route(start_lat: float, start_lon: float, 
                   end_lat: float, end_lon: float,
                   step_km: float = 10.0,
                   min_clearance_km: float = 10.0,
                   max_iterations: int = 1000) -> Dict:
    """
    두 점 사이의 해상 경로를 찾습니다.
    
    파동 전파(Wave Propagation) 알고리즘:
    1. 경로 주변의 육지 폴리곤만 로드
    2. 목적지에서 "물"을 붓듯이 파동을 사방으로 전파
    3. 육지를 만나면 파동이 멈춤 (장벽)
    4. 출발지에 파동이 도달하면 경로 역추적
    5. 최적 경로(최단 거리) 보장
    """
    print(f"\n{'='*60}")
    print(f"MARITIME ROUTE CALCULATION")
    print(f"{'='*60}")
    print(f"From: ({start_lat:.6f}, {start_lon:.6f})")
    print(f"To:   ({end_lat:.6f}, {end_lon:.6f})")
    print(f"Min clearance: {min_clearance_km} km")
    print(f"Grid size: {step_km} km\n")
    
    # 경로가 황해 구역 내에 있는지 확인
    bbox = YELLOW_SEA_BBOX["bbox"]
    min_lat_bbox, min_lon_bbox, max_lat_bbox, max_lon_bbox = bbox
    
    in_yellow_sea = (
        min_lat_bbox <= start_lat <= max_lat_bbox and min_lon_bbox <= start_lon <= max_lon_bbox and
        min_lat_bbox <= end_lat <= max_lat_bbox and min_lon_bbox <= end_lon <= max_lon_bbox
    )
    
    if in_yellow_sea:
        print("🌊 Route is within Yellow Sea region - using optimized cache\n")
        initialize_yellow_sea_checker()
    else:
        print("⚠️  Route is outside Yellow Sea region - using custom bbox\n")
        margin_km = max(200.0, min_clearance_km * 5)
        initialize_checker_for_route(start_lat, start_lon, end_lat, end_lon, margin_km)
    
    print("\n--- Validating start and end points ---")
    # 출발지와 목적지가 안전한 바다인지 확인
    if not is_safe_water(start_lat, start_lon, min_clearance_km):
        return {"error": "Start point is not in safe water", "waypoints": [], "iterations": 0}
    print("✓ Start point is in safe water")
    
    if not is_safe_water(end_lat, end_lon, min_clearance_km):
        return {"error": "End point is not in safe water", "waypoints": [], "iterations": 0}
    print("✓ End point is in safe water")
    
    # 직선 거리 계산
    direct_distance = haversine_distance(start_lat, start_lon, end_lat, end_lon)
    print(f"\n--- Route Information ---")
    print(f"Direct distance: {direct_distance:.2f} km\n")
    
    # 파동 전파로 경로 탐색
    result = wave_propagation_search(
        start_lat, start_lon,
        end_lat, end_lon,
        step_km,
        min_clearance_km
    )
    
    if result is None:
        return {
            "error": "No route found - destination unreachable",
            "waypoints": [],
            "iterations": 0
        }
    
    # 결과에 직선 거리와 효율성 추가
    result["direct_distance"] = direct_distance
    result["efficiency"] = (direct_distance / result["total_distance"] * 100) if result["total_distance"] > 0 else 0
    
    return result
