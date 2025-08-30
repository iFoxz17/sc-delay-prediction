# Delivery time

## Indicators
- ***AST***: **Average Shipment Time**
- ***CTDI***: **Carrier Transit Delay Index**

## Endpoints
<code>GET /indicators/delivery-time</code>

<code>GET /indicators/delivery-time/ast</code>

<code>GET /indicators/delivery-time/ctdi</code>

## Query Parameters

| Parameter  | Type | Required | Description                                                                                               |
|------------|------|----------|-----------------------------------------------------------------------------------------------------------|
| `carrier`  | str  | No       | One or more carrier to filter indicators by (multiple carriers can be provided, separated by commas). If not provided, all the carriers are included.    |
| `site`     | int  | No       | One or more supplier site IDs to filter indicators by (multiple IDs can be provided, separated by commas). |
| `supplier` | int  | No       | One or more supplier IDs to filter indicators by (multiple IDs can be provided, separated by commas).      |

If both <code>supplier</code> and <code>site</code> are omitted, indicators for all the sites are included.


## Examples 

### Single site and carrier

<code>GET /indicators/dispatch-time?site=1&carrier=ups</code>

#### Response

```json
{
  "site": 1,
  "supplier": 3,
  "carrier": "ups",
  "indicators": {
    "AST": 56.8,
    "CTDI": {
      "lower": 4.3,
      "upper": 3.6
    }
  }
}
```

### Multiple carriers

<code>GET /indicators/dispatch-time/ast?site=1&carrier=ups,dhl</code>

#### Response

```json
[
  {
    "site": 1,
    "supplier": 3,
    "carrier": "ups",
    "indicators": {
      "AST": 56.8
    }
  },
  {
    "site": 1,
    "supplier": 3,
    "carrier": "dhl",
    "indicators": {
      "AST": 45.9
    }
  },
]
```

### Single supplier

<code>GET /indicators/dispatch-time?supplier=3&carrier=ups</code>

#### Response

```json
[
  {
    "site": 1,
    "supplier": 3,
    "carrier": "ups",
    "indicators": {
      "AST": 56.8,
      "CTDI": {
        "lower": 4.3,
        "upper": 3.6
      }
    }
  },
  {
    "site": 5,
    "supplier": 3,
    "carrier": "ups",
    "indicators": {
      "AST": 56.8,
      "CTDI": {
        "lower": 4.3,
        "upper": 3.6
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
    "supplier": 2,
    "carrier": "ups",
    "indicators": {
      "AST": 64.3,
      "CTDI": {
        "lower": 1.7,
        "upper": 5.9
      }
    }
  },
  {
    "site": 1,
    "supplier": 2,
    "carrier": "dhl",
    "indicators": {
      "AST": 49.6,
      "CTDI": {
        "lower": 3.1,
        "upper": 4.4
      }
    }
  },
  {
    "site": 4,
    "supplier": 2,
    "carrier": "fedex",
    "indicators": {
      "AST": 52.7,
      "CTDI": {
        "lower": 2.8,
        "upper": 6.3
      }
    }
  },
  {
    "site": 9,
    "supplier": 5,
    "carrier": "dhl",
    "indicators": {
      "AST": 73.5,
      "CTDI": {
        "lower": 4.0,
        "upper": 4.9
      }
    }
  },
  {
    "site": 9,
    "supplier": 5,
    "carrier": "fedex",
    "indicators": {
      "AST": 60.4,
      "CTDI": {
        "lower": 3.3,
        "upper": 6.1
      }
    }
  }
]
```