# Arany Példapárok (Gold Dataset) a GEPA optimalizációhoz
# Generált Story → KB Article párok, amelyek a te Integration Team Template sablonod (KBA1-KBA11) struktúráját követik.
# Minden példa tartalmazza a Story szövegét és a várt KB cikket.

---

## Példa 1: Inbound Integráció (Jira Webhook)

### Story
```json
{
  "number": "STRY0010001",
  "short_description": "[Interface Mgmt]: Implement Inbound Webhook for Jira Issue creation in SNOW",
  "description": "Implemented an inbound integration to receive Jira webhooks and create corresponding Incidents in ServiceNow. When a Jira issue is created, the webhook posts to a Scripted REST API in ServiceNow, which parses the JSON payload and creates a new Incident with the Jira issue key mapped to a custom field.",
  "acceptance_criteria": "1. A Scripted REST API endpoint (/api/x_jira/webhook) accepts POST requests from Jira.\n2. The payload includes jira_key, summary, description, and priority.\n3. A new Incident is created in ServiceNow with u_jira_key populated.\n4. Authentication uses Basic Auth credentials validated via a Script Include.",
  "u_technical_specification": "1. Created a Scripted REST API (Scripted REST API: JiraInboundWebhook) with HTTP Method POST.\n2. Configured a Script Include (JiraInboundUtils) to parse JSON and map fields.\n3. Implemented Basic Auth validation using a custom credential record.\n4. Mapped jira_key to u_jira_key on the incident table.",
  "work_notes": "2024-07-16 10:00: Dev - Created Scripted REST API endpoint.\n2024-07-16 12:00: Dev - Tested with Postman, 200 OK received.\n2024-07-16 14:30: Dev - Implemented Basic Auth validation.",
  "comments": "2024-07-16 15:00: QA - Verified Incident creation with correct u_jira_key mapping.",
  "state": "Closed Complete",
  "assigned_to": "Jane Dev",
  "assignment_group": "Integration Team"
}
```

### Várt KB Cikk (Gold Article)
```html
<h1>Inbound Jira Webhook Integration</h1>
<h2>Overview / Summary</h2>
<h3>Purpose / Background / Overview</h3>
<p>This document outlines the inbound integration between Jira and ServiceNow. When a new issue is created in Jira, a webhook automatically sends the issue details to a Scripted REST API in ServiceNow, which parses the data and creates a corresponding Incident record.</p>
<h3>Content</h3>
<ul>
    <li>What the interface is: An inbound webhook listener in ServiceNow that receives Jira issue creation events.</li>
    <li>Who uses it: Support teams and Jira administrators who need to track Jira issues as ServiceNow Incidents.</li>
    <li>What type of data is exchanged: Jira issue details (key, summary, description, priority) mapped to Incident fields.</li>
    <li>High-level process flow: Jira issue created → Jira webhook sends POST → ServiceNow Scripted REST API parses payload → Incident created with Jira key mapped.</li>
    <li>Table of related KB articles, including:
        <ul>
            <li>Short description: Jira Cloud Outbound Integration</li>
            <li>Article number: KBXXXXXXX</li>
        </ul>
    </li>
</ul>
<hr />
<h2>Inbound Technical Implementation</h2>
<h3>Content</h3>
<ul>
    <li>Script Includes and their functions: JiraInboundUtils (parses JSON, validates credentials, maps fields to Incident).</li>
    <li>Scripted REST APIs and endpoints: /api/x_jira/webhook (POST method).</li>
    <li>Required parameters: jira_key (string), summary (string), description (string), priority (string).</li>
    <li>Payload sample: {"jira_key": "PROJ-123", "summary": "Fix login bug", "description": "Users cannot log in", "priority": "High"}.</li>
    <li>Flow and its steps: 1. Jira webhook sends POST → 2. Scripted REST API receives payload → 3. Script Include parses JSON → 4. Incident created → 5. u_jira_key populated.</li>
    <li>Validation steps: 1. Send test POST from Postman → 2. Verify Incident created in ServiceNow → 3. Check u_jira_key matches Jira key.</li>
</ul>
<hr />
<h2>Outbound Technical Implementation</h2>
<h3>Content</h3>
<ul>
    <li>Technical components used: N/A (This is an inbound integration; no outbound ServiceNow message is sent in this flow).</li>
    <li>Dependencies between records or functions: N/A</li>
    <li>Authentication method: N/A</li>
    <li>Validation steps: N/A</li>
</ul>
<hr />
<h2>How to Use the Interface</h2>
<h3>Content</h3>
<ul>
    <li>Typical usage scenarios: A Jira issue is created and needs to be tracked as a ServiceNow Incident.</li>
    <li>Step-by-step instructions: 1. Ensure Jira webhook is configured to point to the ServiceNow endpoint. 2. Create a Jira issue. 3. Verify a new Incident appears in ServiceNow with the Jira key populated.</li>
    <li>Expected results: A new Incident is created in ServiceNow with u_jira_key set to the Jira issue key.</li>
</ul>
<hr />
<h2>Testing Guide</h2>
<h3>Content</h3>
<ul>
    <li>Test scenarios: Validate end-to-end flow of Jira issue creation to ServiceNow Incident creation.</li>
    <li>Test data: A test Jira issue (e.g., PROJ-TEST-1).</li>
    <li>Step-by-step testing instructions: 1. Configure Jira webhook to send to ServiceNow endpoint. 2. Create a test issue in Jira. 3. Check ServiceNow for the new Incident. 4. Verify u_jira_key is populated.</li>
    <li>Expected results: Incident created successfully with correct Jira key mapping.</li>
    <li>Where to check logs: ServiceNow System Logs (syslog) for inbound API errors.</li>
</ul>
<hr />
<h2>Known Issues</h2>
<h3>Content</h3>
<ul>
    <li>Symptoms: Incident not created or u_jira_key is empty.</li>
    <li>Root causes: Invalid Basic Auth credentials, malformed JSON payload, or Script Include errors.</li>
    <li>Diagnostic steps: 1. Check ServiceNow System Logs for "JiraInboundUtils" errors. 2. Verify credentials record is active. 3. Test payload structure in Postman.</li>
    <li>Resolution / Workaround: Re-authenticate Jira webhook or fix Script Include parsing logic.</li>
    <li>Prevention: Regularly test the webhook endpoint and monitor credential expiry.</li>
</ul>
<hr />
<h2>Investigation Steps</h2>
<h3>Content</h3>
<ul>
    <li>Quick, structured troubleshooting guide
        <ul>
            <li>When to use this guide: If Incidents are not being created from Jira issues.</li>
            <li>Step-by-step investigation flow: 1. Check if the Jira webhook is firing (Jira logs). 2. Check ServiceNow System Logs for inbound API errors. 3. Verify Basic Auth credentials are valid. 4. Test the endpoint manually with Postman.</li>
            <li>Where to check logs: ServiceNow System Logs, Jira Webhook logs.</li>
            <li>Key components: JiraInboundUtils Script Include, Scripted REST API endpoint, Basic Auth credential record.</li>
            <li>Escalation guide: Escalate to integration developers if credentials are valid but API returns 500 errors.</li>
        </ul>
    </li>
</ul>
```

