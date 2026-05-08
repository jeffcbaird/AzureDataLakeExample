# ── Analysis Services server ──────────────────────────────────────────────────
# Gated behind deploy_expensive_resources in root main.tf.
# SKU is driven by the environment: D1 (dev/test) or S0+ (prod).
# The server is paused nightly by the ADF aas_pause_resume pipeline to
# minimise cost; it self-resumes on first query or via the ADF resume trigger.

locals {
  server_name = "aas-${var.project_name}-${var.environment}"

  # Power BI service public IP ranges (global + westus/westus2 regional).
  # Source: https://docs.microsoft.com/en-us/power-bi/admin/power-bi-allow-list-urls
  # Keep in sync if Microsoft updates these.
  power_bi_ips = var.enable_power_bi_service_ips ? [
    { name = "pbi-global-1",   start = "13.64.176.0",   end = "13.64.191.255"  },
    { name = "pbi-global-2",   start = "40.74.128.0",   end = "40.74.143.255"  },
    { name = "pbi-westus-1",   start = "13.86.0.0",     end = "13.86.15.255"   },
    { name = "pbi-westus2-1",  start = "20.42.128.0",   end = "20.42.135.255"  },
    { name = "pbi-westus2-2",  start = "20.42.0.0",     end = "20.42.7.255"    },
  ] : []
}

resource "azurerm_analysis_services_server" "main" {
  name                = local.server_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = var.sku

  # Admin users receive full server-level admin rights.
  admin_users = var.admin_users

  # Allow Power BI service and optional developer IPs.
  # Each IP entry creates a named firewall rule.
  dynamic "ipv4_firewall_rule" {
    for_each = local.power_bi_ips
    content {
      name        = ipv4_firewall_rule.value.name
      range_start = ipv4_firewall_rule.value.start
      range_end   = ipv4_firewall_rule.value.end
    }
  }

  dynamic "ipv4_firewall_rule" {
    for_each = { for idx, cidr in var.allowed_ip_ranges : "custom-${idx}" => cidr }
    content {
      name        = ipv4_firewall_rule.key
      range_start = cidrhost(ipv4_firewall_rule.value, 0)
      range_end   = cidrhost(ipv4_firewall_rule.value, -1)
    }
  }

  tags = var.tags
}
