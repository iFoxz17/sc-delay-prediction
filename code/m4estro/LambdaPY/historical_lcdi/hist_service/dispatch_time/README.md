# Dispatch time

## Indicators
- ***ADT***: **Average Dispatch Time**
- ***DDI***: **Dispatch Delay Index**

## Endpoints
<code>GET /indicators/dispatch-time</code>

<code>GET /indicators/dispatch-time/adt</code>

<code>GET /indicators/dispatch-time/ddi</code>

## Query Parameters

| Parameter  | Type | Required | Description                                                                                               |
|------------|------|----------|-----------------------------------------------------------------------------------------------------------|
| `site`     | int  | No       | One or more supplier site IDs to filter indicators by (multiple IDs can be provided, separated by commas). |
| `supplier` | int  | No       | One or more supplier IDs to filter indicators by (multiple IDs can be provided, separated by commas).      |

If both <code>site</code> and <code>supplier</code> are omitted, indicators for all the sites are included.


## Examples 

### Single site 

<code>GET /indicators/dispatch-time?site=1</code>

#### Response

```json
{
  "site": 1,
  "supplier": 3,
  "indicators": {
    "ADT": 56.8,
    "DDI": {
      "lower": 1.2,
      "upper": 3.55
    }
  }
}
```

### Multiple sites 

<code>GET /indicators/dispatch-time/adt?site=1,5,6</code>

#### Response

```json
[
  {
    "site": 1,
    "supplier": 3,
    "indicators": {
      "ADT": 56.8
    }
  },
  {
    "site": 5,
    "supplier": 3,
    "indicators": {
      "ADT": 45.9
    }
  },
  {
    "site": 6,
    "supplier": 4,
    "indicators": {
      "ADT": 12.44
    }
  }
]
```

### Single supplier 

<code>GET /indicators/dispatch-time?supplier=3</code>

#### Response

```json
[
  {
    "site": 1,
    "supplier": 3,
    "indicators": {
      "ADT": 56.8,
      "DDI": {
        "lower": 1.2,
        "upper": 3.55
      }
    }
  },
  {
    "site": 5,
    "supplier": 3,
    "indicators": {
      "ADT": 45.9,
      "DDI": {
        "lower": 1.2,
        "upper": 3.55
      }
    }
  }
]
```

### Multiple suppliers 

<code>GET /indicators/dispatch-time?supplier=3,4</code>

#### Response

```json
[
  {
    "site": 1,
    "supplier": 3,
    "indicators": {
      "ADT": 56.8,
      "DDI": {
        "lower": 1.2,
        "upper": 3.55
      }
    }
  },
  {
    "site": 5,
    "supplier": 3,
    "indicators": {
      "ADT": 45.9,
      "DDI": {
        "lower": 1.2,
        "upper": 3.55
      }
    }
  },
  {
    "site": 11,
    "supplier": 4,
    "indicators": {
      "ADT": 78.43,
      "DDI": {
        "lower": 1.2,
        "upper": 3.55
      }
    }
  }
]
```