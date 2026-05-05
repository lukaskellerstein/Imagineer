# Feature Specification: Imagineer MVP — From a Picture to a 3D Preview

**Feature Directory**: `specs/001-init/`
**Created**: 2026-05-05
**Status**: Ready for `/speckit.plan` (clarifications resolved)
**Input**: User description in [`../../docs/my-specs/001-init/README.md`](../../docs/my-specs/001-init/README.md).

> Imagineer turns a customer's reference photo into a previewable 3D model. The customer uploads an image, the platform runs a locally-hosted AI generator, and the customer interacts with the result in the browser. From the preview the customer can either **download the mesh** to print themselves, or **request a quote** so an operator can follow up about a printed-and-shipped piece.
>
> **What this MVP is** — a focused validation of (a) AI quality (does an image produce a usable mesh?), (b) the preview UX (do customers understand what they are seeing?), and (c) demand for fulfilled prints (do customers click "request a quote"?).
>
> **What this MVP is not** — a commerce platform. Payment, shipping, automated print-shop integration, order status, and accounts are explicitly post-MVP; the operator handles every quote off-platform.

## Clarifications

| # | Question | Resolution |
|---|----------|------------|
| Q1 | MVP scope | **RESOLVED — Option A**: generate-and-preview only. Customer can download the GLB or submit a quote request. No payment, no shipping, no automated fulfillment in v1. |
| Q2 | Input modes | **RESOLVED — Option A**: image upload only. Text-to-3D is post-MVP. |
| Q3 | Fulfillment integration depth | **RESOLVED — Option A**: manual operator handoff. Operator receives quote requests in a dashboard and follows up with the customer off-platform. No print-shop API integration in v1. |

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Hobbyist previews a model from a photo and downloads it (Priority: P1)

A hobbyist saw an unusual object online (e.g., a unique cookie cutter, a stylised animal figurine), has a clear reference photo, and owns a 3D printer. They want to inspect a generated mesh before deciding whether to print it themselves.

**Why this priority**: This is the core value proposition of the MVP. It exercises every system the v1 introduces — image intake, background removal, AI generation, print-readiness check, in-browser preview, GLB download.

**Independent Test**: A tester uploads a reference image (e.g., `subaru_impreza.png`), watches the model render in the browser, rotates and inspects it, downloads the GLB, and opens it in a third-party slicer. Pass = the slicer accepts the file and shows a sensible mesh.

**Acceptance Scenarios**:

1. **Given** a customer with a clear reference image (subject ≥ 60% of frame, foreground / background distinguishable), **When** they upload it and confirm "Generate", **Then** the system removes the background, runs shape generation, runs the print-readiness check, and renders an interactive 3D preview within the time budget defined in NFR-001.
2. **Given** the preview is loaded, **When** the customer rotates / zooms the model and clicks "Download", **Then** the browser downloads the GLB file.
3. **Given** the readiness check found a fixable defect, **When** the preview loads, **Then** the customer sees a clear notice ("auto-repaired N issues") explaining what was changed.

### User Story 2 — Gift-buyer with a phone photo requests a quote (Priority: P1)

