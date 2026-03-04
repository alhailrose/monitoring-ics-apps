# Frontend Implementation Guide

## Overview

Build a React/TypeScript web interface for the AWS Monitoring Hub that mirrors TUI functionality. The backend API is already implemented and running on FastAPI.

## Tech Stack

- React 18+ with TypeScript
- Vite for build tooling
- React Router for navigation
- Tailwind CSS for styling (dark theme)
- Existing web/ directory in the worktree

## API Base URL

```
http://localhost:8080/api/v1
```

## Pages & Routes

### 1. `/` - Home / Navigation

Simple landing page with navigation cards to:
- Single Check
- All Check
- Arbel Check
- Customer Management
- History
- Profile Detection

### 2. `/checks/single` - Single Check

**Flow:**
1. Dropdown: Select customer (`GET /api/v1/customers`)
2. Dropdown: Select check type (`GET /api/v1/checks/available`)
3. Multi-select: Select accounts (populated from selected customer's accounts)
4. Checkbox: "Select All Accounts"
5. Toggle: Send to Slack (on/off)
6. Button: "Run Check"
7. Loading state while executing
8. Display results as copyable text output

**API Call:**
```
POST /api/v1/checks/execute
{
  "customer_id": "uuid",
  "mode": "single",
  "check_name": "guardduty",
  "account_ids": ["uuid1", "uuid2"],  // null = all
  "send_slack": true
}
```

**Response Display:**
- Show execution time
- For each account result:
  - Account name + status badge (OK=green, WARN=yellow, ERROR=red, ALARM=orange)
  - Summary text
  - Expandable/collapsible output text with "Copy" button
- Show Slack sent status if enabled

### 3. `/checks/all` - All Check

**Flow:**
1. Dropdown: Select customer
2. Accounts auto-selected (all active)
3. Toggle: Send to Slack
4. Button: "Run All Checks"
5. Display grouped results

**API Call:**
```
POST /api/v1/checks/execute
{
  "customer_id": "uuid",
  "mode": "all",
  "send_slack": false
}
```

**Results grouped by check type:**
- Cost Anomaly results
- GuardDuty results
- Notifications results
- CloudWatch Alarm results

Each with status badge + copyable output.

### 4. `/checks/arbel` - Arbel Check (Aryanoble-specific)

**Flow:**
1. Customer auto-locked to Aryanoble (find by name "aryanoble")
2. Toggle: Send to Slack
3. Button: "Run Arbel Checks"
4. Display results (same format as All Check)

**API Call:**
```
POST /api/v1/checks/execute
{
  "customer_id": "<aryanoble-uuid>",
  "mode": "arbend_slack": false
}
```

### 5. `/customers` - Customer Management

**List View:**
- Table of customers with columns: Name, Display Name, Accounts Count, Slack Enabled
- Click row to expand/edit
- "Add Customer" button

**Add Customer Form:**
```
POST /api/v1/customers
{
  "name": "customer-slug",
  "display_name": "Customer Name",
  "slack_webhook_url": "https://hooks.slack.com/...",
  "slack_channel": "#monitoring",
  "slack_enabled": true
}
```

**Customer Detail (expanded):**
- Edit customer info (PATCH /api/v1/customers/{id})
- List of accounts with status badges
- "Add Account" button
- Delete customer button (with confirmation)

**Add Account Form:**
```
POST /api/v1/customers/{customer_id}/accounts
{
  "profile_name": "aws-profile-name",
  "display_name": "Production",
  "config_extra": {}  // optional
}
```

- profile_name: dropdown from detected profiles OR free text input
- Auto-detects AWS account ID on backend

**Edit/Delete Account:**
- PATCH /api/v1/accounts/{account_id}
- DELETE /api/v1/accounts/{account_id}

### 6. `/profiles` - Profile Detection

**Flow:**
1. Button: "Scan AWS Profiles"
2. Call `GET /api/v1/profiles/detect`
3. Display three lists:
   - All detected profiles
   - Already mapped profiles (with customer name)
   - Unmapped profiles (with "Add to Customer" quick action)

### 7. `/history` - Check History

**Filters:**
- Dropdown: Customer (required)
- Date range picker: Start date, End date
- Dropdown: Check mode (single/all/arbel/any)
- Dropdown: Check name (optional)
- Pagination controls

**API Call:**
```
GET /api/v1/history?customer_id=uuid&start_date=2026-03-01&end_date=2026-03-03&limit=50&offset=0
```

**List View:**
- Table: Date, Mode, Check Name, Duration, Status Summary (OK/WARN/ERROR counts), Slack Sent
- Click row to see detail

**Detail View (modal or page):**
```
GET /api/v1/history/{check_run_id}
```
- Full results per account
- Copyable output text
- Status badges

## UI Components

### Status Badge
```tsx
type Status = "OK" | "WARN" | "ERROR" | "ALARM" | "NO_DATA";

const colors = {
  OK: "bg-green-500",
  WARN: "bg-yellow-500",
  ERROR: "bg-red-500",
  ALARM: "bg-orange-500",
  NO_DATA: "bg-gray-500",
};
```

### Copyable Output Block
```tsx
// Pre-formatted text block with "Copy to Clipboard" button
// Monospace font, dark background
// Scrollable if content is long
```

### Loading State
```tsx
// Full-width spinner/progress indicator
// Show "Executing checks... this may take a few minutes"
// Disable form controls during execution
```

### Customer Selector
```tsx
// Reusable dropdown that fetches GET /api/v1/customers
// Shows display_name, stores id
// Used across Single Check, All Check, History pages
```

### Account Multi-Select
```tsx
// Checkbox list of accounts for selected customer
// "Select All" toggle
// Shows profile_name + display_name + account_id
// Disabled accounts shown but not selectable
```

## Design Guidelines

- Dark theme (slate/navy background)
- Monospace font for check outputs
- Status colors: green=OK, yellow=WARN, red=ERROR, orange=ALARM, gray=NO_DATA
- Responsive layout (works on desktop, reasonable on tablet)
- Copy buttons on all output text
- Loading states on all async operations
- Error handling with user-friendly messages
- Toast notifications for success/error actions

## API Error Handling

All API errors return:
```json
{
  "detail": "Error message string"
}
```

Handle:
- 400: Validation error (show message)
- 404: Not found (show message)
- 409: Conflict (e.g., duplicate customer name)
- 500: Server error (show generic message + retry option)
- Network error: Show connection error + retry

## File Structure

```
web/
  src/
    components/
      StatusBadge.tsx
      CopyableOutput.tsx
      CustomerSelector.tsx
      AccountMultiSelect.tsx
      LoadingSpinner.tsx
      Layout.tsx
      Navbar.tsx
    pages/
      Home.tsx
      SingleCheck.tsx
      AllCheck.tsx
      ArbelCheck.tsx
      Customers.tsx
      Profiles.tsx
      History.tsx
      HistoryDetail.tsx
    api/
      client.ts          # Axios/fetch wrapper
      customers.ts       # Customer API calls
      checks.ts          # Check execution API calls
      history.ts         # History API calls
      profiles.ts        # Profile detection API calls
    types/
      index.ts           # TypeScript interfaces
    App.tsx
    main.tsx
```

## TypeScript Interfaces

```typescript
interface Customer {
  id: string;
  name: string;
  display_name: string;
  slack_webhook_url: string | null;
  slack_channel: string | null;
  slack_enabled: boolean;
  created_at: string;
  updated_at: string;
  accounts: Account[];
}

interface Account {
  id: string;
  profile_name: string;
  account_id: string | null;
  display_name: string;
  is_active: boolean;
  config_extra: Record<string, any> | null;
  created_at: string;
}

interface CheckExecuteRequest {
  customer_id: string;
  mode: "single" | "all" | "arbel";
  check_name?: string;
  account_ids?: string[];
  send_slack: boolean;
}

interface CheckExecuteResponse {
  check_run_id: string;
  execution_time_seconds: number;
  results: CheckResultItem[];
  slack_sent: boolean;
}

interface CheckResultItem {
  account: {
    id: string;
    profile_name: string;
    display_name: string;
  };
  check_name: string;
  status: "OK" | "WARN" | "ERROR" | "ALARM" | "NO_DATA";
  summary: string;
  output: string;
}

interface HistoryItem {
  check_run_id: string;
  check_mode: string;
  check_name: string | null;
  created_at: string;
  execution_time_seconds: number | null;
  slack_sent: boolean;
  results_summary: {
    total: number;
    ok: number;
    warn: number;
    error: number;
  };
}

interface AvailableCheck {
  name: string;
  class: string;
}

interface ProfileDetection {
  all_profiles: string[];
  mapped_profiles: string[];
  unmapped_profiles: string[];
}
```