---

## Példa 2: Outbound Integráció (Jira REST API)

### Story
```json
{
  "number": "STRY0010002",
  "short_description": "[Interface Mgmt]: Implement Outbound REST API for Jira Bug creation from SNOW Incident",
  "description": "Implemented an outbound REST integration to automatically push ServiceNow Incidents to Jira Cloud when escalated. This integration pushes incident details via REST API and writes the returned Jira Issue Key back to the Incident.",
  "acceptance_criteria": "1. When an Incident state changes to 'Escalated', a Business Rule triggers the outbound payload.\n2. The payload includes number, short_description, description, and assignment_group.\n3. Authentication uses Basic Auth with an API Token stored in ServiceNow Credentials table.\n4. The returned Jira Issue Key is written to the Incident's u_jira_key field.",
  "u_technical_specification": "1. Used the ServiceNow RESTMessageV2 (Outbound) to POST to https://yourcompany.atlassian.net/rest/api/2/issue.\n2. Set HTTP Headers: 'Content-Type': 'application/json', 'Authorization': 'Basic <base64_token>'.\n3. Built JSON payload dynamically in a Script Include (JiraIntegrationUtils) using JSON.stringify.\n4. Configured a Business Rule (After Update) on incident table to check for state change to 'Escalated' (state=6) and call the Script Include.\n5. Parsed the HTTP response to extract the Jira 'key' (e.g., PROJ-123) and wrote it back to the Incident.",
  "work_notes": "2024-07-16 09:00: Dev - Created credentials in the ServiceNow Basic Auth configuration.\n2024-07-16 11:30: Dev - Wrote the Script Include (JiraIntegrationUtils) and tested the POST request via REST Explorer. 200 OK received.\n2024-07-16 14:00: Dev - Implemented the Business Rule and verified it works when the state changes.",
  "comments": "2024-07-16 16:00: QA - Verified payload structure matches Jira requirements. Jira Issue Key successfully written back to SNOW.",
  "state": "Closed Complete",
  "assigned_to": "Jane Dev",
  "assignment_group": "Integration Team"
}
```

