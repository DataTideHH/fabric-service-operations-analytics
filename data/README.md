# Generated Source Data

The 1,000-row service-operations source fixture is generated deterministically instead of being stored as a large derived CSV in Git.

```bash
python -m service_operations generate \
  --output .ci-output/service_requests.csv
```

The generator uses seed `20260729`. Tests and GitHub Actions verify the complete SHA-256 fingerprint of the generated CSV before validation and Medallion processing:

```text
292ed8fb2857e3927936a5b3ca002492b146875d04baee77a9322de287db8914
```

This keeps the repository reviewable while preserving byte-for-byte reproducibility on Windows and Ubuntu. The generated file contains synthetic data only and must not be confused with production service-management data.
