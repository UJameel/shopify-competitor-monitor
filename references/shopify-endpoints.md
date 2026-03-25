# Shopify /products.json Endpoint Reference

## Overview

Every Shopify store exposes a public JSON API at `/products.json`. This requires no authentication and returns structured product data. This is the primary data source for the shopify-competitor-monitor skill.

## Endpoint

```
GET https://{store-domain}/products.json
```

## Parameters

| Parameter | Type   | Default | Description                          |
|-----------|--------|---------|--------------------------------------|
| limit     | int    | 30      | Products per page (max 250)          |
| page      | int    | 1       | Page number for pagination           |
| collection_id | string | — | Filter by collection                 |
| product_type  | string | — | Filter by product type               |

## Example Request

```bash
curl "https://www.gymshark.com/products.json?limit=250&page=1"
```

## Response Structure

```json
{
  "products": [
    {
      "id": 123456789,
      "title": "Product Name",
      "handle": "product-name",
      "body_html": "<p>Description</p>",
      "vendor": "Brand Name",
      "product_type": "Category",
      "created_at": "2024-01-15T10:00:00-05:00",
      "updated_at": "2024-03-20T14:30:00-05:00",
      "published_at": "2024-01-15T10:00:00-05:00",
      "tags": ["tag1", "tag2", "sale"],
      "variants": [
        {
          "id": 987654321,
          "title": "Small / Black",
          "price": "49.99",
          "compare_at_price": "65.00",
          "sku": "GS-PROD-S-BLK",
          "available": true,
          "option1": "Small",
          "option2": "Black",
          "grams": 250,
          "requires_shipping": true
        }
      ],
      "images": [
        {
          "id": 111222333,
          "src": "https://cdn.shopify.com/s/files/...",
          "width": 1024,
          "height": 1024
        }
      ],
      "options": [
        {
          "name": "Size",
          "values": ["Small", "Medium", "Large"]
        }
      ]
    }
  ]
}
```

## Pagination

- Request with `?limit=250&page=1`
- If the response returns exactly 250 products, there are likely more pages
- Increment `page` until fewer than 250 products are returned
- Add a small delay (0.5s) between requests to avoid rate limiting

## Rate Limiting

- No official rate limit documentation for public endpoints
- In practice, aggressive scraping may result in temporary blocks
- Use polite delays (0.5-1s between requests)
- Set a recognizable User-Agent header

## Limitations

- Only returns published/visible products
- Does not include draft or archived products
- Inventory quantities are not directly exposed (only available/unavailable)
- Some stores may disable this endpoint via Shopify settings (rare)
- The `compare_at_price` field shows the original price when an item is on sale

## Alternative: Collections

Individual collections are also available:

```
GET https://{store-domain}/collections/{collection-handle}/products.json
```

## Alternative: Single Product

```
GET https://{store-domain}/products/{product-handle}.json
```
