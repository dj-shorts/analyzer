# COST MODEL — MVP Analyzer

## Assumptions

```json
{
  "region": "eu-central-1",
  "instances": {
    "api_workers": {
      "type": "t4g.medium",
      "hourly": 0.0384
    },
    "analyzer": {
      "type": "c7g.large",
      "hourly": 0.0825
    },
    "redis": {
      "type": "cache.t4g.small",
      "hourly": 0.032
    }
  },
  "db": {
    "option": "Neon Launch",
    "compute_hour_price": 0.14,
    "storage_gb_month": 0.35
  },
  "s3": {
    "standard_gb_month": 0.023,
    "put_per_1k": 0.005,
    "get_per_1k": 0.0004
  },
  "cloudfront": {
    "free_tier_gb": 1024.0,
    "europe_next_9tb_per_gb": 0.085
  },
  "job_profile": {
    "input_gb": 2.5,
    "outputs_gb": 0.6,
    "avg_runtime_min": 8.0,
    "s3_puts": 30,
    "s3_gets": 40
  },
  "retention_days": {
    "input": 7,
    "output": 30
  }
}
```

## Scenarios

|   jobs_per_month |   api_workers_ec2_usd |   analyzer_ec2_usd |   redis_elasticache_usd |   db_neon_usd |   s3_storage_usd |   s3_requests_usd |   cloudfront_egress_usd |   total_monthly_usd |
|-----------------:|----------------------:|-------------------:|------------------------:|--------------:|-----------------:|------------------:|------------------------:|--------------------:|
|               50 |                 27.65 |               0.55 |                   23.04 |          17.5 |             1.36 |            0.0083 |                    0    |               70.11 |
|              200 |                 27.65 |               2.2  |                   23.04 |          17.5 |             5.44 |            0.0332 |                    0    |               75.86 |
|             1000 |                 27.65 |              11    |                   23.04 |          31.5 |            27.22 |            0.166  |                    0    |              120.57 |
|             5000 |                 27.65 |              55    |                   23.04 |         143.5 |           136.08 |            0.83   |                  167.96 |              554.06 |