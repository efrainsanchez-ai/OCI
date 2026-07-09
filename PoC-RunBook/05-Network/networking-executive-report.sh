#!/usr/bin/env bash

WORKBOOK_DIR="${WORKBOOK_DIR:-$HOME/workbook}"
REPORT_FILE="$WORKBOOK_DIR/networking-executive-report.txt"

cd "$WORKBOOK_DIR" || exit 1
. ./helpers.sh
load_cli_env

line() {
  printf '%*s\n' 96 '' | tr ' ' '-'
}

section() {
  printf '\n%s\n' "$1"
  line
}

kv_header() {
  printf '%-30s | %s\n' "ITEM" "VALUE"
  printf '%-30s | %s\n' "------------------------------" "-----"
}

kv() {
  printf '%-30s | %s\n' "$1" "${2:-NOT_AVAILABLE}"
}

shorten() {
  VALUE="$1"
  MAX="$2"
  if [ "${#VALUE}" -gt "$MAX" ]; then
    printf '%s...' "${VALUE:0:$((MAX - 3))}"
  else
    printf '%s' "$VALUE"
  fi
}

run_table() {
  TITLE="$1"
  shift
  section "$TITLE"
  if ! "$@"; then
    kv_header
    kv "Status" "Not available or review required"
  fi
}

run_optional_table() {
  TITLE="$1"
  REQUIRED_KEY="$2"
  shift 2
  if [ -n "${!REQUIRED_KEY:-}" ]; then
    run_table "$TITLE" "$@"
  else
    section "$TITLE"
    kv_header
    kv "Status" "Not available"
  fi
}

access_header() {
  printf '%-22s | %-43s | %s\n' "NSG" "INGRESS ACCESS" "EGRESS ACCESS"
  printf '%-22s | %-43s | %s\n' "----------------------" "-------------------------------------------" "-------------------------------------------"
}

access_row() {
  NSG="$(shorten "$1" 22)"
  INGRESS="$(shorten "$2" 43)"
  EGRESS="$(shorten "$3" 43)"
  printf '%-22s | %-43s | %-43s\n' "$NSG" "$INGRESS" "$EGRESS"
}

rule_header() {
  printf '%-20s | %-7s | %-5s | %-10s | %-24s | %s\n' \
    "NSG" "DIR" "PROTO" "PORTS" "NSG / SERVICE / CIDR" "DESCRIPTION"
  printf '%-20s | %-7s | %-5s | %-10s | %-24s | %s\n' \
    "--------------------" "-------" "-----" "----------" "------------------------" "------------------------------"
}

rule_row() {
  NSG="$(shorten "$1" 20)"
  DIRECTION="$(shorten "$2" 7)"
  PROTOCOL="$(shorten "$3" 5)"
  PORTS="$(shorten "$4" 10)"
  PEER="$(shorten "$5" 24)"
  DESCRIPTION="$(shorten "$6" 30)"
  printf '%-20s | %-7s | %-5s | %-10s | %-24s | %-30s\n' \
    "$NSG" "$DIRECTION" "$PROTOCOL" "$PORTS" "$PEER" "$DESCRIPTION"
}

security_list_header() {
  printf '%-20s | %-7s | %-5s | %-10s | %-24s | %s\n' \
    "SECURITY LIST" "DIR" "PROTO" "PORTS" "CIDR / SERVICE" "DESCRIPTION"
  printf '%-20s | %-7s | %-5s | %-10s | %-24s | %s\n' \
    "--------------------" "-------" "-----" "----------" "------------------------" "------------------------------"
}

security_list_row() {
  LIST_NAME="$(shorten "$1" 20)"
  DIRECTION="$(shorten "$2" 7)"
  PROTOCOL="$(shorten "$3" 5)"
  PORTS="$(shorten "$4" 10)"
  PEER="$(shorten "$5" 24)"
  DESCRIPTION="$(shorten "$6" 30)"
  printf '%-20s | %-7s | %-5s | %-10s | %-24s | %-30s\n' \
    "$LIST_NAME" "$DIRECTION" "$PROTOCOL" "$PORTS" "$PEER" "$DESCRIPTION"
}

