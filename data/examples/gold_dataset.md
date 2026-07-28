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
    <li>Table of related KB articles: N/A
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
    <li>Table of related KB articles: N/A
    </li>
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
    <li>Table of related KB articles: N/A
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
    <li>Table of related KB articles: N/A
    </li>
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
    <li>Table of related KB articles: N/A
    </li>
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
## Példa 6: SolMan Bidirectional Integration (valódi, prod-minőségű pár)

### Story
```json
{
  "number": "STRY0010014",
  "short_description": "[ServiceNow] ServiceNow <-> SAP SolMan (Conigma) Bidirectional Integration",
  "description": "",
  "acceptance_criteria": "Create Bidirectional Integration between ServiceNow &lt;-&gt; SAP SolMan (Conigma)",
  "u_technical_specification": "Overview \n\r\n\r\n \r\n Table of Contents \n\r\n \n- 1. Executive Summary \n\n- 2. Scope and Objectives \n\n- 3. Record Inventory (as configured) \r\n \n- Script Includes \n\n- Scripted REST API \n\n- REST Message Function (Outbound) \n\n- Flow Actions \n\n- Business Rules (BR) \n\n- Client Script \n\n- Supporting BR (Scratchpad) \n\n\r\n\n- 4. System Properties \n\n- 5. Environment Configuration and Endpoints \n\n- 6. Functional Design \r\n \n- 6.1 SolMan-Managed Change Identification \n\n- 6.2 Outbound Triggers (ServiceNow → SolMan) \n\n- 6.3 Payload Construction \n\n- 6.4 Change Task Closure and CR State Progression \n\n- 6.5 Inbound Change Task Update (SolMan → ServiceNow) \n\n\r\n\n- 7. Data and Field Mapping \r\n \n- 7.1 Outbound Change Task – representative fields \n\n- 7.2 Inbound Change Task – field handling \n\n\r\n\n- 8. Logging \n\n- 9. Security and Access \n\n- 10. Testing and Validation \r\n \n- 10.1 Inbound – Change Task Update \n\n- 10.2 Outbound – Change Request/Task \n\n\r\n\n- 11. Deployment and Configuration Steps \n\n- 12. Troubleshooting \n\n- 13. Governance and Operations \n\n- 14. Appendices \r\n \n- 14.1 Key sys_ids and Names (quick reference) \n\n- 14.2 Message Keys observed \n\n- 14.3 Notes on Legacy RFC Transfer \n\n\r\n\n\r\n\n\r\n \r\n 1. Executive Summary \n\r\n This document describes the current implementation of the 'SolMan' integration between ServiceNow and SAP Solution Manager (via Conigma/PO). It includes: record inventory, environment configuration, properties, data flows (outbound and inbound), field mapping, triggers, logging, security, testing, deployment, and troubleshooting. All concrete values, names, and sys_ids. \n\r\n 2. Scope and Objectives \n\r\n \n- Processes in scope: \r\n \n- Change Request and Change Task synchronization (primary) \n\n- Related reference updates from Incident and Problem to a Change Request (secondary triggers) \n\n\r\n\n- Directions: \r\n \n- Outbound: ServiceNow → SolMan via REST (Conigma endpoint) \n\n- Inbound: SolMan/Conigma → ServiceNow via Scripted REST API (change task update) \n\n\r\n\n- Goal: \r\n \n- Keep the Change lifecycle in sync, transfer key attributes, and reflect technical deployment states (CD) and assignments. \n\n\r\n\n\r\n 3. Record Inventory (as configured) \n\r\n The following records exist and drive the integration: \n\r\n Script Includes \n\r\n \n- ALDISolManChangeInterface (global) \r\n \n- sys_id: d46079041b18c51034b7dceacd4bcb20 \n\n- Purpose: Validations for SolMan Change applicability, payload building (Change Request/Task), inbound handler for Change Task update, user lookups, logging, and Change Request state updates after Change Task closure. \n\n\r\n\n- ALDIIntegrationFrameworkUtil (global) \r\n \n- sys_id: 69b110be1bff3f4034b7dceacd4bcbb6 \n\n- Purpose: Generic framework to evaluate interface trigger conditions, build payloads (including Flow Action–generated payloads), and deliver them to environment-specific REST endpoints; logs all transactions. \n\n\r\n\n- ChangeRequestUIActionHelper (global) \r\n \n- sys_id: ff81f04cdb869b00f546f3d31d961969 \n\n- Note: Integration-related condition prevents showing certain UI actions (e.g., Test) for SolMan-managed Changes. \n\n\r\n\n\r\n Scripted REST API \n\r\n \n- Service: ALDI SolMan \r\n \n- Base URI: /api/aldie/solman \n\n- sys_id: 35e59e481bdcc51034b7dceacd4bcb6c \n\n\r\n\n- Resource: Change Task | Post (POST /change/task ) \r\n \n- Full path: /api/aldie/solman/change/task \n\n- sys_id: 94369acc1bdcc51034b7dceacd4bcb45 \n\n- Enforces ACL: b7b63e761b89499034b7dceacd4bcb6d \n\n- Requires authentication and SNC internal role. \n\n\r\n\n\r\n REST Message Function (Outbound) \n\r\n \n- Conigma PROD ( sys_rest_message_fn ) \r\n \n- Rest Message: ALDI SolMan Interface FrameWork (sys_id: 34714d4c1bd8851034b7dceacd4bcb82 ) \n\n- Function name: Conigma PROD (sys_id: ba25ea721b45499034b7dceacd4bcb9c ) \n\n- Endpoint: https://conigma.prd.aldi-sued.com/${rest_uri} \n\n- Authentication type: inherit_from_parent; Mutual Auth: true \n\n- Protocol: conigma ( ae59d2d61be7381434b7dceacd4bcb5a ) \n\n\r\n\n\r\n Flow Actions \n\r\n \n- Flow Action - ALDI SolMan Get Payload for Change Request \r\n \n- Purpose: Generates payload for Change Request updates by delegating to ALDISolManChangeInterface.getPayloadForChangeRequest(triggerconditiongr, currentgr) . \n\n\r\n\n- Flow Action - ALDI SolMan Get Payload for Change Task \r\n \n- Purpose: Generates payload for Change Task updates by delegating to ALDISolManChangeInterface.getPayloadForChangeTask(triggerconditiongr, currentgr) . \n\n\r\n\n\r\n Business Rules (BR) \n\r\n \n- ALDI Interface SolMan Change Request (after) \r\n \n- Table: change_request , sys_id: bb3096cc1b9cc51034b7dceacd4bcb71 \n\n- Condition: (new global.ALDISolManChangeInterface().isChangeRequestValidToSync(current)) \n\n- Filter: correlation_display=SolMan, state NOT IN (-5,-4,3,4) , u_change_coordinator ISNOTEMPTY , and any of u_change_coordinator/u_demand/priority/u_release value changes; exclude sys_updated_by LIKE interface.solman . \n\n- Action: new ALDIIntegrationFrameworkUtil().triggerInterfaces(current, current.operation()) \n\n\r\n\n- ALDI Interface SolMan Change Task (after) \r\n \n- Table: change_task , sys_id: f6a20a441b1cc51034b7dceacd4bcbf6 \n\n- Filter: parent.correlation_display=SolMan, state = -5 (Pending) , key fields value changes ( short_description , description , business_service , change_request , due_date , u_change_subtype , u_application , u_scope ) or state CHANGESTO -5 ; exclude sys_updated_by LIKE interface.solman . \n\n- Action: new ALDIIntegrationFrameworkUtil().triggerInterfaces(current, current.operation()) \n\n\r\n\n- ALDI Interface SolMan Incident-Change (after) \r\n \n- Table: incident , sys_id: f9de05241b4d415039f811739b4bcb4f \n\n- Filter: rfc value changes. \n\n- Action: If the referenced Change Request is a SolMan interface Change and valid to sync, then triggerInterfaces(change, current.operation()) . Also evaluates previous.rfc for removals. \n\n\r\n\n- ALDI Interface SolMan Problem-Change (after) \r\n \n- Table: u_m2m_problems_change_requests , sys_id: 7b2add201b41815039f811739b4bcb31 \n\n- Filter: u_change_request ISNOTEMPTY \n\n- Action: If the CR is SolMan interface CR and valid to sync, triggerInterfaces(change, 'update') . \n\n\r\n\n- ALDI SolMan async CD or ChTask State upd ( async_always ; order 5555 ) \r\n \n- Table: change_task , sys_id: bf7a55df1b5409d039f811739b4bcbd6 \n\n- Filter: parent.correlation_display=SolMan, u_cd_state value changes or state value changes. \n\n- Action: new ALDISolManChangeInterface().updateChangeRequestOnTaskUpdate(current.getUniqueValue()) \n\n\r\n\n- ALDI SolMan before CD State update (before update) \r\n \n- Table: change_task , sys_id: 71f545931b9009d039f811739b4bcb7d \n\n- Filter: parent.correlation_display=SolMan and u_cd_state CHANGESTO Confirmed OR Withdrawn . \n\n- Note: Dedicated placeholder; final close operation executed in Script Include method (see section 6.4). \n\n\r\n\n- Legacy RFC Transfer (before insert/update; order 1,000,001 ) \r\n \n- Aldi Solman CHG Transfer Normal RFC (sys_id: 744c7fa5db919f001e2cf9c41d9619c7 ) \n\n- Aldi Solman CHG Transfer Emergency RFC (sys_id: eb7c7b69db919f001e2cf9c41d961996 ) \n\n- Aldi Solman CHG Transfer Standard RFC (sys_id: b8b68e21db2d9f401e2cf9c41d9619e4 ) \n\n- These call AldiSoapProcessorSolManChangeInterface (legacy path) and filter on assigned_to = Dummy Change User (3776580adba61704f546f3d31d9619b1) . \n\n\r\n\n\r\n Client Script \n\r\n \n- ALDI SolMan msg when state is open (onLoad; change_task ) \r\n \n- sys_id: 48122f041be4491439f811739b4bcb80 \n\n- Shows info message when state == Open (1) and the parent CR qualifies as a SolMan interface record. \n\n\r\n\n\r\n Supporting BR (Scratchpad) \n\r\n \n- Populate scratchpad with valid states ( before_display ; change_task ) \r\n \n- sys_id: 07898c63dbb2df80f546f3d31d961918 \n\n- Populates g_scratchpad.stateModel , parentChangeState , and isChangeRequestSolManInterface . \n\n\r\n\n\r\n 4. System Properties \n\r\n Property Purpose \n aldi.sap.solman.rest.log.interface.id Interface trigger condition record id used when logging Scripted REST calls in u_aldi_interface_transaction . \n aldi.sap.solman.ticket.data.error.json Default JSON to use for payload.ticketData when Flow Action generation returns a non-success status. \n instance_name Drives environment selection in ALDIIntegrationFrameworkUtil ( aldidev , alditest , aldiqa , aldiprod ). \n \n\r\n 5. Environment Configuration and Endpoints \n\r\n Outbound REST routing is fully data-driven by the interface trigger record (table u_aldi_interface_trigger_condition ): \n\r\n \n- References on trigger condition: \r\n \n- u_base_endpoint_dev/test/qa/prod → Reference to REST Message + Function \n\n- u_endpoint → String appended as ${rest_uri} to the selected base endpoint \n\n\r\n\n- ALDIIntegrationFrameworkUtil.triggerInterface(record, triggerRule, …) \r\n \n- Picks RESTMessageV2 based on gs.getProperty('instance_name') \n\n- Sets String parameter rest_uri to triggerRule.u_endpoint \n\n- Sends JSON payload constructed by generatePayload() \n\n\r\n\n\r\n Production Conigma function (from XML): \n\r\n \n- REST Message: ALDI SolMan Interface FrameWork \n\n- Function: Conigma PROD \n\n- Endpoint: https://conigma.prd.aldi-sued.com/${rest_uri} \n\n- Mutual TLS: true (ensure certificates and profiles are installed and bound to the parent REST Message) \n\n\r\n Inbound Scripted REST: \n\r\n \n- Service: ALDI SolMan ( /api/aldie/solman ) \n\n- Resource: POST /change/task \n\n- ACL enforcement: b7b63e761b89499034b7dceacd4bcb6d \n\n- Requires authentication and SNC internal role \n\n\r\n 6. Functional Design \n\r\n 6.1 SolMan-Managed Change Identification \n\r\n Historically, a Change Request was treated as SolMan-managed if: \n\r\n \n- Assigned to equals gs.getProperty('aldi.sap.solman.change.assigned.to') \n\n- Assignment group equals gs.getProperty('aldi.sap.solman.change.assignment.group') \n\n\r\n The SolMan business rules still reference specific sys_ids for these properties: \n\r\n \n- Group (Trigger_SNow2SolMan_Interface): 554b8cb5db159f001e2cf9c41d9619f2 \n\n- User (Dummy Change 2022 User): 53a1f8b11b188d5039f811739b4bcb69 \n\n\r\n ALDISolManChangeInterface.isChangeRequestSolManInterface(changeRequestSysId) encapsulates this property-based validation. \n\r\n Change Model–based identification (SolMan Integration stories) \n\r\n With the SolMan Integration work (stories STRY0669841, STRY0682952, STRY0684587 and STRY0669846) the primary identifier for SolMan-managed changes is now the Change Model plus a correlation tag, rather than the assignment group alone: \n\r\n \n- change_request.correlation_display = \"SolMan\" \n\n- change_request.model is one of: \r\n \n- SolMan Normal → Normal SolMan changes. \n\n- SolMan Emergency → Emergency SolMan changes. \n\n- Standard → OOTB Standard model used for SolMan-driven standard changes. \n\n\r\n\n\r\n A one-off Scheduled Script Execution is used as a deployment step to migrate existing data: \n\r\n \n- Query active Change Requests where: \r\n \n- Assignment group is in aldi.sap.solman.webservice.change.outboundAssignmentGroup (list of SolMan groups), and \n\n- Assigned to equals aldi.sap.solman.change.assigned.to . \n\n\r\n\n- Set correlation_display = \"SolMan\" . \n\n- Set the Model based on the Change Request type: \r\n \n- Normal → SolMan Normal \n\n- Emergency → SolMan Emergency \n\n- Standard → Standard (OOB Standard model) and cancel any running legacy Change Management workflows via Workflow.cancel(current) . \n\n\r\n\n\r\n The same script also normalises Standard Change Templates ( std_change_template ) by: \n\r\n \n- Removing hard-coded SolMan assignment values. \n\n- Setting correlation_display = \"SolMan\" and model = Standard . \n\n\r\n After this migration, new and existing SolMan changes can be detected reliably using the Change Model and correlation_display , which is what the newer interface triggers and state-model logic rely on. \n\r\n 6.2 Outbound Triggers (ServiceNow → SolMan) \n\r\n For the purposes of the rules below, a SolMan-managed Change Request is one whose correlation/model identify it as SolMan (see 6.1). Older filters based purely on assignment group and user remain in some business rules for backward compatibility but are no longer the primary trigger mechanism. \n\r\n \n- Change Request (after): fires on coordinator/demand/priority/release changes (excluding some terminal states) for SolMan-managed CRs with at least one active change task. \n\n- Change Task (after): fires on key field updates, while state remains Pending ( -5 ); excludes updates performed by interface.solman to prevent loops. \n\n- Incident (after): fires when the rfc reference is updated; triggers re-sync for affected CR. \n\n- Problem-Change m2m (after): fires on insert/delete of CR link for a Problem; triggers CR update. \n\n\r\n All these call: new ALDIIntegrationFrameworkUtil().triggerInterfaces(record, operation) . \n\r\n SolMan Normal Change Model (STRY0669841) \n\r\n The SolMan Normal Change Model defines the end-to-end state machine for normal SolMan changes: \n\r\n \n- States: New → Assess → Build → Test → Authorize → Scheduled → Deploy → Review → Closed / Canceled . \n\n- Key transition conditions: \r\n \n- Build → Test – Check Risk Assessment \n Requires at least one completed task_assessment of type Change Risk Management for the Change ( ALDISolManChangeInterface.hasRiskAssessment ). \n\n- Test → Authorize – Check Change Tasks \n If there is at least one Change Task, every task must have u_cd_state in the configured \"successfully tested\" states (for example PRE-PRD / Imported into PRE / Withdrawn). \n\n- Authorize → Scheduled – Check Approval / Approved by CAB \n All Change Tasks must be approved; CAB approval drives the Authorize → Scheduled transition. \n\n- Authorize → New – Rejected by CAB \n CAB rejection drives the Authorize New transition. \n\n\r\n\n\r\n These model-level checks implement the acceptance criteria that SolMan changes must be fully tested and approved before moving to Authorize/Scheduled , and they gate when outbound SolMan interface calls are allowed. \n\r\n SolMan Emergency Change Model (STRY0682952) \n\r\n The SolMan Emergency Change Model mirrors the Normal model but for Emergency changes: \n\r\n \n- States: New (initial) → Assess → Build → Test → Authorize → Scheduled → Deploy → Review → Closed / Canceled . \n\n- Transitions cover all paths between these states (New/Assess/Build/Test/Authorize/Scheduled/Deploy/Review plus Canceled) and reuse the same family of transition conditions: \r\n \n- Check Assessment , Check Change Tasks , Check Approval , Approved by CAB , Rejected by CAB . \n\n\r\n\n\r\n This model is used for Change Requests whose type is Emergency and whose model is set to SolMan Emergency . Outbound SolMan triggers effectively see the same gating behaviour as for normal SolMan changes. \n\r\n Change Request Interceptor and Standard / Direct-to-Change Models (STRY0684587) \n\r\n To ensure all relevant entry points route through Change Models: \n\r\n \n- The Change Request interceptor ( sys_wizard ) has been migrated to the new UI and now redirects to sn_chg_model_ui_landing.do . \n\n- The legacy 'Direct to Normal/Standard/Emergency Change' interceptor answers are deactivated. \n\n- New Normal and Emergency Change Models have been created for: \r\n \n- New / modify / delete Configuration Item variants in each type. \n\n\r\n\n- The global New Change Request UI actions (list and related list) now simply redirect to sn_chg_model_ui_landing.do . \n\n\r\n As a result, creation of SolMan-related Change Requests always goes through a Change Model, guaranteeing that the model field is populated and that the state machine and SolMan interface triggers described above apply consistently. \n\r\n 6.3 Payload Construction \n\r\n ALDIIntegrationFrameworkUtil.generatePayload(record, triggerRule, attachment, transactionGr) : \n\r\n \n- Builds payload.interfaceConfig by reading active fields on u_aldi_interface_trigger_condition . \n\n- Builds payload.ticketData . \n\n- If u_flow_action is set: runs the specified Flow Action with inputs {triggerconditiongr, currentgr} ; expects outputs.payload (JSON) and outputs.statuscode = success . \r\n \n- For CR: 'Flow Action - ALDI SolMan Get Payload for Change Request'. \n\n- For CTASK: 'Flow Action - ALDI SolMan Get Payload for Change Task'. \n\n\r\n\n- Else: resolves configured u_fields and u_manual_fields to produce a key-value map (dot-walked values replaced with _ in the key). \n\n- Adds last work_note/comments when flags set and values changed. \n\n- Optionally attaches one or all attachments (base64) with size limits. \n\n- Logs request body to u_aldi_interface_transaction . \n\n- Submits to REST endpoint depending on instance_name and triggerRule 's environment bindings. \n\n\r\n 6.4 Change Task Closure and CR State Progression \n\r\n On change task update (async BR): \n\r\n \n- ALDISolManChangeInterface.updateChangeRequestOnTaskUpdate(currentChangeTaskSysId) \r\n \n- If u_cd_state transitions to Confirmed or Withdrawn , set task state = 3 (Closed) and update. \n\n- If all tasks under the parent CR are closed and CR type is in [normal, emergency] : \r\n \n- Set CR approval = approved . \n\n- Move CR state to Review (0) . \n\n\r\n\n\r\n\n\r\n 6.5 Inbound Change Task Update (SolMan → ServiceNow) \n\r\n \n- Endpoint: POST /api/aldie/solman/change/task \n\n- Handler: Scripted REST Operation 'Change Task | Post' delegates to ALDISolManChangeInterface.updateChangeTaskFromAPI(headers, queryParams, body) . \n\n- Mandatory request fields: \r\n \n- number , sys_id , short_description , u_cd_state , u_cd_number \n\n\r\n\n- Optional fields handled: \r\n \n- description , u_cd_transport_request , u_cd_url , u_cd_actual_start_date , u_cd_actual_end_date \n\n- cr_u_developer , cr_u_change_coordinator , cr_u_technical_change_manager → mapped to sys_user via u_ad_upn . \n\n\r\n\n- Success response: \r\n \n- HTTP 202, JSON: { status: \"Success\", details: \"…updated successfully…\", sys_id: \"…\", code: \"202\" } \n\n\r\n\n- Failure responses: \r\n \n- HTTP 400 for missing mandatory fields (helpful concatenated message). \n\n- HTTP 500 when handler returns null or other runtime exceptions. \n\n\r\n\n- All inbound calls are logged to u_aldi_interface_transaction (request, response, code, error). \n\n\r\n 7. Data and Field Mapping \n\r\n 7.1 Outbound Change Task (payload.ticketData) – representative fields \n\r\n Generated by ALDISolManChangeInterface.getOneChangeTaskJson(triggerConditionGr, crTaskGr) : \n\r\n \n- Task level \r\n \n- number (CTASK…) \n\n- sys_id \n\n- short_description , description \n\n- due_date (YYYY-MM-DD; time removed if present) \n\n- u_change_subtype \n\n- u_application (code) \n\n- u_scope (code) \n\n- business_service (display value) \n\n- u_cd_number \n\n- u_system_integrator (display value) \n\n\r\n\n- Parent Change Request (prefixed with cr_ ) \r\n \n- cr_number (CHG…) \n\n- cr_priority \n\n- cr_u_demand (via change_request.parent.parent , display) \n\n- cr_u_release (display) and cr_u_release_short_description \n\n- cr_u_developer ( u_ad_upn ) \n\n- cr_u_technical_change_manager ( u_ad_upn ) \n\n- cr_u_change_coordinator ( u_ad_upn ) \n\n- cr_u_implementation_partner ( u_ad_upn ) \n\n- cr_u_story ( change_request.parent.number ) \n\n- cr_u_epic ( change_request.parent.parent_work_item.number ) \n\n- cr_u_epic_sys_id ( change_request.parent.parent_work_item.sys_id ) \n\n\r\n\n- Related items \r\n \n- cr_u_incident : First Incident linked by RFC field (active prioritized). \n\n- cr_u_problem : First Problem from u_m2m_problems_change_requests (display). \n\n\r\n\n\r\n 7.2 Inbound Change Task (POST /change/task) – field handling \n\r\n \n- Writes to change_task : \r\n \n- short_description (mandatory) \n\n- description (optional) \n\n- u_cd_state (mandatory) \n\n- u_cd_number (mandatory) \n\n- u_cd_transport_request (optional) \n\n- u_cd_url (optional) \n\n- u_cd_actual_start_date (optional) \n\n- u_cd_actual_end_date (optional) \n\n- u_developer , u_change_coordinator , u_technical_change_manager via getUser(u_ad_upn) \n\n\r\n\n\r\n 8. Logging \n\r\n \n- Transaction logging: u_aldi_interface_transaction captures interface trigger, target endpoint, request/response, HTTP code, error message, and associated data record. \n\n- Inbound logging: ALDISolManChangeInterface.logRestScriptedCall writes the Scripted REST call inputs and outcome into the same table. \n\n- Loop prevention: All outbound BRs exclude sys_updated_by LIKE interface.solman to avoid echoing inbound updates back out. \n\n- Idempotency: Inbound handler updates a specific task by sys_id ; Business Rules focus on value changes ( VALCHANGES / CHANGESTO ) for outbound. \n\n\r\n 9. Security and Access \n\r\n \n- Outbound: Parent REST Message enforces mutual TLS to Conigma in PROD. Ensure certificates are properly installed and attached to the REST Message. \n\n- Inbound: Scripted REST API requires authentication and enforces ACL ( b7b63e761b89499034b7dceacd4bcb6d ) and SNC internal role. Ensure the integration user has the required role(s) and table access for change_task updates. \n\n- Integration user: interface.solman (used for inbound updates). Outbound BRs explicitly exclude this user from triggering. \n\n- Properties: Do not log sensitive secrets; leverage sys_properties and Connection & Credential aliases where applicable. \n\n\r\n 10. Testing and Validation \n\r\n 10.1 Inbound – Change Task Update \n\r\n Request (example): \n\r\n POST https:///api/aldie/solman/change/task\r\nContent-Type: application/json\r\nAuthorization: Bearer \r\n \r\n {\r\n \"number\": \"CTASK0012345\",\r\n \"sys_id\": \"\",\r\n \"short_description\": \"Deploy transport CD12345\",\r\n \"u_cd_state\": \"Confirmed\",\r\n \"u_cd_number\": \"CD12345\",\r\n \"u_cd_transport_request\": \"TRK900123\",\r\n \"u_cd_url\": \"https://solman/...\",\r\n \"u_cd_actual_start_date\": \"2025-08-22 08:00:00\",\r\n \"u_cd_actual_end_date\": \"2025-08-22 10:30:00\",\r\n \"cr_u_developer\": \"developer@aldi.com\",\r\n \"cr_u_change_coordinator\": \"coordinator@aldi.com\",\r\n \"cr_u_technical_change_manager\": \"tcm@aldi.com\"\r\n}\r\n \r\n Expected: \n\r\n \n- HTTP 202 on success; change_task updated; task closed if u_cd_state in { Confirmed , Withdrawn }; CR moved to Review if all tasks closed and type ∈ { normal , emergency }. \n\n- Transaction logged in u_aldi_interface_transaction . \n\n\r\n 10.2 Outbound – Change Request/Task \n\r\n \n- Precondition: CR is assigned to the configured SolMan group and user; CR has at least one active change task. \n\n- Perform changes on fields listed in BR filters (e.g., u_change_coordinator , u_demand , priority , u_release , etc. for CR; key fields for CTASK; Incident rfc or Problem-Change link). \n\n- Validate: u_aldi_interface_transaction captures outbound call with resolved endpoint and request body. Verify Conigma response and status code. \n\n\r\n 11. Deployment and Configuration Steps \n\r\n Use the steps below only for: \n\r\n \n- Optional, non-invasive production verification \n\n- Future changes or re-deployments (reference) \n\n\r\n Optional verification (non-invasive): \n\r\n \n- Ensure Properties are set (section 4) and match the actual group/user sys_ids used in BRs. \n\n- Confirm Scripted REST API is active and ACLs/roles are configured for the integration user. \n\n- Validate REST Message and child functions for PROD; run connection tests only and ensure certificates for Mutual TLS are installed and valid. \n\n- Review u_aldi_interface_trigger_condition records: \r\n \n- u_flow_action (if used) is set to the appropriate Flow Action: \r\n \n- Change Request: 'Flow Action - ALDI SolMan Get Payload for Change Request' \n\n- Change Task: 'Flow Action - ALDI SolMan Get Payload for Change Task' \n\n\r\n\n- Environment bindings ( u_base_endpoint_dev/test/qa/prod ) are accurate and point to the correct REST Message + Function. \n\n- u_endpoint is populated and correct. \n\n- u_fields / u_manual_fields reflect all required payload attributes. \n\n- Attachment flags and limits align with expectations. \n\n\r\n\n\r\n Reference deployment checklist (for future changes): \n\r\n \n- Ensure Properties are set (section 4) and match the actual group/user sys_ids used in BRs. \n\n- Confirm Scripted REST API is active and ACLs/roles are configured for the integration user. \n\n- Validate REST Message and child functions for each environment; ensure certificates for Mutual TLS are installed and connection tests pass. \n\n- Review u_aldi_interface_trigger_condition records and ensure u_flow_action references the correct Flow Action(s) as above. \n\n- Migrate and commit Update Sets containing the above records; re-run tests in the target environment. \n\n\r\n 12. Troubleshooting \n\r\n \n- Outbound calls not firing: \r\n \n- Check that CR/CTASK meet SolMan group/user filter and state criteria. \n\n- Confirm ALDISolManChangeInterface.isChangeRequestValidToSync returns true (at least one active change task). \n\n- Ensure updates are not performed by interface.solman (excluded by BR). \n\n\r\n\n- Outbound request/response issues: \r\n \n- Inspect u_aldi_interface_transaction for request body, status code, and response. \n\n- Verify REST Message function resolves to correct endpoint by instance_name and that rest_uri is set. \n\n- Check certificate bindings for Mutual TLS. \n\n\r\n\n- Inbound failures: \r\n \n- Check Scripted REST API authentication and ACLs. \n\n- Validate mandatory fields are present ( number , sys_id , short_description , u_cd_state , u_cd_number ). \n\n- Review syslog and u_aldi_interface_transaction for detailed errors. \n\n\r\n\n- CR not moving to Review: \r\n \n- Confirm all tasks are closed ( state = 3 ) and CR type is normal/emergency . \n\n- Validate async BR fired and ALDISolManChangeInterface.updateChangeRequestOnTaskUpdate executed. \n\n\r\n\n\r\n 13. Governance and Operations \n\r\n \n- Daily checks: Review u_aldi_interface_transaction for failures; monitor syslog for aldi/solman errors. \n\n- Change control: Keep BR filters ( sys_ids ) synchronized with property values; avoid drift when user/group records change. \n\n- Payload evolution: Prefer Flow Action output for complex payloads. Keep aldi.sap.solman.ticket.data.error.json updated for consistent fallback messaging. \n\n\r\n 14. Appendices \n\r\n 14.1 Key sys_ids and Names (quick reference) \n\r\n Item Value \n Group (Trigger_SNow2SolMan_Interface) 554b8cb5db159f001e2cf9c41d9619f2 \n User (Dummy Change 2022 User) 53a1f8b11b188d5039f811739b4bcb69 \n REST Message → Function → Endpoint ALDI SolMan Interface FrameWork → Conigma PROD → https://conigma.prd.aldi-sued.com/${rest_uri} \n Script Includes ALDISolManChangeInterface (d46079041b18c51034b7dceacd4bcb20) , ALDIIntegrationFrameworkUtil (69b110be1bff3f4034b7dceacd4bcbb6) \n Scripted REST ALDI SolMan (35e59e481bdcc51034b7dceacd4bcb6c) → Change Task | Post (94369acc1bdcc51034b7dceacd4bcb45) \n \n\r\n 14.2 Message Keys observed \n\r\n \n- aldi.solman.change.task.updated.successfully \n\n- aldi.solman.change.task.must.be.pending \n\n- aldi.solman.change.task.must.be.assigned \n\n- aldi.solman.change.task.not.found \n\n- aldi.solman.change.task.state.pending (Client info message) \n\n\r\n 14.3 Notes on Legacy RFC Transfer \n\r\n \n- The three 'Aldi Solman CHG Transfer … RFC' BRs use AldiSoapProcessorSolManChangeInterface and historically controlled SolMan RFC creation/update per Change type. \n\n- Current implementation for 2022 SolMan integration relies on ALDISolManChan geInterfa ce and the ALDIIntegrationFrameworkUtil with Flow Action support and refined BR filters.",
  "work_notes": "",
  "comments": "",
  "state": "3",
  "assignment_group": "Integration Team"
}```

