# PROMPT.md — Generate an Azure architecture diagram (D2)

You turn the ADS discovery notes into a **single D2 file** that renders as a
professional Azure architecture diagram. You write only the D2 text. You never
position anything by pixel and you never run layout by hand — the renderer and
optimizer do that.

## Before you write anything, read
1. `style-contract.md` — the rules you must obey (layers, colours, line meaning).
2. `icon-index.md` — the only icons you may use (canonical name → file).
3. `../styles/azure.d2` — the class definitions you will reference.

## Inputs
- The ADS notes / `[Customer]-PLAN.md` (services, tiers, connectivity, phases).
- If a phased design: produce one file per phase (see "Phases" below).

## Output
- One file: `designs/<customer>/<customer>.d2` (or `.../phases/phase-<n>.d2`).
- **Line 2 must declare the diagram type**: `# diagram-type: component` (or
  `context`, `container`, `network`, `resilience`, `identity`). Pick one layer
  and stay in it — a context diagram must not grow subnets. `component` is the
  usual ADS target-state deliverable. If the notes clearly need two layers,
  produce two files.
- **First line must be the style import**, which inherits every class:
  - from `designs/<customer>/` → `...@../../styles/azure.d2`
  - from `designs/<customer>/phases/` → `...@../../../styles/azure.d2`
  - (The render scripts handle the rest of D2's path quirks; just write
    `icon: ./icons/<slug>.svg` and the depth-relative import above.)
- Then, in order: the metadata title block, the legend, the topology.
- **Never use a `|md|` block.** D2 renders markdown as an HTML foreignObject that
  the rasterizer drops, so it vanishes from the PNG. Titles are quoted text
  labels with `\n`, using `class: titleblock`.
- **Never set colours, fills, strokes, or sizes inline.** Use only the classes
  from the style file: `sub`, `rg`, `vnet`, `subnet` (containment), `svc` (leaf),
  `ingress`, `sync`, `devops`, `egress`, `pe`, `peering`, `replication`, `mgmt`
  (flows), `future` (deferred/standby), `legend`, `titleblock` (chrome).
  If you find yourself writing a `style:` block on a node, stop — use a class.

## Process — do these in order

1. **Inventory.** List every Azure service and, for each: its tier
   (frontend / app / data / networking / security), and its *home* —
   which subscription, resource group, VNet, and subnet it belongs to.
2. **Apply the accuracy rule.** A PaaS service reached over a **private
   endpoint** (Storage, Key Vault, SQL DB, Service Bus, etc.) does **not** go
   inside a subnet. Place it outside the VNet and connect it with a `pe`
   connection. Only things actually *in* a subnet (VMs, App Gateway, a
   delegated-subnet service like SQL Managed Instance, private endpoints
   themselves) go inside `subnet` containers.
3. **Flows.** For each connection record source → target, a short label
   (protocol or purpose), and which flow class it is:

   | Class | Use it for |
   |---|---|
   | `ingress` | user / app inflow from outside |
   | `sync` | internal service-to-service call |
   | `devops` | DevOps and CI/CD |
   | `egress` | anything crossing the internet boundary |
   | `pe` | private endpoint |
   | `peering` | VNet peering |
   | `replication` | geo-replication, ASR |
   | `mgmt` | monitoring, backup, diagnostics |

   Arrows point from caller to dependency. Use `<->` only where the relationship
   really is two-way (VNet peering, read/write to profile storage).
   Then **prune the legend to exactly the classes you used** — an unused entry is
   clutter, a missing one is a contract error.
4. **Icons.** Map each service to a `./icons/<slug>.svg` from `icon-index.md`.
   If a service is not listed, pick the closest and add a `# TODO: icon` comment.
5. **Write the D2** using the structure below. Start from
   `templates/target-state.d2` or `templates/phase.d2` — they already carry the
   metadata block and legend the guidelines require.
6. **Check the contract.** Run
   `python bin/contract.py designs/<customer>/<file>.d2` from the repository
   root. Every ERROR must be fixed; the report names the rule and the Microsoft
   guideline behind it. This is not optional and it runs before rendering,
   because a diagram that breaks the contract is wrong even if it looks tidy.
7. **Render + check geometry.** Run
   `python bin/optimize.py designs/<customer>/<file>.d2`. If the
   lint score is below ~85 or it reports overlaps/crossings, revise (shorten
   labels, split an overcrowded subnet, drop non-essential edges) and re-run.
   Do not hand-tune positions.

