# Data Privacy and Security

At LLM, **safeguarding your data privacy and security** is our top priority. We recognize the critical importance of the data you share with us and handle it with the highest level of diligence.

With LLM Cloud, we handle:

- Deployment
- Scaling
- Upgrades and security patches
- Ensuring high availability

  <iframe
    src="https://status.hanzo.ai/badge?theme=light"
    width="250"
    height="30"
    className="inline-block dark:hidden"
    style={{
      colorScheme: "light",
      marginTop: "5px",
    }}
  ></iframe>

## Security Measures

### LLM Cloud

- We encrypt all data stored using your `LLM_MASTER_KEY` and in transit using TLS.
- Our database and application run on GCP, AWS infrastructure, partly managed by NeonDB.
    - US data region: Northern California (AWS/GCP `us-west-1`) & Virginia (AWS `us-east-1`)
    - EU data region Germany/Frankfurt (AWS/GCP `eu-central-1`)
- All users have access to SSO (Single Sign-On) through OAuth 2.0 with Google, Okta, Microsoft, KeyCloak.
- Audit Logs with retention policy
- Control Allowed IP Addresses that can access your Cloud LLM Instance

### Self-hosted Instances LLM

- **No data or telemetry is stored on LLM Servers when you self-host**
- For installation and configuration, see: [Self-hosting guide](../docs/proxy/deploy.md)
- **Telemetry**: We run no telemetry when you self-host LLM

For security inquiries, please contact us at support@hanzo.ai

## **Security Certifications**

| **Certification** | **Status**                                                                                      |
|-------------------|-------------------------------------------------------------------------------------------------|
| SOC 2 Type I      | Certified. Report available upon request on Enterprise plan.                                                           |
| SOC 2 Type II     | In progress. Certificate available by April 15th, 2025                   |
| ISO 27001          | Certified. Report available upon request on Enterprise                              |


## Supported Data Regions for LLM Cloud

LLM supports the following data regions:

- US, Northern California (AWS/GCP `us-west-1`)
- Europe, Frankfurt, Germany (AWS/GCP `eu-central-1`)

All data, user accounts, and infrastructure are completely separated between these two regions

## Collection of Personal Data

### For Self-hosted LLM Users:
- No personal data is collected or transmitted to LLM servers when you self-host our software.
- Any data generated or processed remains entirely within your own infrastructure.

### For LLM Cloud Users:
- LLM Cloud tracks LLM usage data - We do not access or store the message / response content of your API requests or responses. You can see the [fields tracked here](https://github.com/hanzoai/llm/blob/main/schema.prisma#L174)

**How to Use and Share the Personal Data**
- Only proxy admins can view their usage data, and they can only see the usage data of their organization.
- Proxy admins have the ability to invite other users / admins to their server to view their own usage data
- LLM Cloud does not sell or share any usage data with any third parties.


## Cookies Information, Security, and Privacy

### For Self-hosted LLM Users:
- Cookie data remains within your own infrastructure.
- LLM uses minimal cookies, solely for the purpose of allowing Proxy users to access the LLM Admin UI.
- These cookies are stored in your web browser after you log in.
- We do not use cookies for advertising, tracking, or any purpose beyond maintaining your login session.
- The only cookies used are essential for maintaining user authentication and session management for the app UI.
- Session cookies expire when you close your browser, logout or after 24 hours.
- LLM does not use any third-party cookies.
- The Admin UI accesses the cookie to authenticate your login session.
- The cookie is stored as JWT and is not accessible to any other part of the system.
- We (LLM) do not access or share this cookie data for any other purpose.


### For LLM Cloud Users:
- LLM uses minimal cookies, solely for the purpose of allowing Proxy users to access the LLM Admin UI.
- These cookies are stored in your web browser after you log in.
- We do not use cookies for advertising, tracking, or any purpose beyond maintaining your login session.
- The only cookies used are essential for maintaining user authentication and session management for the app UI.
- Session cookies expire when you close your browser, logout or after 24 hours.
- LLM does not use any third-party cookies.
- The Admin UI accesses the cookie to authenticate your login session.
- The cookie is stored as JWT and is not accessible to any other part of the system.
- We (LLM) do not access or share this cookie data for any other purpose.

## Security Vulnerability Reporting Guidelines

We value the security community's role in protecting our systems and users. To report a security vulnerability:

- Email support@hanzo.ai with details
- Include steps to reproduce the issue
- Provide any relevant additional information

We'll review all reports promptly. Note that we don't currently offer a bug bounty program.

## Vulnerability Scanning

- LLM runs [`grype`](https://github.com/anchore/grype) security scans on all built Docker images.
    - See [`grype llm` check on ci/cd](https://github.com/hanzoai/llm/blob/main/.circleci/config.yml#L1099).
    - Current Status: ✅ Passing. 0 High/Critical severity vulnerabilities found.

## Legal/Compliance FAQs

### Procurement Options

1. Invoicing
2. AWS Marketplace
3. Azure Marketplace


### Vendor Information

Legal Entity Name: Hanzo Industries Inc

Company Phone Number: 9137774443

Point of contact email address for security incidents: dev@hanzo.ai

Point of contact email address for general security-related questions: dev@hanzo.ai

Has the Vendor been audited / certified?
- SOC 2 Type I. Certified. Report available upon request on Enterprise plan.
- SOC 2 Type II. In progress. Certificate available by April 15th, 2025.
- ISO 27001. Certified. Report available upon request on Enterprise plan.

Has an information security management system been implemented?
- Yes - [CodeQL](https://codeql.github.com/) and a comprehensive ISMS covering multiple security domains.

Is logging of key events - auth, creation, update changes occurring?
- Yes - we have [audit logs](https://docs.hanzo.ai/docs/proxy/multiple_admins#1-switch-on-audit-logs)

Does the Vendor have an established Cybersecurity incident management program?
- Yes, Incident Response Policy available upon request.


Does the vendor have a vulnerability disclosure policy in place? [Yes](https://github.com/hanzoai/llm?tab=security-ov-file#security-vulnerability-reporting-guidelines)

Does the vendor perform vulnerability scans?
- Yes, regular vulnerability scans are conducted as detailed in the [Vulnerability Scanning](#vulnerability-scanning) section.

Signer Name: Krish Amit Dholakia

Signer Email: dev@hanzo.ai
