#!/bin/bash

. "$HOME/workbook/helpers.sh" || exit 1
WORKBOOK_DIR="${WORKBOOK_DIR:-$HOME/workbook}"
CLI_ENV="${CLI_ENV:-$WORKBOOK_DIR/cli.env}"
STATUS_FILE="$WORKBOOK_DIR/recovery-status.tsv"
FOUND=0
MISS=0

phase() { printf '\n%s ...\n' "$1"; }
note() { printf '  - %s\n' "$1"; }
ok() { case "$1" in ""|null|None|Usage:*|Error:*|*"
"*) return 1;; *) return 0;; esac; }
rmkey() { [ -f "$CLI_ENV" ] || return 0; t="$(mktemp "$WORKBOOK_DIR/cli.env.XXXXXX")" || return 1; awk -v k="$1" '$0 !~ "^" k "=" {print}' "$CLI_ENV" > "$t" && mv "$t" "$CLI_ENV"; }
save() { k="$1"; v="$2"; if ok "$v"; then FOUND=$((FOUND+1)); upsert_cli_env "$k" "$v" >/dev/null; [ "$k" = CDB_ADMIN_PASSWORD ] && out='<stored_in_cli_env>' || out="$v"; printf '%s\tFOUND\t%s\n' "$k" "$out" >> "$STATUS_FILE"; else MISS=$((MISS+1)); rmkey "$k"; printf '%s\tMISS\t\n' "$k" >> "$STATUS_FILE"; fi; }
ociq() { "$@" --raw-output 2>/dev/null || true; }
first_id() { "$@" --query 'data[0].id' --raw-output 2>/dev/null || true; }

read_profile() {
  cfg="${OCI_CLI_CONFIG_FILE:-$HOME/.oci/config}"
  profile="${OCI_CLI_PROFILE:-DEFAULT}"
  [ -f "$cfg" ] || return 0
  TENANCY_ID="$(awk -F= -v p="$profile" '$0=="["p"]"{i=1;next} /^\[/{i=0} i&&$1~/^[[:space:]]*tenancy[[:space:]]*$/{gsub(/[[:space:]]/,"",$2);print $2;exit}' "$cfg")"
  REGION="$(awk -F= -v p="$profile" '$0=="["p"]"{i=1;next} /^\[/{i=0} i&&$1~/^[[:space:]]*region[[:space:]]*$/{gsub(/[[:space:]]/,"",$2);print $2;exit}' "$cfg")"
}

lookup_subnet() { first_id oci network subnet list --region "$REGION" --compartment-id "$POC_COMPARTMENT_OCID" --vcn-id "$VCN_OCID" --display-name "$1" --all; }
lookup_nsg() { first_id oci network nsg list --region "$REGION" --compartment-id "$POC_COMPARTMENT_OCID" --vcn-id "$VCN_OCID" --display-name "$1" --all; }
lookup_rt() { first_id oci network route-table list --region "$REGION" --compartment-id "$POC_COMPARTMENT_OCID" --vcn-id "$VCN_OCID" --display-name "$1" --all; }
lookup_secret() { first_id oci vault secret list --region "$REGION" --compartment-id "$POC_COMPARTMENT_OCID" --name "$1" --all; }

phase 'Reading active OCI CLI profile'
read_profile
REGION="${REGION:-$(oci configure get region 2>/dev/null || true)}"
note "Region candidate: ${REGION:-<not_found>}"
ok "$REGION" || { printf 'STOP: REGION not found.\n' >&2; exit 1; }
case "$TENANCY_ID" in ocid1.tenancy.oc1*) ;; *) printf 'STOP: TENANCY_ID not found.\n' >&2; exit 1;; esac

phase 'Confirming target compartment'
printf 'Enter parent compartment name [Partner]: '; IFS= read -r POC_PARENT_COMPARTMENT_NAME
POC_PARENT_COMPARTMENT_NAME="${POC_PARENT_COMPARTMENT_NAME:-Partner}"
printf 'Enter assigned compartment name under %s [LAD-01]: ' "$POC_PARENT_COMPARTMENT_NAME"; IFS= read -r POC_COMPARTMENT_NAME
POC_COMPARTMENT_NAME="${POC_COMPARTMENT_NAME:-LAD-01}"
printf 'This recovery will discover existing resources in /%s/%s and write %s.\n' "$POC_PARENT_COMPARTMENT_NAME" "$POC_COMPARTMENT_NAME" "$CLI_ENV"
printf 'Confirm this compartment path? [y/N]: '; IFS= read -r ans
case "$ans" in y|Y|yes|YES) ;; *) printf 'STOP: Recovery was not confirmed.\n' >&2; exit 1;; esac
printf 'Enter CDB_ADMIN_PASSWORD [Enter to use Default]: '; IFS= read -r CDB_ADMIN_PASSWORD
CDB_ADMIN_PASSWORD="${CDB_ADMIN_PASSWORD:-WelCome#2026_}"

