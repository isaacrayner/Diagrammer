#!/usr/bin/env python3
"""
build_manifest.py - resolve the canonical slug vocabulary (skill/icon-index.md)
against Microsoft's official Azure icon set in icons/<category>/ and produce:

  icons/<slug>.svg   flat, unmodified copies the .d2 files reference directly
  icons/manifest.json  slug -> {file, source, aliases}

Icons are copied byte-for-byte; they are never recoloured, scaled non-uniformly,
or otherwise altered (see LICENCE-NOTES.md).

Usage:  python bin/build_manifest.py [--check]
        --check  report resolution only, write nothing
"""
import os, sys, json, shutil, re

ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS = os.path.join(ROOT, "icons")

# slug -> (list of aliases, official-filename match terms)
# match terms are matched against the official file stem, case/punctuation
# insensitive; the first term that resolves uniquely wins.
VOCAB = {
    # users / boundary
    "users":            (["Users", "People", "Public users"], ["service-Users", "Users"]),
    "onprem":           (["On-premises", "Corporate datacentre"], ["Server-Farm"]),
    "internet":         (["Internet"], ["Globe-Success"]),
    # frontend / edge
    "frontdoor":        (["Azure Front Door", "Front Door"], ["Front-Door-and-CDN-Profiles", "Front-Door"]),
    "waf":              (["Web Application Firewall", "WAF"], ["Web-Application-Firewall-Policies", "Application-Gateway-WAF"]),
    "appgw":            (["Application Gateway", "App Gateway", "AppGW"], ["Application-Gateways"]),
    "apim":             (["API Management", "APIM"], ["API-Management-Services"]),
    "cdn":              (["Azure CDN", "CDN"], ["CDN-Profiles", "Front-Door-and-CDN-Profiles"]),
    "trafficmanager":   (["Traffic Manager"], ["Traffic-Manager-Profiles"]),
    "dns":              (["Azure DNS", "DNS"], ["DNS-Zones"]),
    "privatedns":       (["Private DNS Zone"], ["DNS-Private-Resolver", "Private-Link"]),
    # application / compute
    "appservice":       (["App Service", "Web App"], ["App-Services"]),
    "appserviceplan":   (["App Service Plan"], ["App-Service-Plans"]),
    "function":         (["Function App", "Azure Functions"], ["Function-Apps"]),
    "containerapps":    (["Container Apps"], ["Container-Apps-Environments"]),
    "aks":              (["Azure Kubernetes Service", "AKS"], ["Kubernetes-Services"]),
    "aci":              (["Container Instances", "ACI"], ["Container-Instances"]),
    "acr":              (["Container Registry", "ACR"], ["Container-Registries"]),
    "vm":               (["Virtual Machine", "VM"], ["Virtual-Machine"]),
    "vmss":             (["VM Scale Set", "VMSS"], ["VM-Scale-Sets"]),
    "servicebus":       (["Service Bus"], ["Service-Bus"]),
    "eventgrid":        (["Event Grid"], ["Event-Grid-Topics", "Event-Grid-Domains"]),
    "eventhubs":        (["Event Hubs"], ["Event-Hubs"]),
    "logicapps":        (["Logic Apps"], ["Logic-Apps"]),
    "avd":              (["Azure Virtual Desktop", "AVD"], ["Azure-Virtual-Desktop", "Virtual-Desktop"]),
    # data
    "sqldb":            (["Azure SQL Database", "SQL DB"], ["SQL-Database"]),
    "sqlmi":            (["SQL Managed Instance", "SQL MI"], ["SQL-Managed-Instance"]),
    "sqlvm":            (["SQL Server on VM", "SQL IaaS"], ["Azure-SQL-VM"]),
    "sqlserver":        (["SQL Server"], ["SQL-Server"]),
    "cosmos":           (["Cosmos DB"], ["Azure-Cosmos-DB"]),
    "storage":          (["Storage Account", "Blob", "Storage"], ["Storage-Accounts"]),
    "files":            (["Azure Files", "File Share", "FSLogix profile share"], ["Storage-Azure-Files"]),
    "redis":            (["Azure Cache for Redis", "Redis"], ["Cache-Redis"]),
    "postgres":         (["Azure Database for PostgreSQL"], ["Azure-Database-PostgreSQL-Server"]),
    "mysql":            (["Azure Database for MySQL"], ["Azure-Database-MySQL-Server"]),
    "datalake":         (["Data Lake Storage"], ["Data-Lake-Storage-Gen1", "Data-Lake-Store"]),
    "synapse":          (["Synapse Analytics"], ["Azure-Synapse-Analytics"]),
    "datafactory":      (["Data Factory", "ADF"], ["Data-Factories"]),
    "dms":              (["Database Migration Service", "DMS"], ["Azure-Database-Migration-Services"]),
    # networking / security
    "vnet":             (["Virtual Network", "VNet"], ["Virtual-Networks"]),
    "subnet":           (["Subnet"], ["Subnet"]),
    "vnetgw":           (["VNet Gateway", "VPN Gateway"], ["Virtual-Network-Gateways"]),
    "expressroute":     (["ExpressRoute"], ["ExpressRoute-Circuits"]),
    "firewall":         (["Azure Firewall"], ["Firewalls"]),
    "bastion":          (["Azure Bastion"], ["Bastions"]),
    "lb":               (["Load Balancer"], ["Load-Balancers"]),
    "natgw":            (["NAT Gateway"], ["NAT"]),
    "privateendpoint":  (["Private Endpoint"], ["Private-Link-Service", "Private-Link"]),
    "nsg":              (["Network Security Group", "NSG"], ["Network-Security-Groups"]),
    "routetable":       (["Route Table", "UDR"], ["Route-Tables"]),
    "keyvault":         (["Key Vault"], ["Key-Vaults"]),
    "defender":         (["Microsoft Defender for Cloud"], ["Microsoft-Defender-for-Cloud", "Security-Center"]),
    "ddos":             (["DDoS Protection"], ["DDoS-Protection-Plans"]),
    "sentinel":         (["Microsoft Sentinel"], ["Azure-Sentinel", "Sentinel"]),
    # identity
    # The plain Entra ID tenant icon is not in the Azure architecture set; it
    # comes from Microsoft's separate Entra pack, vendored in icons/entra pack/.
    "entra":            (["Microsoft Entra ID", "Azure AD", "AAD", "Entra ID"], ["Microsoft Entra ID color icon"]),
    "entragovernance":  (["Entra ID Governance"], ["Microsoft Entra ID Governance color icon"]),
    "entraworkloadid":  (["Entra Workload ID"], ["Microsoft Entra Workload ID color icon"]),
    "entraconnect":     (["Entra Connect", "AAD Connect"], ["Entra-Connect-Sync", "Entra-Connect"]),
    "entradomain":      (["Entra Domain Services", "AAD DS"], ["Entra-Domain-Services"]),
    "managedidentity":  (["Managed Identity"], ["Managed-Identities"]),
    # management / operations
    "monitor":          (["Azure Monitor"], ["Monitor"]),
    "loganalytics":     (["Log Analytics"], ["Log-Analytics-Workspaces"]),
    "appinsights":      (["Application Insights"], ["Application-Insights"]),
    "automation":       (["Azure Automation"], ["Automation-Accounts"]),
    "backup":           (["Azure Backup"], ["Azure-Backup-Center"]),
    "recovery":         (["Recovery Services", "ASR", "Site Recovery"], ["Recovery-Services-Vaults", "Site-Recovery"]),
    "migrate":          (["Azure Migrate"], ["Azure-Migrate"]),
    "devops":           (["Azure DevOps", "Pipelines", "Repos", "Boards"], ["Azure-DevOps"]),
    "updatemanager":    (["Azure Update Manager"], ["Update-Management-Center"]),
    "policy":           (["Azure Policy"], ["Policy"]),
    "imagetemplate":    (["Azure Image Builder", "Compute Gallery image"], ["Image-Templates"]),
    "resourcegroup":    (["Resource Group"], ["Resource-Groups"]),
    "subscription":     (["Subscription"], ["Subscriptions"]),
}