A gift-buyer wants a 3D-printed memento of an in-joke (e.g., a stylised version of a friend's pet) but does not own a printer. They upload a phone photo, like the result, and submit a "request a quote" form so an operator can follow up.

**Why this priority**: Personalised gifts are one of the largest target segments named in the brief, and they are the source of every potential paying customer in the MVP. They also stress-test the AI on real-world (low-quality, cluttered-background) photos rather than curated reference shots.

**Independent Test**: Tester uploads a phone photo with a busy background, approves the preview, submits the quote form with email and optional notes, and receives the confirmation email. The operator sees the request appear in the operator dashboard with a downloadable GLB.

**Acceptance Scenarios**:

1. **Given** a phone photo with a cluttered but distinguishable subject, **When** the customer uploads it, **Then** background removal runs, the cleaned subject is shown for confirmation, and the customer can re-upload before the system spends GPU time on a bad image.
2. **Given** the preview is approved, **When** the customer submits the quote form (email required; name, message, preferred material, and scale optional), **Then** the system sends a confirmation email and creates a quote record visible in the operator dashboard.
3. **Given** background removal fails (e.g., the subject blends into the background), **When** the system detects low-confidence segmentation, **Then** the customer is shown a clear error and offered tips for a better photo, and the request is **not** queued for generation.

### User Story 3 — Tabletop gamer wants a printability verdict before committing (Priority: P2)

A tabletop gamer wants a unique miniature for their campaign. They will only print (or request a quote) if the system tells them the geometry is actually printable.

**Why this priority**: Tabletop gaming is a high-engagement segment that creates repeat interactions, but only if the platform does not waste their time on unprintable geometry. Their needs drive the print-readiness bar of the MVP.

**Independent Test**: Tester uploads a miniature reference image; system produces a model that either passes its own print-readiness check (manifold mesh, minimum-feature-size threshold met) or surfaces a clear "not printable" verdict before the customer can download or request a quote.

**Acceptance Scenarios**:

1. **Given** the AI returns a mesh, **When** the print-readiness check runs, **Then** the verdict is one of `printable`, `auto-repaired`, or `not printable`, and that verdict is displayed alongside the preview.
2. **Given** a `not printable` verdict, **When** the customer views the preview, **Then** the "Request a quote" action is disabled (with an explanation), and the "Download" action remains available.

### Edge Cases

- **Cluttered or low-resolution images**: surface a quality warning before consuming GPU time; allow re-upload at no cost.
- **Disallowed content** (people / faces, copyrighted characters, weapons, IP-protected designs): block at intake with a clear policy reason; do not submit to the model.
- **Generation failure** (model error, OOM on the GPU host): retry once with a more conservative octree resolution, then surface a friendly error.
- **Mesh fails print-readiness**: keep the preview, allow download, disable quote-request, offer one free regeneration.
- **Customer abandons mid-flow**: keep the generated mesh briefly so they can resume from the same browser session (see NFR-007).
- **Concurrent generations exceed GPU capacity**: queue the request, surface position-in-queue and estimated wait, do not silently time out.
- **Customer submits a quote with an obviously-wrong email**: validate format on the form; if confirmation email bounces, flag the quote in the operator dashboard.

## Requirements *(mandatory)*

### Functional Requirements

**Image Intake**

- **FR-001**: System MUST accept an image upload from the customer in PNG, JPEG, or WebP. Maximum file size and resolution thresholds are defined in NFR-002.
- **FR-002**: System MUST validate the input before any GPU work — checking format, size, content policy, and that a foreground subject is detectable.
- **FR-003**: System MUST reject content that violates the platform policy (people / faces, copyrighted characters, weapons, illegal goods) at intake, with a specific reason.

**3D Generation**

- **FR-010**: System MUST generate a 3D mesh from the validated image using the locally-hosted Hunyuan3D-2.1 shape pipeline as the canonical generator (see Dependencies).
- **FR-011**: System MUST run background removal on uploaded images before invoking the generator (matching the local script's `BackgroundRemover` behaviour) unless the image is already RGBA with a transparent background.
- **FR-012**: System MUST produce a shape-only mesh in GLB format. Texture / PBR generation is **out of scope** for the MVP — it requires more VRAM than the available 16 GB GPU budget (the local script explicitly excludes it).
- **FR-013**: System MUST stream progress updates to the browser during generation (queued → running → finalising) so the customer is not staring at a blank screen.
- **FR-014**: System MUST queue requests when the GPU host is busy and surface the queue position and estimated wait time. The MVP runs against a single 16 GB GPU host (the developer's RTX 4060 Ti); concurrency is bounded by VRAM.
- **FR-015**: System MUST allow regeneration with a different seed from the same input, without re-uploading the image, at most twice per session.

**Print Readiness**

- **FR-020**: System MUST run a print-readiness check on every generated mesh: manifold edges, no isolated components, minimum wall thickness above a documented default threshold.
- **FR-021**: System MUST attempt mesh auto-repair (close holes, remove disconnected components below a noise threshold) and report what was changed.
- **FR-022**: System MUST classify every mesh as `printable`, `auto-repaired`, or `not printable`, and display that verdict in the preview UI.

**3D Preview & Decision**

- **FR-030**: System MUST render the generated mesh in an interactive 3D viewer in the browser (orbit, pan, zoom; no edit operations).
- **FR-031**: System MUST display the mesh's bounding-box dimensions in millimetres at the model's native scale.
- **FR-032**: System MUST allow the customer to download the GLB at any time after the preview loads, regardless of the readiness verdict.
- **FR-033**: System MUST allow the customer to submit a quote request only if the readiness verdict is `printable` or `auto-repaired`.
- **FR-034**: System MUST allow the customer to discard the result and retry with a different seed (FR-015) at no cost beyond GPU time already spent.

**Quote Request & Operator Handoff**

- **FR-040**: System MUST capture, when a quote is requested: customer email (required), and optional name, message, preferred material, and preferred scale.
- **FR-041**: System MUST send a confirmation email to the customer immediately after a successful quote submission, containing a quote reference and a copy of their submitted information.
- **FR-042**: System MUST create a quote record visible to the operator in an operator dashboard, containing the customer-submitted form, the source image, the generated GLB, and the readiness verdict.
- **FR-043**: System MUST allow the operator to mark a quote as `responded`, `archived`, or `rejected` from the dashboard. No further customer-facing automation in v1 — the operator follows up by email off-platform.
- **FR-044**: System MUST flag any quote whose confirmation email bounces, and surface that flag in the operator dashboard.

**Operations & Observability**

- **FR-050**: System MUST log every generation request with: input hash, model parameters (seed, steps, octree resolution), GPU host, duration, peak VRAM, readiness verdict, and final outcome (success / repair / not-printable / error).
- **FR-051**: System MUST retain quote submissions, their attached source images, and their generated meshes per the schedule in NFR-007. Anonymous (download-only) generations expire faster than quote-attached ones.

### Non-Functional Requirements

- **NFR-001**: 3D generation latency (background removal + shape pipeline + readiness check + GLB export) SHOULD complete in under **3 minutes for the 50th percentile** on the reference 16 GB GPU host with `octree_resolution=256` and `steps=30`. The local reference script measures the underlying generation step at tens of seconds; the budget allows for queue, transfer, and post-processing.
- **NFR-002**: Maximum input image: 4096 × 4096 px, 20 MB. Files exceeding either dimension are downscaled before generation.
- **NFR-003**: The web app MUST run on the latest two stable versions of Chrome, Firefox, Safari, and Edge.
- **NFR-004**: The 3D viewer MUST render meshes up to 1 M triangles without dropping below 30 fps on a mid-range laptop GPU.
- **NFR-005**: Customer-facing error messages MUST never leak Python tracebacks, stack frames, model internals, or GPU diagnostics. Operator-facing logs MAY include them.
- **NFR-006**: Personally-identifiable quote data (name, email, free-text message) MUST be stored encrypted at rest. Imagineer holds **no** payment data in v1 — there is no payment.
- **NFR-007**: Anonymous (download-only) generations: input image and mesh retained for **24 hours** then deleted. Quote-attached generations: input image, mesh, and form data retained until the operator marks the quote `archived` or `rejected`, then **90 days**, then deleted. Generation logs (without PII) retained for **1 year** for capacity planning.
- **NFR-008**: The operator dashboard MUST be access-controlled. The exact mechanism (single-user password, IP allow-list, or simple OAuth) is selected in `/speckit.plan` — but it MUST NOT be reachable from a public URL without authentication.

### Key Entities

- **GenerationJob**: One run of the AI pipeline. Inputs: source image, parameters (seed, steps, octree resolution). Outputs: mesh GLB, peak VRAM, duration, readiness verdict, repair log. Owned by a session at first; promoted to a Quote if the customer submits the form.
- **Mesh**: The output of a successful GenerationJob. Holds the GLB blob, bounding box in mm, triangle count, readiness verdict.
- **Quote**: A customer's request for an off-platform follow-up. Holds the submitted form (email + optional fields), the attached GenerationJob and Mesh, the quote reference, and the operator-managed status (`new`, `responded`, `archived`, `rejected`).
- **Operator**: The single human who works the dashboard. Authenticated; not modelled as a customer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A customer with a usable reference image can complete the upload-to-preview flow in **under 10 minutes** for the 90th percentile of sessions, including model generation.
- **SC-002**: Of all reference-quality images uploaded (≥ 60% subject coverage, distinguishable foreground / background), **≥ 80%** produce a `printable` or `auto-repaired` verdict on the first generation, **≥ 95%** after at most one regeneration.
- **SC-003**: Of all approved meshes a customer attempts to download, **≥ 99%** download successfully without retry.
- **SC-004**: Of customers who load a preview, **≥ 30%** take a follow-on action (download or quote-request) within the same session — the floor for "the preview UX is doing its job".
- **SC-005**: The operator responds to **≥ 90% of quote requests within 1 business day**, measured across the first 50 quotes (validates that manual handoff is sustainable at MVP volume).
- **SC-006**: **< 5%** of `printable`-classified meshes are reported as actually unprintable during operator follow-up across the first 50 quotes (validates that the readiness check is calibrated correctly).

## Assumptions

These are defaults applied where the input was silent. Surface any disagreement before `/speckit.plan`.

- **A1**: The MVP serves customers in the Czech Republic and the EU. Czech-language UI is **not** required for the first release; English UI is acceptable.
- **A2**: The MVP runs the AI generator on a single developer-grade GPU host (RTX 4060 Ti, 16 GB VRAM). Concurrent generations are queued, not horizontally scaled.
- **A3**: Output meshes are shape-only (no colour / texture). Material and colour are discussed off-platform during the operator's quote response.
- **A4**: Each session generates one mesh at a time. Multi-item carts are post-MVP (and irrelevant in v1 since there is no cart).
- **A5**: The operator is a single person (the project owner) for the duration of the MVP. SC-005 assumes no operator team is needed at this scale.
- **A6**: Quote follow-up happens off-platform via email. Imagineer does not host the quote conversation, the price negotiation, or the shipping arrangement.

## Dependencies

- **Hunyuan3D-2.1 shape pipeline** (`tencent/Hunyuan3D-2.1` on Hugging Face), running locally per `/home/lukas/Projects/Temp/img23d/main.py`. This is the canonical 3D generator. Texture / PBR weights from the same model are explicitly **not** used.
- **`rembg` background-removal model**, used by the local script's `BackgroundRemover`.
- **A 16 GB-class CUDA GPU host** for shape generation. The reference is the developer's RTX 4060 Ti.
- **An email delivery provider** for the quote-confirmation email.

## Out of Scope (Initial Release)

- **Text-to-3D / text input** — image upload only in v1 (Q2 = A).
- **Payment processing of any kind** (Q1 = A).
- **Automated print-shop integration / fulfillment** (Q1 = A, Q3 = A). The operator handles every quote off-platform.
- **Order status state machine, shipping notifications, delivery tracking** — not modelled in v1.
- **Customer accounts, login, persistent order history** — guest-only flow; the only persistent customer record is a Quote.
- **Material / colour / scale pricing inside the app** — the operator quotes off-platform.
- **Texture / PBR / multi-colour generation** (capacity-bounded — needs ~21 GB VRAM, a custom rasterizer, and is excluded by the reference script).
- **Customer-uploaded mesh files** — the platform always generates the mesh.
- **Editor / sculpting tools in the browser** — preview is read-only.
- **Native mobile apps** — mobile-friendly web only.
- **Multi-shop routing, multi-shop quote comparison, multi-item carts** — single operator, single conversation.
- **Subscription / repeat-print credits, loyalty programmes, referral codes, gift cards.**
- **Public model gallery, sharing, social features.**
- **Localised Czech UI / multi-language UI** — English only at launch (per A1).
