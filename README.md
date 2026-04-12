# ApiTrak — IoT Asset Tracking Platform

> Real-time GPS tracking for vehicles, containers, personnel, and equipment.

---

## Table of Contents

- [English Version](#english-version)
  - [Overview](#overview)
  - [Business Logic](#business-logic)
  - [Architecture Design](#architecture-design)
  - [Data Flow](#data-flow)
  - [API Reference](#api-reference)
  - [Setup Guide](#setup-guide)
  - [Simulating Devices](#simulating-devices)
- [Phiên Bản Tiếng Việt](#phiên-bản-tiếng-việt)
  - [Tổng Quan](#tổng-quan)
  - [Logic Nghiệp Vụ](#logic-nghiệp-vụ)
  - [Thiết Kế Kiến Trúc](#thiết-kế-kiến-trúc)
  - [Luồng Dữ Liệu](#luồng-dữ-liệu)
  - [Tài Liệu API](#tài-liệu-api)
  - [Hướng Dẫn Cài Đặt](#hướng-dẫn-cài-đặt)
  - [Mô Phỏng Thiết Bị](#mô-phỏng-thiết-bị)

---

# English Version

## Overview

**ApiTrak** is a production-grade IoT asset tracking platform built with a microservice architecture. It enables organisations to track the real-time GPS positions of their assets (vehicles, containers, people, equipment) on a live map, define geographic boundaries (geofences), and receive instant alerts when assets enter or exit those boundaries.

### Key Features

| Feature | Description |
|---|---|
| Live Map | Real-time device positions updated via WebSocket — zero polling |
| Historical Track | Query full movement history for any device across any time range |
| Geofence Alerts | Instant push notifications when a device crosses a geofence boundary |
| Device Management | Create and manage IoT devices with secure API key authentication |
| Asset Management | Attach devices to assets (vehicles, people, equipment) |
| Multi-Organisation | Isolated data per organisation; scoped JWT tokens for WebSocket auth |

---

## Business Logic

### Entities and Relationships

```
Organization
  └── Asset (vehicle / container / person / equipment)
        └── Device (1 IoT device per asset)
              └── LocationRecord[] (time-series position history)

Organization
  └── Geofence[] (named geographic boundaries)
```

### Authentication Flow

```
1. User logs in          POST /api/v1/token/
                         → returns access token (15 min) + refresh token (7 days)

2. User selects org      POST /api/v1/token/org-scope/  { org_id }
                         → returns org-scoped JWT (8 h) with org_id claim
                           used exclusively for WebSocket connections

3. Access token expires  POST /api/v1/token/refresh/
                         → silent auto-refresh by the frontend interceptor
                           user never sees a logout
```

### Device Telemetry Flow

IoT firmware sends GPS pings directly to the **FastAPI ingestion service** using a secret API key. This is machine-to-machine; no human UI is involved.

```
IoT Device  →  POST /ingest  (X-API-Key: <raw_key>)
               FastAPI authenticates via Redis lookup (zero SQL)
               Stores position in Redis (TTL 1 hour)
               Publishes event to Redis Stream
                   ├── Django Channels  →  WebSocket broadcast to all browsers
                   ├── Celery cold_write →  Persist to PostGIS (LocationRecord)
                   └── Celery geofences →  Check PostGIS spatial containment
                                           If crossed boundary → WebSocket geofence_event
```

### Geofence Logic

1. Celery geofence worker receives lat/lng from Redis Stream.
2. Queries PostGIS `MultiPolygonField` for all active geofences containing that point.
3. Compares current containment set against previous state stored in Redis Set.
4. Fires `entered` / `exited` events only on **state transitions** (not on every ping).
5. Broadcasts geofence events via Django Channels WebSocket to all connected browsers.

### Live Map vs. Historical Track

| | Live Map | Historical Track |
|---|---|---|
| Data source | Redis Hot Storage (O(1)) | PostGIS LocationRecord table |
| Fallback | Latest DB record if Redis TTL expired | N/A |
| SQL queries | 0 (fast path) / 1 (fallback) | Yes (cursor-paginated) |
| Real-time | Yes, via WebSocket | No, snapshot query |

### API Key Security

- Raw API keys are **never stored** anywhere in the system.
- Only the **SHA-256 hex digest** is stored in PostgreSQL (`api_key_hash`).
- FastAPI authenticates a device by hashing the incoming `X-API-Key` header and looking up the hash in Redis.
- If you lose an API key, create a new one via `PATCH /api/v1/devices/{id}/` with a new `api_key` value.

---

## Architecture Design

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser (port 3000)                     │
│                    React + Vite + TypeScript                     │
│         Leaflet Maps │ TanStack Query │ Zustand │ Axios          │
└──────────┬──────────────────────────┬──────────────────────────┘
           │ REST (HTTP/S)            │ WebSocket (WS/WSS)
           ▼                          ▼
┌──────────────────────┐   ┌──────────────────────────────────────┐
│  Django Core         │   │  Django Channels (ASGI)              │
│  port 8000           │   │  ws://.../ws/tracking/<org_id>/      │
│                      │   │  JWT-authenticated per org           │
│  DRF REST API        │   └──────────────┬───────────────────────┘
│  - Organizations     │                  │ Channel Layer (Redis)
│  - Assets            │                  ▼
│  - Devices           │   ┌──────────────────────────────────────┐
│  - Geofences         │   │  Redis                               │
│  - Live Map          │   │  ├─ Hot Storage  device:*:position   │
│  - Track History     │   │  ├─ Org index   org:*:device_ids     │
│  - JWT Auth          │   │  ├─ Device creds device_creds:*      │
└──────────┬───────────┘   │  ├─ Telemetry Stream                │
           │               │  ├─ Celery broker/results            │
           │               │  └─ Channel Layer                    │
           ▼               └──────┬─────────────────┬────────────┘
┌──────────────────────┐          │                 │
│  PostgreSQL/PostGIS  │    ┌─────▼──────┐   ┌──────▼──────────┐
│  port 5432           │    │  Celery    │   │  FastAPI         │
│                      │◄───│  cold_write│   │  Ingestion       │
│  - organizations     │    │  worker    │   │  port 8001       │
│  - assets            │    └─────┬──────┘   │                  │
│  - devices           │    ┌─────▼──────┐   │  POST /ingest    │
│  - geofences         │    │  Celery    │   │  X-API-Key auth  │
│  - location_records  │◄───│  geofences │   │  Rate limited    │
│                      │    │  worker    │   │  120 req/min     │
└──────────────────────┘    └────────────┘   └──────────────────┘
                                                      ▲
                                             IoT Devices / GPS firmware
                                             (Machine-to-machine, no UI)
```

### Services

| Service | Technology | Port | Role |
|---|---|---|---|
| `postgres` | PostgreSQL 16 + PostGIS 3.4 | 5432 | Relational + spatial data store |
| `redis` | Redis 7 | 6379 | Hot storage, streams, broker, channel layer |
| `django-core` | Django 5 + DRF + Channels | 8000 | REST API, WebSocket hub, admin |
| `fastapi-ingestion` | FastAPI + uvicorn | 8001 | High-throughput IoT telemetry ingestion |
| `celery-worker-cold-write` | Celery | — | Async PostGIS writes |
| `celery-worker-geofences` | Celery | — | Spatial boundary evaluation |
| `react-frontend` | React 18 + Vite | 3000 | Single-page web application |

### Technology Stack

**Backend**
- Django 5, Django REST Framework, djangorestframework-gis
- Django Channels 4 (ASGI WebSocket via Daphne/uvicorn)
- Celery 5 (async task queue)
- FastAPI 0.115, Pydantic v2
- PostgreSQL 16 + PostGIS 3.4
- Redis 7

**Frontend**
- React 18, Vite, TypeScript
- Leaflet.js + react-leaflet + Leaflet.Draw
- TanStack Query v5 (data fetching & caching)
- Zustand v5 (auth state, persisted to localStorage)
- Axios (HTTP client, JWT auto-refresh interceptor)
- TailwindCSS

**Auth**
- simplejwt — access token 15 min, refresh token 7 days, auto-rotate
- Org-scoped HS256 JWT for WebSocket — 8 hour validity

---

## Data Flow

### Telemetry Hot Path (low latency)

```
IoT GPS Ping
  → FastAPI /ingest (authenticated in ~1 ms via Redis)
  → Redis HSET device:{id}:position  (TTL 1 hour)
  → Redis XADD telemetry_stream
  → Stream Consumer (async loop in ASGI process)
      → Channel Layer group_send  →  WebSocket → Browser map update (~50 ms)
      → Celery cold_write.delay() →  PostGIS INSERT (async, ~200 ms)
      → Celery geofences.delay()  →  PostGIS spatial query → geofence_event
```

### Live Map Fetch (on page load)

```
Browser GET /api/v1/map/{org_id}/live/
  → Redis SMEMBERS org:{org_id}:device_ids
  → Redis Pipeline HGETALL device:{id}:position × N  (zero SQL)
  → If any position key expired:
      → PostGIS: SELECT DISTINCT ON (device_id) ... ORDER BY device_id, -timestamp
      → Re-seed Redis with the fetched position
  → Return JSON {org_id, devices: [...]}
```

### WebSocket Connection

```
Browser  →  ws://host/ws/tracking/{org_id}/?token={org_jwt}
          Channels authenticates JWT (org_id claim must match URL)
          Joins group org_{org_id}_tracking
          Receives:
            - location_update  {type, device_id, lat, lng, timestamp, speed, heading, battery}
            - geofence_event   {type, device_id, geofence_id, event: "entered"|"exited"}
```

---

## API Reference

### Auth

| Method | URL | Body | Description |
|---|---|---|---|
| `POST` | `/api/v1/token/` | `{username, password}` | Login, get access + refresh tokens |
| `POST` | `/api/v1/token/refresh/` | `{refresh}` | Refresh access token |
| `POST` | `/api/v1/token/org-scope/` | `{org_id}` | Get org-scoped JWT for WebSocket |

### Organizations

| Method | URL | Description |
|---|---|---|
| `GET` | `/api/v1/organizations/` | List all organisations |
| `POST` | `/api/v1/organizations/` | Create organisation |
| `GET` | `/api/v1/organizations/{id}/` | Get one |
| `PATCH` | `/api/v1/organizations/{id}/` | Update |
| `DELETE` | `/api/v1/organizations/{id}/` | Delete |

### Assets

| Method | URL | Description |
|---|---|---|
| `GET` | `/api/v1/assets/` | List assets |
| `POST` | `/api/v1/assets/` | Create asset |
| `PATCH` | `/api/v1/assets/{id}/` | Update asset |
| `DELETE` | `/api/v1/assets/{id}/` | Delete asset |

### Devices

| Method | URL | Description |
|---|---|---|
| `GET` | `/api/v1/devices/` | List devices (api_key never returned) |
| `POST` | `/api/v1/devices/` | Create device (`api_key` required — save it!) |
| `PATCH` | `/api/v1/devices/{id}/` | Update device (pass new `api_key` to rotate) |
| `DELETE` | `/api/v1/devices/{id}/` | Delete device |

### Geofences

| Method | URL | Description |
|---|---|---|
| `GET` | `/api/v1/geofences/?org_id={id}` | List geofences as GeoJSON FeatureCollection |
| `POST` | `/api/v1/geofences/` | Create geofence (GeoJSON Feature body) |
| `PATCH` | `/api/v1/geofences/{id}/` | Update geofence |
| `DELETE` | `/api/v1/geofences/{id}/` | Delete geofence |

### Tracking

| Method | URL | Description |
|---|---|---|
| `GET` | `/api/v1/map/{org_id}/live/` | Latest positions for all org devices |
| `GET` | `/api/v1/devices/{id}/track/?after=&before=` | Historical track (cursor-paginated) |
| `WS` | `ws://host/ws/tracking/{org_id}/?token=` | Live WebSocket feed |

### Ingestion (FastAPI — port 8001)

| Method | URL | Header | Description |
|---|---|---|---|
| `POST` | `/ingest` | `X-API-Key: <raw_key>` | Submit GPS telemetry |

**Telemetry payload:**
```json
{
  "lat": 21.028500,
  "lng": 105.854200,
  "timestamp": "2026-04-12T09:00:00Z",
  "speed": 45.5,
  "heading": 90.0,
  "accuracy": 5.0,
  "battery": 87
}
```

---

## Setup Guide

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- Git

### Step 1 — Clone the repository

```bash
git clone <repo-url>
cd apitrak_project
```

### Step 2 — Start all services

```bash
docker-compose up --build
```

This starts 7 services: `postgres`, `redis`, `django-core`, `fastapi-ingestion`, `celery-worker-cold-write`, `celery-worker-geofences`, `react-frontend`.

Wait until you see:
```
django-core  | Application startup complete.
react-frontend | VITE ready in ...
```

### Step 3 — Apply database migrations

In a second terminal:

```bash
docker-compose exec django-core python manage.py migrate
```

### Step 4 — Create a Django superuser

```bash
docker-compose exec django-core python manage.py createsuperuser
```

### Step 5 — Verify services

| URL | Expected |
|---|---|
| http://localhost:3000 | React frontend login page |
| http://localhost:8000/admin/ | Django admin (login with superuser) |
| http://localhost:8001/docs | FastAPI Swagger UI |
| http://localhost:8000/api/v1/token/ | Returns `{"detail":"..."}` (POST only) |

### Step 6 — First login and setup

1. Open **http://localhost:3000** → log in with your superuser credentials
2. Go to **Organizations** → create an organisation (e.g. `Acme Corp`, slug `acme`)
3. Go to **Assets** → create an asset (e.g. `Truck 01`, type `vehicle`, select your org)
4. Go to **Devices** → create a device:
   - Select the asset
   - Enter a serial number (e.g. `GPS-001`)
   - Enter an **API key** (e.g. `my-secret-key-123`) — **save this, it cannot be retrieved later**
5. Go to **Geofences** → draw a polygon on the map and save it
6. Open **Live Map** → select your organisation

### Step 7 — Send test telemetry

```bash
curl -X POST http://localhost:8001/ingest \
  -H "Content-Type: application/json" \
  -H "X-API-Key: my-secret-key-123" \
  -d '{
    "lat": 21.028500,
    "lng": 105.854200,
    "timestamp": "2026-04-12T09:00:00Z",
    "speed": 45.5,
    "heading": 90.0,
    "accuracy": 5.0,
    "battery": 87
  }'
```

Expected response: **HTTP 202** (empty body).

Refresh the live map — the device marker should appear.

### Step 8 — Run the simulation script

```bash
# Edit DEVICES list in simulate_devices.py first
pip install requests
python simulate_devices.py
```

---

## Simulating Devices

`simulate_devices.py` simulates one or more IoT devices doing a random walk around Ha Noi.

Edit the `DEVICES` list at the top of the file:

```python
DEVICES = [
    {"api_key": "my-secret-key-123", "label": "Truck 01"},
    {"api_key": "another-key-456",   "label": "Truck 02"},
]
```

Optional environment variable overrides:

```bash
INGEST_URL=http://localhost:8001   # where to send pings
PING_INTERVAL=3                    # seconds between pings
```

Run:

```bash
python simulate_devices.py
```

---

---

# Phiên Bản Tiếng Việt

## Tổng Quan

**ApiTrak** là nền tảng theo dõi tài sản IoT theo thời gian thực, được xây dựng theo kiến trúc microservice. Hệ thống cho phép các tổ chức theo dõi vị trí GPS của tài sản (xe cộ, container, người, thiết bị) trên bản đồ trực tiếp, định nghĩa các vùng địa lý (geofence), và nhận cảnh báo ngay lập tức khi tài sản vào hoặc ra khỏi vùng đó.

### Tính Năng Chính

| Tính năng | Mô tả |
|---|---|
| Bản đồ trực tiếp | Vị trí thiết bị cập nhật realtime qua WebSocket — không cần polling |
| Lịch sử di chuyển | Truy vấn toàn bộ lộ trình của bất kỳ thiết bị nào trong khoảng thời gian bất kỳ |
| Cảnh báo Geofence | Thông báo ngay khi thiết bị vượt ranh giới geofence |
| Quản lý thiết bị | Tạo và quản lý thiết bị IoT với xác thực API key bảo mật |
| Quản lý tài sản | Gắn thiết bị với tài sản (xe, người, thiết bị) |
| Đa tổ chức | Dữ liệu cô lập theo từng tổ chức; JWT có phạm vi tổ chức cho WebSocket |

---

## Logic Nghiệp Vụ

### Thực Thể và Quan Hệ

```
Tổ chức (Organization)
  └── Tài sản (Asset: xe / container / người / thiết bị)
        └── Thiết bị GPS (Device — 1 thiết bị mỗi tài sản)
              └── Bản ghi vị trí (LocationRecord[] — chuỗi thời gian)

Tổ chức (Organization)
  └── Vùng địa lý (Geofence[])
```

### Luồng Xác Thực

```
1. Người dùng đăng nhập   POST /api/v1/token/
                          → trả về access token (15 phút) + refresh token (7 ngày)

2. Chọn tổ chức           POST /api/v1/token/org-scope/  { org_id }
                          → trả về JWT có phạm vi tổ chức (8 giờ) mang claim org_id
                            chỉ dùng cho kết nối WebSocket

3. Access token hết hạn   POST /api/v1/token/refresh/
                          → tự động làm mới ngầm bởi interceptor frontend
                            người dùng không bị đăng xuất
```

### Luồng Telemetry Thiết Bị

Firmware IoT gửi ping GPS trực tiếp đến **FastAPI ingestion service** bằng API key bí mật. Đây là giao tiếp máy-máy, không có giao diện người dùng.

```
Thiết bị IoT  →  POST /ingest  (X-API-Key: <raw_key>)
                 FastAPI xác thực qua Redis (không cần SQL)
                 Lưu vị trí vào Redis (TTL 1 giờ)
                 Publish event vào Redis Stream
                     ├── Django Channels  →  Broadcast WebSocket tới trình duyệt
                     ├── Celery cold_write →  Ghi vào PostGIS (LocationRecord)
                     └── Celery geofences →  Kiểm tra không gian PostGIS
                                             Nếu vượt ranh giới → geofence_event qua WS
```

### Logic Geofence

1. Celery geofence worker nhận lat/lng từ Redis Stream.
2. Truy vấn PostGIS `MultiPolygonField` để tìm tất cả geofence đang hoạt động chứa điểm đó.
3. So sánh tập geofence hiện tại với trạng thái trước đó lưu trong Redis Set.
4. Kích hoạt sự kiện `entered` / `exited` chỉ khi **có chuyển đổi trạng thái** (không phải mỗi ping).
5. Broadcast geofence event qua Django Channels WebSocket đến tất cả trình duyệt đang kết nối.

### Bản Đồ Trực Tiếp vs. Lịch Sử Di Chuyển

| | Bản đồ trực tiếp | Lịch sử di chuyển |
|---|---|---|
| Nguồn dữ liệu | Redis Hot Storage (O(1)) | Bảng PostGIS LocationRecord |
| Dự phòng | Bản ghi DB mới nhất nếu Redis TTL hết | Không áp dụng |
| Câu truy vấn SQL | 0 (đường nhanh) / 1 (dự phòng) | Có (phân trang cursor) |
| Thời gian thực | Có, qua WebSocket | Không, snapshot query |

### Bảo Mật API Key

- API key thô **không bao giờ được lưu** ở bất kỳ đâu trong hệ thống.
- Chỉ lưu **SHA-256 hex digest** trong PostgreSQL (`api_key_hash`).
- FastAPI xác thực thiết bị bằng cách hash header `X-API-Key` đến và tra cứu hash trong Redis.
- Nếu mất API key, tạo key mới qua `PATCH /api/v1/devices/{id}/` với giá trị `api_key` mới.

---

## Thiết Kế Kiến Trúc

```
┌─────────────────────────────────────────────────────────────────┐
│                    Trình duyệt (cổng 3000)                      │
│                    React + Vite + TypeScript                     │
│         Leaflet Maps │ TanStack Query │ Zustand │ Axios          │
└──────────┬──────────────────────────┬──────────────────────────┘
           │ REST (HTTP/S)            │ WebSocket (WS/WSS)
           ▼                          ▼
┌──────────────────────┐   ┌──────────────────────────────────────┐
│  Django Core         │   │  Django Channels (ASGI)              │
│  cổng 8000           │   │  ws://.../ws/tracking/<org_id>/      │
│                      │   │  Xác thực JWT theo tổ chức           │
│  DRF REST API        │   └──────────────┬───────────────────────┘
│  - Tổ chức           │                  │ Channel Layer (Redis)
│  - Tài sản           │                  ▼
│  - Thiết bị          │   ┌──────────────────────────────────────┐
│  - Geofence          │   │  Redis                               │
│  - Bản đồ trực tiếp  │   │  ├─ Hot Storage  device:*:position   │
│  - Lịch sử           │   │  ├─ Org index   org:*:device_ids     │
│  - Xác thực JWT      │   │  ├─ Thông tin xác thực thiết bị      │
└──────────┬───────────┘   │  ├─ Telemetry Stream                │
           │               │  ├─ Celery broker/results            │
           │               │  └─ Channel Layer                    │
           ▼               └──────┬─────────────────┬────────────┘
┌──────────────────────┐          │                 │
│  PostgreSQL/PostGIS  │    ┌─────▼──────┐   ┌──────▼──────────┐
│  cổng 5432           │    │  Celery    │   │  FastAPI         │
│                      │◄───│  cold_write│   │  Ingestion       │
│  - organizations     │    │  worker    │   │  cổng 8001       │
│  - assets            │    └─────┬──────┘   │                  │
│  - devices           │    ┌─────▼──────┐   │  POST /ingest    │
│  - geofences         │    │  Celery    │   │  Xác thực X-API-Key│
│  - location_records  │◄───│  geofences │   │  Giới hạn tốc độ │
│                      │    │  worker    │   │  120 req/phút    │
└──────────────────────┘    └────────────┘   └──────────────────┘
                                                      ▲
                                          Thiết bị IoT / Firmware GPS
                                          (Giao tiếp máy-máy, không có UI)
```

### Các Dịch Vụ

| Dịch vụ | Công nghệ | Cổng | Vai trò |
|---|---|---|---|
| `postgres` | PostgreSQL 16 + PostGIS 3.4 | 5432 | Lưu trữ quan hệ + không gian |
| `redis` | Redis 7 | 6379 | Hot storage, streams, broker, channel layer |
| `django-core` | Django 5 + DRF + Channels | 8000 | REST API, WebSocket hub, admin |
| `fastapi-ingestion` | FastAPI + uvicorn | 8001 | Nhận telemetry IoT hiệu suất cao |
| `celery-worker-cold-write` | Celery | — | Ghi PostGIS bất đồng bộ |
| `celery-worker-geofences` | Celery | — | Đánh giá ranh giới không gian |
| `react-frontend` | React 18 + Vite | 3000 | Ứng dụng web single-page |

### Stack Công Nghệ

**Backend**
- Django 5, Django REST Framework, djangorestframework-gis
- Django Channels 4 (ASGI WebSocket qua Daphne/uvicorn)
- Celery 5 (hàng đợi tác vụ bất đồng bộ)
- FastAPI 0.115, Pydantic v2
- PostgreSQL 16 + PostGIS 3.4
- Redis 7

**Frontend**
- React 18, Vite, TypeScript
- Leaflet.js + react-leaflet + Leaflet.Draw
- TanStack Query v5 (lấy và cache dữ liệu)
- Zustand v5 (trạng thái xác thực, lưu vào localStorage)
- Axios (HTTP client, interceptor tự động làm mới JWT)
- TailwindCSS

**Xác thực**
- simplejwt — access token 15 phút, refresh token 7 ngày, tự rotate
- Org-scoped HS256 JWT cho WebSocket — hiệu lực 8 giờ

---

## Luồng Dữ Liệu

### Hot Path Telemetry (độ trễ thấp)

```
Ping GPS từ IoT
  → FastAPI /ingest (xác thực ~1ms qua Redis)
  → Redis HSET device:{id}:position  (TTL 1 giờ)
  → Redis XADD telemetry_stream
  → Stream Consumer (vòng lặp async trong ASGI)
      → Channel Layer group_send  →  WebSocket → Cập nhật bản đồ trình duyệt (~50ms)
      → Celery cold_write.delay() →  PostGIS INSERT (bất đồng bộ, ~200ms)
      → Celery geofences.delay()  →  Truy vấn không gian PostGIS → geofence_event
```

### Lấy Bản Đồ Trực Tiếp (khi tải trang)

```
Trình duyệt GET /api/v1/map/{org_id}/live/
  → Redis SMEMBERS org:{org_id}:device_ids
  → Redis Pipeline HGETALL device:{id}:position × N  (không SQL)
  → Nếu key vị trí đã hết hạn:
      → PostGIS: SELECT DISTINCT ON (device_id) ORDER BY device_id, -timestamp
      → Nạp lại Redis với vị trí vừa lấy
  → Trả về JSON {org_id, devices: [...]}
```

### Kết Nối WebSocket

```
Trình duyệt → ws://host/ws/tracking/{org_id}/?token={org_jwt}
          Channels xác thực JWT (claim org_id phải khớp URL)
          Tham gia group org_{org_id}_tracking
          Nhận:
            - location_update  {type, device_id, lat, lng, timestamp, speed, heading, battery}
            - geofence_event   {type, device_id, geofence_id, event: "entered"|"exited"}
```

---

## Tài Liệu API

### Xác Thực

| Method | URL | Body | Mô tả |
|---|---|---|---|
| `POST` | `/api/v1/token/` | `{username, password}` | Đăng nhập, lấy access + refresh token |
| `POST` | `/api/v1/token/refresh/` | `{refresh}` | Làm mới access token |
| `POST` | `/api/v1/token/org-scope/` | `{org_id}` | Lấy JWT phạm vi tổ chức cho WebSocket |

### Tổ Chức

| Method | URL | Mô tả |
|---|---|---|
| `GET` | `/api/v1/organizations/` | Danh sách tổ chức |
| `POST` | `/api/v1/organizations/` | Tạo tổ chức |
| `PATCH` | `/api/v1/organizations/{id}/` | Cập nhật |
| `DELETE` | `/api/v1/organizations/{id}/` | Xoá |

### Tài Sản

| Method | URL | Mô tả |
|---|---|---|
| `GET` | `/api/v1/assets/` | Danh sách tài sản |
| `POST` | `/api/v1/assets/` | Tạo tài sản |
| `PATCH` | `/api/v1/assets/{id}/` | Cập nhật |
| `DELETE` | `/api/v1/assets/{id}/` | Xoá |

### Thiết Bị

| Method | URL | Mô tả |
|---|---|---|
| `GET` | `/api/v1/devices/` | Danh sách thiết bị (không trả về api_key) |
| `POST` | `/api/v1/devices/` | Tạo thiết bị (`api_key` bắt buộc — **lưu lại ngay!**) |
| `PATCH` | `/api/v1/devices/{id}/` | Cập nhật (truyền `api_key` mới để đổi key) |
| `DELETE` | `/api/v1/devices/{id}/` | Xoá |

### Geofence

| Method | URL | Mô tả |
|---|---|---|
| `GET` | `/api/v1/geofences/?org_id={id}` | Danh sách geofence dạng GeoJSON FeatureCollection |
| `POST` | `/api/v1/geofences/` | Tạo geofence (body dạng GeoJSON Feature) |
| `PATCH` | `/api/v1/geofences/{id}/` | Cập nhật |
| `DELETE` | `/api/v1/geofences/{id}/` | Xoá |

### Tracking

| Method | URL | Mô tả |
|---|---|---|
| `GET` | `/api/v1/map/{org_id}/live/` | Vị trí mới nhất của tất cả thiết bị trong tổ chức |
| `GET` | `/api/v1/devices/{id}/track/?after=&before=` | Lịch sử di chuyển (phân trang cursor) |
| `WS` | `ws://host/ws/tracking/{org_id}/?token=` | Luồng WebSocket trực tiếp |

### Ingestion (FastAPI — cổng 8001)

| Method | URL | Header | Mô tả |
|---|---|---|---|
| `POST` | `/ingest` | `X-API-Key: <raw_key>` | Gửi dữ liệu GPS telemetry |

**Payload telemetry:**
```json
{
  "lat": 21.028500,
  "lng": 105.854200,
  "timestamp": "2026-04-12T09:00:00Z",
  "speed": 45.5,
  "heading": 90.0,
  "accuracy": 5.0,
  "battery": 87
}
```

---

## Hướng Dẫn Cài Đặt

### Yêu Cầu

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (bao gồm Docker Compose)
- Git

### Bước 1 — Clone repository

```bash
git clone <repo-url>
cd apitrak_project
```

### Bước 2 — Khởi động tất cả dịch vụ

```bash
docker-compose up --build
```

Lệnh này khởi động 7 dịch vụ: `postgres`, `redis`, `django-core`, `fastapi-ingestion`, `celery-worker-cold-write`, `celery-worker-geofences`, `react-frontend`.

Chờ đến khi thấy:
```
django-core  | Application startup complete.
react-frontend | VITE ready in ...
```

### Bước 3 — Áp dụng migrations database

Mở terminal thứ hai:

```bash
docker-compose exec django-core python manage.py migrate
```

### Bước 4 — Tạo tài khoản Django superuser

```bash
docker-compose exec django-core python manage.py createsuperuser
```

### Bước 5 — Kiểm tra dịch vụ

| URL | Kết quả mong đợi |
|---|---|
| http://localhost:3000 | Trang đăng nhập React frontend |
| http://localhost:8000/admin/ | Django admin (đăng nhập bằng superuser) |
| http://localhost:8001/docs | FastAPI Swagger UI |
| http://localhost:8000/api/v1/token/ | Trả về lỗi (vì chỉ nhận POST) |

### Bước 6 — Đăng nhập lần đầu và thiết lập

1. Mở **http://localhost:3000** → đăng nhập bằng tài khoản superuser
2. Vào **Organizations** → tạo tổ chức (ví dụ: tên `Công ty ABC`, slug `cong-ty-abc`)
3. Vào **Assets** → tạo tài sản (ví dụ: `Xe tải 01`, loại `vehicle`, chọn tổ chức)
4. Vào **Devices** → tạo thiết bị:
   - Chọn tài sản
   - Nhập số serial (ví dụ: `GPS-001`)
   - Nhập **API key** (ví dụ: `my-secret-key-123`) — **lưu lại ngay, không thể xem lại sau này**
5. Vào **Geofences** → vẽ vùng polygon trên bản đồ và lưu
6. Mở **Live Map** → chọn tổ chức của bạn

### Bước 7 — Gửi telemetry thử nghiệm

```bash
curl -X POST http://localhost:8001/ingest \
  -H "Content-Type: application/json" \
  -H "X-API-Key: my-secret-key-123" \
  -d '{
    "lat": 21.028500,
    "lng": 105.854200,
    "timestamp": "2026-04-12T09:00:00Z",
    "speed": 45.5,
    "heading": 90.0,
    "accuracy": 5.0,
    "battery": 87
  }'
```

Kết quả mong đợi: **HTTP 202** (body rỗng).

Làm mới bản đồ trực tiếp — marker thiết bị sẽ xuất hiện.

### Bước 8 — Chạy script mô phỏng

```bash
# Chỉnh sửa danh sách DEVICES trong simulate_devices.py trước
pip install requests
python simulate_devices.py
```

---

## Mô Phỏng Thiết Bị

`simulate_devices.py` mô phỏng một hoặc nhiều thiết bị IoT di chuyển ngẫu nhiên quanh Hà Nội.

Chỉnh sửa danh sách `DEVICES` ở đầu file:

```python
DEVICES = [
    {"api_key": "my-secret-key-123", "label": "Xe tải 01"},
    {"api_key": "another-key-456",   "label": "Xe tải 02"},
]
```

Có thể đặt biến môi trường:

```bash
INGEST_URL=http://localhost:8001   # địa chỉ gửi ping
PING_INTERVAL=3                    # giây giữa các lần ping
```

Chạy:

```bash
python simulate_devices.py
```

Mỗi thiết bị bắt đầu ở vị trí ngẫu nhiên gần Hà Nội và di chuyển ~55m mỗi bước.
