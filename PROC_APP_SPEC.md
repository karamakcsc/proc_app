# KCSC Proc — Project Specification
## Built on Frappe Framework / ERPNext v16

---

> **Document Status:** `DRAFT v0.1`
> **Last Updated:** 2026-08-03
> **Maintained by:** KCSC — Karama Computer Services Company
> **App Name:** `proc_app`
> **Target Version:** ERPNext v16.30 / Frappe v16.29
> **Deployment Model:** Multi-client reusable app — standalone-capable, no dependency on any supplier portal. `supplier_portal` (VendorGate) optionally depends on this app; this app never depends on `supplier_portal`.
> **Update Policy:** This document MUST be updated whenever a feature, flow, architecture decision, or implementation detail changes. Every Claude Code session should begin by reading this file and end by proposing updates to it.

---

## 1. Project Overview

### 1.1 Purpose

KCSC Proc is the reusable back-office procurement system underlying KCSC's procurement solution suite. It covers Procurement Management (Purchase Requisition through Goods Receipt), Stock Management, and procurement/stock reporting, built entirely on ERPNext v16 out-of-the-box functionality wherever possible, with custom development limited to genuine gaps only.

KCSC Proc is designed to function as a complete, standalone procurement system via the ERPNext desk alone — a client may deploy it with or without a supplier-facing portal.

### 1.2 Relationship to supplier_portal (VendorGate)

