(function () {
  const shared = {
    supportedLanguages: ["en"],
    defaultLanguage: "en",
    seriesBrand: {
      title: "OCI PoC RunBook",
      subtitle: "Workbook"
    },
    notices: {
      en: {
        title: "Educational use and validation required",
        body: "This content is for educational and planning purposes only. Apply every command and configuration first in a non-production test environment that mirrors your target platform, product version, network, security, workload, integration, and failover requirements. The recommended values shown here may not work in your specific environment, may require change-control approval, and can affect availability, performance, security, routing, transaction behavior, resource use, or operational placement. Validate with application owners, administrators, network teams, security teams, and vendor support guidance before using any setting in production."
      }
    },
    guideRegistry: [
      {
            "key": "00-oci-poc-runbook",
            "rootPath": "00-oci-poc-runbook/index.html",
            "nestedPath": "../00-oci-poc-runbook/index.html",
            "label": "00. OCI PoC RunBook"
      },
      {
            "key": "01-scope-and-design-principles",
            "rootPath": "01-scope-and-design-principles/index.html",
            "nestedPath": "../01-scope-and-design-principles/index.html",
            "label": "01. Scope and Design Principles"
      },
      {
            "key": "02-target-oci-network-architecture",
            "rootPath": "02-target-oci-network-architecture/index.html",
            "nestedPath": "../02-target-oci-network-architecture/index.html",
            "label": "02. Target OCI Network Architecture"
      },
      {
            "key": "03-addressing-naming-and-dns",
            "rootPath": "03-addressing-naming-and-dns/index.html",
            "nestedPath": "../03-addressing-naming-and-dns/index.html",
            "label": "03. Addressing, Naming, and DNS"
      },
      {
            "key": "04-bastion-and-administrator-access",
            "rootPath": "04-bastion-and-administrator-access/index.html",
            "nestedPath": "../04-bastion-and-administrator-access/index.html",
            "label": "04. Bastion and Administrator Access"
      },
      {
            "key": "05-Network",
            "rootPath": "05-Network/index.html",
            "nestedPath": "../05-Network/index.html",
            "label": "05. Network"
      },
      {
            "key": "06-exadata-environment-initialization",
            "rootPath": "06-exadata-environment-initialization/index.html",
            "nestedPath": "../06-exadata-environment-initialization/index.html",
            "label": "06. Exadata Environment Initialization"
      },
      {
            "key": "07-bastion-vm-creation",
            "rootPath": "07-bastion-vm-creation/index.html",
            "nestedPath": "../07-bastion-vm-creation/index.html",
            "label": "07. Bastion VM Creation"
      },
      {
            "key": "08-create-exadata-cluster",
            "rootPath": "08-create-exadata-cluster/index.html",
            "nestedPath": "../08-create-exadata-cluster/index.html",
            "label": "08. Create Exadata Cluster"
      },
      {
            "key": "09-upscale-the-cluster-to-two-nodes",
            "rootPath": "09-upscale-the-cluster-to-two-nodes/index.html",
            "nestedPath": "../09-upscale-the-cluster-to-two-nodes/index.html",
            "label": "09. Upscale the Cluster to Two Nodes"
      },
      {
            "key": "10-create-container-database",
            "rootPath": "10-create-container-database/index.html",
            "nestedPath": "../10-create-container-database/index.html",
            "label": "10. Create Container Database"
      },
      {
            "key": "11-enable-automatic-backups",
            "rootPath": "11-enable-automatic-backups/index.html",
            "nestedPath": "../11-enable-automatic-backups/index.html",
            "label": "11. Enable Automatic Backups"
      },
      {
            "key": "12-create-database-credential-secrets",
            "rootPath": "12-create-database-credential-secrets/index.html",
            "nestedPath": "../12-create-database-credential-secrets/index.html",
            "label": "12. Create Database Credential Secrets"
      },
      {
            "key": "13-oci-database-management",
            "rootPath": "13-oci-database-management/index.html",
            "nestedPath": "../13-oci-database-management/index.html",
            "label": "13. OCI Database Management"
      },
      {
            "key": "14-stop-and-start-services",
            "rootPath": "14-stop-and-start-services/index.html",
            "nestedPath": "../14-stop-and-start-services/index.html",
            "label": "14. Stop and Start Services"
      },
      {
            "key": "15-recover-variables",
            "rootPath": "15-recover-variables/index.html",
            "nestedPath": "../15-recover-variables/index.html",
            "label": "15. Recover Variables"
      }
]
  };

  function normalizeLanguage(value) {
    return value === "en" ? "en" : shared.defaultLanguage;
  }

  function languageFromLocation() {
    return shared.defaultLanguage;
  }

  function withLanguage(href) {
    return href;
  }

  function chooseHref(entry, scope) {
    return scope === "root" ? entry.rootPath : entry.nestedPath;
  }

  function relatedLinks(currentKey, scope) {
    return shared.guideRegistry
      .filter((entry) => entry.key !== currentKey)
      .map((entry) => ({
        key: entry.key,
        href: withLanguage(chooseHref(entry, scope)),
        label: entry.label
      }));
  }

  function renderGuideCard(link, template) {
    const anchor = document.createElement("a");
    anchor.className = template?.className || "related-link";
    anchor.href = link.href;
    anchor.dataset.guideKey = link.key;

    const title = document.createElement("strong");
    title.className = template?.titleClassName || "";
    title.textContent = link.label;

    anchor.append(title);
    return anchor;
  }

  function hydrateGuideCards(root = document, options = {}) {
    const containers = root.querySelectorAll("[data-guide-cards]");
    containers.forEach((container) => {
      const variant = container.dataset.guideVariant || options.variant || "root";
      const scope = container.dataset.guideScope || options.scope || "nested";
      const firstCard = container.querySelector("a");
      const template = firstCard
        ? {
            className: firstCard.className,
            titleClassName: firstCard.querySelector("strong")?.className || ""
          }
        : null;
      const links = relatedLinks(variant, scope);
      container.replaceChildren(...links.map((link) => renderGuideCard(link, template)));
    });
  }

  function applyStaticPage({ variant, scope, document }) {
    document.querySelectorAll("[data-series-brand-title]").forEach((node) => {
      node.textContent = shared.seriesBrand.title;
    });
    document.querySelectorAll("[data-series-brand-subtitle]").forEach((node) => {
      node.textContent = shared.seriesBrand.subtitle;
    });
    hydrateGuideCards(document, { variant, scope });
  }

  window.GuideSet = {
    shared,
    normalizeLanguage,
    languageFromLocation,
    withLanguage,
    chooseHref,
    relatedLinks,
    hydrateGuideCards,
    applyStaticPage
  };

  document.addEventListener("DOMContentLoaded", () => {
    const body = document.body;
    applyStaticPage({
      variant: body.dataset.guideKey || "root",
      scope: body.dataset.guideScope || "nested",
      document
    });
  });
})();
