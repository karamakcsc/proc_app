# Procurement Suite — Architecture & Cross-App Decisions

---

> **Document Status:** `DRAFT v1.3`
> **Last Updated:** 2026-08-11
> **Maintained by:** KCSC — Karama Computer Services Company
> **Scope:** Cross-app architecture decisions spanning `supplier_portal` (VendorGate) and `proc_app` (KCSC Proc). This document does NOT describe either app's internal implementation details — see SUPPLIER_PORTAL_SPEC.md and PROC_APP_SPEC.md respectively for those.
> **Origin:** This content was originally written directly into SUPPLIER_PORTAL_SPEC.md (as Sections 16-18) during Phase 2 of the supplier_portal project, then relocated here on 2026-08-06 once proc_app existed, to avoid burying cross-app decisions inside a single app's spec. Full history of when each decision was made is preserved in SUPPLIER_PORTAL_SPEC.md's Changelog (Section 14, entries v5.1-v5.3) — this document does not duplicate that history, only the living content.
> **Update Policy:** This document MUST be updated whenever a cross-app architecture decision changes. Every Claude Code session working on either app should check this document for relevant context.

---

## 1. App Boundary & Ownership

### 1.1 Background

The project scope has expanded from a portal-only deliverable to a complete procurement system (see Solution Description Document), covering Procurement Management, Stock Management, VendorGate Supplier Portal, Supplier Invoice Workflow, and Supplier Scorecard. This system will be reused across multiple client deployments, some of which may run the back-office procurement functionality **without** the supplier portal at all.

> **Status of the Solution Description Document:** This document was authored by KCSC and shared with the pilot client as a commercial proposal. As of 2026-08-03, no workshop has yet taken place to confirm, adjust, or finalize its contents with the client. It should be treated as KCSC's informed starting point, not as agreed or final requirements. Scope, functions, roles, and approval thresholds described in Sections 1 and 2 below are expected to change — items may be added, removed, or redefined — once the Study & Design workshop takes place. Nothing in this spec sourced from the Solution Description Document should be built in Phase 3 as final without re-confirming it against the post-workshop outcome. `supplier_portal` (VendorGate) remains explicitly multi-client reusable per its own spec (SUPPLIER_PORTAL_SPEC.md, Section 1) — no client name is used elsewhere in this document, and the pilot client's identity is intentionally kept out of the architecture and scope sections below.

This requires splitting functionality across two separate Frappe apps:

- **`supplier_portal`** — the external-facing self-service UI only (branded VendorGate)
- **`proc_app`** (title: "KCSC Proc") — the reusable back-office core

**Dependency direction:** `supplier_portal` depends on `proc_app`. `proc_app` must function as a complete standalone system with zero dependency on `supplier_portal` being installed. A bank can deploy full back-office procurement via the ERPNext desk alone.

### 1.2 Decision Rule

For every doctype, custom field, and piece of logic currently in `supplier_portal`, the test applied is:

> **"Would this still need to exist if the procurement system were deployed with only the ERPNext desk UI, no portal at all?"**
> - Yes → belongs in `proc_app`
> - No, purely about the supplier-facing self-service experience → stays in `supplier_portal`

### 1.3 Ownership Decision Log (Code-Verified — Full Source Audit 2026-08-03)