security_list_rules() {
  TITLE="$1"
  SECURITY_LIST_ID="$2"
  LIST_NAME="$3"
  section "$TITLE"

  if [ -z "$SECURITY_LIST_ID" ]; then
    kv_header
    kv "Status" "Not available"
    return
  fi

  if ! command -v jq >/dev/null 2>&1; then
    kv_header
    kv "Status" "jq not available; showing compact OCI output"
    oci network security-list get \
      --security-list-id "$SECURITY_LIST_ID" \
      --query 'data.{Ingress:"ingress-security-rules",Egress:"egress-security-rules"}' \
      --output table
    return
  fi

  RULES_JSON="$(
    oci network security-list get \
      --security-list-id "$SECURITY_LIST_ID" \
      --output json
  )"

  security_list_header
  printf '%s\n' "$RULES_JSON" | jq -r \
    --arg name "$LIST_NAME" '
      def protocol_name:
        if .protocol == "6" then "TCP"
        elif .protocol == "1" then "ICMP"
        else (.protocol // "-")
        end;
      def port_from:
        if ."tcp-options"?."destination-port-range"? then
          ((."tcp-options"."destination-port-range".min // "All") | tostring)
        elif ."icmp-options"? then
          ((."icmp-options".type // "All") | tostring)
        else
          "All"
        end;
      def port_to:
        if ."tcp-options"?."destination-port-range"? then
          ((."tcp-options"."destination-port-range".max // "All") | tostring)
        elif ."icmp-options"? then
          ((."icmp-options".code // "All") | tostring)
        else
          "All"
        end;
      (
        (.data."ingress-security-rules" // [])[] |
        [$name, "INGRESS", protocol_name, port_from, port_to, ((.source // "-") | tostring), (.description // "-")]
      ),
      (
        (.data."egress-security-rules" // [])[] |
        [$name, "EGRESS", protocol_name, port_from, port_to, ((.destination // "-") | tostring), (.description // "-")]
      ) | @tsv
    ' | while IFS="$(printf '\t')" read -r LIST_NAME DIRECTION PROTOCOL PORT_FROM PORT_TO PEER DESCRIPTION; do
      if [ "$PORT_TO" = "All" ] && [ "$PROTOCOL" = "ICMP" ]; then
        PORTS="$PORT_FROM"
      elif [ "$PORT_FROM" = "$PORT_TO" ]; then
        PORTS="$PORT_FROM"
      else
        PORTS="$PORT_FROM-$PORT_TO"
      fi
      security_list_row "$LIST_NAME" "$DIRECTION" "$PROTOCOL" "$PORTS" "$PEER" "$DESCRIPTION"
    done
}

nsg_rules() {
  TITLE="$1"
  REQUIRED_KEY="$2"
  CURRENT_NSG="$3"
  section "$TITLE"

  if [ -z "${!REQUIRED_KEY:-}" ]; then
    kv_header
    kv "Status" "Not available"
    return
  fi

  if ! command -v jq >/dev/null 2>&1; then
    kv_header
    kv "Status" "jq not available; showing compact OCI output"
    oci network nsg rules list \
      --nsg-id "${!REQUIRED_KEY}" \
      --query 'data[].{Direction:direction,Protocol:protocol,PortFrom:"tcp-options"."destination-port-range".min,PortTo:"tcp-options"."destination-port-range".max}' \
      --output table
    return
  fi

  RULES_JSON="$(
    oci network nsg rules list \
      --nsg-id "${!REQUIRED_KEY}" \
      --output json
  )"

  rule_header
  printf '%s\n' "$RULES_JSON" | jq -r \
    --arg current "$CURRENT_NSG" \
    --arg client "${NSG_EXADATA_CLIENT_OCID:-}" \
    --arg apps "${NSG_APPLICATIONS_OCID:-}" \
    --arg dbtools "${NSG_DBTOOLS_OCID:-}" \
    --arg bastion "${NSG_BASTION_OCID:-}" \
    --arg lb "${NSG_PUBLIC_LB_OCID:-}" '
      def nsg_name($id):
        if $id == $client then "nsg-exadata-client"
        elif $id == $apps then "nsg-applications"
        elif $id == $dbtools then "nsg-dbtools-endpoint"
        elif $id == $bastion then "nsg-bastion-admin"
        elif $id == $lb then "nsg-public-lb"
        else "-"
        end;
      def protocol_name:
        if .protocol == "6" then "TCP"
        elif .protocol == "1" then "ICMP"
        else (.protocol // "-")
        end;
      def service_name($value):
        if ($value // "") | contains("sjc") then "All SJC Services"
        else ($value // "-")
        end;
      .data[] |
      [
        $current,
        (.direction // "-"),
        protocol_name,
        ((."tcp-options"?."destination-port-range"?.min // "All") | tostring),
        ((."tcp-options"?."destination-port-range"?.max // "All") | tostring),
        (
          if .direction == "INGRESS" then
            if ."source-type" == "NETWORK_SECURITY_GROUP" then nsg_name(.source)
            elif ."source-type" == "SERVICE_CIDR_BLOCK" then service_name(.source)
            elif ."source-type" == "CIDR_BLOCK" then .source
            else "-"
            end
          else
            if ."destination-type" == "NETWORK_SECURITY_GROUP" then nsg_name(.destination)
            elif ."destination-type" == "SERVICE_CIDR_BLOCK" then service_name(.destination)
            elif ."destination-type" == "CIDR_BLOCK" then .destination
            else "-"
            end
          end
        ),
        (.description // "-")
      ] | @tsv
    ' | while IFS="$(printf '\t')" read -r NSG DIRECTION PROTOCOL PORT_FROM PORT_TO PEER DESCRIPTION; do
      if [ -z "$PORT_FROM" ] && [ -z "$PORT_TO" ]; then
        PORTS="All"
      elif [ "$PORT_FROM" = "All" ] && [ "$PORT_TO" = "All" ]; then
        PORTS="All"
      elif [ "$PORT_FROM" = "$PORT_TO" ]; then
        PORTS="$PORT_FROM"
      else
        PORTS="$PORT_FROM-$PORT_TO"
      fi
      rule_row "$NSG" "$DIRECTION" "$PROTOCOL" "$PORTS" "$PEER" "$DESCRIPTION"
    done
}

gateway_header() {
  printf '%-18s | %-28s | %s\n' "TYPE" "NAME" "STATE"
  printf '%-18s | %-28s | %s\n' "------------------" "----------------------------" "---------------"
}

gateway_row() {
  TYPE="$(shorten "$1" 18)"
  NAME="$(shorten "${2:-Not available}" 28)"
  STATE="$(shorten "${3:-Not available}" 15)"
  printf '%-18s | %-28s | %s\n' "$TYPE" "$NAME" "$STATE"
}

gateway_from_list() {
  TYPE="$1"
  shift
  RESULT="$("$@" --output json 2>/dev/null)"
  if [ -n "$RESULT" ] && command -v jq >/dev/null 2>&1; then
    COUNT="$(printf '%s\n' "$RESULT" | jq '.data | length')"
    if [ "$COUNT" -gt 0 ]; then
      printf '%s\n' "$RESULT" | jq -r \
        --arg type "$TYPE" \
        '.data[] | [$type, (."display-name" // .name // "Not available"), (."lifecycle-state" // "Not available")] | @tsv' |
        while IFS="$(printf '\t')" read -r ROW_TYPE ROW_NAME ROW_STATE; do
          gateway_row "$ROW_TYPE" "$ROW_NAME" "$ROW_STATE"
        done
      return
    fi
  fi
  gateway_row "$TYPE" "Not available" "Not available"
}

gateway_from_get() {
  TYPE="$1"
  REQUIRED_KEY="$2"
  shift 2
  if [ -z "${!REQUIRED_KEY:-}" ]; then
    gateway_row "$TYPE" "Not available" "Not available"
    return
  fi
  RESULT="$("$@" --output json 2>/dev/null)"
  if [ -n "$RESULT" ] && command -v jq >/dev/null 2>&1; then
    printf '%s\n' "$RESULT" | jq -r \
      --arg type "$TYPE" \
      '.data | [$type, (."display-name" // .name // "Not available"), (."lifecycle-state" // "Not available")] | @tsv' |
      while IFS="$(printf '\t')" read -r ROW_TYPE ROW_NAME ROW_STATE; do
        gateway_row "$ROW_TYPE" "$ROW_NAME" "$ROW_STATE"
      done
    return
  fi
  gateway_row "$TYPE" "Not available" "Not available"
}

gateway_summary() {
  section "Gateways"
  gateway_header
  gateway_from_list "gw-internet" \
    oci network internet-gateway list \
      --compartment-id "$NETWORK_COMPARTMENT_OCID" \
      --vcn-id "$VCN_OCID"
  gateway_from_get "gw-service" SGW_OCID \
    oci network service-gateway get \
      --service-gateway-id "$SGW_OCID"
  gateway_from_list "gw-nat" \
    oci network nat-gateway list \
      --compartment-id "$NETWORK_COMPARTMENT_OCID" \
      --vcn-id "$VCN_OCID"
  gateway_from_get "DRG" DRG_OCID \
    oci network drg get \
      --drg-id "$DRG_OCID"
}

subnet_header() {
  printf '%-21s | %-13s | %-7s | %-7s | %-22s | %s\n' \
    "NAME" "CIDR" "DNS" "PRIVATE" "SECURITY LISTS" "STATE"
  printf '%-21s | %-13s | %-7s | %-7s | %-22s | %s\n' \
    "---------------------" "-------------" "-------" "-------" "----------------------" "---------------"
}

subnet_row() {
  NAME="$(shorten "$1" 21)"
  CIDR="$(shorten "$2" 13)"
  DNS="$(shorten "$3" 7)"
  PRIVATE="$(shorten "$4" 7)"
  SECURITY_LISTS="$(shorten "$5" 22)"
  STATE="$(shorten "$6" 15)"
  printf '%-21s | %-13s | %-7s | %-7s | %-22s | %s\n' \
    "$NAME" "$CIDR" "$DNS" "$PRIVATE" "$SECURITY_LISTS" "$STATE"
}

show_subnet_inventory() {
  section "Subnets"

  if ! command -v jq >/dev/null 2>&1; then
    run_table "Subnets" \
      oci network subnet list \
        --compartment-id "$NETWORK_COMPARTMENT_OCID" \
        --vcn-id "$VCN_OCID" \
        --query 'data[].{Name:"display-name",Cidr:"cidr-block",Dns:"dns-label",Private:"prohibit-public-ip-on-vnic",State:"lifecycle-state"}' \
        --output table
    return
  fi

  SUBNETS_JSON="$(
    oci network subnet list \
      --compartment-id "$NETWORK_COMPARTMENT_OCID" \
      --vcn-id "$VCN_OCID" \
      --output json
  )"

  subnet_header
  printf '%s\n' "$SUBNETS_JSON" | jq -r \
    --arg default_sl "${DEFAULT_SECURITY_LIST_OCID:-}" \
    --arg backup_sl "${SECURITY_LIST_BACKUP_OCID:-}" '
      def sl_name($id):
        if $id == $default_sl then "default"
        elif $id == $backup_sl then "sl-backup"
        else ($id[0:12] + "...")
        end;
      .data[] |
      [
        (."display-name" // "-"),
        (."cidr-block" // "-"),
        (."dns-label" // "-"),
        (if has("prohibit-public-ip-on-vnic") then (."prohibit-public-ip-on-vnic" | tostring) else "-" end),
        ((."security-list-ids" // []) | map(sl_name(.)) | join(",")),
        (."lifecycle-state" // "-")
      ] | @tsv
    ' | while IFS="$(printf '\t')" read -r NAME CIDR DNS PRIVATE SECURITY_LISTS STATE; do
      subnet_row "$NAME" "$CIDR" "$DNS" "$PRIVATE" "$SECURITY_LISTS" "$STATE"
    done
}

show_nsg_access_model() {
  section "NSG Access Model"
  access_header
  access_row "nsg-exadata-client" "Client TCP/ICMP; app/admin/dbtools SQL/ONS; SSH" "Backup 8005/2484; VCN TCP"
  access_row "nsg-applications" "Public LB 80/8080/443; admin SSH" "Exadata client TCP 1521 and 6200"
  access_row "nsg-dbtools-endpoint" "None" "Exadata client TCP 1521 and 6200"
  access_row "nsg-bastion-admin" "Internet SSH" "SSH to client/app; SQL/ONS to client; internet"
  access_row "nsg-public-lb" "Internet 80/443/8080" "Internet TCP 80, 443, and 8080"
}

show_security_list_rule_details() {
  section "Current Security List Rule Details"
  kv_header
  kv "Display focus" "Direction, protocol, port range, CIDR or service, and rule description"

  security_list_rules "Default security list ingress and egress" "${DEFAULT_SECURITY_LIST_OCID:-}" "default"
  security_list_rules "sl-backup ingress and egress" "${SECURITY_LIST_BACKUP_OCID:-}" "sl-backup"
}

show_nsg_inventory() {
  run_table "NSGs" \
    oci network nsg list \
      --compartment-id "$NETWORK_COMPARTMENT_OCID" \
      --vcn-id "$VCN_OCID" \
      --query 'data[].{Name:"display-name",State:"lifecycle-state"}' \
      --output table
}

show_nsg_rule_details() {
  section "Current NSG Rule Details"
  kv_header
  kv "Display focus" "Direction, protocol, port range, and rule description"

  nsg_rules "nsg-exadata-client ingress and egress" NSG_EXADATA_CLIENT_OCID "nsg-exadata-client"
  nsg_rules "nsg-applications ingress and egress" NSG_APPLICATIONS_OCID "nsg-applications"
  nsg_rules "nsg-dbtools-endpoint ingress and egress" NSG_DBTOOLS_OCID "nsg-dbtools-endpoint"
  nsg_rules "nsg-bastion-admin ingress and egress" NSG_BASTION_OCID "nsg-bastion-admin"
  nsg_rules "nsg-public-lb ingress and egress" NSG_PUBLIC_LB_OCID "nsg-public-lb"
}

show_nsg_sections() {
  show_nsg_access_model
  show_nsg_inventory
  show_nsg_rule_details
}

show_full_report() {
  COMPARTMENT_PATH="${POC_PARENT_COMPARTMENT_NAME:-Partner}/${POC_COMPARTMENT_NAME:-LAD-01}"

  section "OCI PoC RunBook Executive Report"
  kv_header
  kv "Generated UTC" "$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
  kv "Region" "${REGION:-NOT_AVAILABLE}"
  kv "Workbook directory" "$WORKBOOK_DIR"
  kv "Report file" "$REPORT_FILE"
  kv "Format" "Names, states, and access details"
  kv "PoC compartment" "(root)/$COMPARTMENT_PATH"
  kv "Network artifacts compartment" "(root)/$COMPARTMENT_PATH"
  kv "Admin artifacts compartment" "(root)/$COMPARTMENT_PATH"
  kv "VCN name" "${VCN_NAME:-VCN-${POC_COMPARTMENT_NAME:-LAD-01}}"
  kv "VCN CIDR" "${VCN_CIDR:-10.0.0.0/16}"
  kv "DNS domain" "poc.oraclevcn.com"

  section "Current Artifacts"
  kv_header
  kv "PoC compartment" "(root)/$COMPARTMENT_PATH"
  kv "Network artifacts compartment" "(root)/$COMPARTMENT_PATH"
  kv "Admin artifacts compartment" "(root)/$COMPARTMENT_PATH"
  kv "VCN" "${VCN_NAME:-VCN-${POC_COMPARTMENT_NAME:-LAD-01}}"
  kv "Gateways" "gw-internet, gw-service, gw-nat, optional dynamic-routing-gateway"
  kv "Route tables" "rt-public, rt-private"
  kv "Subnets" "subnet-admin, subnet-dbclient, subnet-db-backup, subnet-dbtools, subnet-public-lb, subnet-applications"
  kv "Security lists" "default security list, sl-backup"
  kv "NSGs" "nsg-exadata-client, nsg-applications, nsg-dbtools-endpoint, nsg-bastion-admin, nsg-public-lb"
  kv "Service access" "Route tables provide NAT, Service Gateway, and Internet Gateway paths; security-list baseline uses the default list plus sl-backup"

  show_nsg_access_model

  run_optional_table "VCN" VCN_OCID \
    oci network vcn get \
      --vcn-id "$VCN_OCID" \
      --query 'data.{Name:"display-name",Cidr:"cidr-block",Dns:"dns-label",State:"lifecycle-state"}' \
      --output table

  gateway_summary

  run_table "Route Tables" \
    oci network route-table list \
      --compartment-id "$NETWORK_COMPARTMENT_OCID" \
      --vcn-id "$VCN_OCID" \
      --query 'data[].{Name:"display-name",State:"lifecycle-state"}' \
      --output table

  show_subnet_inventory

  run_table "Security Lists" \
    oci network security-list list \
      --compartment-id "$NETWORK_COMPARTMENT_OCID" \
      --vcn-id "$VCN_OCID" \
      --query 'data[].{Name:"display-name",State:"lifecycle-state"}' \
      --output table

  show_security_list_rule_details

  show_nsg_inventory
  show_nsg_rule_details

  section "Completion Notes"
  kv_header
  kv "Report saved" "$REPORT_FILE"
  kv "Next action" "Review NSG ingress and egress with the security owner"
}

main() {
  REPORT_SCOPE="${1:-all}"
  case "$REPORT_SCOPE" in
    all|full)
      show_full_report
      ;;
    nsg|nsg-only|--nsg|--nsg-only)
      show_nsg_sections
      ;;
    *)
      printf 'Usage: %s [all|nsg]\n' "$0" >&2
      exit 2
      ;;
  esac
}

main "${1:-all}" | tee "$REPORT_FILE"