### Várt KB Cikk (Gold Article)
```html
<h1>Outbound Jira REST API Integration</h1>
<h2>Overview / Summary</h2>
<h3>Purpose / Background / Overview</h3>
<p>This document outlines the outbound integration between ServiceNow and Jira Cloud. When a ServiceNow Incident is escalated, the integration automatically pushes the incident details to Jira to create a linked Bug, ensuring seamless tracking across platforms.</p>
<h3>Content</h3>
<ul>
    <li>What the interface is: An outbound REST API integration from ServiceNow to Jira Cloud.</li>
    <li>Who uses it: Support engineers and system administrators who escalate Incidents to Jira.</li>
    <li>What type of data is exchanged: Incident details including number, short_description, description, and assignment_group.</li>
    <li>High-level process flow: Incident state changes to 'Escalated' → Business Rule triggers → Script Include builds payload and sends to Jira → Jira returns issue key → Key saved to Incident.</li>
    <li>Table of related KB articles, including:
        <ul>
            <li>Short description: Jira Webhook Inbound Integration</li>
            <li>Article number: KBXXXXXXX</li>
        </ul>
    </li>
</ul>
<hr />
<h2>Inbound Technical Implementation</h2>
<h3>Content</h3>
<ul>
    <li>Script Includes and their functions: N/A (This is an outbound integration; no inbound scripted REST API is defined for this specific flow).</li>
    <li>Scripted REST APIs and endpoints: N/A</li>
    <li>Required parameters: N/A</li>
    <li>Payload sample: N/A</li>
    <li>Flow and its steps: N/A</li>
    <li>Validation steps: N/A</li>
</ul>
<hr />
<h2>Outbound Technical Implementation</h2>
<h3>Content</h3>
<ul>
    <li>Technical components used: JiraIntegrationUtils Script Include (builds JSON payload, sends REST request, parses response).</li>
    <li>Dependencies between records or functions: Incident state changed to 'Escalated' (state=6), Jira API Token credential record.</li>
    <li>Authentication method: Basic Auth using base64-encoded email:token.</li>
    <li>Validation steps: 1. Escalate test incident → 2. Verify payload sent to https://yourcompany.atlassian.net/rest/api/2/issue → 3. Verify Bug created in Jira → 4. Verify u_jira_key populated on Incident.</li>
</ul>
<hr />
<h2>How to Use the Interface</h2>
<h3>Content</h3>
<ul>
    <li>Typical usage scenarios: Escalating an Incident to a Jira Bug.</li>
    <li>Step-by-step instructions: 1. Open the Incident record. 2. Change the state to 'Escalated' (state=6). 3. Save the record. The integration automatically sends the payload to Jira.</li>
    <li>Expected results: A Bug is created in Jira, and the Jira Issue Key is written to the Incident's u_jira_key field.</li>
</ul>
<hr />
<h2>Testing Guide</h2>
<h3>Content</h3>
<ul>
    <li>Test scenarios: Validate end-to-end flow of incident escalation to Jira Bug creation.</li>
    <li>Test data: A test Incident record.</li>
    <li>Step-by-step testing instructions: 1. Open test Incident → 2. Change state to Escalated (6) → 3. Save. 4. Check Jira for the new Bug. 5. Verify u_jira_key is populated on the Incident.</li>
    <li>Expected results: Jira Bug created successfully, and Jira key written back to the Incident.</li>
    <li>Where to check logs: ServiceNow System Logs (syslog) for RESTMessageV2 errors, Jira instance for Bug creation.</li>
</ul>
<hr />
<h2>Known Issues</h2>
<h3>Content</h3>
<ul>
    <li>Symptoms: Jira Key not updated on Incident, or Bug not created in Jira.</li>
    <li>Root causes: Invalid Jira credentials, network connectivity issues, or Jira API rate limits.</li>
    <li>Diagnostic steps: 1. Check ServiceNow System Logs for "JiraIntegrationUtils" errors. 2. Verify credentials in ServiceNow Credentials table. 3. Test REST API manually with Postman.</li>
    <li>Resolution / Workaround: Re-authenticate Jira API token or fix Script Include payload structure.</li>
    <li>Prevention: Regularly test the REST endpoint and monitor Jira API token expiry.</li>
</ul>
<hr />
<h2>Investigation Steps</h2>
<h3>Content</h3>
<ul>
    <li>Quick, structured troubleshooting guide
        <ul>
            <li>When to use this guide: If Jira Bugs are not created or keys are not written back.</li>
            <li>Step-by-step investigation flow: 1. Check if Incident state was changed to Escalated. 2. Check ServiceNow System Logs for RESTMessageV2 errors. 3. Verify Jira credentials are valid. 4. Test the REST API endpoint manually.</li>
            <li>Where to check logs: ServiceNow System Logs, Jira API logs.</li>
            <li>Key components: JiraIntegrationUtils Script Include, Business Rule on incident table, Jira API Token credential record.</li>
            <li>Escalation guide: Escalate to integration developers if credentials are valid but REST call fails.</li>
        </ul>
    </li>
</ul>
```

---

## Példa 3: LDAP Hitelesítési Hiba

### Story
```json
{
  "number": "STRY0010003",
  "short_description": "[Portal]: Fix intermittent LDAP authentication failures during SSO login",
  "description": "Implemented a fix for intermittent LDAP authentication failures on the Service Portal. Users were experiencing 'User Not Found' errors when logging in via SSO due to LDAP query timeouts under heavy load. A retry mechanism was added to the LDAP connection logic.",
  "acceptance_criteria": "1. LDAP connection retry logic is implemented (max 3 attempts with 500ms delay).\n2. A friendly error message is shown if the LDAP server is unreachable after retries.\n3. No high-priority incidents are created for transient LDAP failures.",
  "u_technical_specification": "1. Modified the standard LDAP Server record configuration to increase the 'Connection Timeout' from 5s to 15s.\n2. Created a custom Script Include 'LDAP_Retry_Authenticator' using the GlideLDAP API.\n3. The script uses a 'do-while' loop to attempt the LDAP search up to 3 times with a 500ms delay between attempts.\n4. Added an Email Alert rule triggered by a scheduled job checking the 'ldap_connection_status' metric every 10 minutes.",
  "work_notes": "2024-07-16 10:00: Dev - Increased timeout on the production LDAP server record.\n2024-07-16 14:00: Dev - Wrote the LDAP_Retry_Authenticator Script Include and tested the loop logic.\n2024-07-17 09:30: Dev - Disabled the standard event rule that auto-created Incidents for login failures.",
  "comments": "2024-07-17 15:00: QA - Tested with 50 mock users. 0 false negatives. The friendly message works perfectly.",
  "state": "Closed Complete",
  "assigned_to": "Jane Dev",
  "assignment_group": "Integration Team"
}
```

