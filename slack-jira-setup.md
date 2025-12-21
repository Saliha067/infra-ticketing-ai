# Slack & JIRA Setup Guide

## Slack App Setup

### Step 1: Create a Slack App
1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"**
3. Choose **"From scratch"**
4. Name: `Infrastructure Bot`
5. Select your workspace

### Step 2: Enable Socket Mode
1. In app settings → **Socket Mode**
2. Toggle **"Enable Socket Mode"** to ON
3. Name: `InfraBot Socket`
4. Copy the token starting with `xapp-` → This is your **SLACK_APP_TOKEN**

### Step 3: Configure Bot Scopes
1. Go to **"OAuth & Permissions"**
2. Scroll to **"Scopes"** → **"Bot Token Scopes"**
3. Add these scopes:
   - `app_mentions:read`
   - `channels:history`
   - `channels:read`
   - `chat:write`
   - `commands`
   - `im:history`
   - `im:read`
   - `im:write`
   - `users:read`
   - `conversations.open`
4. Scroll up and click **"Install to Workspace"**
5. Authorize the app
6. Copy the **"Bot User OAuth Token"** starting with `xoxb-` → This is your **SLACK_BOT_TOKEN**

### Step 4: Create Slash Commands
1. Go to **"Slash Commands"**
2. Click **"Create New Command"** for each:

**Command 1:**
- Command: `/infra-inquiry`
- Request URL: _(leave empty - Socket Mode handles this)_
- Short Description: `Submit infrastructure inquiry`
- Usage Hint: `[your question]`

**Command 2:**
- Command: `/infra-metrics`
- Request URL: _(leave empty)_
- Short Description: `View infrastructure inquiry metrics`
- Usage Hint: `[today|week|month|all]`

3. Click **"Save"** for each

### Step 5: Enable Event Subscriptions
1. Go to **"Event Subscriptions"**
2. Toggle **"Enable Events"** to ON
3. Under **"Subscribe to bot events"**, add:
   - `app_mention`
   - `message.im`
4. Click **"Save Changes"**

### Step 6: Update .env File
Edit your `.env` file with your tokens:
```env
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_APP_TOKEN=xapp-your-token-here
```

### Step 7: Start the Bot
```bash
python src/main.py
```

---

## JIRA Setup

### Step 1: Create Free Atlassian JIRA Account
1. Go to: [https://www.atlassian.com/try/cloud/signup?product=jira-software](https://www.atlassian.com/try/cloud/signup?product=jira-software)
2. Sign up with your email
3. Create a site name (e.g., `your-name-test.atlassian.net`)
4. Choose **Jira Software** (free for up to 10 users)
5. Skip team invitation

### Step 2: Generate API Token
1. Go to: [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **"Create API token"**
3. Label: `Infrastructure Bot`
4. Click **Create**
5. **Copy the token immediately** (you can't see it again!)

### Step 4: Get Your Project Key
In your JIRA project, check the URL:
```
https://your-site.atlassian.net/jira/software/projects/INFRA/boards/1
                                                          ^^^^^^
                                                      Project Key
```

### Step 5: Update .env File
Add JIRA credentials to `.env`:
```env
JIRA_URL=https://your-site.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token-here
JIRA_PROJECT_KEY=INFRA
```

### Step 6: Restart Bot
```bash
python src/main.py
```

---

## Testing

### Test Slack Commands
```
/infra-inquiry How to restart a Kubernetes pod?
/infra-metrics today
/infra-metrics week
```

### Verify JIRA Integration
1. Submit an inquiry that requires team action
2. Check your JIRA project for the created ticket
3. Verify ticket has correct:
   - Summary
   - Description
   - Team label
   - Priority



