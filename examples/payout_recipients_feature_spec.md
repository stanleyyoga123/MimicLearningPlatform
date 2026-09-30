# Feature request: manage payout recipients

This is a fictional training scenario inspired by business payments platforms
such as Airwallex. It does not describe Airwallex's actual systems or APIs.
No real bank details, customer data, or credentials are needed.

## Product context

Borderless Business helps small businesses organise international supplier
payments. Before preparing a payout, an operations teammate needs to maintain
a simple address book of recipients. Today, the service has a health endpoint
and a SQLite connection, but no way to manage recipients.

## Requested feature

Build a small REST API to create, list, view, update, and delete payout
recipients. This task only manages recipient records; it never sends money.

## Recipient record

- `id`: a server-generated integer, returned by the API and never editable.
- `name`: a recipient's display name, trimmed, between 1 and 100 characters.
- `country`: one of `AU`, `US`, or `SG` for this exercise.
- `currency`: one of `AUD`, `USD`, or `SGD` for this exercise.

All three editable fields are required. Country and currency are independent:
a recipient in Singapore may receive USD. Duplicate names are allowed.

Example request:

```json
{
  "name": "Harbour Design Studio",
  "country": "SG",
  "currency": "USD"
}
```

## API contract and acceptance criteria

| Operation | Endpoint | Expected result |
| --- | --- | --- |
| Create | `POST /recipients` | `201` with the saved record and its generated ID |
| List | `GET /recipients` | `200` with an array ordered by ID ascending; `[]` when empty |
| View | `GET /recipients/{id}` | `200` with the matching record |
| Update | `PUT /recipients/{id}` | `200` with the updated record, retaining its ID |
| Delete | `DELETE /recipients/{id}` | `204` with no response body |

- Update replaces all three editable fields; partial updates are not required.
- Viewing, updating, or deleting an unknown ID returns `404`.
- Missing fields, blank names, names longer than 100 characters, and unsupported
  country or currency values return `422` without modifying stored records.
- Trim names before checking their length and saving them. Country and currency
  values must match the uppercase values above.
- A deleted recipient disappears from the list and returns `404` when viewed.
- Creating, updating, or deleting one recipient must not change another.
- Saved records and updates survive an application restart; deleted records
  must not reappear.

## Example user journey

An operations teammate adds Harbour Design Studio as a Singapore recipient paid
in USD. They find it in the recipient list, rename it to Harbour Design Pte Ltd,
and confirm the new name appears when they reopen the record. When the supplier
relationship ends, they remove it from the address book.

## Exercise setup

Generate a feature task, not a bugfix. Provide a runnable starter with a passing
health check, database setup, and clearly marked recipient endpoint stubs. The
learner implements the CRUD feature and makes the provided exercise tests pass.
Keep the completed implementation in the private reference project.

The fictional backend teammate knows the API contract and database layout.
The fictional QA teammate knows example requests, invalid inputs, and expected
responses. Neither should give the learner a finished implementation.

## Training boundary

Target one junior-level, 30–60 minute task using FastAPI, SQLite, and pytest.
Use fictional recipient names. Keep SQL queries parameterised.

Bank accounts, actual payouts, exchange rates, balances, authentication,
multi-tenant access, compliance checks, pagination, search, and external service
integrations are outside this exercise. No frontend is required.