### Várt KB Cikk (Gold Article)
```html
<h1>LDAP Authentication Retry Fix for Service Portal</h1>
<h2>Overview / Summary</h2>
<h3>Purpose / Background / Overview</h3>
<p>This document describes the fix for intermittent LDAP authentication failures on the Service Portal. Users experienced 'User Not Found' errors during SSO login due to LDAP query timeouts under heavy load. A retry mechanism was added to the LDAP connection logic to improve reliability.</p>
<h3>Content</h3>
<ul>
    <li>What the interface is: An enhanced LDAP authentication module for the Service Portal with retry logic.</li>
    <li>Who uses it: End users logging in via SSO, and IT support teams managing authentication issues.</li>
    <li>What type of data is exchanged: LDAP query results (user DN, groups, attributes) and authentication status codes.</li>
    <li>High-level process flow: User attempts SSO login → LDAP query initiated → If timeout occurs, retry up to 3 times with 500ms delay → If still fails, show friendly error message → If succeeds, user logged in.</li>
    <li>Table of related KB articles, including:
        <ul>
            <li>Short description: SSO Configuration Guide</li>
            <li>Article number: KBXXXXXXX</li>
        </ul>
    </li>
</ul>
<hr />
<h2>Inbound Technical Implementation</h2>
<h3>Content</h3>
<ul>
    <li>Script Includes and their functions: LDAP_Retry_Authenticator (handles LDAP connection retries, error handling, and logging).</li>
    <li>Scripted REST APIs and endpoints: N/A (This is a backend authentication module, not a REST API).</li>
    <li>Required parameters: LDAP server URL, bind DN, credentials, search base.</li>
    <li>Payload sample: N/A (Internal authentication flow, not a REST payload).</li>
    <li>Flow and its steps: 1. User attempts SSO login → 2. LDAP query initiated → 3. If timeout, retry up to 3 times with 500ms delay → 4. If still fails, show friendly error message → 5. If succeeds, user logged in.</li>
    <li>Validation steps: 1. Test SSO login with valid credentials → 2. Verify no 'User Not Found' errors occur. 3. Check System Logs for retry attempts.</li>
</ul>
<hr />
<h2>Outbound Technical Implementation</h2>
<h3>Content</h3>
<ul>
    <li>Technical components used: N/A (This is an inbound authentication module; no outbound ServiceNow message is sent in this flow).</li>
    <li>Dependencies between records or functions: N/A</li>
    <li>Authentication method: N/A</li>
    <li>Validation steps: N/A</li>
</ul>
<hr />
<h2>How to Use the Interface</h2>
<h3>Content</h3>
<ul>
    <li>Typical usage scenarios: Users logging into the Service Portal via SSO.</li>
    <li>Step-by-step instructions: 1. Open the Service Portal login page. 2. Enter SSO credentials. 3. If LDAP server is slow, the system automatically retries. 4. If retries succeed, user is logged in. If not, a friendly error message is shown.</li>
    <li>Expected results: Successful login without 'User Not Found' errors, even under heavy load.</li>
</ul>
<hr />
<h2>Testing Guide</h2>
<h3>Content</h3>
<ul>
    <li>Test scenarios: Validate LDAP retry logic under simulated heavy load.</li>
    <li>Test data: 50 mock user accounts with valid credentials.</li>
    <li>Step-by-step testing instructions: 1. Open Service Portal login page. 2. Attempt SSO login with valid credentials. 3. Simulate LDAP server delay (e.g., using a proxy). 4. Verify the system retries and eventually succeeds. 5. Check System Logs for retry attempts.</li>
    <li>Expected results: No 'User Not Found' errors occur, and users are logged in successfully after retries.</li>
    <li>Where to check logs: ServiceNow System Logs (syslog) for LDAP_Retry_Authenticator messages.</li>
</ul>
<hr />
<h2>Known Issues</h2>
<h3>Content</h3>
<ul>
    <li>Symptoms: Users still see 'User Not Found' errors despite the retry logic.</li>
    <li>Root causes: LDAP server completely down, invalid bind credentials, or network firewall blocking LDAP port.</li>
    <li>Diagnostic steps: 1. Check ServiceNow System Logs for LDAP_Retry_Authenticator errors. 2. Verify LDAP server is reachable (ping/telnet). 3. Check bind credentials in ServiceNow LDAP Server record.</li>
    <li>Resolution / Workaround: Restart LDAP server or fix bind credentials. If network firewall blocks LDAP, add an exception.</li>
    <li>Prevention: Regularly monitor LDAP server health and credential expiry.</li>
</ul>
<hr />
<h2>Investigation Steps</h2>
<h3>Content</h3>
<ul>
    <li>Quick, structured troubleshooting guide
        <ul>
            <li>When to use this guide: If users report 'User Not Found' errors during SSO login.</li>
            <li>Step-by-step investigation flow: 1. Check if the LDAP server is reachable. 2. Check ServiceNow System Logs for LDAP_Retry_Authenticator errors. 3. Verify bind credentials are valid. 4. Test LDAP query manually.</li>
            <li>Where to check logs: ServiceNow System Logs, LDAP server logs.</li>
            <li>Key components: LDAP_Retry_Authenticator Script Include, LDAP Server record, SSO configuration.</li>
            <li>Escalation guide: Escalate to infrastructure team if LDAP server is down or network issues persist.</li>
        </ul>
    </li>
</ul>
```