| Item | Currently In | Decision | Reasoning |
|---|---|---|---|
| `Supplier ASN` + `Supplier ASN Item` doctypes | supplier_portal | **Move → `proc_app`** | Genuinely missing from ERPNext OOB (confirmed). Not portal-specific — a warehouse team could log expected shipments without a portal. |
| `Supplier Invoice Dispute` doctype | supplier_portal | **Move → `proc_app`** | Disputes are a procurement-process concept, not a UI concept. |
| Purchase Order fields: `supplier_acknowledged`, `supplier_acknowledged_on`, `supplier_acknowledgment_note` | supplier_portal | **Move → `proc_app`** | Core PO lifecycle state; needed regardless of channel. |
| Supplier fields: `commercial_registration_no`, `portal_onboarding_status`, `onboarding_submitted_on`, `onboarding_reviewed_by` | supplier_portal | **Move → `proc_app`** | Onboarding/KYC approval is a business process, not a UI concept. |
| `api/orders.py` → `acknowledge_po()`, `request_amendment()` | supplier_portal | **Split**: core logic (field updates / Comment creation) → callable function in `proc_app`. Portal keeps a thin `@frappe.whitelist()` wrapper that resolves the current session's supplier, then calls `proc_app`'s function. | Session/auth resolution is portal-specific; the underlying PO logic is not. |
| `api/asn.py` → `submit_asn()` | supplier_portal | **Split**, same pattern as above | |
| `api/invoices.py` → `get_po_items_for_invoice()`, `submit_invoice()`, `submit_dispute()` | supplier_portal | **Split**, same pattern | 3-way-match and invoice-building logic is procurement-domain. |
| `api/rfq.py` → `submit_quotation()` | supplier_portal | **Split**, same pattern | |
| `hooks.py` → `doc_events` (`on_po_submit`, `on_invoice_submit`, `on_grn_submit`) + all of `hooks_handlers.py` | supplier_portal | **Move → `proc_app`**, with the hardcoded `/supplier-portal/...` links removed or made conditional on the portal app being installed | These fire on core ERPNext doctypes (PO, Purchase Invoice, Purchase Receipt) regardless of whether a portal exists. See 1.4 below — this mechanism also needs a functional fix, not just relocation. |
| `setup.py` → `DOCTYPE_PERMS` / Custom DocPerm setup for the `Supplier Portal User` role | supplier_portal | **Stays in supplier_portal** | Frappe permissions are not app-scoped; this can reference doctypes owned by `proc_app`. This creates an expected hard dependency: supplier_portal requires `proc_app` to be installed to function fully. |
| `Supplier Portal Settings` doctype (branding: portal name, logo, colors, footer) | supplier_portal | **Stays** | Purely UI/branding, meaningless without a portal. |
| `Supplier Portal User` role (`desk_access: 0`) | supplier_portal | **Stays** | Only meaningful for a portal user. |
| `api/lang.py`, `api/notifications.py` (in-portal bell), `api/supplier.py` → `get_supplier_for_current_user()`, `require_supplier_login()` | supplier_portal | **Stays** | Pure portal-session/UI concerns. |
| All 13 `www/` pages (controllers + templates) | supplier_portal | **Stays** | Confirmed via code review — thin controllers calling into `api/`, no business logic of their own worth relocating. |

### 1.4 Known Issue Found During This Audit — Duplicate Supplier Notifications (Not Yet Fixed)

**Finding (2026-08-03, full source code review):** Two independent mechanisms are both wired to fire on the same three events, both emailing the same supplier contact:

| Event | Mechanism A — `fixtures/notification.json` (Frappe `Notification` doctype, declarative) | Mechanism B — `hooks.py` `doc_events` → `hooks_handlers.py` (`frappe.sendmail()`, imperative) |
|---|---|---|
| Purchase Order submit | "SP: Purchase Order Issued" | `on_po_submit()` |
| Purchase Receipt submit | "SP: Goods Receipt Created" | `on_grn_submit()` |
| Purchase Invoice submit | "SP: Invoice Approved" | `on_invoice_submit()` |

This means suppliers are likely receiving two separate emails per event today. This was not previously documented and has not been verified against live Email Queue data or fixed — it is logged here as a confirmed code-level finding pending a functional test and fix.

**Decision:** Standardize on Mechanism A (the fixture-based `Notification` doctype) going forward, since it is declarative, editable from the ERPNext desk without a deploy, and is the pattern already used for the other 3 of the 6 notifications (RFQ Assigned, Payment Made, Onboarding Status Updated). Mechanism B (`hooks_handlers.py` manual `sendmail()` calls) should be retired during the `proc_app` build in Phase 3, and its logic — the *decision* of when to notify and about what — moved into `proc_app`'s own notification fixtures, with the `/supplier-portal/...` links either parameterized or omitted when the portal is not installed.

