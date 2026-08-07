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

This app was scaffolded on 2026-08-03 (re-scaffolded from the earlier `karama_proc` under a new name, before any real content existed — see Section 3 below). It currently contains no custom doctypes, fields, or business logic — installation shell only.

### 1.4 Scope (Planned — Not Yet Built)

Per `PROC_SUITE_ARCHITECTURE.md` Sections 2 and 3 (OOB-vs-Custom Decision Log, Notifications Master List — this app's repo, relocated from `SUPPLIER_PORTAL_SPEC.md` on 2026-08-06, see Section 3 below), pending items include:
- Purchase Order Amendment (the one confirmed genuine custom-build gap)
- Migration of `Supplier ASN`, `Supplier ASN Item`, `Supplier Invoice Dispute` doctypes from `supplier_portal`
- Migration of PO acknowledgment fields and Supplier onboarding fields from `supplier_portal`
- Purchase Requisition + approval workflow (OOB via Material Request + Frappe Workflow)
- Stock Management (OOB — Item, Warehouse, Stock Entry, Reorder Tool, Stock Reconciliation)
- Procurement and Stock reports (mix of OOB standard reports + custom Query Reports)
- Roles & Permissions (draft baseline adopted — see `PROC_SUITE_ARCHITECTURE.md` Section 1.6)

The relocation of cross-app architecture content (App Boundary, OOB-vs-Custom log, Notifications Master List, Roles & Permissions) from `SUPPLIER_PORTAL_SPEC.md` into `PROC_SUITE_ARCHITECTURE.md` in this app's repo is complete as of 2026-08-06 — see Section 3 below for the record of that move. All items listed above remain genuinely not started; only the relocation of the planning content itself is done.

---

## 2. Development Phases

| Phase | Status | Description |
|---|---|---|
| 0 — Scaffolding | ✅ Complete (2026-08-03) | App created (as `karama_proc`, then renamed to `proc_app` before any real content existed), installed on site1.local, this spec file initialized |
| 1 — Doctype Migration | ⬜ Not started | Move ASN, Invoice Dispute doctypes + PO/Supplier custom fields from supplier_portal |
| 2 — Purchase Requisition & Approval Workflow | ⬜ Not started | Configure Material Request + Frappe Workflow |
| 3 — Stock Management | ⬜ Not started | Configure Item, Warehouse, Stock Entry, Reorder Tool, Stock Reconciliation |
| 4 — PO Amendment (custom build) | ⬜ Not started | The one confirmed custom-doctype gap |
| 5 — Reports | ⬜ Not started | Procurement + Stock reports |
| 6 — Roles & Permissions | ⬜ Not started | Fixtures-based role/permission setup, following supplier_portal's pattern |

---

## 3. Known Issues & Decisions Log

| Date | Type | Description | Decision / Resolution |
|---|---|---|---|
| 2026-08-03 | Scaffolding | App created as `karama_proc` | `bench new-app karama_proc`, installed on site1.local. No custom code yet. |
| 2026-08-03 | Rename | Renamed `karama_proc` → `proc_app` (App Title: KCSC Proc) | Decided before any real content was added. Since the app was still an empty shell, executed as uninstall + folder removal + fresh `bench new-app proc_app`, rather than an in-place rename — avoids any risk of leftover references. |
| 2026-08-03 | Planned | Future task: split cross-app architecture content into `PROC_SUITE_ARCHITECTURE.md` | Sections 16-18 of `SUPPLIER_PORTAL_SPEC.md` (App Boundary & Ownership, OOB-vs-Custom Decision Log, Notifications Master List, Roles & Permissions) will be relocated to a new `PROC_SUITE_ARCHITECTURE.md` living in this app's repo. Decided to do this before Phase 1 (doctype migration) begins, not after. Not yet started. |
| 2026-08-06 | Complete | Cross-app architecture content relocated to `PROC_SUITE_ARCHITECTURE.md` | The task planned on 2026-08-03 (row above) is done. Old Sections 16-18 of `SUPPLIER_PORTAL_SPEC.md` were moved into this app's repo as `PROC_SUITE_ARCHITECTURE.md`, renumbered as Sections 1-3 there. All internal cross-references within the moved content were renumbered to match; 8 external cross-references remaining in `SUPPLIER_PORTAL_SPEC.md` were updated to point at the new location. Completed before Phase 1 (doctype migration) began, as planned. |

---

## 4. Changelog

| Version | Date | Author | Summary |
|---|---|---|---|
| 0.2 | 2026-08-06 | KCSC | Received the relocated cross-app architecture content (App Boundary & Ownership, OOB-vs-Custom Decision Log, Notifications Master List) from SUPPLIER_PORTAL_SPEC.md Sections 16-18, now living in this repo as PROC_SUITE_ARCHITECTURE.md. Updated Section 1.2 and Section 3 accordingly. |
| 0.1 | 2026-08-03 | KCSC | App scaffolded as `karama_proc`, then renamed to `proc_app` (App Title: KCSC Proc) before any real content was added. Spec file created/renamed to PROC_APP_SPEC.md accordingly. No functional content yet. |

---

*This document is the single source of truth for the KCSC Proc project. All team members and AI coding sessions must keep it current.*