### Várt KB Cikk (Gold Article)
```html
<h2>Overview / Summary</h2>
<h3>Content</h3>
<p>This interface synchronizes SAP-related Change Requests and Change Tasks between ServiceNow and SAP Solution Manager (SolMan). Communication is routed through the Conigma middleware. ServiceNow sends change and task information to SolMan, while SolMan returns technical deployment status and transport details.</p>
<p>The integration is used for changes managed through the SolMan process, including normal and emergency change models. A record is synchronized only when it meets the configured SolMan identification and trigger conditions.</p>
<ul style="list-style-position: inside;"><li>Interface: Bidirectional REST integration between ServiceNow and SolMan through Conigma.</li><li>Users: Change Management process users, SAP Solution Manager, integration operators, and support teams.</li><li>Outbound data: Change Request attributes such as coordinator and priority, together with Change Task details such as description, CD state and transport request.</li><li>Inbound data: Change Task status, CD state, actual start and end dates, and transport information.</li></ul>
<p>Outbound processing starts from ServiceNow Business Rules. ALDIIntegrationFrameworkUtil evaluates the trigger configuration, generates the payload and sends the request to Conigma. Inbound updates are received through POST /api/aldie/solman/change/task and processed by ALDISolManChangeInterface.</p>
<h3>Related KB articles</h3>
<p>The following articles were returned as related content. Their relevance should be reviewed before they are linked from the published article.</p>
<ul style="list-style-position: inside;"><li><a href="https://aldiprod.service-now.com/kb_view.do?sysparm_article&#61;KB0038409" target="_blank" aria-label="KB0038409 - Open record: KB0038409 v6.0" rel="noopener noreferrer nofollow">KB0038409</a> - C&amp;D: SAP - SolMan (Solution Manager) or ChaRM(Change Request Management) incident</li><li><a href="https://aldiprod.service-now.com/kb_view.do?sysparm_article&#61;KB0041535" target="_blank" aria-label="KB0041535 - Open record: KB0041535 v5.0" rel="noopener noreferrer nofollow">KB0041535</a>  - OpH - Application - ALM (SAP SolMan)</li><li><a href="https://aldiprod.service-now.com/kb_view.do?sysparm_article&#61;KB0044855" target="_blank" aria-label="KB0044855 - Open record: KB0044855 v2.0" rel="noopener noreferrer nofollow">KB0044855</a>  - C&amp;D: SAP Solution Manager (SolMan) interface issue in ServiceNow</li><li><a href="https://aldiprod.service-now.com/kb_view.do?sysparm_article&#61;KB0018578" target="_blank" aria-label="KB0018578 - Open record: KB0018578 v14.0" rel="noopener noreferrer nofollow">KB0018578</a>  - C&amp;D: Solution Manager/SolMan/SM1 is not working</li><li><a href="https://aldiprod.service-now.com/kb_knowledge.do?sys_id&#61;82c6e4073b40e250754c454a85e45ad0&amp;sysparm_record_target&#61;kb_knowledge&amp;sysparm_record_row&#61;5&amp;sysparm_record_rows&#61;5&amp;sysparm_record_list&#61;workflow_state%3Dpublished%5Esys_class_name%21%3Dkb_knowledge_block%5Eshort_descriptionCONTAINSsolman%5EORDERBYsys_updated_on%5EORDERBYsys_id" target="_blank" aria-label="KB0041670 - Open record: KB0041670 v2.0" rel="noopener noreferrer nofollow">KB0041670</a>  - C&amp;D: Technical issue in Solution Manager (SolMan) or issues with interface between SolMan and SNow</li></ul>
<h2>Inbound Technical Implementation</h2>
<h3>Content</h3>
<p>Conigma sends Change Task updates to the ALDI SolMan Scripted REST API. The resource delegates processing to ALDISolManChangeInterface.updateChangeTaskFromAPI(), which validates the request and updates the matching change_task record.</p>
<ul style="list-style-position: inside;"><li>Scripted REST service: ALDI SolMan</li><li>Base path: /api/aldie/solman</li><li>Resource: Change Task | Post</li><li>Endpoint: POST /change/task</li><li>Handler: ALDISolManChangeInterface.updateChangeTaskFromAPI()</li></ul>
<h3>Required parameters</h3>
<ul style="list-style-position: inside;"><li>number - Change Task number</li><li>sys_id - Change Task sys_id</li><li>short_description</li><li>u_cd_state - CD state</li><li>u_cd_number - CD number</li></ul>
<h3>Payload sample</h3>
<pre>{
  &#34;number&#34;: &#34;CTASK0012345&#34;,
  &#34;sys_id&#34;: &#34;&#34;,
  &#34;short_description&#34;: &#34;Deploy transport CD12345&#34;,
  &#34;u_cd_state&#34;: &#34;Confirmed&#34;,
  &#34;u_cd_number&#34;: &#34;CD12345&#34;,
  &#34;u_cd_transport_request&#34;: &#34;TRK900123&#34;,
  &#34;u_cd_url&#34;: &#34;<a href="https://solman/" rel="nofollow">https://solman/</a>...&#34;,
  &#34;u_cd_actual_start_date&#34;: &#34;2025-08-22 08:00:00&#34;,
  &#34;u_cd_actual_end_date&#34;: &#34;2025-08-22 10:30:00&#34;,
  &#34;cr_u_developer&#34;: &#34;developer&#64;aldi.com&#34;,
  &#34;cr_u_change_coordinator&#34;: &#34;coordinator&#64;aldi.com&#34;,
  &#34;cr_u_technical_change_manager&#34;: &#34;tcm&#64;aldi.com&#34;
}</pre>
<h3>Flow and validation</h3>
<ol style="list-style-position: inside;"><li>The Scripted REST API authenticates the caller and checks access through the configured SNC internal role.</li><li>The handler verifies the mandatory request values. Missing mandatory data results in an HTTP 400 response.</li><li>The target Change Task is identified and the supplied CD, transport and date values are applied.</li><li>User values such as cr_u_developer are resolved against ServiceNow users by UPN.</li><li>If the CD state becomes <em>Confirmed</em> or <em>Withdrawn</em>, follow-up logic may close the task. When all applicable tasks are closed, the parent Change Request can move to Review.</li></ol>
<p>Inbound access is controlled by bearer-token authentication and the related ACL with sys_id.</p>
<h2>Outbound Technical Implementation</h2>
<h3>Content</h3>
<p>Outbound synchronization is triggered by Business Rules on eligible Change Requests and Change Tasks. The implementation uses the common ALDI Integration Framework for trigger evaluation, payload generation, routing and transaction logging.</p>
<h3>Technical components</h3>
<ul style="list-style-position: inside;"><li>ALDISolManChangeInterface: SolMan-specific validation, payload construction and inbound update logic.</li><li>ALDIIntegrationFrameworkUtil: Generic trigger handling, payload generation and REST dispatch.</li><li>ALDI Interface SolMan Change Request: Handles relevant Change Request updates.</li><li>ALDI Interface SolMan Change Task: Handles relevant Change Task updates while the task is in Pending state (-5).</li><li>ALDI SolMan async CD or ChTask State upd: Updates the parent request after a task CD state changes to Confirmed or Withdrawn.</li><li>REST Message: ALDI SolMan Interface FrameWork, using the Conigma PROD function and <a href="https://conigma.prd.aldi-sued.com/$" rel="nofollow">https://conigma.prd.aldi-sued.com/$</a>{rest_uri}.</li></ul>
<h3>Dependencies and authentication</h3>
<p>Routing is configured through u_aldi_interface_trigger_condition records and their environment-specific REST endpoints. Payload generation can use a referenced u_flow_action; if no Flow Action is configured, the framework falls back to the u_fields mapping.</p>
<p>Outbound requests use mutual TLS configured on the parent REST Message. The required certificate must be installed, valid and bound to the REST Message.</p>
<h3>Validation steps</h3>
<ul style="list-style-position: inside;"><li>Confirm that the Change Request is SolMan-managed, including the expected model and correlation_display &#61; &#39;SolMan&#39;.</li><li>Confirm that the Change Request has at least one active Change Task.</li><li>Check that a monitored field has changed and the corresponding Business Rule conditions are satisfied.</li><li>Updates made by interface.solman are excluded to prevent an inbound update from triggering another outbound call.</li></ul>
<h2>How to Use the Interface</h2>
<h3>Content</h3>
<p>No manual action is normally required for outbound synchronization. Use an eligible SolMan Change Model, such as <em>SolMan Normal</em> or <em>SolMan Emergency</em>, and make sure the record meets the configured assignment and trigger criteria.</p>
<h3>Outbound</h3>
<ol style="list-style-position: inside;"><li>Create or update an eligible Change Request and ensure that it has an active Change Task.</li><li>Update a monitored field, for example the change coordinator, priority or a relevant task field.</li><li>Open u_aldi_interface_transaction and check the latest outbound transaction.</li><li>Verify the target endpoint, payload and Conigma response.</li></ol>
<h3>Inbound</h3>
<ol style="list-style-position: inside;"><li>SolMan or Conigma sends the Change Task payload to /api/aldie/solman/change/task.</li><li>ServiceNow validates the request, resolves user references and updates the Change Task.</li><li>Check the Change Task for the received CD state, CD number, dates and transport information.</li><li>If the final applicable task is closed, verify the resulting state of the parent Change Request.</li></ol>
<p>A successful call is recorded in u_aldi_interface_transaction. The transaction record contains the endpoint, request, response and HTTP status used for operational verification.</p>
<h2>Testing Guide</h2>
<h3>Content</h3>
<h3>Outbound scenarios</h3>
<ul style="list-style-position: inside;"><li>Update the coordinator or priority of an eligible SolMan Change Request.</li><li>Update a monitored field on a Change Task in Pending state (-5).</li><li>Verify that the generated payload contains the expected values and is sent to the correct environment.</li></ul>
<h3>Inbound scenarios</h3>
<ul style="list-style-position: inside;"><li>Send a valid request with CD state <em>Confirmed</em>.</li><li>Send a request with one mandatory value omitted and verify that it is rejected.</li><li>Send user UPN values and verify that they resolve to the expected ServiceNow users.</li></ul>
<h3>Suggested test data</h3>
<ul style="list-style-position: inside;"><li>Change Request model: <em>SolMan Normal</em></li><li>Assigned user: <em>Dummy Change User</em></li><li>Assignment group: <em>Trigger_SNow2SolMan_Interface</em></li><li>Linked Change Task state: <em>Pending</em> (-5)</li></ul>
<h3>Test procedure</h3>
<ol style="list-style-position: inside;"><li>Update u_change_coordinator on the test Change Request.</li><li>Check u_aldi_interface_transaction for the outbound request and response.</li><li>Send a valid JSON request to the inbound endpoint.</li><li>Verify that u_cd_state, u_cd_number and the supplied transport data were updated.</li><li>Review syslog if the expected transaction or record update is missing.</li></ol>
<h2>Known Issues</h2>
<h3>Content</h3>
<h3>Outbound synchronization is not triggered</h3>
<p>Symptoms: No transaction is created after an apparently valid Change Request or Change Task update.</p>
<p>Likely cause: The record no longer meets the SolMan identification criteria, no active Change Task exists, or the updated field is not part of the configured trigger.</p>
<p>Diagnostic steps: Check the model, correlation_display, active tasks, Business Rule conditions and ALDISolManChangeInterface.isChangeRequestValidToSync().</p>
<p>Resolution: Correct the record or trigger configuration. Legacy records may require verification or migration to the current Change Model.</p>
<p>Prevention: Keep model and trigger configuration aligned across environments and include eligibility checks in regression testing.</p>
<h3>Outbound transaction fails</h3>
<p>Symptoms: A transaction exists, but Conigma does not accept the request or the connection fails.</p>
<p>Likely cause: Incorrect environment routing, endpoint availability, or an expired or incorrectly bound mutual TLS certificate.</p>
<p>Diagnostic steps: Review the endpoint, payload, response and HTTP status in u_aldi_interface_transaction. Check the certificate configuration on the parent REST Message.</p>
<p>Resolution: Correct the endpoint or certificate binding. Engage the Network/Security team for connectivity and mutual TLS problems.</p>
<p>Prevention: Monitor certificate expiry and verify environment-specific routing after deployments or clones.</p>
<h3>Inbound update is rejected or fails</h3>
<p>Symptoms: The caller receives an error and the Change Task is not updated.</p>
<p>Likely cause: A mandatory field is missing, authentication or role validation fails, or a supplied UPN cannot be mapped.</p>
<p>Diagnostic steps: Review u_aldi_interface_transaction and syslog. Compare the request with the mandatory field list and verify user records.</p>
<p>Resolution: Correct the source payload, access configuration or user mapping. Do not bypass request validation in the Scripted REST resource.</p>
<p>Prevention: Validate payloads in the source system and maintain the required integration user access and UPN data.</p>
<h2>Investigation Steps</h2>
<h3>Content</h3>
<p>Use this guide when SolMan data is out of sync, an expected transaction is missing, or an interface call returns an error.</p>
<ol style="list-style-position: inside;"><li>Identify the direction. Determine whether the failing flow is outbound from ServiceNow or inbound from SolMan.</li><li>Locate the transaction. Search u_aldi_interface_transaction using the Change Request or Change Task number and review the latest request, response and HTTP status.</li><li>For outbound issues, verify eligibility. Check the Change Model, correlation_display, active tasks, changed fields and Business Rule conditions.</li><li>For outbound connection issues, verify routing and mutual TLS. Confirm the selected endpoint, certificate validity and Conigma availability.</li><li>For inbound issues, verify the request. Check mandatory values, bearer-token access, ACL/role configuration and UPN mappings.</li><li>Review application logs. Check syslog for messages associated with aldi.solman and for errors raised by the Script Includes.</li><li>Reproduce safely. Use a non-production test record and repeat the smallest update that should trigger the interface.</li></ol>
<h3>Key components</h3>
<ul style="list-style-position: inside;"><li>ALDIIntegrationFrameworkUtil - <a href="https://aldidev.service-now.com/now/nav/ui/classic/params/target/sys_script_include.do%3Fsys_id%3D69b110be1bff3f4034b7dceacd4bcbb6%26sysparm_record_target%3Dsys_script_include%26sysparm_record_row%3D1%26sysparm_record_rows%3D2%26sysparm_record_list%3DnameSTARTSWITHALDIIntegrationFrameworkUtil%255Ename%2521%253DSNCAPICallWrapper%255EORDERBYname" rel="nofollow">ALDIIntegrationFrameworkUtil | Script Include | SNOW | DEV</a> </li><li>ALDISolManChangeInterface - <a href="https://aldidev.service-now.com/now/nav/ui/classic/params/target/sys_script_include.do%3Fsys_id%3Dd46079041b18c51034b7dceacd4bcb20%26sysparm_record_target%3Dsys_script_include%26sysparm_record_row%3D1%26sysparm_record_rows%3D1%26sysparm_record_list%3DnameSTARTSWITHALDISolManChangeInterface%255Ename%2521%253DSNCAPICallWrapper%255EORDERBYname" rel="nofollow">ALDISolManChangeInterface | Script Include | SNOW | DEV</a> </li><li>Change Task | Post Scripted REST resource - <a href="https://aldidev.service-now.com/now/nav/ui/classic/params/target/sys_ws_operation.do%3Fsys_id%3D94369acc1bdcc51034b7dceacd4bcb45%26sysparm_record_target%3Dsys_ws_operation%26sysparm_record_row%3D1%26sysparm_record_rows%3D1%26sysparm_record_list%3DnameSTARTSWITHChange%2BTask%255EORDERBYname" rel="nofollow">Change Task | Post | Scripted REST Resource | SNOW | DEV</a> </li><li>u_aldi_interface_trigger_condition - <a href="https://aldidev.service-now.com/now/nav/ui/classic/params/target/u_aldi_interface_trigger_condition_list.do%3Fsysparm_filter_pinned%3Dtrue%26sysparm_query%3D" rel="nofollow">ALDI Interface Trigger Conditions | SNOW | DEV</a> </li><li>u_aldi_interface_transaction - <a href="https://aldidev.service-now.com/now/nav/ui/classic/params/target/u_aldi_interface_transaction_list.do%3Fsysparm_filter_pinned%3Dtrue%26sysparm_query%3D" rel="nofollow">ALDI Interface Transactions | SNOW | DEV</a> </li></ul>
<h3>Escalation</h3>
<ul style="list-style-position: inside;"><li>Engage Network/Security for endpoint connectivity, firewall or mutual TLS certificate problems.</li><li>Engage the ALDI Integration team for trigger, payload, mapping or Script Include logic problems.</li><li>Provide the transaction record, timestamp, affected record number, environment and relevant system log entries with the escalation.</li></ul>
```