**Status:** FIXED 2026-08-03. A full static code trace (not a live email test — this dev site has zero Email Account records configured, so no live test was possible; see investigation below) definitively confirmed the duplication was structural: `hooks.py`'s `doc_events` unconditionally wired `on_po_submit`/`on_grn_submit`/`on_invoice_submit` to fire on every submit, independent of and in addition to the fixture-based `Notification` records firing on the same three events. The three `doc_events` entries were disabled (`doc_events = {}`, commented with full context) in `hooks.py`; `hooks_handlers.py` was left in place with a deprecation notice for reference, not deleted, in case any logic from it is needed when `proc_app` absorbs this functionality in Phase 3. The fixture-based `Notification` records (all 6, including the 3 previously-duplicated ones) were confirmed untouched and enabled after the change. Site verified loading cleanly post-cache-clear. **Not yet verified against a live submit with real email delivery** — this dev site has no Email Account configured, so this fix is confirmed correct by code inspection, not by observing actual Email Queue behavior. Should be spot-checked on any site with a working Email Account before considering this fully closed.

### 1.5 Additional Finding — Incomplete File

`supplier_portal/api/delivery.py` exists but contains only a placeholder comment (`# placeholder`) — no functions implemented. The actual delivery/GRN tracking page (`www/supplier-portal/delivery.py`) reads data directly rather than routing through this file. Not a bug (nothing calls it), but noted so Phase 3 doesn't assume this file does something it doesn't.

### 1.6 Roles & Permissions — Adoption Decision (2026-08-03)

Given the Study & Design workshop with the pilot client will not happen in the near future, and holding all of Phase 3 indefinitely for it would stall real progress, the following decision was made:

**Adopted now, as the working baseline:**
- Role names and the function-level access matrix from the Solution Description Document (Section 10, page 28) — 6 internal roles (Department User, Procurement Officer, Procurement Manager, Finance, Warehouse, Management) plus Supplier, and which functions each can access — are adopted as-is for Phase 3 build purposes. This matrix is generic enough that it carries no client-specific assumptions.

**Not adopted — remains genuinely undefined:**
- Approval value thresholds (the JOD amounts that route a requisition to one approval tier vs. another) are NOT adopted, because the Solution Description Document does not specify even provisional numbers — it explicitly defers them to the workshop. Any approval Workflow built in Phase 3 must leave these as configurable values with no hardcoded defaults, not guessed numbers.

**Implementation pattern — roles/permissions in code, user assignment in the desk:**
- Role definitions, Custom DocPerm records, and Workflow state/transition definitions belong in `proc_app`'s source code as fixtures + an `after_install` setup routine — following the exact pattern already used in `supplier_portal` (`fixtures/role.json` + `setup.py`'s `DOCTYPE_PERMS` / `add_permission()` / `update_permission_property()`). This is what makes the app installable and functional out-of-the-box across multiple client deployments without manual reconfiguration each time.
- Assigning specific people to roles (e.g., "Ahmad — Procurement Officer") is tenant-specific data and is done per-deployment through ERPNext's standard Users and Roles desk screens — never hardcoded or shipped as fixture data.

**Status:** This baseline is provisional and explicitly subject to change once the workshop eventually happens — role names, access rules, and especially approval thresholds may all be revised. Nothing built against this baseline in Phase 3 should be treated as final. This decision unblocks Phase 3 planning and build work; it does not represent client sign-off.

---

## 2. OOB-vs-Custom Decision Log

### 2.1 Purpose

Per the project's Golden Rule (SUPPLIER_PORTAL_SPEC.md, Section 6): only build custom doctypes or fields where ERPNext genuinely has no equivalent. This section applies that same audit discipline to every new item introduced by the Solution Description Document, before any Phase 3 build work begins. Note: the decisions below are based on the Solution Description Document's current, pre-workshop content — see the disclaimer in Section 1.1. Where the workshop changes a requirement, its OOB-vs-Custom classification must be re-checked, not assumed to carry over.

### 2.2 Procurement Management

