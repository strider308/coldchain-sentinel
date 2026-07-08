# Sensor Adapters

ColdChain Sentinel includes local deterministic synthetic adapters that normalize vendor-style payloads into Data Contract v2.

## Formats

- `sentinel_native_v1`: internal-style field names close to the platform schema.
- `vendor_flat_csv_v1`: flat logistics-style keys such as `ts`, `device`, `temp_c`, and `seq`.
- `vendor_nested_iot_v1`: nested IoT-style payload with `meta`, `shipment`, and `reading` objects.

## Validation

Adapters return:

- `normalizedReading`
- `accepted`
- `warnings`
- `errors`

Missing optional context creates warnings. Missing required fields or impossible values reject the reading.

## Boundary

Adapters use compact synthetic examples only. They do not call external sensor APIs, ingest real customer data, or change deterministic review facts.
