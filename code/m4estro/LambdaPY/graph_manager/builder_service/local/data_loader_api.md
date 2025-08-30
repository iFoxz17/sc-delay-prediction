
### Health & Management

```http
# Health check
GET /db/health

# Run database migration
GET /db/migration

# Get all tables info
GET /db/tables
```

### Table Operations

```http
# Get table information
GET /db/tables/{tableName}

# Get table data (with pagination)
GET /db/tables/{tableName}/data
GET /db/tables/{tableName}/data?page=1&pageSize=50&orderBy=id&direction=asc

# Get specific record
GET /db/tables/{tableName}/data/{id}

# Insert data
POST /db/tables/{tableName}
{
  "data": {
    "field1": "value1",
    "field2": "value2"
  }
}

# Insert multiple records
POST /db/tables/{tableName}
{
  "data": [
    {"field1": "value1", "field2": "value2"},
    {"field1": "value3", "field2": "value4"}
  ]
}

# Update record
PUT /db/tables/{tableName}/{id}
{
  "data": {
    "field1": "updated_value"
  }
}

# Delete record (requires confirmation)
DELETE /db/tables/{tableName}/{id}
{
  "confirmDelete": true
}
```

### Advanced Operations

```http
# Bulk operations
POST /db/bulk
{
  "operations": [
    {
      "type": "insert",
      "tableName": "countries",
      "data": {"code": "US", "name": "United States"}
    },
    {
      "type": "update", 
      "tableName": "countries",
      "data": {"name": "United States of America"},
      "whereClause": {"code": "US"}
    }
  ],
  "useTransaction": true
}

# Raw SQL query (SELECT only)
POST /db/query
{
  "sql": "SELECT * FROM countries WHERE code = ?",
  "bindings": ["US"]
}
```

### Query Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `page` | Page number for pagination | `?page=2` |
| `pageSize` | Records per page (max 1000) | `?pageSize=50` |
| `orderBy` | Column to sort by | `?orderBy=created_at` |
| `direction` | Sort direction | `?direction=desc` |
| `where` | JSON filter conditions | `?where={"status":"active"}` |
| `select` | Specific columns to return | `?select=id,name,status` |
| `limit` | Limit results (alternative to pagination) | `?limit=100` |
| `offset` | Skip records | `?offset=50` |

## 💡 Usage Examples

### 1. Insert a New Country

```bash
curl -X POST "https://api-url/db/tables/countries" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "code": "IT", 
      "name": "Italy",
      "total_holidays": 12,
      "weekend_start": 6,
      "weekend_end": 0
    }
  }'
```

### 2. Get Orders with Pagination

```bash
curl "https://api-url/db/tables/orders/data?page=1&pageSize=20&orderBy=created_at&direction=desc"
```

### 3. Update Order Status

```bash
curl -X PUT "https://api-url/db/tables/orders/123" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "status": "DELIVERED",
      "carrier_confirmed_delivery_timestamp": "2024-01-15T10:30:00Z"
    }
  }'
```

### 4. Bulk Insert Locations

```bash
curl -X POST "https://api-url/db/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "operations": [
      {
        "type": "insert",
        "tableName": "locations",
        "data": {
          "name": "Milan Hub",
          "city": "Milan", 
          "country_code": "IT",
          "latitude": 45.4642,
          "longitude": 9.1900
        }
      },
      {
        "type": "insert", 
        "tableName": "locations",
        "data": {
          "name": "Rome Hub",
          "city": "Rome",
          "country_code": "IT", 
          "latitude": 41.9028,
          "longitude": 12.4964
        }
      }
    ],
    "useTransaction": true
  }'
```