| Requirement | ERPNext v16 OOB Equivalent | Decision | Notes |
|---|---|---|---|
| Purchase Requisition (internal request, draft/submit, multi-item, attachments) | `Material Request` doctype | **Use OOB** | Material Request natively supports draft/submit, multiple items, attachments, and a `material_request_type` field. Maps cleanly to the described form and list view. |
| Requisition Approval Workflow (value/department-based routing, approve/reject/return, comments, approval trail) | Frappe `Workflow` doctype (configurable state machine) applied to `Material Request` | **Use OOB** | Frappe's native Workflow engine supports role-based transitions, conditional routing, and an approval trail via the document's timeline. Exact approval tiers and thresholds await the Study & Design workshop (see SUPPLIER_PORTAL_SPEC.md, Section 13). |
| RFQ (create, invite suppliers, deadline, attachments) | `Request for Quotation` | **Use OOB** | Already in use — no change needed. |
| Supplier Quotation & Comparison | `Supplier Quotation` doctype; comparison view | **Use OOB doctype; comparison likely needs a custom Query Report** | The quotation doctype is OOB. A side-by-side price comparison across multiple quotations for one RFQ is not a standard ERPNext report — needs a custom Query Report (not a new doctype) in Phase 3. |
| Purchase Order (issue, acknowledgment, timeline, cancel) | `Purchase Order` | **Use OOB** | Already in use. Acknowledgment fields already exist as custom fields on PO (SUPPLIER_PORTAL_SPEC.md, Section 6.1) — these move to `proc_app` per Section 1.3. |
| **Purchase Order Amendment** (amendment type, old-vs-new value comparison, reason, internal approval before supplier notification, amendment history) | None | **Genuine gap — requires a new custom doctype** | Confirmed no OOB equivalent. The current `Comment`-based workaround in `supplier_portal` (SUPPLIER_PORTAL_SPEC.md Section 7.4, and Section 1.3 below) is materially simpler than what the Solution Description Document actually specifies — it has no amendment-type classification, no old/new value comparison, and no internal approval gate before the supplier sees it. **This needs to be rebuilt as a proper custom doctype in `proc_app` during Phase 3**, not carried forward as-is. Flagged as a required scope item, not yet built. |
| Goods Receipt / GRN (accepted/rejected qty, batch/serial, rejection reasons) | `Purchase Receipt` + `Purchase Receipt Item` | **Use OOB** | Already in use. Batch/serial tracking and accepted/rejected quantity are native fields. |
| Procurement Reports (7 named reports in Solution Description Document) | Frappe `Report Builder` / `Query Report` | **Use OOB reporting framework** | None require new doctypes. Each is a query against existing/planned doctypes (Material Request, PO, Purchase Receipt, Purchase Invoice, Supplier Quotation). To be built as Query Reports in Phase 3. |
| Supplier Scorecard | `Supplier Scorecard` + `Supplier Scorecard Period` | **Use OOB** | Already in use (SUPPLIER_PORTAL_SPEC.md, Section 7.7 / dashboard). |

### 2.3 Stock Management

| Requirement | ERPNext v16 OOB Equivalent | Decision | Notes |
|---|---|---|---|
| Item Master (code, UOM, category, reorder level/qty, serial/batch tracking) | `Item` doctype | **Use OOB** | All described fields exist natively on Item. |
| Warehouse Setup (name, type, sub-warehouses, responsible person) | `Warehouse` doctype | **Use OOB** | Native tree-structure doctype supports sub-warehouses. |
| Stock Entry & Movements (Receipt/Issue/Transfer/Write-Off, linked to GRN) | `Stock Entry` doctype | **Use OOB** | `stock_entry_type` field natively covers all four described movement types. |
| Reorder Alerts (below reorder level, suggested qty, create requisition from alert) | `Bin` (tracks reorder level per item/warehouse) + ERPNext's built-in Reorder Tool → auto-creates `Material Request` | **Use OOB** | ERPNext already has a native "Reorder" report/tool that generates Material Requests for items below their reorder level. |
| Stock Valuation (value by item/warehouse, valuation rate, export) | `Stock Ledger Entry` + native Stock Valuation reports | **Use OOB** | Valuation method (FIFO/Moving Average) is a per-Item/Company setting, already native. |
| Physical Stock Count (count sheet, variance, approval, auto-adjust) | `Stock Reconciliation` doctype | **Use OOB** | Natively supports count entry, variance calculation, and stock adjustment on submit. |
| Stock Reports (6 named reports in Solution Description Document) | Frappe `Report Builder` / `Query Report`; several already exist as ERPNext standard reports (Stock Balance, Stock Ledger, Stock Ageing) | **Use OOB where standard reports exist; custom Query Report for the rest** | Stock Balance, Stock Ledger, and Stock Ageing are existing ERPNext standard reports. Items Below Reorder Level and Physical Count Variance likely need light custom Query Reports — confirm exact fit during Phase 3, not assumed here. |

