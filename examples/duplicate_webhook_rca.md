# Incident review: duplicate orders after webhook retries

This is a fictional training scenario. No customer data or credentials are included.

## Service
ParcelDesk receives payment webhooks and creates orders in a SQLite database.
Each webhook contains an event ID, customer ID, item SKU, and quantity.

## Incident
On Tuesday, the payment provider retried a webhook after its first request timed
out. The service had already created an order before the timeout. The retry
created a second order for the same payment. The customer was scheduled to
receive the same item twice.

## Root cause
The webhook handler inserts a new order for every delivery. It does not use the
provider's event ID to identify a delivery that has already been processed.

## Required behavior
- The first valid delivery creates exactly one order.
- Repeating the same event ID returns the existing order without creating another.
- A different event ID creates a separate order, even for the same customer.
- Invalid input is rejected and does not create an order.
- Processed event IDs survive an application restart.

## Training boundary
Use a single FastAPI service and local SQLite. Simulate webhook requests; do not
integrate with a real payment provider. Focus on one junior-level idempotency
bugfix. Payment capture, authentication, inventory, and distributed concurrency
are outside this exercise.
