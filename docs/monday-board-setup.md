# Monday.com Board Setup

Import the two Skylark files into separate boards.

## Deals

- Deal Name -> Item name
- Owner code -> Text
- Client Code -> Text
- Deal Status -> Status
- Close Date (A) -> Date
- Closure Probability -> Status/Dropdown
- Masked Deal value -> Numbers
- Tentative Close Date -> Date
- Deal Stage -> Status/Dropdown
- Product deal -> Text
- Sector/service -> Dropdown/Text
- Created Date -> Date

## Work Orders

- Deal name masked -> Item name
- Customer Name Code -> Text
- Serial # -> Text
- Nature of Work -> Dropdown/Text
- Last executed month -> Date/Text
- Execution Status -> Status
- Data Delivery Date -> Date
- Date of PO/LOI -> Date
- Document Type -> Dropdown/Text
- Probable Start Date -> Date
- Probable End Date -> Date
- BD/KAM Personnel code -> Text
- Sector -> Dropdown/Text
- Type of Work -> Dropdown/Text
- Skylark software platform -> Status/Text
- Last invoice date -> Date
- latest invoice no. -> Text
- All monetary fields -> Numbers
- AR Priority account -> Status/Text
- Quantity fields -> Numbers/Text
- Invoice Status -> Status
- Billing/collection month fields -> Date/Text
- WO Status (billed) -> Status
- Collection status -> Status
- Collection Date -> Date
- Billing Status -> Status

Preserve blanks. Do not replace missing monetary values with zero.

After import, verify item counts and put the two numeric board IDs in `.env`.