phase 'Resolving compartment OCIDs'
POC_PARENT_COMPARTMENT_OCID="$(ociq oci iam compartment list --compartment-id "$TENANCY_ID" --all --query "data[?name=='$POC_PARENT_COMPARTMENT_NAME' && \"lifecycle-state\"=='ACTIVE'].id | [0]")"
POC_COMPARTMENT_OCID="$(ociq oci iam compartment list --compartment-id "$POC_PARENT_COMPARTMENT_OCID" --all --query "data[?name=='$POC_COMPARTMENT_NAME' && \"lifecycle-state\"=='ACTIVE'].id | [0]")"
ok "$POC_PARENT_COMPARTMENT_OCID" || { printf 'STOP: Parent compartment not found.\n' >&2; exit 1; }
ok "$POC_COMPARTMENT_OCID" || { printf 'STOP: Assigned compartment not found.\n' >&2; exit 1; }
note "Parent compartment OCID: $POC_PARENT_COMPARTMENT_OCID"
note "Assigned compartment OCID: $POC_COMPARTMENT_OCID"

VCN_NAME="VCN-$POC_COMPARTMENT_NAME"; ADMIN_BUCKET_NAME="${REGION}-${POC_PARENT_COMPARTMENT_NAME}-${POC_COMPARTMENT_NAME}"
BASTION_DISPLAY_NAME=bastion-01; EXADATA_DISPLAY_NAME=VMCluster-01; DB_HOME_DISPLAY_NAME=dbhome_01
CDB_NAME=CDB01; PDB_NAME=PDB01; CDB_CREDENTIAL_VAULT_NAME=vault-01; CDB_CREDENTIAL_KEY_NAME=key-01
CDB_SYS_SECRET_NAME=cdb01-sys-password; CDB_SYSTEM_SECRET_NAME=cdb01-system-password; DBMGMT_PRIVATE_ENDPOINT_NAME=pe-dbmgmt-cdb01

phase 'Discovering network and bastion artifacts'
VCN_OCID="$(first_id oci network vcn list --region "$REGION" --compartment-id "$POC_COMPARTMENT_OCID" --display-name "$VCN_NAME" --all)"
VCN_CIDR="$(ociq oci network vcn get --region "$REGION" --vcn-id "$VCN_OCID" --query 'data."cidr-block"')"
DEFAULT_SECURITY_LIST_OCID="$(ociq oci network vcn get --region "$REGION" --vcn-id "$VCN_OCID" --query 'data."default-security-list-id"')"
for item in 'SUBNET_ADMIN_OCID subnet-admin' 'SUBNET_DBCLIENT_OCID subnet-dbclient' 'SUBNET_DB_BACKUP_OCID subnet-db-backup' 'SUBNET_DBTOOLS_OCID subnet-dbtools' 'SUBNET_PUBLIC_LB_OCID subnet-public-lb' 'SUBNET_APPS_OCID subnet-applications'; do set -- $item; eval "$1=\$(lookup_subnet $2)"; done
for item in 'RT_PUBLIC_OCID rt-public' 'RT_PRIVATE_OCID rt-private'; do set -- $item; eval "$1=\$(lookup_rt $2)"; done
IGW_OCID="$(first_id oci network internet-gateway list --region "$REGION" --compartment-id "$POC_COMPARTMENT_OCID" --vcn-id "$VCN_OCID" --display-name gw-internet --all)"
NAT_OCID="$(first_id oci network nat-gateway list --region "$REGION" --compartment-id "$POC_COMPARTMENT_OCID" --vcn-id "$VCN_OCID" --display-name gw-nat --all)"
SGW_OCID="$(ociq oci network service-gateway list --region "$REGION" --compartment-id "$POC_COMPARTMENT_OCID" --vcn-id "$VCN_OCID" --all --query "data[?\"display-name\"=='gw-service'].id | [0]")"
for item in 'NSG_EXADATA_CLIENT_OCID nsg-exadata-client' 'NSG_APPLICATIONS_OCID nsg-applications' 'NSG_DBTOOLS_OCID nsg-dbtools-endpoint' 'NSG_BASTION_OCID nsg-bastion-admin' 'NSG_PUBLIC_LB_OCID nsg-public-lb'; do set -- $item; eval "$1=\$(lookup_nsg $2)"; done
SECURITY_LIST_BACKUP_OCID="$(first_id oci network security-list list --region "$REGION" --compartment-id "$POC_COMPARTMENT_OCID" --vcn-id "$VCN_OCID" --display-name sl-backup --all)"
ALL_REGION_SERVICES_SERVICE_OCID="$(ociq oci network service list --region "$REGION" --query "data[?contains(name, 'All') && contains(name, 'Oracle Services Network')].id | [0]")"
SERVICE_CIDR_BLOCK_LABEL="$(ociq oci network service list --region "$REGION" --query "data[?contains(name, 'All') && contains(name, 'Oracle Services Network')].\"cidr-block\" | [0]")"
BASTION_VM_OCID="$(first_id oci compute instance list --region "$REGION" --compartment-id "$POC_COMPARTMENT_OCID" --display-name "$BASTION_DISPLAY_NAME" --sort-by TIMECREATED --sort-order DESC --all)"
BASTION_PUBLIC_IP="$(ociq oci compute instance list-vnics --region "$REGION" --instance-id "$BASTION_VM_OCID" --query 'data[0]."public-ip"')"
note "VCN: ${VCN_OCID:-<not_found>}"
note "Bastion public IP: ${BASTION_PUBLIC_IP:-<not_found>}"