---

## Példa 4: SAP IDOC Hiba Kezelés

### Story
```json
{
  "number": "STRY0010004",
  "short_description": "[SAP Integration]: Resolve IDOC status 51 failures for Vendor Invoice creation",
  "description": "Implemented a fix for SAP IDOC status 51 failures during Vendor Invoice (MIR4) creation. The middleware (PI/PO) now sends a callback to ServiceNow with the exact IDOC error message, allowing the finance team to identify and resolve tax code mismatches or missing purchase order references automatically.",
  "acceptance_criteria": "1. When SAP returns a status 51 error, the middleware sends a callback to ServiceNow with the exact IDOC error message.\n2. The ServiceNow Incident or custom 'Invoice Status' record is automatically updated with the IDOC failure reason.\n3. An automated notification is sent to the finance group (SAP_Finance_Team) alerting them of the failure.\n4. A 'Retry' UI action is made available on the form to re-trigger the IDOC.",
  "u_technical_specification": "1. Configured SAP PI/PO to send a REST Outbound message (HTTP POST) to ServiceNow's custom Scripted REST API: /api/x_sap/invoice/idoc_status.\n2. The ServiceNow Scripted REST API parses the JSON payload, specifically extracting the IDOC number, MIR4 transaction ID, and the exact status 51 error text (e.g., 'Tax code I2 does not exist').\n3. Implemented a Business Rule on the 'u_invoice_tracker' table that triggers a workflow.\n4. The workflow sends an event to the notification engine sysevent for the SAP_Finance_Team group.\n5. Created a UI Policy to make the 'IDOC Error Reason' field read-only and red, so finance cannot overwrite it during manual fixes.",
  "work_notes": "2024-03-12 09:00: Dev - Installed the SAP Rest API plugin.\n2024-03-12 11:00: Dev - Tested Scripted REST API with SAP PI/PO team. Payload is accepted successfully.\n2024-03-12 14:30: Dev - Configured the sysevent for the notification email.",
  "comments": "2024-03-13 09:00: SAP Admin - Validated the test failure with Finance. The system caught the Tax code error perfectly. Ready for production.",
  "state": "Closed Complete",
  "assigned_to": "Jane Dev",
  "assignment_group": "Integration Team"
}
```

