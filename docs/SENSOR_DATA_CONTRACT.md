# Sensor Data Contract v2

The beta generates synthetic sensor readings in memory from compact local case configuration.

## Normalized Fields

- `timestampUtc`
- `sensorId`
- `deviceId`
- `shipmentId`
- `containerId`
- `zoneId`
- `palletId`
- `temperatureC`
- `humidityPercent`
- `batteryPercent`
- `signalStrength`
- `doorOpen`
- `readingSequence`
- `firmwareVersion`
- `gatewayId`
- `ingestionDelaySeconds`
- `sourceFormat`
- `adapterVersion`
- `normalizationWarnings`

## Required Fields

- `timestampUtc`
- `sensorId`
- `shipmentId`
- `temperatureC`

## Recommended Context

Missing `readingSequence`, `zoneId`, or `shipmentId` produces warnings. Impossible temperatures or missing required fields reject the normalized reading.

## Supported Synthetic Source Formats

- `sentinel_native_v1`
- `vendor_flat_csv_v1`
- `vendor_nested_iot_v1`

## Default Scale

- 24 sensors
- 4 zones
- 48 hours
- 5-minute interval
- 13,824 readings per case
- 41,472 readings across three synthetic cases

## Boundary

No real customer, patient, pharma, logistics, shipment, or sensor data is used.

The contract never authorizes autonomous operational action.