phase 'Discovering Exadata and database artifacts'
VM_CLUSTER_OCID="$(first_id oci db exadb-vm-cluster list --region "$REGION" --compartment-id "$POC_COMPARTMENT_OCID" --display-name "$EXADATA_DISPLAY_NAME" --sort-by TIMECREATED --sort-order DESC --all)"
VM_CLUSTER_JSON="$WORKBOOK_DIR/recovered-vm-cluster.json"
oci db exadb-vm-cluster get --region "$REGION" --exadb-vm-cluster-id "$VM_CLUSTER_OCID" --output json > "$VM_CLUSTER_JSON" 2>/dev/null || printf '{}\n' > "$VM_CLUSTER_JSON"
VM_CLUSTER_STATUS="$(jq -r '.data."lifecycle-state" // empty' "$VM_CLUSTER_JSON" 2>/dev/null)"
EXADATA_DISPLAY_NAME="$(jq -r '.data."display-name" // .data.displayName // empty' "$VM_CLUSTER_JSON" 2>/dev/null)"
EXADATA_CLUSTER_NAME="$(jq -r '.data."cluster-name" // .data.clusterName // empty' "$VM_CLUSTER_JSON" 2>/dev/null)"
EXADATA_ENABLED_ECPU_COUNT="$(jq -r '.data."enabled-e-cpu-count" // .data.enabledEcpuCount // .data."enabled-ecpu-count" // empty' "$VM_CLUSTER_JSON" 2>/dev/null)"
EXADATA_TOTAL_ECPU_COUNT="$(jq -r '.data."total-e-cpu-count" // .data.totalEcpuCount // .data."total-ecpu-count" // empty' "$VM_CLUSTER_JSON" 2>/dev/null)"
EXADATA_VM_FS_STORAGE_GB="$(jq -r '.data."vm-file-system-storage"."total-size-in-gbs" // .data.vmFileSystemStorage.totalSizeInGbs // empty' "$VM_CLUSTER_JSON" 2>/dev/null)"
EXADATA_SCAN_PORT_TCP="$(jq -r '.data."scan-listener-port-tcp" // .data.scanListenerPortTcp // empty' "$VM_CLUSTER_JSON" 2>/dev/null)"
EXADATA_SCAN_PORT_TCPS="$(jq -r '.data."scan-listener-port-tcp-ssl" // .data.scanListenerPortTcpSsl // empty' "$VM_CLUSTER_JSON" 2>/dev/null)"
EXADATA_TIME_ZONE="$(jq -r '.data."time-zone" // .data.timeZone // empty' "$VM_CLUSTER_JSON" 2>/dev/null)"
LICENSE_MODEL="$(jq -r '.data."license-model" // .data.licenseModel // empty' "$VM_CLUSTER_JSON" 2>/dev/null)"
DB_HOME_OCID="$(first_id oci db db-home list --region "$REGION" --compartment-id "$POC_COMPARTMENT_OCID" --vm-cluster-id "$VM_CLUSTER_OCID" --display-name "$DB_HOME_DISPLAY_NAME" --all)"
CDB_OCID="$(ociq oci db database list --region "$REGION" --db-home-id "$DB_HOME_OCID" --db-name "$CDB_NAME" --query 'data[0].id')"
ok "$CDB_OCID" || CDB_OCID="$(ociq oci db database list --region "$REGION" --compartment-id "$POC_COMPARTMENT_OCID" --query "data[?\"db-name\"=='$CDB_NAME'].id | [0]")"
DBMGMT_CDB_CONNECT_STRING="$(ociq oci db database get --region "$REGION" --database-id "$CDB_OCID" --query 'data."connection-strings"."cdb-ip-default"')"
ok "$DBMGMT_CDB_CONNECT_STRING" || DBMGMT_CDB_CONNECT_STRING="$(ociq oci db database get --region "$REGION" --database-id "$CDB_OCID" --query 'data."connection-strings"."all-connection-strings"."CDB Default"')"
DBMGMT_CDB_SERVICE_NAME="$(printf '%s\n' "$DBMGMT_CDB_CONNECT_STRING" | sed -n 's/.*SERVICE_NAME=\([^)]*\)).*/\1/p' | sed -n '1p')"
ok "$DBMGMT_CDB_SERVICE_NAME" || DBMGMT_CDB_SERVICE_NAME="$(printf '%s\n' "$DBMGMT_CDB_CONNECT_STRING" | sed 's/[?].*$//' | sed 's#.*/##' | sed 's/[[:space:]]*$//' | sed -n '1p')"
PDB_OCID="$(ociq oci db pluggable-database list --region "$REGION" --database-id "$CDB_OCID" --all --query "data[?\"pdb-name\"=='$PDB_NAME'].id | [0]")"
DB_VERSION="$(ociq oci db db-home get --region "$REGION" --db-home-id "$DB_HOME_OCID" --query 'data."db-version"')"
CDB_CHARACTER_SET="$(ociq oci db database get --region "$REGION" --database-id "$CDB_OCID" --query 'data."character-set"')"
CDB_CHARACTER_SET_MODE=EXPLICIT
note "VM cluster: ${VM_CLUSTER_OCID:-<not_found>}"
note "CDB: ${CDB_OCID:-<not_found>}"