### Várt KB Cikk (Gold Article)
```html
<h1>SAP IDOC Status 51 Error Handling for Vendor Invoices</h1>
<h2>Overview / Summary</h2>
<h3>Purpose / Background / Overview</h3>
<p>This document describes the fix for SAP IDOC status 51 failures during Vendor Invoice (MIR4) creation. The middleware (PI/PO) now sends a callback to ServiceNow with the exact IDOC error message, allowing the finance team to identify and resolve tax code mismatches or missing purchase order references automatically.</p>
<h3>Content</h3>
<ul>
    <li>What the interface is: An error handling and notification system for SAP IDOC status 51 failures in ServiceNow.</li>
    <li>Who uses it: Finance teams (SAP_Finance_Team) and SAP administrators who process vendor invoices.</li>
    <li>What type of data is exchanged: IDOC number, MIR4 transaction ID, exact status 51 error text (e.g., 'Tax code I2 does not exist'), and notification events.</li>
    <li>High-level process flow: SAP PI/PO sends IDOC status 51 callback → ServiceNow Scripted REST API parses payload → Incident/Invoice Status updated with error reason → Notification sent to SAP_Finance_Team → Finance team reviews and fixes the issue → 'Retry' UI action re-triggers the IDOC.</li>
    <li>Table of related KB articles, including:
        <ul>
            <li>Short description: SAP Vendor Invoice Processing Guide</li>
            <li>Article number: KBXXXXXXX</li>
        </ul>
    </li>
</ul>
<hr />
<h2>Inbound Technical Implementation</h2>
<h3>Content</h3>
<ul>
    <li>Script Includes and their functions: N/A (This is an outbound integration; no inbound scripted REST API is defined for this specific flow).</li>
    <li>Scripted REST APIs and endpoints: N/A</li>
    <li>Required parameters: N/A</li>
    <li>Payload sample: N/A</li>
    <li>Flow and its steps: N/A</li>
    <li>Validation steps: N/A</li>
</ul>
<hr />
<h2>Outbound Technical Implementation</h2>
<h3>Content</h3>
<ul>
    <li>Technical components used: SAP PI/PO (sends REST Outbound message), ServiceNow Scripted REST API (/api/x_sap/invoice/idoc_status), ServiceNow Business Rule on 'u_invoice_tracker' table, Notification engine (sysevent).</li>
    <li>Dependencies between records or functions: SAP PI/PO sends callback to ServiceNow, ServiceNow Scripted REST API parses payload and updates record, Business Rule triggers notification.</li>
    <li>Authentication method: N/A (Internal system-to-system communication via REST API).</li>
    <li>Validation steps: 1. Simulate an IDOC status 51 error in SAP → 2. Verify callback is sent to ServiceNow → 3. Verify Incident/Invoice Status is updated with error reason → 4. Verify notification is sent to SAP_Finance_Team.</li>
</ul>
<hr />
<h2>How to Use the Interface</h2>
<h3>Content</h3>
<ul>
    <li>Typical usage scenarios: A vendor invoice fails to post in SAP due to a tax code mismatch, and the finance team needs to be notified to fix it.</li>
    <li>Step-by-step instructions: 1. When an IDOC status 51 error occurs, the middleware sends a callback to ServiceNow. 2. The Incident/Invoice Status record is automatically updated with the error reason. 3. A notification is sent to SAP_Finance_Team. 4. The finance team reviews the error and fixes the issue in SAP. 5. The 'Retry' UI action is used to re-trigger the IDOC.</li>
    <li>Expected results: Finance team is notified of the error, and the issue is resolved without manual checking of middleware logs.</li>
</ul>
<hr />
<h2>Testing Guide</h2>
<h3>Content</h3>
<ul>
    <li>Test scenarios: Validate end-to-end flow of IDOC status 51 error handling and notification.</li>
    <li>Test data: A test IDOC with status 51 error (e.g., 'Tax code I2 does not exist').</li>
    <li>Step-by-step testing instructions: 1. Simulate an IDOC status 51 error in SAP PI/PO. 2. Verify callback is sent to ServiceNow. 3. Check Incident/Invoice Status record is updated with error reason. 4. Check notification is sent to SAP_Finance_Team. 5. Verify 'Retry' UI action is available.</li>
    <li>Expected results: Incident/Invoice Status updated with error reason, notification sent to SAP_Finance_Team, and 'Retry' UI action available.</li>
    <li>Where to check logs: ServiceNow System Logs (syslog) for Scripted REST API errors, SAP PI/PO logs for callback errors.</li>
</ul>
<hr />
<h2>Known Issues</h2>
<h3>Content</h3>
<ul>
    <li>Symptoms: Incident/Invoice Status not updated with error reason, or notification not sent to SAP_Finance_Team.</li>
    <li>Root causes: Scripted REST API error, Business Rule not triggering, or notification engine (sysevent) misconfiguration.</li>
    <li>Diagnostic steps: 1. Check ServiceNow System Logs for Scripted REST API errors. 2. Verify Business Rule on 'u_invoice_tracker' table is active. 3. Check notification engine (sysevent) configuration for SAP_Finance_Team group.</li>
    <li>Resolution / Workaround: Fix Scripted REST API parsing logic, reactivate Business Rule, or reconfigure notification engine.</li>
    <li>Prevention: Regularly test the callback endpoint and monitor notification delivery.</li>
</ul>
<hr />
<h2>Investigation Steps</h2>
<h3>Content</h3>
<ul>
    <li>Quick, structured troubleshooting guide
        <ul>
            <li>When to use this guide: If IDOC status 51 errors are not being captured or notified correctly.</li>
            <li>Step-by-step investigation flow: 1. Check if the callback from SAP PI/PO is reaching ServiceNow (check SAP PI/PO logs). 2. Check ServiceNow System Logs for Scripted REST API errors. 3. Verify Business Rule on 'u_invoice_tracker' table is triggering. 4. Check notification engine (sysevent) configuration.</li>
            <li>Where to check logs: ServiceNow System Logs, SAP PI/PO logs.</li>
            <li>Key components: SAP PI/PO, ServiceNow Scripted REST API, Business Rule on 'u_invoice_tracker' table, Notification engine (sysevent).</li>
            <li>Escalation guide: Escalate to integration developers if callback is not reaching ServiceNow or Scripted REST API returns errors.</li>
        </ul>
    </li>
</ul>
```

---

## Példa 5: SolMan Adatinkonzisztencia