## Structure to follow

```d2
...@../../styles/azure.d2          # depth-appropriate path to styles/azure.d2
# diagram-type: component

title: "<Customer> — Azure <Target-State | Phase N> Architecture\nRev <n> · <date> · <author>" {
  near: top-center
  class: titleblock
}

legend: Legend {                   # exactly the classes used below, no more
  near: bottom-left
  class: legend
  direction: right
  i1.class: legendkey;  i2.class: legendkey
  s1.class: legendkey;  s2.class: legendkey
  p1.class: legendkey;  p2.class: legendkey
  i1 -> i2: user / app inflow  { class: ingress }
  s1 -> s2: internal call      { class: sync }
  p1 -> p2: private endpoint   { class: pe }
}

# containment: subscription → resource group → VNet → subnet → service
sub_work: "SUBSCRIPTION · <name>" { class: sub
  rg_app: "RG · rg-app" { class: rg
    vnet: "vnet 10.1.0.0/16" { class: vnet
      snet_app: "snet-app 10.1.1.0/24" { class: subnet
        app: App Service { class: svc; icon: ./icons/appservice.svg }
      }
    }
  }
}

# PaaS-over-private-endpoint sits OUTSIDE the subnet
kv: Key Vault { class: svc; icon: ./icons/keyvault.svg }

sub_work.rg_app.vnet.snet_app.app -> kv: secrets { class: pe }
```

## Worked example (notes → D2)

Notes: *"Public users hit Front Door → App Gateway in the hub. App Service in
spoke-vnet calls Azure SQL DB and Key Vault over private endpoints."*

```d2
...@../../styles/azure.d2
# diagram-type: component
title: "Acme — Azure Target-State Architecture\nRev 1 · 2026-07-18 · I. Consultant" {
  near: top-center
  class: titleblock
}

legend: Legend {
  near: bottom-left
  class: legend
  direction: right
  i1.class: legendkey;  i2.class: legendkey
  p1.class: legendkey;  p2.class: legendkey
  i1 -> i2: user / app inflow { class: ingress }
  p1 -> p2: private endpoint  { class: pe }
}

users: Users { class: svc; icon: ./icons/users.svg }
fd: Front Door { class: svc; icon: ./icons/frontdoor.svg }

sub: "SUBSCRIPTION · Workload-Prod" { class: sub
  rg: "RG · rg-app" { class: rg
    vnet: "spoke-vnet 10.1.0.0/16" { class: vnet
      snet_fe: "snet-agw 10.1.0.0/24" { class: subnet
        agw: App Gateway { class: svc; icon: ./icons/appgw.svg }
      }
      snet_app: "snet-app 10.1.1.0/24" { class: subnet
        app: App Service { class: svc; icon: ./icons/appservice.svg }
      }
    }
  }
}
sql: Azure SQL DB { class: svc; icon: ./icons/sqldb.svg }
kv:  Key Vault    { class: svc; icon: ./icons/keyvault.svg }

users -> fd: HTTPS 443 { class: ingress }
fd -> sub.rg.vnet.snet_fe.agw: HTTPS { class: ingress }
sub.rg.vnet.snet_fe.agw -> sub.rg.vnet.snet_app.app: HTTPS { class: ingress }
sub.rg.vnet.snet_app.app -> sql: "TDS · private endpoint" { class: pe }
sub.rg.vnet.snet_app.app -> kv:  "secrets · private endpoint" { class: pe }
```

## Phases
For a phased migration, produce `phases/phase-1.d2 … phase-N.d2`. Keep **node
IDs identical across phases** for services that persist, so a service sits in the
same place every phase and the migration reads as one story. When a service is
replaced (e.g. `sqlvm` → `sqlmi`), keep the surrounding IDs stable and only swap
the leaf.

## Do not
- set inline styles (use classes)
- put PaaS-over-private-endpoint services inside subnets
- use a flow class without a matching legend entry, or leave unused legend entries
- use `<->` for anything that isn't genuinely two-way
- mix diagram types in one file — one `# diagram-type:` per file
- invent icon filenames — only use slugs from `icon-index.md`
- use an icon that doesn't represent the labelled thing (domain controllers are
  `entradomain`, not `entra`)