phase 'Discovering backup, Vault, and Database Management artifacts'
CDB_CREDENTIAL_VAULT_OCID="$(ociq oci kms management vault list --region "$REGION" --compartment-id "$POC_COMPARTMENT_OCID" --all --query "data[?\"display-name\"=='$CDB_CREDENTIAL_VAULT_NAME']|[0].id")"
CDB_CREDENTIAL_VAULT_MANAGEMENT_ENDPOINT="$(ociq oci kms management vault get --region "$REGION" --vault-id "$CDB_CREDENTIAL_VAULT_OCID" --query 'data."management-endpoint"')"
CDB_CREDENTIAL_KEY_OCID="$(ociq oci kms management key list --endpoint "$CDB_CREDENTIAL_VAULT_MANAGEMENT_ENDPOINT" --compartment-id "$POC_COMPARTMENT_OCID" --all --query "data[?\"display-name\"=='$CDB_CREDENTIAL_KEY_NAME']|[0].id")"
CDB_SYS_SECRET_OCID="$(lookup_secret "$CDB_SYS_SECRET_NAME")"; CDB_SYSTEM_SECRET_OCID="$(lookup_secret "$CDB_SYSTEM_SECRET_NAME")"
DBMGMT_PRIVATE_ENDPOINT_RESPONSE_JSON="$WORKBOOK_DIR/recovered-dbmgmt-private-endpoint.json"
oci database-management private-endpoint list \
  --region "$REGION" \
  --compartment-id "$POC_COMPARTMENT_OCID" \
  --name "$DBMGMT_PRIVATE_ENDPOINT_NAME" \
  --vcn-id "$VCN_OCID" \
  --all \
  --query "data.items[?\"subnet-id\"=='$SUBNET_DBTOOLS_OCID' && \"lifecycle-state\"=='ACTIVE']|[0]" \
  > "$DBMGMT_PRIVATE_ENDPOINT_RESPONSE_JSON" 2>/dev/null || printf '{}\n' > "$DBMGMT_PRIVATE_ENDPOINT_RESPONSE_JSON"