### Story
```json
{
  "number": "STRY0010005",
  "short_description": "[SolMan]: Fix data inconsistencies between ServiceNow and SolMan for Change Tasks",
  "description": "Implemented a fix for data inconsistencies between ServiceNow Change Tasks (CTASKs) and SolMan Change Documents (CDs). CTASKs were not automatically closing when their corresponding SolMan CDs reached terminal states ('Confirmed' or 'Withdrawn'). A Business Rule and a Fix Script were implemented to synchronize the states and close orphaned CTASKs.",
  "acceptance_criteria": "1. When a SolMan CD state changes to 'Confirmed' or 'Withdrawn', the corresponding CTASK is automatically closed (state=3).\n2. A Fix Script reconciles historical CTASKs that were stuck open due to this gap.\n3. A log output is generated to validate the count and correctness of updated records.",
  "u_technical_specification": "1. Reviewed the Business Rule named 'SolMan: Sync CD State to CTASK Closure Readiness' on the change_task table. Confirmed it is configured to run Before update with the condition u_cd_state.changesTo() == true.\n2. Verified the Business Rule logic: when a CTASK's u_cd_state changes to 'Confirmed' or 'Withdrawn', the script queries all sibling CTASKs linked to the same parent CHG and auto-closes them (state=3) only if every sibling CTASK has a terminal CD state.\n3. In a non-production environment, executed the Fix Script named 'SolMan: Fix CD State Inconsistencies' as a one-time Scheduled Script Execution.\n4. Confirmed the Fix Script queries all CTASKs where u_cd_state IN ('Confirmed', 'Withdrawn') AND state != 3, verifies the parent CHG has no active CTASKs with non-terminal CD states, and updates qualifying CTASKs to state=3.\n5. Reviewed the log output in non-prod to validate the count and correctness of updated records before proceeding.",
  "work_notes": "2024-07-16 10:00: Dev - Reproduced locally with test IDP instance.\n2024-07-16 14:00: Dev - Identified hardcoded TTL in auth/middleware.py line 142.\n2024-07-16 16:00: Dev - Patched to v2.3, added env var support.\n2024-07-16 11:00: Dev - Deployed to staging, verified login works.",
  "comments": "2024-07-16 12:00: QA Team - Confirmed resolved in staging environment. Running full regression.\n2024-07-16 15:00: QA Team - All regression tests passed. Ready for production.",
  "state": "Closed Complete",
  "assigned_to": "Jane Dev",
  "assignment_group": "Integration Team"
}
```

