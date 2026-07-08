# Sensor Data Contract

The beta generates synthetic sensor readings in memory from compact local case configuration.

## Reading Fields

- `timestampUtc`
- `sensorId`
- `zoneId`
- `temperatureC`
- `humidityPercent`
- `batteryPercent`
- `signalStrength`
- `doorOpen`
- `readingSequence`
- `ingestionDelaySeconds`
- `qualityLabel`
- `evidenceId`

## Default Scale

- 24 sensors
- 4 zones
- 48 hours
- 5-minute interval
- 13,824 readings per case
- 41,472 readings across three synthetic cases

## Boundary

No real customer, patient, pharma, logistics, shipment, or sensor data is used.