DBMGMT_PRIVATE_ENDPOINT_OCID="$(sed -n 's/^[[:space:]]*"id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$DBMGMT_PRIVATE_ENDPOINT_RESPONSE_JSON" | sed -n '1p')"
if ! ok "$DBMGMT_PRIVATE_ENDPOINT_OCID"; then
  oci database-management private-endpoint list \
    --region "$REGION" \
    --compartment-id "$POC_COMPARTMENT_OCID" \
    --vcn-id "$VCN_OCID" \
    --all \
    --query "data.items[?\"subnet-id\"=='$SUBNET_DBTOOLS_OCID' && \"lifecycle-state\"=='ACTIVE']|[0]" \
    > "$DBMGMT_PRIVATE_ENDPOINT_RESPONSE_JSON" 2>/dev/null || printf '{}\n' > "$DBMGMT_PRIVATE_ENDPOINT_RESPONSE_JSON"
  DBMGMT_PRIVATE_ENDPOINT_OCID="$(sed -n 's/^[[:space:]]*"id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$DBMGMT_PRIVATE_ENDPOINT_RESPONSE_JSON" | sed -n '1p')"
fi
if ! ok "$DBMGMT_PRIVATE_ENDPOINT_OCID"; then
  DBMGMT_PRIVATE_ENDPOINT_OCID="$(ociq oci database-management private-endpoint list --region "$REGION" --compartment-id "$POC_COMPARTMENT_OCID" --name "$DBMGMT_PRIVATE_ENDPOINT_NAME" --vcn-id "$VCN_OCID" --all --query 'data.items[0].id')"
fi
RECOVERY_SERVICE_SUBNET_OCID="$(ociq oci recovery recovery-service-subnet-collection list-recovery-service-subnets --region "$REGION" --compartment-id "$POC_COMPARTMENT_OCID" --display-name rss-exadata-backup --vcn-id "$VCN_OCID" --lifecycle-state ACTIVE --all --query 'data.items[0].id')"
PROTECTION_POLICY_NAME=Bronze; BACKUP_DESTINATION_TYPE=DBRS; BACKUP_RETENTION_POLICY_ON_TERMINATE=RETAIN_FOR_72_HOURS; REAL_TIME_DATA_PROTECTION_ENABLED=false
PROTECTION_POLICY_OCID="$(ociq oci recovery protection-policy-collection list-protection-policies --region "$REGION" --compartment-id "$POC_COMPARTMENT_OCID" --display-name "$PROTECTION_POLICY_NAME" --all --query 'data.items[0].id')"
BACKUP_LIST_JSON="$WORKBOOK_DIR/recovered-backup-list.json"
oci db backup list \
  --region "$REGION" \
  --database-id "$CDB_OCID" \
  --all \
  --output json > "$BACKUP_LIST_JSON" 2>/dev/null || printf '{"data":[]}\n' > "$BACKUP_LIST_JSON"
