# Azure style conformance — do our diagrams match Microsoft's guidance?

A review of the tool's **format and styling** (both the D2 render path and the new
draw.io path) against Microsoft's own diagramming recommendations. Verified against
the live sources on **2026-07-19**, not from memory:

- **Architecture design diagrams** — WAF, architect role:
  https://learn.microsoft.com/en-us/azure/well-architected/architect-role/design-diagrams
- **Azure architecture icons** (download + terms):
  https://learn.microsoft.com/en-us/azure/architecture/icons/

> **Verdict:** the styling **conforms** to every WAF diagramming practice and every
> icon term. Consistency is enforced *in code* (`styles/azure.d2` for the look,
> `bin/contract.py` for the rules), so it holds automatically on every diagram. The
> only items outstanding are **look enhancements** that would make our output
> resemble Microsoft's *reference-architecture* aesthetic even more closely — chiefly
> numbered dataflow steps. Those are additive, not corrections.

---

## 1. Conformance to the WAF diagramming practices

Each practice is quoted in substance from the live WAF page, then mapped to the
mechanism that enforces it — on **both** paths.

| WAF practice | D2 path | draw.io path | Status |
|---|---|---|---|
| **Use standard notations** | Only the classes in `styles/azure.d2`; `contract.py` R4 rejects unknown classes | Same classes, translated 1:1 into the draw.io style-map | ✅ |
| **Avoid ambiguous lines** | Fixed flow vocabulary (`ingress/sync/devops/egress/pe/peering/mgmt`), one meaning each | Same vocabulary, same stroke/dash per class | ✅ |
| **Use directional arrows** | `contract.py` R2 bans bare `--`; every edge is `->` | Every edge carries `endArrow=block` (or `open` for PE) | ✅ |
| **Avoid bidirectional arrows** | `<->` used only for genuinely two-way links (VNet peering), per the documented exception | `peering` is the only start+end arrow style | ✅ (deliberate, documented) |
| **Label everything clearly** | Every `svc`, container, and non-obvious edge is labelled; R6 flags unlabelled `svc` | Labels carried through; product name sits under each icon | ✅ |
| **Maintain consistency** (colours, casing, icon sizes, line weights, arrowheads, borders) | One source of truth: `styles/azure.d2`. Icon size fixed 74×74; line weights/dashes per class | The style-map mirrors those exact values; icons fixed 74×74; **Segoe UI** now applied (Azure's font) | ✅ |
| **Be accurate** (no PaaS-in-subnet if reached over a private endpoint) | `contract.py` R10 enforces PE-outside-subnet | Structure carried from the D2, so it inherits the rule | ✅ — **matches Microsoft's own baseline example** (see §3) |
| **Include metadata** (title, date, version, author) | Titleblock in every template; PASS on `radical-systems.d2` | Titleblock reproduced as a text shape (survives PNG) | ✅ |
| **Use official icons and service names** (latest, unmodified) | `contract.py` R5: must be `./icons/<slug>.svg` from the vendored set | Same official SVGs embedded, unscaled beyond a uniform square | ✅ |
| **Provide a legend** (as soon as line/border semantics appear) | `contract.py` R8: legend must carry an entry for **every** flow class used | Full legend reproduced with a colour+pattern key per class | ✅ |
| **Design for accessibility** (pair colour with pattern, never colour alone) | Every layer/flow has a distinct **pattern** as well as colour: RG dashed, group dotted, PE dashed, peering dash-dot, mgmt dashed | The style-map preserves each `dashPattern`, so colour is never the sole signal | ✅ |
| **Layer, don't overload** (progressive disclosure) | `contract.py` R13: every diagram declares `# diagram-type:` and is checked against that layer | Diagram type carried from the D2 | ✅ |
| **Version control** (sources beside the workload's assets) | `.d2` versioned in `designs/<customer>/` | `.drawio` versioned alongside it | ✅ |

**Why this is durable, not aspirational:** the LLM only writes *semantics* (D2);
the *look* is produced by code (`azure.d2` → style-map → converter). The model can't
drift the palette, icon size, or line style, because it never touches them. That is
a stronger consistency guarantee than a style guide humans follow by hand.

---

## 2. Icon terms compliance

From the icons download page (terms verified 2026-07-19):

| Term | How we comply |
|---|---|
| Include the product name near the icon | Every `svc` node has a label directly beneath its icon |
| Use icons as they appear in Azure | Rendered from the unmodified official SVGs |
| Don't crop, flip, rotate | Icons are placed as whole images; no transform |
| Don't distort or change shape | Fixed **square** 74×74 with `imageAspect=1;aspect=fixed` in draw.io — never stretched |
| Don't use MS icons for your own product | Icons map to the actual Azure service, via `skill/icon-index.md` |
| Permitted-use only (diagrams/docs) | Recorded in `LICENCE-NOTES.md`; set is the current **V24** (July 2026) |

---

## 3. We match Microsoft's own example

The icons page ships a **baseline App Service** reference architecture. Its structure:
a VNet with three subnets — App Gateway + WAF in one, **private endpoints for PaaS in
a dedicated subnet**, VNet-integration NICs in a third — with **App Service reaching
SQL Database, Key Vault, and Storage over private endpoints**, those PaaS services
drawn **outside the subnet**.

That is exactly the convention `contract.py` R10 enforces and the `radical-systems`
sample follows (a dedicated `snet_pe` Private Endpoint subnet; Key Vault, Storage,
Cosmos, ACR, Files drawn in a PaaS group outside the VNet, reached by `pe` links).
So the tool doesn't just follow the written rules — it reproduces the visual pattern
Microsoft uses in its own published diagram.

---

## 4. Enhancements to match the reference-architecture *look* (optional, additive)

These aren't conformance gaps — the guidance doesn't require them — but they are the
signatures that make a diagram read as "an Azure reference architecture." Worth
considering:

1. **Numbered dataflow steps (highest value).** Azure reference architectures almost
   always number the flow (①→⑨) and pair it with a "Dataflow" step list. We label
   edges but don't number them. Adding a `step: N` annotation to edges + an auto-built
   numbered list would most strongly evoke the Azure house look. This touches the D2
   schema and the converter, so it's a small feature, not a style tweak — flagged for
   a decision.
2. **Boundary-type icons in container headers — done.** Each subscription,
   resource group, VNet, and subnet now carries its official Azure icon in the
   header (as Azure reference architectures do), locked as chrome so it can't be
   dragged out of place. A logical `group` deliberately has none — it isn't an
   Azure hierarchy level.
3. **Segoe UI font — done.** Applied to the draw.io style-map in this change so text
   matches Microsoft's diagrams (draw.io falls back gracefully off-Windows).

---

## 5. What changed in this review

- **`bin/build_manifest.py`**: added a `subnet` slug (official `Subnet` icon) so
  every hierarchy level has a boundary icon available (73/73 slugs resolve).
- **`bin/phase0_radical_to_drawio.py`**: applied `fontFamily=Segoe UI` across the
  draw.io styles, and added **boundary icons** — the official subscription /
  resource-group / VNet / subnet icon in each container header, indented clear of
  the title and locked as chrome. Regenerated `radical-systems.drawio`.
- Added this conformance record. No rule or palette value was changed — the existing
  styling already conforms; this documents/verifies it against the live sources and
  adds the typography + boundary icons to match Azure's reference-architecture look.

*Companion docs: `docs/azure-diagram-guidelines.md` (the sourced rules the contract
enforces) and `docs/reference-review.md` (the hand-made house diagrams audited against
those rules).*
