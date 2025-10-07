# UK DTC D0010 File Format - Complete Attribute List

## ZHD - File Header Record

| Position | Attribute | Description | Format | Example |
|----------|-----------|-------------|--------|---------|
| 1 | Record Type | Always "ZHD" | AN3 | ZHD |
| 2 | Flow Reference | Flow identifier | AN5 | D0010 |
| 3 | Version Number | File format version | N3 | 001 |
| 4 | From Role Code | Sender market participant ID | AN13 | SUPPLIRID |
| 5 | To Role Code | Receiver market participant ID | AN13 | DISTRBTR |
| 6 | File Creation Date | Date file was created | CCYYMMDD | 20241007 |
| 7 | File Creation Time | Time file was created | HHMMSS | 120000 |
| 8 | Application Reference | Optional application identifier | AN15 | (blank) |

---

## 026 - MPAN Core Record

| Position | Attribute | Description | Format | Example |
|----------|-----------|-------------|--------|---------|
| 1 | Record Type | Always "026" | N3 | 026 |
| 2 | MPAN Core | 13-digit Meter Point Administration Number | N13 | 1234567890123 |
| 3 | Measurement Class | E=Electricity, G=Gas | A1 | E |

---

## 028 - Meter Reading and Register Details

| Position | Attribute | Description | Format | Example |
|----------|-----------|-------------|--------|---------|
| 1 | Record Type | Always "028" | N3 | 028 |
| 2 | Register ID | Unique identifier for the register | AN2 | 01 |
| 3 | TPR Code | Time Pattern Regime code (rate type) | N3 | 210 |
| 4 | Measurement Quantity ID | Unit of measurement | AN4 | kWh |
| 5 | Meter Serial Number | Serial number of the meter | AN10 | 00001 |
| 6 | Reading Type | Type of reading (A=Actual, E=Estimate, C=Customer) | A1 | A |
| 7 | Previous Reading Date | Date of previous meter reading | CCYYMMDD | 20241001 |
| 8 | Previous Reading Time | Time of previous reading | HHMMSS | 00000 |
| 9 | Current Reading Date | Date of current meter reading | CCYYMMDD | 20241007 |
| 10 | Current Reading Time | Time of current reading | HHMMSS | 00000 |
| 11 | Current Reading Value | The actual meter reading value | N8.2 | 12345.67 |
| 12 | MD Reset Flag | Maximum Demand reset indicator | A1 | N |

---

## 029 - Individual Register Reading Details

| Position | Attribute | Description | Format | Example |
|----------|-----------|-------------|--------|---------|
| 1 | Record Type | Always "029" | N3 | 029 |
| 2 | Reading Sequence | Sequence number (1=previous, 2=current) | N1 | 1 |
| 3 | Reading Date | Date of this specific reading | CCYYMMDD | 20241001 |
| 4 | Reading Time | Time of this specific reading | HHMMSS | 00000 |
| 5 | Register Reading | The meter register value | N8.2 | 11234.56 |
| 6 | Reading Reason | Reason code for reading (C=Customer, S=Scheduled, etc.) | A1 | C |
| 7 | Reading Method | How reading was obtained (A=Actual, E=Estimate, etc.) | A1 | A |
| 8 | Reading Date/Time Received | When reading was received by system | CCYYMMDD HHMMSS | 20241007 120000 |

---

## ZTR - File Trailer Record

| Position | Attribute | Description | Format | Example |
|----------|-----------|-------------|--------|---------|
| 1 | Record Type | Always "ZTR" | AN3 | ZTR |
| 2 | Record Count | Total number of records in file (excluding ZHD and ZTR) | N6 | 18 |
| 3 | Checksum | Optional file checksum | AN20 | (blank) |

---

## Common TPR Codes (Time Pattern Regime)

| Code | Description |
|------|-------------|
| 210 | Single Rate / Day Rate |
| 220 | Night Rate (Economy 7) |
| 221 | Off-Peak Rate |
| 251 | Evening and Weekend |
| 252 | Day Rate (Multi-rate) |

---

## Common Reading Type Codes

| Code | Description |
|------|-------------|
| A | Actual - Physical meter reading |
| E | Estimate - Estimated reading |
| C | Customer - Customer-provided reading |
| W | Withdrawn - Reading withdrawn |
| Z | Zero Consumption - No usage recorded |

---

## Common Reading Reason Codes

| Code | Description |
|------|-------------|
| C | Customer Read |
| S | Scheduled Read |
| F | Final Read |
| O | Opening Read |
| M | Move In |
| X | Move Out |
| Q | Query |

---

## Format Notation

- **AN** = Alphanumeric (letters and numbers)
- **N** = Numeric only
- **A** = Alphabetic only
- **N8.2** = Numeric with 8 total digits, 2 decimal places
- **CCYYMMDD** = Century, Year, Month, Day
- **HHMMSS** = Hour, Minute, Second

---

## File Structure Summary

```
ZHD (1 record)
  └─ 026 MPAN Core (1 per meter)
      └─ 028 Register Details (1 per register/rate)
          └─ 029 Reading Details (2 per 028: previous + current)
ZTR (1 record)
```

## Notes

- Each MPAN can have multiple registers (028 records) for different rates
- Each register (028) typically has 2 associated 029 records (previous and current readings)
- The file delimiter is the pipe character "|"
- All fields are mandatory unless otherwise specified
- Date/Time fields use 24-hour format