INITIAL_BACKUP_OCID="$(
  jq -r --arg prefix "${CDB_NAME}-initial-full-" '
    def t: ."time-started" // ."time-created" // "";
    ((.data // [])
      | map(select((."display-name" // "") | startswith($prefix)))
      | sort_by(t)
      | reverse
      | .[0].id)
    // ((.data // []) | sort_by(t) | reverse | .[0].id)
    // empty
  ' "$BACKUP_LIST_JSON" 2>/dev/null
)"
DBMGMT_MANAGEMENT_TYPE=ADVANCED; DBMGMT_CREDENTIAL_USERNAME=SYSTEM; DBMGMT_PROTOCOL=TCP; DBMGMT_PORT=1521; DBMGMT_ROLE=NORMAL; DBMGMT_SECRET_POLICY_NAME=DBMgmt_Resource_Policy
DBMGMT_SYSTEM_SECRET_OCID="$CDB_SYSTEM_SECRET_OCID"; DBMGMT_PASSWORD_SECRET_OCID="$CDB_SYSTEM_SECRET_OCID"; DBMGMT_IAM_HOME_REGION=us-phoenix-1; DBMGMT_SECRET_POLICY_COMPARTMENT_NAME="$POC_COMPARTMENT_NAME"
DBMGMT_SECRET_POLICY_OCID="$(ociq oci iam policy list --region "$DBMGMT_IAM_HOME_REGION" --compartment-id "$POC_COMPARTMENT_OCID" --name "$DBMGMT_SECRET_POLICY_NAME" --all --query 'data[0].id')"

AVAILABILITY_DOMAIN="$(ociq oci iam availability-domain list --region "$REGION" --compartment-id "$TENANCY_ID" --query 'data[0].name')"
EXADATA_AVAILABILITY_DOMAIN="$(ociq oci iam availability-domain list --region "$REGION" --compartment-id "$TENANCY_ID" --query 'data[1].name')"
EXADATA_AD_NUMBER=2; EXADATA_STORAGE_GB=512; EXADB_SHAPE=EXADBXS; EXADB_SHAPE_ATTRIBUTE=SMART_STORAGE; EXADB_SHAPE_FAMILY=EXADB_XS; GI_MAJOR_VERSION=26.0.0.0
EXADATA_CLUSTER_NAME="${EXADATA_CLUSTER_NAME:-vmc01}"; EXADATA_ENABLED_ECPU_COUNT="${EXADATA_ENABLED_ECPU_COUNT:-8}"; EXADATA_TOTAL_ECPU_COUNT="${EXADATA_TOTAL_ECPU_COUNT:-8}"; EXADATA_VM_FS_STORAGE_GB="${EXADATA_VM_FS_STORAGE_GB:-260}"
EXADATA_SCAN_PORT_TCP="${EXADATA_SCAN_PORT_TCP:-1521}"; EXADATA_SCAN_PORT_TCPS="${EXADATA_SCAN_PORT_TCPS:-2484}"; EXADATA_TIME_ZONE="${EXADATA_TIME_ZONE:-UTC}"; LICENSE_MODEL="${LICENSE_MODEL:-BRING_YOUR_OWN_LICENSE}"
EXADATA_SYSTEM_VERSION=25.2.3.0.0.251020; EXADATA_TARGET_SYSTEM_VERSION=25.2.11.0.0.260604.1; TOTAL_ECPU_PER_VM=12; ENABLED_ECPU_PER_VM=8; TARGET_MEMORY_GB_PER_VM=33
BASTION_SHAPE=VM.Standard.E5.Flex; OL9_MARKETPLACE_IMAGE_OCID="$(ociq oci compute image list --region "$REGION" --compartment-id "$TENANCY_ID" --operating-system 'Oracle Linux' --operating-system-version 9 --shape "$BASTION_SHAPE" --all --query 'data[?contains("display-name", `Oracle-Linux-9`)] | [0].id')"
VAULT_OCID="$(first_id oci db exascale-db-storage-vault list --region "$REGION" --compartment-id "$POC_COMPARTMENT_OCID" --display-name Vault-01 --all)"
GRID_IMAGE_ID_AD1=ocid1.dbpatch.oc1.iad.anuwcljtt5t4sqqasz3qnoo5rd57dcduckkxleotng5hnyxx22vko2g3w7ra
GRID_IMAGE_ID_AD2=ocid1.dbpatch.oc1.iad.anuwcljst5t4sqqa352vh7qiqpual26qxqwkmkcqiyi6draczpiblr73araa
GRID_IMAGE_ID_AD3="${GRID_IMAGE_ID_AD3:-}"
case "$EXADATA_AD_NUMBER" in
  1) GRID_IMAGE_ID="$GRID_IMAGE_ID_AD1" ;;
  2) GRID_IMAGE_ID="$GRID_IMAGE_ID_AD2" ;;
  3) GRID_IMAGE_ID="$GRID_IMAGE_ID_AD3" ;;
esac
SSH_PRIVATE_KEY_FILE=bastion-01_rsa; SSH_PUBLIC_KEY_FILE=bastion-01_rsa.pub; EXADATA_SSH_PRIVATE_KEY_FILE=vmcluster-01_rsa; EXADATA_SSH_PUBLIC_KEY_FILE=vmcluster-01_rsa.pub
EXADATA_HOSTNAME=exasc01; BASTION_SSH_USER=opc; CLUSTER_SSH_USER=opc; OBJECT_STORAGE_NAMESPACE="$(ociq oci os ns get --region "$REGION" --query data)"
if ok "$DBMGMT_CDB_SERVICE_NAME"; then
  EXADATA_DOMAIN="${DBMGMT_CDB_SERVICE_NAME#*.}"
  [ "$EXADATA_DOMAIN" = "$DBMGMT_CDB_SERVICE_NAME" ] && EXADATA_DOMAIN=""