### Várt KB Cikk (Gold Article)
```html
<h1>SolMan Change Task State Synchronization Fix</h1>
<h2>Overview / Summary</h2>
<h3>Purpose / Background / Overview</h3>
<p>This document describes the fix for data inconsistencies between ServiceNow Change Tasks (CTASKs) and SolMan Change Documents (CDs). CTASKs were not automatically closing when their corresponding SolMan CDs reached terminal states ('Confirmed' or 'Withdrawn'). A Business Rule and a Fix Script were implemented to synchronize the states and close orphaned CTASKs.</p>
<h3>Content</h3>
<ul>
    <li>What the interface is: A state synchronization mechanism between ServiceNow Change Tasks and SolMan Change Documents.</li>
    <li>Who uses it: Change Managers, Change Coordinators, and IT support teams managing Change Tasks in ServiceNow.</li>
    <li>What type of data is exchanged: SolMan CD states ('Confirmed', 'Withdrawn'), CTASK states (1=New, 2=Open, 3=Closed), and synchronization logs.</li>
    <li>High-level process flow: SolMan CD state changes to 'Confirmed' or 'Withdrawn' → Business Rule triggers → Script queries all sibling CTASKs → If all sibling CTASKs have terminal CD states, they are auto-closed (state=3) → Fix Script reconciles historical orphaned CTASKs → Log output generated to validate updates.</li>
    <li>Table of related KB articles, including:
        <ul>
            <li>Short description: ServiceNow Change Management Guide</li>
            <li>Article number: KBXXXXXXX</li>
        </ul>
    </li>
</ul>
<hr />
<h2>Inbound Technical Implementation</h2>
<h3>Content</h3>
<ul>
    <li>Script Includes and their functions: N/A (This is an outbound integration; no inbound scripted REST API is defined for this specific flow).</li>
    <li>Scripted REST APIs and endpoints: N/A</li>
    <li>Required parameters: N/A</li>
    <li>Payload sample: N/A</li>
    <li>Flow and its steps: N/A</li>
    <li>Validation steps: N/A</li>
</ul>
<hr />
<h2>Outbound Technical Implementation</h2>
<h3>Content</h3>
<ul>
    <li>Technical components used: Business Rule 'SolMan: Sync CD State to CTASK Closure Readiness' on the change_task table, Fix Script 'SolMan: Fix CD State Inconsistencies' as a one-time Scheduled Script Execution.</li>
    <li>Dependencies between records or functions: Business Rule runs Before update with the condition u_cd_state.changesTo() == true. Script queries all sibling CTASKs linked to the same parent CHG and auto-closes them (state=3) only if every sibling CTASK has a terminal CD state.</li>
    <li>Authentication method: N/A (Internal system-to-system communication via database).</li>
    <li>Validation steps: 1. In a non-production environment, execute the Fix Script. 2. Confirm the Fix Script queries all CTASKs where u_cd_state IN ('Confirmed', 'Withdrawn') AND state != 3. 3. Verify the parent CHG has no active CTASKs with non-terminal CD states. 4. Review the log output to validate the count and correctness of updated records.</li>
</ul>
<hr />
<h2>How to Use the Interface</h2>
<h3>Content</h3>
<ul>
    <li>Typical usage scenarios: A Change Document (CD) in SolMan reaches a terminal state ('Confirmed' or 'Withdrawn'), and the corresponding Change Task (CTASK) in ServiceNow needs to be closed automatically.</li>
    <li>Step-by-step instructions: 1. When a SolMan CD state changes to 'Confirmed' or 'Withdrawn', the Business Rule triggers automatically. 2. The script queries all sibling CTASKs linked to the same parent CHG. 3. If all sibling CTASKs have terminal CD states, they are auto-closed (state=3). 4. If orphaned CTASKs exist from before the fix, the Fix Script reconciles them.</li>
    <li>Expected results: CTASKs are automatically closed when their corresponding SolMan CDs reach terminal states, and orphaned CTASKs are reconciled by the Fix Script.</li>
</ul>
<hr />
<h2>Testing Guide</h2>
<h3>Content</h3>
<ul>
    <li>Test scenarios: Validate end-to-end flow of SolMan CD state change to CTASK closure, and Fix Script reconciliation of historical orphaned CTASKs.</li>
    <li>Test data: A test Change Request (CHG) with associated Change Tasks (CTASKs) and SolMan Change Documents (CDs).</li>
    <li>Step-by-step testing instructions: 1. In a non-production environment, execute the Fix Script 'SolMan: Fix CD State Inconsistencies' as a one-time Scheduled Script Execution. 2. Confirm the Fix Script queries all CTASKs where u_cd_state IN ('Confirmed', 'Withdrawn') AND state != 3. 3. Verify the parent CHG has no active CTASKs with non-terminal CD states. 4. Review the log output to validate the count and correctness of updated records. 5. Test the Business Rule by changing a SolMan CD state to 'Confirmed' or 'Withdrawn' and verifying the corresponding CTASK is closed.</li>
    <li>Expected results: CTASKs are automatically closed when their corresponding SolMan CDs reach terminal states, and orphaned CTASKs are reconciled by the Fix Script.</li>
    <li>Where to check logs: ServiceNow System Logs (syslog) for Business Rule and Fix Script execution logs.</li>
</ul>
<hr />
<h2>Known Issues</h2>
<h3>Content</h3>
<ul>
    <li>Symptoms: CTASKs are not closing when their corresponding SolMan CDs reach terminal states, or orphaned CTASKs are not being reconciled by the Fix Script.</li>
    <li>Root causes: Business Rule not triggering, Business Rule logic error, Fix Script not querying the correct CTASKs, or parent CHG has active CTASKs with non-terminal CD states.</li>
    <li>Diagnostic steps: 1. Check ServiceNow System Logs for Business Rule and Fix Script execution logs. 2. Verify Business Rule on change_task table is active and configured correctly. 3. Check the Business Rule logic to ensure it queries all sibling CTASKs and checks their CD states. 4. Check the Fix Script logic to ensure it queries all CTASKs where u_cd_state IN ('Confirmed', 'Withdrawn') AND state != 3.</li>
    <li>Resolution / Workaround: Reactivate Business Rule, fix Business Rule logic, or fix Fix Script logic. If parent CHG has active CTASKs with non-terminal CD states, close those CTASKs first.</li>
    <li>Prevention: Regularly monitor Business Rule and Fix Script execution logs, and ensure SolMan CD states are correctly synchronized with CTASK states.</li>
</ul>
<hr />
<h2>Investigation Steps</h2>
<h3>Content</h3>
<ul>
    <li>Quick, structured troubleshooting guide
        <ul>
            <li>When to use this guide: If CTASKs are not closing when their corresponding SolMan CDs reach terminal states, or orphaned CTASKs are not being reconciled by the Fix Script.</li>
            <li>Step-by-step investigation flow: 1. Check if the Business Rule on change_task table is triggering (check System Logs). 2. Check if the Business Rule logic is correct (queries all sibling CTASKs and checks their CD states). 3. Check if the Fix Script is querying the correct CTASKs (where u_cd_state IN ('Confirmed', 'Withdrawn') AND state != 3). 4. Check if the parent CHG has active CTASKs with non-terminal CD states.</li>
            <li>Where to check logs: ServiceNow System Logs, SolMan logs.</li>
            <li>Key components: Business Rule 'SolMan: Sync CD State to CTASK Closure Readiness' on the change_task table, Fix Script 'SolMan: Fix CD State Inconsistencies', parent CHG record.</li>
            <li>Escalation guide: Escalate to integration developers if Business Rule or Fix Script logic is incorrect, or if parent CHG has active CTASKs with non-terminal CD states that need to be closed manually.</li>
        </ul>
    </li>
</ul>
```

---

## Összegzés (Gold Dataset Summary)

Ez a 5 arany példapár lefedi a különböző típusú ServiceNow Story-kat és a hozzájuk tartozó KB cikkeket, amelyek a te Integration Team Template sablonod (KBA1-KBA11) struktúráját követik:

1. **Inbound Integráció** (Jira Webhook) - Inbound Technical Implementation fejezet tele van, Outbound N/A
2. **Outbound Integráció** (Jira REST API) - Outbound Technical Implementation fejezet tele van, Inbound N/A
3. **LDAP Hitelesítési Hiba** - Inbound Technical Implementation fejezet tele van (LDAP auth), Outbound N/A
4. **SAP IDOC Hiba** - Outbound Technical Implementation fejezet tele van (SAP callback), Inbound N/A
5. **SolMan Adatinkonzisztencia** - Outbound Technical Implementation fejezet tele van (Business Rule + Fix Script), Inbound N/A

Minden példa tartalmazza a Story szövegét és a várt KB cikket (HTML formátumban), amelyek a te sablonod szerint épülnek fel. Ezeket a példapárokat a GEPA optimalizáció arany standardjaként (gold set) fogja használni a metrika és a reflection modell (Kimi K3) tanulásához.