### 2.4 Summary

Of the entire expanded scope reviewed here, **only one genuine custom-build gap was identified: the Purchase Order Amendment workflow**, and even that is a refinement of something already partially built (the `Comment`-based version), not a build-from-zero item. Every other new requirement — Purchase Requisition, approval routing, all of Stock Management, and all named reports — has a direct, native ERPNext v16 equivalent. This confirms the OOB-first approach is viable for the vast majority of the expanded scope and significantly limits the custom development surface for Phase 3.

Not yet audited in this pass (deferred — insufficient detail in the Solution Description Document, or requires the Study & Design workshop first): Contract Management (mentioned only in the permissions matrix and glossary, no dedicated section in the Solution Description Document to audit against).

---

## 3. Notifications Master List

### 3.1 Purpose

The Solution Description Document specifies 21 notification events across the full procurement lifecycle. This section maps each one against what currently exists (6 notifications, built for the portal-only scope — SUPPLIER_PORTAL_SPEC.md, Section 10.1), to identify what's net-new for Phase 3. As with Section 2, this is based on pre-workshop content — see the disclaimer in Section 1.1.

### 3.2 Full Event List vs. Current State

| # | Event | Recipient | Channel | Current State |
|---|---|---|---|---|
| 1 | New RFQ assigned to supplier | Supplier | Email + Portal bell | ✅ Exists ("SP: New RFQ Assigned") |
| 2 | RFQ deadline approaching (24 hours) | Supplier | Email | ⬜ Net-new — needs a scheduled/time-based trigger, not a simple doc-event |
| 3 | Supplier quotation received | Procurement Officer | Email + Desk notification | ⬜ Net-new — internal-facing, not built (current scope only notifies suppliers) |
| 4 | Purchase Order issued to supplier | Supplier | Email + Portal bell | ⚠️ Exists, but duplicated — see Section 1.4 (both "SP: Purchase Order Issued" fixture and `on_po_submit()` code fire on the same event) |
| 5 | Supplier acknowledges PO | Procurement Officer | Email + Desk notification | ⬜ Net-new — internal-facing, not built |
| 6 | Supplier submits ASN | Warehouse Manager | Email + Desk notification | ⬜ Net-new — internal-facing, not built |
| 7 | Goods Receipt recorded | Supplier | Email + Portal bell | ⚠️ Exists, but duplicated — see Section 1.4 ("SP: Goods Receipt Created" + `on_grn_submit()`) |
| 8 | Goods Receipt has rejected items | Procurement Officer | Email + Desk notification | ⬜ Net-new — internal-facing, and depends on GRN rejection-quantity logic not yet confirmed as built |
| 9 | Supplier submits invoice | Procurement Officer | Email + Desk notification | ⬜ Net-new — internal-facing, not built |
| 10 | Invoice approved by Procurement | Finance Officer | Email + Desk notification | ⬜ Net-new — internal-facing, not built |
| 11 | Invoice approved for payment | Supplier | Email + Portal bell | ⚠️ Exists, but duplicated — see Section 1.4 ("SP: Invoice Approved" + `on_invoice_submit()`). Note: current code fires this on invoice *submit*, not on payment-approval — the trigger point itself may not match the Solution Description Document's intent; needs re-verification in Phase 3. |
| 12 | Payment made to supplier | Supplier | Email + Portal bell | ✅ Exists ("SP: Payment Made") |
| 13 | Invoice rejected | Supplier | Email + Portal bell | ⬜ Net-new — not built |
| 14 | Dispute raised by supplier | Procurement Officer | Email + Desk notification | ⬜ Net-new — internal-facing, not built (supplier can raise a dispute via `api/invoices.py` → `submit_dispute()`, but no notification currently fires from it) |
| 15 | Dispute resolved / rejected | Supplier | Email + Portal bell | ⬜ Net-new — not built |
| 16 | Onboarding approved | Supplier | Email + Portal bell | ⚠️ Partially covered — "SP: Onboarding Status Updated" fires on any `portal_onboarding_status` value change (Approved, Rejected, or Under Review alike), not specifically on Approved. Needs splitting or conditioning in Phase 3 to match the two distinct events (#16, #17) the Solution Description Document expects. |
| 17 | Onboarding rejected | Supplier | Email + Portal bell | ⚠️ Same as #16 — currently one generic event, not two distinct ones |
| 18 | Stock below reorder level | Procurement Officer | Email + Desk notification | ⬜ Net-new — depends on Stock Management (Section 2.3) being built first; ERPNext's native Reorder Tool may have its own alerting to evaluate before building custom notification logic |
| 19 | Requisition submitted for approval | Approver | Email + Desk notification | ⬜ Net-new — depends on Requisition Approval Workflow (Section 2.2) being built first; Frappe's native Workflow engine may handle this automatically via its own notification hooks — needs verification before assuming custom work is required |
| 20 | Requisition approved | Requester | Email + Desk notification | ⬜ Net-new — same dependency as #19 |
| 21 | Requisition rejected | Requester | Email + Desk notification | ⬜ Net-new — same dependency as #19 |

### 3.3 Summary

- **2 of 21** events are cleanly built and working as specified (#1 New RFQ Assigned, #12 Payment Made)
- **3 of 21** exist but are affected by the duplicate-mechanism issue documented in Section 1.4 (#4, #7, #11) and must be fixed as part of retiring the `hooks_handlers.py` mechanism, not simply left as-is
- **2 of 21** exist but don't match the Solution Description Document's granularity (#16, #17 — one generic onboarding-status event needs to become two specific ones)
- **14 of 21** are net-new, not yet built in any form
- **6 of the net-new events** (#18–21, and arguably #2) may be partially or fully satisfiable by Frappe/ERPNext's own native scheduler, Workflow engine, or Reorder Tool notification hooks rather than requiring fully custom notification logic — this should be checked during Phase 3 build, following the same OOB-first discipline as Section 2, rather than assumed to need custom code.

All notification ownership (which app owns which notification definition) follows the same App Boundary logic as Section 1: notifications tied to internal procurement events (##2, 3, 5, 6, 8, 9, 10, 13, 14, 15, 18, 19, 20, 21) belong in `proc_app`; notifications specifically about the supplier's portal experience may still originate from procurement-app events but should not hardcode portal URLs unless supplier_portal is confirmed installed (same caveat as Section 1.4).

---

## 4. Internal Self-Service Portal — Strategic Decision (2026-08-10, Not Yet Built)

### 4.1 Decision

A third companion app will be built: an internal self-service portal for bank staff, following the exact same architectural relationship already established for supplier_portal — a UI-only app that depends on proc_app, never the reverse. This is a deliberate application of the App Boundary principle (Section 1) to a second audience.

proc_app is the core logic layer (doctypes, roles, workflow, permissions). supplier_portal depends on it and is external-facing, for suppliers, branded VendorGate. `proc_portal` (title: "Proc Portal") will also depend on proc_app, and will be internal-facing, for bank staff, with its own branding not yet decided.

### 4.2 Vision and Scope Ambition

Unlike a narrow single-task add-on, this portal is intended to be comprehensive enough to cover most bank-user tasks across the procurement lifecycle — not just requisition creation, but the full range of actions a bank employee would otherwise need desk access for, including approval actions. This means Department Manager, Department Officer, and Procurement Officer approvals (currently only exercised via the ERPNext desk's native Workflow buttons) are expected to eventually be performed through this portal too, not just by requesters creating new documents.

The ERPNext desk interface remains available in parallel, for genuinely power users who want full platform flexibility. This is not a replacement of desk access — it is establishing the portal as the default experience for most users, including managers, while desk access remains an option for those who prefer or need it.

### 4.3 Strategic Rationale — Product Identity

Beyond usability, this is a deliberate branding and product-identity decision: a well-designed, KCSC-branded portal gives the overall system its own identity, distinct from "an ERPNext deployment." This mirrors the same reasoning that shaped VendorGate's branding for supplier_portal — the portal becomes the face of the product that most users actually experience, while the underlying ERPNext/Frappe platform remains largely invisible to them.

### 4.4 Architectural Principles (carried forward from Section 1 and PROC_APP_SPEC.md's established patterns)

- Thin client over proc_app, never a reimplementation: the portal must call the same underlying mechanisms already proven in proc_app — apply_workflow() for approval actions, the same permission model, the same doctypes — rather than reimplementing business rules in the portal layer. This is the same discipline supplier_portal already follows.
- Role/permission work does not disappear, it relocates: the portal still requires correct DocPerm scoping underneath every action it exposes, same as the desk does. Custom API endpoints (matching supplier_portal's api/ pattern) allow enforcing intended business rules precisely, which can arguably be safer than generic desk-level permission checks.
- Feature scope is a living, explicit decision, not implicit: whatever is not yet exposed in the portal remains accessible only via the desk. This must be tracked explicitly (a living scope list) rather than assumed complete, to avoid users hitting silent walls.

### 4.5 Known Risks (assessed 2026-08-10, none blocking, all requiring ongoing attention)

| Risk | Mitigation |
|---|---|
| Feature drift — portal not covering something the desk does | Maintain an explicit, living "portal scope" list; review each time proc_app's workflow or doctypes change |
| Workflow changes need portal updates too (desk reflects Frappe Workflow automatically; a custom portal does not) | Portal must call the same apply_workflow() mechanism, never hardcode state/transition logic independently |
| Build effort is substantial — the single Material Request workflow alone took a full session with multiple real discoveries | Phase the build: start with the highest-value, already-proven flow (Material Request) before expanding to Purchase Orders, balance-checking, etc. |
| Two UIs (desk + portal) performing the same approval actions could diverge in behavior if not both routed through the same underlying mechanism | Enforced by the "thin client" principle in 4.4 — both UIs are just different front doors onto the same proc_app logic |

### 4.6 Status

Decision made, not yet built. App named 2026-08-11: proc_portal (App Title: "Proc Portal" — working title, real brand identity to be decided later, consistent with the strategic product-identity goal in Section 4.3). Remaining open item before build begins: scope/order of the first screens to build. Recommended starting point (not yet confirmed): Material Request creation and approval, since the underlying workflow is already fully built and tested in proc_app as of 2026-08-09.

---

## 5. Known Issue — Login Redirect Only Works on the Login Request Itself (Found 2026-08-22, Not Yet Fixed)

### 5.1 Symptom

`requester.test` logged in fresh and still landed on the desk instead of `/proc-portal`, despite the `on_login`-based redirect fix (see `PROC_PORTAL_SPEC.md` Section 3) having been built, tested, and confirmed working via real HTTP login tests in an earlier session.

### 5.2 Investigation — Hypotheses Tested and Ruled Out

Each of the following was tested directly against real HTTP requests/live data before being ruled out, rather than assumed:

- **Bookmark/`redirect-to` query parameter** taking priority over the `on_login` flag — refuted. An unauthenticated visit to the bare domain root produces no redirect at all (`200`, no `Location` header, no redirect history); the login page is rendered directly at `/` with a clean URL.
- **A hidden field or embedded JS variable in the login page defaulting a redirect target to `/app`** — refuted. A full-text search of the rendered login page HTML for `redirect`, `redirect_to`, `redirect_location`, and `"app"` found zero matches.
- **Stale running web-server processes from an incomplete restart** (e.g. after Yasser's laptop reboot) — refuted. The process bound to port 8000 that's actually serving requests is Werkzeug's reloader *child*, which restarts automatically on every `.py` file change; it was confirmed fresh (started one second after the most recent `.py` edit in the session, well after `hooks.py`'s last real change). No process restart was needed or performed to resolve this investigation.

### 5.3 Actual Root Cause — Confirmed via Source

The `on_login` hook (`proc_portal.before_request.redirect_portal_users`) sets `frappe.local.flags.home_page`, which is consulted by `frappe.website.utils.get_home_page()` — **but that flag is request-scoped**. It only exists for the lifetime of the login POST request itself. Any subsequent, separate request to `/` (a fresh page load, a reload, or the browser's own top-level navigation landing back on `/` rather than following the login response's `home_page` value directly) starts a new request where the flag is empty, and `get_home_page()` falls through its own independent chain instead: `Role.home_page` → `Portal Settings.default_portal_home` → hook-based overrides (`get_website_user_home_page`, `website_user_home_page`, `role_home_page`, `home_page`) → `Website Settings.home_page` → default `"me"`, which is hard-coded to `"desk"` for any `System User` with no `default_workspace` set. **`User.default_app` — the field `on_login` actually keys off — is never read anywhere in this fallback chain.**

Traced with real data for `requester.test` (`user_type: System User`, roles `Department User`/`All`/`Guest`/`Desk User`, none with `Role.home_page` set, no matching hooks registered, no `default_workspace`): this chain resolves to `"desk"` deterministically, every time, for any request to `/` other than the login POST itself.

### 5.4 Status

**Fixed (2026-08-23), via a second, independent hook alongside `on_login`.** Since `frappe.local.flags.home_page` cannot survive past the login request, a new `before_request` hook (`proc_portal.before_request.redirect_bare_root_for_portal_users`) was added to check `default_app` fresh on every request instead of relying on that one-time flag: it fires on every request, checks `frappe.session.user` (skips `Guest`) and `frappe.request.path` (only acts on bare `/`), then reads `User.default_app` directly from the DB and issues a redirect if it equals `proc_portal`. `on_login` is kept as-is for the immediate post-login case; the two hooks now cover both scenarios (the login response itself, and any later independent visit to `/`).

One non-obvious implementation detail worth recording: raising `frappe.Redirect` from `before_request` does **not** work, confirmed by reading `frappe/app.py`'s request dispatch directly. `before_request` hooks run inside `init_request()`, and any exception they raise is caught by `application()`'s single generic exception handler (`response = e.get_response(...) if isinstance(e, HTTPException) else handle_exception(e)`). `frappe.Redirect` is a plain `Exception`, not a `werkzeug.exceptions.HTTPException`, so it falls to `handle_exception()` — which has no special case for it and would render a broken generic error page (status 301, no `Location` header), not a redirect. `frappe.Redirect` only produces a real redirect when caught by `frappe/website/serve.py`'s page-rendering-specific handler (`RedirectPage(...).render()`), a code path only reached via `get_response()` for page controllers — never reached from `before_request`, which runs earlier. The working fix instead raises `werkzeug.routing.exceptions.RequestRedirect` (a genuine `HTTPException` subclass, so `application()`'s handler correctly calls its `get_response()`), with its default `code` overridden from `308` (permanent — dangerous here, since browsers can cache a permanent redirect indefinitely regardless of session state) to `302` (temporary).

Verified live with 3 scenarios via real HTTP, session-reused where relevant: (A) an already-logged-in `proc_portal` user visiting bare `/` gets `302` → `Location: /proc-portal`; (B) a Guest visiting bare `/` is unaffected (`200`, no `Location`, login page served normally); (C) a normal non-root API call is unaffected (`200`). `Administrator.default_app` reconfirmed `NULL`, so this hook can never match that account. Same underlying gap likely affects `supplier_portal`'s equivalent `on_login` hook (`supplier_portal.on_login.redirect_portal_users`) — not yet fixed there, out of scope for this change, worth revisiting before considering the *category* of issue fully closed.

### 5.5 Process Lesson

Multiple plausible-sounding hypotheses (bookmark parameters, login-page content, stale processes) were tested and refuted via real requests/data before the actual root cause was found by reading `frappe/website/utils.py`'s `get_home_page()` directly — confirming the project's standing practice of verifying against real code and live behavior rather than accepting a plausible-sounding theory (including "it must be a stale process after a restart," which felt intuitive but did not hold up under direct process-timing evidence).

---

*This document is the source of truth for cross-app architecture decisions in the KCSC procurement suite. See SUPPLIER_PORTAL_SPEC.md and PROC_APP_SPEC.md for app-specific implementation details.*