fi
DB_NODE_LIST_JSON="$WORKBOOK_DIR/recovered-db-node-list.json"
DB_NODE_GET_JSON="$WORKBOOK_DIR/recovered-db-node-get.json"
oci db node list \
  --region "$REGION" \
  --compartment-id "$POC_COMPARTMENT_OCID" \
  --vm-cluster-id "$VM_CLUSTER_OCID" \
  --all \
  --output json > "$DB_NODE_LIST_JSON" 2>/dev/null || printf '{"data":[]}\n' > "$DB_NODE_LIST_JSON"
DB_NODE_OCID="$(jq -r '.data | sort_by(."host-name" // .hostname // "") | .[0].id // empty' "$DB_NODE_LIST_JSON" 2>/dev/null)"
if ok "$DB_NODE_OCID"; then
  oci db node get \
    --region "$REGION" \
    --db-node-id "$DB_NODE_OCID" \
    --output json > "$DB_NODE_GET_JSON" 2>/dev/null || printf '{}\n' > "$DB_NODE_GET_JSON"
else
  printf '{}\n' > "$DB_NODE_GET_JSON"
fi
DB_NODE_HOSTNAME="$(jq -rs '.[0].data."host-name" // .[0].data.hostname // (.[1].data | sort_by(."host-name" // .hostname // "") | .[0]."host-name" // .[0].hostname) // empty' "$DB_NODE_GET_JSON" "$DB_NODE_LIST_JSON" 2>/dev/null)"
case "$DB_NODE_HOSTNAME" in
  *.*) CLUSTER_FIRST_NODE_HOSTNAME="$DB_NODE_HOSTNAME" ;;
  ""|null) CLUSTER_FIRST_NODE_HOSTNAME="" ;;
  *) ok "$EXADATA_DOMAIN" && CLUSTER_FIRST_NODE_HOSTNAME="$DB_NODE_HOSTNAME.$EXADATA_DOMAIN" || CLUSTER_FIRST_NODE_HOSTNAME="$DB_NODE_HOSTNAME" ;;
esac
note "DB Management private endpoint: ${DBMGMT_PRIVATE_ENDPOINT_OCID:-<not_found>}"
note "Cluster first node hostname: ${CLUSTER_FIRST_NODE_HOSTNAME:-<not_found>}"