def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())

def index_official():
    """stem -> full path, for every official SVG outside the flat slug files."""
    out = {}
    for dirpath, _dirs, files in os.walk(ICONS):
        if os.path.abspath(dirpath) == os.path.abspath(ICONS):
            continue  # flat slug copies live here; skip
        for f in files:
            if f.lower().endswith(".svg"):
                stem = re.sub(r"^\d+-icon-service-", "", os.path.splitext(f)[0])
                out.setdefault(norm(stem), os.path.join(dirpath, f))
    return out

def resolve(terms, index):
    for t in terms:
        key = norm(t)
        if key in index:
            return index[key]
    # fall back to a unique substring match
    for t in terms:
        key = norm(t)
        hits = [p for k, p in index.items() if key and key in k]
        if len(hits) == 1:
            return hits[0]
        if hits:
            return sorted(hits, key=lambda p: len(os.path.basename(p)))[0]
    return None

def main():
    check = "--check" in sys.argv
    index = index_official()
    manifest, missing = {}, []
    for slug, (aliases, terms) in sorted(VOCAB.items()):
        src = resolve(terms, index)
        if not src:
            missing.append(slug)
            continue
        rel = os.path.relpath(src, ROOT).replace("\\", "/")
        manifest[slug] = {
            "file": f"icons/{slug}.svg",
            "source": rel,
            "aliases": aliases,
        }
        if not check:
            shutil.copyfile(src, os.path.join(ICONS, f"{slug}.svg"))
    if not check:
        with open(os.path.join(ICONS, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump({"generated_by": "bin/build_manifest.py",
                       "note": "official Microsoft Azure icons, copied unmodified",
                       "icons": manifest}, fh, indent=2)
    print(f"resolved {len(manifest)}/{len(VOCAB)} slugs")
    if missing:
        print("UNRESOLVED (add the SVG or fix the match terms):")
        for m in missing:
            print("  -", m)
    return 1 if missing else 0

if __name__ == "__main__":
    sys.exit(main())