`supplier_portal` is a separate, optional companion app that provides supplier self-service UI on top of KCSC Proc. The dependency is one-directional: `supplier_portal` depends on `proc_app`; `proc_app` never depends on `supplier_portal`. Full rationale and the ownership decision log for what belongs in which app is documented in `PROC_SUITE_ARCHITECTURE.md` (this app's repo), Section 1 (App Boundary & Ownership) — this content was originally written into `SUPPLIER_PORTAL_SPEC.md` Section 16 during Phase 2 of the supplier_portal project, then relocated here on 2026-08-06.

### 1.3 Status

This app was scaffolded on 2026-08-03 (re-scaffolded from the earlier `karama_proc` under a new name, before any real content existed — see Section 4 below). It currently contains no custom doctypes, fields, or business logic — installation shell only.

### 1.4 Scope (Planned — Not Yet Built)

Per `PROC_SUITE_ARCHITECTURE.md` Sections 2 and 3 (OOB-vs-Custom Decision Log, Notifications Master List — this app's repo, relocated from `SUPPLIER_PORTAL_SPEC.md` on 2026-08-06, see Section 4 below), pending items include:
- Purchase Order Amendment (the one confirmed genuine custom-build gap)
- Migration of `Supplier ASN`, `Supplier ASN Item`, `Supplier Invoice Dispute` doctypes from `supplier_portal`
- Migration of PO acknowledgment fields and Supplier onboarding fields from `supplier_portal`
- Purchase Requisition + approval workflow (OOB via Material Request + Frappe Workflow)
- Stock Management (OOB — Item, Warehouse, Stock Entry, Reorder Tool, Stock Reconciliation)
- Procurement and Stock reports (mix of OOB standard reports + custom Query Reports)
- Roles & Permissions (draft baseline adopted — see `PROC_SUITE_ARCHITECTURE.md` Section 1.6)

The relocation of cross-app architecture content (App Boundary, OOB-vs-Custom log, Notifications Master List, Roles & Permissions) from `SUPPLIER_PORTAL_SPEC.md` into `PROC_SUITE_ARCHITECTURE.md` in this app's repo is complete as of 2026-08-06 — see Section 4 below for the record of that move. All items listed above remain genuinely not started; only the relocation of the planning content itself is done.

---

## 2. Development Phases

| Phase | Status | Description |
|---|---|---|
| 0 — Scaffolding | ✅ Complete (2026-08-03) | App created (as `karama_proc`, then renamed to `proc_app` before any real content existed), installed on site1.local, this spec file initialized |
| 1 — Doctype Migration | ⬜ Not started | Move ASN, Invoice Dispute doctypes + PO/Supplier custom fields from supplier_portal |
| 2 — Purchase Requisition & Approval Workflow | 🟡 In Progress — design documented, see Section 3. Build not yet started. | Configure Material Request + Frappe Workflow |
| 3 — Stock Management | ⬜ Not started | Configure Item, Warehouse, Stock Entry, Reorder Tool, Stock Reconciliation |
| 4 — PO Amendment (custom build) | ⬜ Not started | The one confirmed custom-doctype gap |
| 5 — Reports | ⬜ Not started | Procurement + Stock reports |
| 6 — Roles & Permissions | ⬜ Not started | Fixtures-based role/permission setup, following supplier_portal's pattern |

---

## 3. Material Request Approval Workflow — Design (Not Yet Built)

### 3.1 Purpose

This documents the design for proc_app's first real feature: a Material Request approval workflow, built entirely on ERPNext v16 OOB capabilities (Material Request doctype + Frappe Workflow engine) plus 4 custom fields. Designed 2026-08-07, based on a real example workflow provided by KCSC, before the client workshop — treated as a standard baseline per the same "adopt now, refine later" principle as Section 1.6 of PROC_SUITE_ARCHITECTURE.md.

### 3.2 Reference Example (source of this design)

A Finance Department employee needs printer ink. They create a Material Request addressed to IT (the department that manages that item type). The Finance Department Manager approves first. Then IT's "person in charge" (Officer) checks stock: if available, it's issued directly from IT's warehouse to Finance; if not, it goes to IT's Manager for approval, then to Procurement's Officer for final approval, before becoming a Purchase Order.

### 3.3 Custom Fields Required

On Material Request:
- requesting_department (Link to Department) — the department that needs the item, e.g. Finance
- concerned_department (Link to Department) — the department that manages/reviews that item type, e.g. IT

On Department:
- department_manager (Link to User) — this department's manager, approves requests where this department is either the requesting or concerned department
- department_officer (Link to User) — this department's person in charge, reviews stock availability and decides the issue-vs-purchase branch when this department is the concerned department

### 3.4 New Roles Required

- Department Manager — generic role, held by whoever manages any department. Actual approval authority for a specific request is enforced via a Workflow transition condition checking that the acting user matches the relevant department's department_manager field, not by the role alone.
- Department Officer — same pattern, checked against department_officer.
- Procurement's final approval reuses the existing draft Procurement Officer role (see PROC_SUITE_ARCHITECTURE.md, Section 1.6) — no new role needed there.

### 3.5 Workflow States & Transitions

Draft, then Submit moves it to Pending Requesting-Department Approval, where the approver is the requesting department's department_manager. Approve moves it to Pending Concerned-Department Review, where the approver is the concerned department's department_officer. From there, two branches: Approve as Issue from Stock moves it directly to Approved – Issue (docstatus: Submitted). Approve as Forward to Purchase moves it to Pending Concerned-Department Manager Approval, where the approver is the concerned department's department_manager; Approve there moves it to Pending Procurement Approval, where the approver holds the Procurement Officer role; Approve there moves it to Approved – Purchase (docstatus: Submitted). A Reject action is available at every approval step and moves the request to Rejected.

Each department-scoped approval uses a Workflow Transition condition (confirmed available on Frappe's Workflow Transition doctype, condition field, Code type) — e.g., a transition is only enabled for the acting user if they match the relevant department's department_manager or department_officer field for the specific department linked on that request. This means the same 2 roles work correctly for every department, without per-department configuration beyond setting the 2 Department fields.

Approved – Issue and Approved – Purchase are both docstatus: Submitted states — at that point, ERPNext's existing native Create actions (confirmed present, no custom code needed) become available: make_stock_entry() for the issue path, make_purchase_order() / make_request_for_quotation() for the purchase path.

### 3.6 Deliberately Deferred (Not Built in This Phase)

- Free-text / not-yet-in-system items: ERPNext's Material Request Item.item_code is mandatory at the Frappe framework level (confirmed via code audit, not just a UI restriction) — allowing a supplier or requester to describe an item that doesn't exist yet in the Item master would require genuine custom code (a flag + description field, plus a script to auto-create the Item record at PO time). This is a real, scoped piece of custom work, deliberately deferred until the core approval workflow is built and proven. Not forgotten — tracked here.
- Approval value thresholds: still pending the client workshop (see PROC_SUITE_ARCHITECTURE.md, Section 1.6) — this workflow's approvals are role/department-based, not value-based, for now.
- **Self-approval:** `allow_self_approval` was left at Frappe's default (`1`, allowed) on all Workflow transitions. This was a deliberate decision (2026-08-08), not an oversight — confirmed explicitly rather than assumed. If a single person holds both the requester's identity and the relevant approval role for a given request, they are permitted to approve their own request at any stage.

---

## 4. Known Issues & Decisions Log

| Date | Type | Description | Decision / Resolution |
|---|---|---|---|
| 2026-08-03 | Scaffolding | App created as `karama_proc` | `bench new-app karama_proc`, installed on site1.local. No custom code yet. |
| 2026-08-03 | Rename | Renamed `karama_proc` → `proc_app` (App Title: KCSC Proc) | Decided before any real content was added. Since the app was still an empty shell, executed as uninstall + folder removal + fresh `bench new-app proc_app`, rather than an in-place rename — avoids any risk of leftover references. |
| 2026-08-03 | Planned | Future task: split cross-app architecture content into `PROC_SUITE_ARCHITECTURE.md` | Sections 16-18 of `SUPPLIER_PORTAL_SPEC.md` (App Boundary & Ownership, OOB-vs-Custom Decision Log, Notifications Master List, Roles & Permissions) will be relocated to a new `PROC_SUITE_ARCHITECTURE.md` living in this app's repo. Decided to do this before Phase 1 (doctype migration) begins, not after. Not yet started. |
| 2026-08-06 | Complete | Cross-app architecture content relocated to `PROC_SUITE_ARCHITECTURE.md` | The task planned on 2026-08-03 (row above) is done. Old Sections 16-18 of `SUPPLIER_PORTAL_SPEC.md` were moved into this app's repo as `PROC_SUITE_ARCHITECTURE.md`, renumbered as Sections 1-3 there. All internal cross-references within the moved content were renumbered to match; 8 external cross-references remaining in `SUPPLIER_PORTAL_SPEC.md` were updated to point at the new location. Completed before Phase 1 (doctype migration) began, as planned. |

---

## 5. Changelog

| Version | Date | Author | Summary |
|---|---|---|---|
| 0.4 | 2026-08-08 | KCSC | Built the Material Request Approval Workflow (inactive, is_active: 0): 4 custom fields (Material Request: requesting_department, concerned_department; Department: department_manager, department_officer), 4 new roles (Department Manager, Department Officer, Department User, Procurement Officer), 8 Workflow States, 3 new Workflow Action Masters, and the Workflow document itself (8 states, 10 transitions, role-based gating, no department-matching conditions yet). All captured as proc_app fixtures via export-fixtures, verified via migrate. Frappe's auto-created workflow_state custom field on Material Request confirmed and fixture-captured. Self-approval left at Frappe's default (allowed) — confirmed as a deliberate decision, documented in Section 3.6. Workflow remains inactive and role-based conditions are not yet department-scoped (Part C, not yet started) — do not activate or rely on this workflow enforcing department-specific routing yet. |
| 0.3 | 2026-08-07 | KCSC | Documented Material Request Approval Workflow design (new Section 3) — custom fields, roles, workflow states/transitions, based on a real example workflow. Confirmed via live ERPNext audit: Material Request has no existing department field, Department has no manager field (both need custom fields), Workflow Transition supports condition-based routing (confirmed viable), native Create actions (Stock Entry, Purchase Order, RFQ) already exist on Material Request. Free-text/not-yet-in-system item support deliberately deferred — confirmed to require genuine custom code (item_code is framework-level mandatory), not just configuration. Design not yet built — this is documentation only. |
| 0.2 | 2026-08-06 | KCSC | Received the relocated cross-app architecture content (App Boundary & Ownership, OOB-vs-Custom Decision Log, Notifications Master List) from SUPPLIER_PORTAL_SPEC.md Sections 16-18, now living in this repo as PROC_SUITE_ARCHITECTURE.md. Updated Section 1.2 and Section 3 accordingly. |
| 0.1 | 2026-08-03 | KCSC | App scaffolded as `karama_proc`, then renamed to `proc_app` (App Title: KCSC Proc) before any real content was added. Spec file created/renamed to PROC_APP_SPEC.md accordingly. No functional content yet. |

---

*This document is the single source of truth for the KCSC Proc project. All team members and AI coding sessions must keep it current.*