phase 'Saving recovered variables'
: > "$STATUS_FILE"; chmod 600 "$STATUS_FILE"; printf '%s\t%s\t%s\n' VARIABLE STATUS VALUE >> "$STATUS_FILE"
printf '\n%-36s | %s\n' VARIABLE VALUE
printf '%-36s | %s\n' ------------------------------------ -----
KEYS='TENANCY_ID REGION POC_PARENT_COMPARTMENT_NAME POC_PARENT_COMPARTMENT_OCID POC_COMPARTMENT_NAME POC_COMPARTMENT_OCID PARENT_COMPARTMENT_NAME PARENT_COMPARTMENT_OCID NETWORK_COMPARTMENT_OCID SECURITY_COMPARTMENT_OCID DATABASE_COMPARTMENT_OCID ADMIN_COMPARTMENT_OCID APPLICATION_COMPARTMENT_OCID LOG_COMPARTMENT_OCID VCN_NAME VCN_CIDR VCN_OCID DEFAULT_SECURITY_LIST_OCID ALL_REGION_SERVICES_SERVICE_OCID SERVICE_CIDR_BLOCK_LABEL SECURITY_LIST_BACKUP_OCID SUBNET_ADMIN_OCID SUBNET_DBCLIENT_OCID SUBNET_DB_BACKUP_OCID SUBNET_DBTOOLS_OCID SUBNET_PUBLIC_LB_OCID SUBNET_APPS_OCID RT_PUBLIC_OCID RT_PRIVATE_OCID IGW_OCID NAT_OCID SGW_OCID NSG_EXADATA_CLIENT_OCID NSG_APPLICATIONS_OCID NSG_DBTOOLS_OCID NSG_BASTION_OCID NSG_PUBLIC_LB_OCID AVAILABILITY_DOMAIN BASTION_SHAPE OL9_MARKETPLACE_IMAGE_OCID BASTION_DISPLAY_NAME BASTION_VM_OCID BASTION_PUBLIC_IP ADMIN_BUCKET_NAME SSH_PRIVATE_KEY_FILE SSH_PUBLIC_KEY_FILE VAULT_OCID EXADATA_STORAGE_GB EXADATA_AVAILABILITY_DOMAIN EXADATA_AD_NUMBER EXADB_SHAPE EXADB_SHAPE_ATTRIBUTE EXADB_SHAPE_FAMILY GI_MAJOR_VERSION GRID_IMAGE_ID EXADATA_SYSTEM_VERSION EXADATA_DISPLAY_NAME EXADATA_CLUSTER_NAME EXADATA_ENABLED_ECPU_COUNT EXADATA_TOTAL_ECPU_COUNT EXADATA_VM_FS_STORAGE_GB EXADATA_SCAN_PORT_TCP EXADATA_SCAN_PORT_TCPS EXADATA_TIME_ZONE LICENSE_MODEL VM_CLUSTER_OCID VM_CLUSTER_STATUS EXADATA_TARGET_SYSTEM_VERSION EXADATA_SSH_PRIVATE_KEY_FILE EXADATA_SSH_PUBLIC_KEY_FILE DB_HOME_OCID DB_VERSION TOTAL_ECPU_PER_VM ENABLED_ECPU_PER_VM TARGET_MEMORY_GB_PER_VM CDB_NAME CDB_OCID CDB_ADMIN_PASSWORD CDB_CHARACTER_SET CDB_CHARACTER_SET_MODE PDB_NAME PDB_OCID PROTECTION_POLICY_NAME BACKUP_DESTINATION_TYPE BACKUP_RETENTION_POLICY_ON_TERMINATE REAL_TIME_DATA_PROTECTION_ENABLED RECOVERY_SERVICE_SUBNET_OCID PROTECTION_POLICY_OCID INITIAL_BACKUP_OCID CDB_CREDENTIAL_VAULT_NAME CDB_CREDENTIAL_VAULT_OCID CDB_CREDENTIAL_VAULT_MANAGEMENT_ENDPOINT CDB_CREDENTIAL_KEY_NAME CDB_CREDENTIAL_KEY_OCID CDB_SYS_SECRET_NAME CDB_SYS_SECRET_OCID CDB_SYSTEM_SECRET_NAME CDB_SYSTEM_SECRET_OCID DBMGMT_SYSTEM_SECRET_OCID DBMGMT_PASSWORD_SECRET_OCID DBMGMT_PRIVATE_ENDPOINT_NAME DBMGMT_MANAGEMENT_TYPE DBMGMT_CREDENTIAL_USERNAME DBMGMT_PROTOCOL DBMGMT_PORT DBMGMT_ROLE DBMGMT_SECRET_POLICY_NAME DBMGMT_PRIVATE_ENDPOINT_OCID DBMGMT_IAM_HOME_REGION DBMGMT_SECRET_POLICY_COMPARTMENT_NAME DBMGMT_SECRET_POLICY_OCID DBMGMT_CDB_SERVICE_NAME EXADATA_HOSTNAME BASTION_SSH_USER OBJECT_STORAGE_NAMESPACE CLUSTER_SSH_USER EXADATA_DOMAIN CLUSTER_FIRST_NODE_HOSTNAME'
PARENT_COMPARTMENT_NAME="$POC_PARENT_COMPARTMENT_NAME"; PARENT_COMPARTMENT_OCID="$POC_PARENT_COMPARTMENT_OCID"; NETWORK_COMPARTMENT_OCID="$POC_COMPARTMENT_OCID"; SECURITY_COMPARTMENT_OCID="$POC_COMPARTMENT_OCID"; DATABASE_COMPARTMENT_OCID="$POC_COMPARTMENT_OCID"; ADMIN_COMPARTMENT_OCID="$POC_COMPARTMENT_OCID"; APPLICATION_COMPARTMENT_OCID="$POC_COMPARTMENT_OCID"; LOG_COMPARTMENT_OCID="$POC_COMPARTMENT_OCID"
for k in $KEYS; do eval "v=\${$k:-}"; save "$k" "$v"; done
printf '\n%-36s | %s\n' RECOVERY_STATUS complete
printf '%-36s | %s\n' RECOVERED_VARIABLES "$FOUND"
printf '%-36s | %s\n' MISSING_VARIABLES "$MISS"
printf '%-36s | %s\n' RECOVERY_STATUS_FILE "$STATUS_FILE"
if [ "$MISS" -gt 0 ]; then
  printf '\nMissing variables:\n'
  awk -F '\t' '$2 == "MISS" { printf "  - %s\n", $1 }' "$STATUS_FILE"
fi
printf '\nRecovered variables were saved to %s.\n' "$CLI_ENV"
